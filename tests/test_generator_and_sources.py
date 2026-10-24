from __future__ import annotations

import json
from collections import Counter

import httpx
import pytest

from funderready import generator
from funderready.pseudonymise import Pseudonymiser
from funderready.sources import (
    google_sheet_csv_url,
    pseudonymised_records,
    read_csv_file,
    read_csv_text,
    read_google_sheet,
)

P = Pseudonymiser("test-key-0123456789")


def test_generator_is_deterministic_and_messy():
    a, b = generator.generate(seed=3), generator.generate(seed=3)
    assert a.sheets == b.sheets and a.planted == b.planted

    kinds = Counter(p["type"] for p in a.planted)
    for kind in ["missing_dob", "duplicate_person", "attendee_typo", "attendee_unknown"]:
        assert kinds[kind] > 0, kind

    dates = [r["Date"] for r in a.sheets["sessions"] if r["Date"]]
    assert any("/" in d for d in dates) and any("-" in d for d in dates)


def test_planted_rows_point_at_the_right_spreadsheet_rows():
    ds = generator.generate(seed=5)
    for p in ds.planted:
        if p["type"] == "missing_dob":
            assert ds.sheets["signups"][p["row"] - 2]["Date of birth"] == ""
        if p["type"] == "session_no_date":
            assert ds.sheets["sessions"][p["row"] - 2]["Date"] == ""


def test_csv_roundtrip_and_blank_rows_skipped(tmp_path):
    ds = generator.generate(seed=1)
    generator.write(ds, tmp_path)
    rows = list(read_csv_file(tmp_path / "signups.csv"))
    assert len(rows) == len(ds.sheets["signups"])
    assert json.loads((tmp_path / "planted_errors.json").read_text()) == ds.planted

    assert list(read_csv_text("A,B\n1,2\n,\n3,4\n")) == [{"A": "1", "B": "2"}, {"A": "3", "B": "4"}]


def test_no_raw_identifiers_reach_the_records():
    ds = generator.generate(seed=2)
    for sheet in ["signups", "attendance", "donations"]:
        raw = ds.sheets[sheet]
        records = list(pseudonymised_records(sheet, iter(raw), P))
        blob = json.dumps(records)
        for row in raw[:50]:
            for field in ["First name", "Last name", "Attendee", "Parent/carer email",
                          "Customer Email", "Phone"]:  # fmt: skip
                value = row.get(field)
                if value and len(value) > 3:
                    assert value not in blob, (sheet, field)
        assert records[0]["_row_number"] == 2


def test_google_sheet_reader_uses_csv_export_and_rejects_private_sheets():
    def ok(request):
        assert request.url == httpx.URL(google_sheet_csv_url("abc", "7"))
        return httpx.Response(200, text="A,B\n1,2\n", headers={"content-type": "text/csv"})

    rows = list(read_google_sheet("abc", "7", transport=httpx.MockTransport(ok)))
    assert rows == [{"A": "1", "B": "2"}]

    def login_page(request):
        return httpx.Response(
            200, text="<html>sign in</html>", headers={"content-type": "text/html"}
        )

    with pytest.raises(RuntimeError, match="anyone with the link"):
        list(read_google_sheet("abc", transport=httpx.MockTransport(login_page)))


def test_truth_records_the_child_behind_every_row(tmp_path):
    ds = generator.generate(seed=7)
    assert len(ds.truth["signups"]) == len(ds.sheets["signups"])
    assert len(ds.truth["attendance"]) == len(ds.sheets["attendance"])

    # every planted repeat sign-up belongs to the same child as an earlier row
    for p in ds.planted:
        if p["type"] == "duplicate_person":
            child = ds.truth["signups"][p["row"] - 2]
            assert child in ds.truth["signups"][: p["row"] - 2]
        if p["type"] == "attendee_unknown":
            assert ds.truth["attendance"][p["row"] - 2] is None

    generator.write(ds, tmp_path)
    truth = json.loads((tmp_path / "truth.json").read_text())
    assert truth["signups"]["2"] == ds.truth["signups"][0]  # keyed by spreadsheet row


def test_the_hard_cases_for_matching_are_present():
    ds = generator.generate(seed=7)
    rows = ds.sheets["signups"]
    by_carer: dict[str, set[str]] = {}
    for r in rows:
        by_carer.setdefault(r["Parent/carer email"], set()).add(r["First name"].lower())
    # siblings: one carer email, different children
    assert sum(len(names) > 1 for names in by_carer.values()) >= 10
    # repeat sign-ups from the other parent
    assert any(r["Parent/carer email"].endswith(".b@example.org") for r in rows)
    # twins: same carer and date of birth, different child
    seen: dict[tuple[str, str], int] = {}
    twins = 0
    for r, child in zip(rows, ds.truth["signups"], strict=True):
        key = (r["Parent/carer email"], r["Date of birth"])
        if r["Date of birth"] and key in seen and seen[key] != child:
            twins += 1
        seen.setdefault(key, child)
    assert twins >= 1
