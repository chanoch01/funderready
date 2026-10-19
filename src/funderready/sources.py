"""Read the spreadsheets a charity already keeps, then pseudonymise each row.

Sources:
  * a folder of CSV exports (sign-ups.csv, sessions.csv, ...)
  * a Google Sheet tab shared as "anyone with the link can view", read through its
    CSV export URL (no Google credentials needed)

Every record keeps `_row_number` (the spreadsheet row, header = row 1), so a data-quality
issue can point a volunteer at the exact cell to fix.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx

from funderready.pseudonymise import Pseudonymiser, dob_month, postcode_district

Row = dict[str, str]
Record = dict[str, Any]


def read_csv_text(text: str) -> Iterator[Row]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    for row in reader:
        if any((v or "").strip() for v in row.values()):  # skip fully blank rows
            yield {(k or "").strip(): (v or "") for k, v in row.items()}


def read_csv_file(path: Path) -> Iterator[Row]:
    yield from read_csv_text(path.read_text(encoding="utf-8-sig"))


def google_sheet_csv_url(sheet_id: str, gid: str = "0") -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def read_google_sheet(
    sheet_id: str, gid: str = "0", transport: httpx.BaseTransport | None = None
) -> Iterator[Row]:
    with httpx.Client(follow_redirects=True, timeout=30, transport=transport) as client:
        resp = client.get(google_sheet_csv_url(sheet_id, gid))
        resp.raise_for_status()
        if "text/csv" not in resp.headers.get("content-type", ""):
            raise RuntimeError("Sheet is not shared as 'anyone with the link can view'")
        yield from read_csv_text(resp.text)


# ---- per-sheet transforms: raw row -> warehouse record ---------------------------------
# Only these functions decide what reaches the warehouse. Raw names, emails and phone
# numbers never leave them.


def _signup(row: Row, p: Pseudonymiser) -> Record:
    full_name = f"{row.get('First name', '')} {row.get('Last name', '')}"
    return {
        "submitted_at": row.get("Timestamp"),
        "person_token": p.name(full_name),
        "name_phonetic": p.name_phonetic(full_name),
        "dob_month": dob_month(row.get("Date of birth")),
        "dob_provided": bool((row.get("Date of birth") or "").strip()),
        "postcode_district": postcode_district(row.get("Postcode")),
        "programme": row.get("Programme"),
        "carer_email_token": p.email(row.get("Parent/carer email")),
        "carer_phone_token": p.phone(row.get("Phone")),
        "photo_consent": row.get("Consent to photos"),
    }


def _session(row: Row, p: Pseudonymiser) -> Record:
    return {k.lower(): row.get(k) for k in ("Date", "Programme", "Venue", "Coach")}


def _attendance(row: Row, p: Pseudonymiser) -> Record:
    return {
        "date": row.get("Date"),
        "programme": row.get("Programme"),
        "person_token": p.name(row.get("Attendee")),
        "name_phonetic": p.name_phonetic(row.get("Attendee")),
    }


def _donation(row: Row, p: Pseudonymiser) -> Record:
    return {
        "created_at": row.get("Created (UTC)"),
        "amount": row.get("Amount"),
        "currency": row.get("Currency"),
        "donor_token": p.email(row.get("Customer Email")),
        "campaign": row.get("Campaign"),
        "status": row.get("Status"),
    }


TRANSFORMS: dict[str, Callable[[Row, Pseudonymiser], Record]] = {
    "signups": _signup,
    "sessions": _session,
    "attendance": _attendance,
    "donations": _donation,
}


def pseudonymised_records(sheet: str, rows: Iterator[Row], p: Pseudonymiser) -> Iterator[Record]:
    transform = TRANSFORMS[sheet]
    for row_number, row in enumerate(rows, start=2):
        yield {"_row_number": row_number, **transform(row, p)}
