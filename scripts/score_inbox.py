"""Score the data-quality inbox against the problems the generator planted.

    python scripts/score_inbox.py data/demo/planted_errors.json

Recall = planted problems the inbox reported on the right row.
"Not planted" = inbox tasks on rows the generator did not break (likely false alarms).

Caveat: the generator and the inbox were written by the same person, so this is an
upper bound. Real spreadsheets are messier; use it as a regression test, not a claim.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

import psycopg2

SHEET = {"signups": "Sign-ups", "sessions": "Sessions", "attendance": "Attendance",
         "donations": "Donations"}  # fmt: skip
EXPECTED = {
    "missing_dob": {"missing_dob"},
    "duplicate_person": {"possible_duplicate"},
    "session_no_date": {"session_no_date"},
    "attendee_typo": {"attendee_spelling", "attendee_unknown"},
    "attendee_unknown": {"attendee_unknown"},
    "amount_text": {"amount_unreadable"},
}


def main(manifest: str, org: str = "leith_community_sports") -> int:
    with open(manifest) as f:
        planted = json.load(f)
    dsn = os.environ.get(
        "DESTINATION__POSTGRES__CREDENTIALS",
        "postgresql://funderready:funderready@localhost:5432/funderready",
    )
    with psycopg2.connect(dsn) as con, con.cursor() as cur:
        cur.execute(f"select sheet, row_number, issue_type from org_{org}_marts.dq_issues")
        issues = cur.fetchall()

    found: dict[tuple[str, int], set[str]] = defaultdict(set)
    for sheet, row, kind in issues:
        found[(sheet, row)].add(kind)

    totals, hits = Counter(), Counter()
    for p in planted:
        totals[p["type"]] += 1
        if found.get((SHEET[p["sheet"]], p["row"]), set()) & EXPECTED[p["type"]]:
            hits[p["type"]] += 1

    planted_rows = {(SHEET[p["sheet"]], p["row"]) for p in planted}
    extra = [i for i in issues if (i[0], i[1]) not in planted_rows]

    print(f"{'problem':20}{'planted':>8}{'found':>7}")
    for kind in totals:
        print(f"{kind:20}{totals[kind]:>8}{hits[kind]:>7}")
    print(f"{'total':20}{sum(totals.values()):>8}{sum(hits.values()):>7}")
    print(f"inbox tasks: {len(issues)}, on rows with no planted problem: {len(extra)}")
    return 0 if sum(hits.values()) == sum(totals.values()) else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
