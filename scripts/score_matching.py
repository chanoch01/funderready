"""Score duplicate resolution against the synthetic ground truth.

    python scripts/score_matching.py data/demo/truth.json
    python scripts/score_matching.py data/demo/truth.json \
        data/holdout_11/truth.json:holdout_11 data/holdout_23/truth.json:holdout_23

Prints:
  1. for the first (tuning) charity, a threshold sweep: pairwise precision and recall if
     every candidate pair scoring at or above each threshold were merged
  2. for every charity, sign-ups resolved to people (after clustering) and attendance rows
     linked to the right child, plus a pooled line over the holdout charities

Pairwise precision = of the pairs we merged, how many really are the same child.
Pairwise recall    = of the pairs that really are the same child, how many we merged.

Exits non-zero if precision or recall falls below the floors CI enforces, so a change to
the weights or thresholds cannot quietly make matching worse.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from itertools import combinations

import psycopg2

PRECISION_FLOOR = 0.95
RECALL_FLOOR = 0.85


def true_pairs(truth: dict[str, int | None]) -> set[tuple[int, int]]:
    by_child: dict[int, list[int]] = defaultdict(list)
    for row, child in truth.items():
        if child is not None:
            by_child[child].append(int(row))
    return {pair for rows in by_child.values() for pair in combinations(sorted(rows), 2)}


def precision_recall(predicted: set, actual: set) -> tuple[float, float]:
    hits = len(predicted & actual)
    precision = hits / len(predicted) if predicted else 1.0
    recall = hits / len(actual) if actual else 1.0
    return precision, recall


def f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if p + r else 0.0


def score_org(truth_path: str, org: str, cur, verbose: bool) -> dict[str, int]:
    """Counts for one organisation: true/false positives and false negatives."""
    with open(truth_path) as f:
        truth = json.load(f)
    schema = f"org_{org}_intermediate"
    cur.execute(
        f"select row_a, row_b, match_weight, decision from {schema}.int_signup_match_scores"
    )
    rows = cur.fetchall()
    scored = [(a, b, float(w)) for a, b, w, _ in rows]
    to_review = {(a, b) for a, b, _, d in rows if d == "review"}
    cur.execute(f"select row_number, person_id from {schema}.int_signups_resolved")
    resolved = dict(cur.fetchall())
    cur.execute(f"select row_number, person_id from {schema}.int_attendance_matched")
    attendance = dict(cur.fetchall())

    actual = true_pairs(truth["signups"])
    candidates = {(a, b) for a, b, _ in scored}
    if verbose:
        print(f"1. Threshold sweep for {org} (pairwise, before clustering)")
        print(f"   {len(actual)} true duplicate pairs; {len(actual & candidates)} of them "
              f"survive blocking into {len(scored)} candidate pairs")  # fmt: skip
        print(f"   {'threshold':>9} {'merged':>7} {'precision':>10} {'recall':>7} {'F1':>6}")
        for t in range(-4, 31, 2):
            predicted = {(a, b) for a, b, w in scored if w >= t}
            p, r = precision_recall(predicted, actual)
            print(f"   {t:>9} {len(predicted):>7} {p:>10.3f} {r:>7.3f} {f1(p, r):>6.3f}")

    clusters: dict[str, list[int]] = defaultdict(list)
    for row, person in resolved.items():
        clusters[person].append(row)
    predicted = {pair for rows in clusters.values() for pair in combinations(sorted(rows), 2)}

    # Which real child does each person_id stand for? The child behind its earliest row.
    child_of_person = {p: truth["signups"][str(min(rows))] for p, rows in clusters.items()}
    linked = correct = linkable = 0
    for row, person in attendance.items():
        true_child = truth["attendance"][str(row)]
        linkable += true_child is not None
        if person is not None:
            linked += 1
            correct += child_of_person.get(person) == true_child

    counts = {
        "signups": len(resolved),
        "people": len(clusters),
        "children": len(set(truth["signups"].values())),
        "pair_tp": len(predicted & actual),
        "pair_fp": len(predicted - actual),
        "pair_fn": len(actual - predicted),
        "pair_fn_reviewed": len((actual - predicted) & to_review),
        "review_pairs": len(to_review),
        "att_rows": len(attendance),
        "att_linked": linked,
        "att_correct": correct,
        "att_linkable": linkable,
    }
    if verbose:
        print(f"   wrongly merged: {sorted(predicted - actual) or 'none'}")
        print(f"   missed: {sorted(actual - predicted) or 'none'}")
    return counts


def summary(c: dict[str, int]) -> tuple[float, float, float, float]:
    pp = c["pair_tp"] / (c["pair_tp"] + c["pair_fp"]) if c["pair_tp"] + c["pair_fp"] else 1.0
    pr = c["pair_tp"] / (c["pair_tp"] + c["pair_fn"]) if c["pair_tp"] + c["pair_fn"] else 1.0
    ap = c["att_correct"] / c["att_linked"] if c["att_linked"] else 1.0
    ar = c["att_correct"] / c["att_linkable"] if c["att_linkable"] else 1.0
    return pp, pr, ap, ar


def main(*specs: str) -> int:
    """Each spec is truth.json[:org]. The first is the tuning charity and gets the sweep;
    with more than one, the rest are pooled as a holdout and the floors apply to them."""
    specs = specs or ("data/demo/truth.json",)
    dsn = os.environ.get(
        "DESTINATION__POSTGRES__CREDENTIALS",
        "postgresql://funderready:funderready@localhost:5432/funderready",
    )
    results = []
    with psycopg2.connect(dsn) as con, con.cursor() as cur:
        for i, spec in enumerate(specs):
            path, _, org = spec.partition(":")
            org = org or "leith_community_sports"
            results.append((org, score_org(path, org, cur, verbose=i == 0)))

    print("\n2. Sign-ups resolved to people, and attendance rows linked, per charity")
    print(f"   {'charity':24} {'sign-ups':>8} {'people':>7} {'truth':>6} "
          f"{'pair P':>7} {'pair R':>7} {'attend P':>9} {'attend R':>9}")  # fmt: skip
    for org, c in results:
        pp, pr, ap, ar = summary(c)
        print(f"   {org:24} {c['signups']:>8} {c['people']:>7} {c['children']:>6} "
              f"{pp:>7.3f} {pr:>7.3f} {ap:>9.3f} {ar:>9.3f}")  # fmt: skip

    gated = results[1:] or results
    pooled = {k: sum(c[k] for _, c in gated) for k in gated[0][1]}
    pp, pr, ap, ar = summary(pooled)
    label = "pooled holdout" if len(results) > 1 else "tuning charity"
    print(f"   {label:24} {pooled['signups']:>8} {pooled['people']:>7} {pooled['children']:>6} "
          f"{pp:>7.3f} {pr:>7.3f} {ap:>9.3f} {ar:>9.3f}")  # fmt: skip
    print(f"   pairs: {pooled['pair_tp']} right, {pooled['pair_fp']} wrongly merged, "
          f"{pooled['pair_fn']} missed ({pooled['pair_fn_reviewed']} of them sent to the inbox "
          f"for review, out of {pooled['review_pairs']} review tasks)")  # fmt: skip

    ok = min(pp, ap) >= PRECISION_FLOOR and min(pr, ar) >= RECALL_FLOOR
    if not ok:
        print(f"\nFAIL: floors are precision {PRECISION_FLOOR}, recall {RECALL_FLOOR}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
