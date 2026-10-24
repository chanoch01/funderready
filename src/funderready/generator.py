"""Generate a realistic, messy, entirely SYNTHETIC charity dataset.

Small charities keep their records in exported Google Forms, sheets typed by volunteers,
and payment-provider exports. This generator reproduces the mess on purpose, and records
every planted problem in `planted_errors.json` so the data-quality inbox (Week 2) can be
scored for recall instead of eyeballed.

Planted problems:
  missing_dob        sign-up with no date of birth
  duplicate_person   the same child signed up twice, with a typo or different casing
  session_no_date    session row with the date left blank
  attendee_typo      attendance name misspelt (phonetic match still possible)
  attendee_unknown   attendance name for someone who never signed up
  amount_text        donation amount typed as text, e.g. "twenty"

Hard cases for duplicate matching (not errors, so not in the manifest):
  siblings           children who share a carer's email and phone, sometimes twins with
                     the same date of birth; matching on carer details alone merges them
  second parent      some repeat sign-ups come from the other parent's email and phone

`truth.json` records which synthetic child is behind every sign-up and attendance row, so
duplicate resolution can be scored for precision and recall. It is never loaded.

None of the people are real: names are random combinations of common first and last names.
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

FIRST = """Ava Isla Olivia Emily Freya Sophie Grace Amelia Ella Lily Jack Noah Leo Harris Lewis
Oliver Charlie James Alfie Finlay Rory Callum Ewan Aisha Zara Kofi Ama Ibrahim Mohammed
Priya Arjun Mei Wei Tomasz Zofia Jon John Sean Shaun Katie Kate""".split()
LAST = """Smith Brown Wilson Campbell Stewart Thomson Robertson Anderson MacDonald Scott Reid
Murray Taylor Clark Mensah Boateng Asante Khan Ahmed Singh Kowalski Nowak Chen Li Wright
Hughes Paterson Fraser""".split()
PROGRAMMES = ["Football U12", "Football U16", "Girls Multisport"]
VENUES = {"Football U12": "Leith Links", "Football U16": "Leith Links", "Girls Multisport": "Hub"}
CAMPAIGNS = ["Spring appeal", "Kit fund", "Holiday camp", "General"]
POSTCODE_DISTRICTS = ["EH6", "EH7", "EH5", "EH4", "EH8"]


@dataclass
class Dataset:
    sheets: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    planted: list[dict[str, object]] = field(default_factory=list)
    # sheet -> one entry per data row: the synthetic child's id, or None (a visitor)
    truth: dict[str, list[int | None]] = field(default_factory=dict)

    def plant(self, sheet: str, row: int, kind: str) -> None:
        # Spreadsheet row numbers: header is row 1, so the first record is row 2.
        self.planted.append({"sheet": sheet, "row": row, "type": kind})


def _fmt_date(d: date, rng: random.Random) -> str:
    """Volunteers type dates in whatever format they like."""
    style = rng.choices(["iso", "uk", "text"], weights=[3, 6, 2])[0]
    if style == "iso":
        return d.isoformat()
    if style == "uk":
        return d.strftime("%d/%m/%Y")
    return f"{d.day} {d.strftime('%b %Y')}"


def _typo(name: str, rng: random.Random) -> str:
    """A believable slip that keeps the same sound: drop/double a letter or change case."""
    if len(name) < 4:
        return name.lower()
    i = rng.randrange(1, len(name) - 1)
    choice = rng.choice(["drop", "double", "lower"])
    if choice == "drop" and name[i].lower() in "aeiouhy":
        return name[:i] + name[i + 1 :]
    if choice == "double":
        return name[: i + 1] + name[i] + name[i + 1 :]
    return name.lower()


def generate(seed: int = 7, n_children: int = 180, weeks: int = 26) -> Dataset:
    rng = random.Random(seed)
    ds = Dataset()
    start = date(2026, 1, 6)

    # --- sign-ups (Google Form export) -------------------------------------------------
    children = []
    seen = set()

    def age_for(programme: str) -> int:
        return rng.randint(9, 11) if programme == "Football U12" else rng.randint(12, 15)

    while len(children) < n_children:
        sibling_of = rng.choice(children) if children and rng.random() < 0.12 else None
        first = rng.choice(FIRST)
        last = sibling_of["last"] if sibling_of else rng.choice(LAST)
        if (first, last) in seen:
            continue
        seen.add((first, last))
        family = [c for c in children if sibling_of and c["carer"] == sibling_of["carer"]]
        has_twin = any(a["dob"] == b["dob"] for a in family for b in family if a is not b)
        if sibling_of and not has_twin and rng.random() < 0.2:
            # twins: same date of birth and programme (only ever a pair)
            programme, dob = sibling_of["programme"], sibling_of["dob"]
        else:
            for _ in range(100):  # siblings who are not twins are born 10+ months apart
                programme = rng.choice(PROGRAMMES)
                dob = date(2026 - age_for(programme), rng.randint(1, 12), rng.randint(1, 28))
                if all(abs((dob - c["dob"]).days) > 300 for c in family):
                    break
            else:
                seen.discard((first, last))
                continue
        children.append(
            {"first": first, "last": last, "dob": dob, "programme": programme,
             "district": sibling_of["district"] if sibling_of else rng.choice(POSTCODE_DISTRICTS),
             "carer": sibling_of["carer"] if sibling_of else len(children)}
        )  # fmt: skip

    signups: list[dict[str, str]] = []
    truth: list[int | None] = []
    for idx, c in enumerate(children):
        submitted = datetime(2025, 12, 1, 9) + timedelta(hours=rng.randrange(0, 24 * 120))
        row = {
            "Timestamp": submitted.strftime("%d/%m/%Y %H:%M:%S"),
            "First name": c["first"],
            "Last name": c["last"],
            "Date of birth": _fmt_date(c["dob"], rng),
            "Postcode": f"{c['district']} {rng.randint(1, 9)}"
            f"{rng.choice('ABDEFGHJ')}{rng.choice('LNPQRSTU')}",
            "Programme": c["programme"],
            "Parent/carer email": f"carer{c['carer']}@example.org",
            # Ofcom drama range, never a real number
            "Phone": f"07700 900{c['carer'] % 1000:03d}",
            "Consent to photos": rng.choice(["Yes", "No", "yes", "Y"]),
        }
        if rng.random() < 0.08:
            row["Date of birth"] = ""
            ds.plant("signups", len(signups) + 2, "missing_dob")
        signups.append(row)
        truth.append(idx)
        if rng.random() < 0.06:  # parent fills the form in again
            dup = dict(row)
            dup["First name"] = _typo(c["first"], rng)
            dup["Timestamp"] = (submitted + timedelta(days=rng.randint(1, 20))).strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            if row["Date of birth"] and rng.random() < 0.5:  # retyped in another format
                dup["Date of birth"] = _fmt_date(c["dob"], rng)
            if rng.random() < 0.35:  # the other parent fills it in
                dup["Parent/carer email"] = f"carer{c['carer']}.b@example.org"
                dup["Phone"] = f"07700 901{c['carer'] % 1000:03d}"
            signups.append(dup)
            truth.append(idx)
            ds.plant("signups", len(signups) + 1, "duplicate_person")
    ds.sheets["signups"] = signups
    ds.truth["signups"] = truth

    # --- sessions (sheet typed by coaches) ---------------------------------------------
    sessions: list[dict[str, str]] = []
    session_keys = []
    for week in range(weeks):
        for p_idx, programme in enumerate(PROGRAMMES):
            d = start + timedelta(weeks=week, days=p_idx * 2)
            row = {
                "Date": _fmt_date(d, rng),
                "Programme": programme if rng.random() > 0.1 else f" {programme.lower()} ",
                "Venue": VENUES[programme],
                "Coach": rng.choice(["AB", "CK", "MM", "JT"]),
            }
            if rng.random() < 0.03:
                row["Date"] = ""
                ds.plant("sessions", len(sessions) + 2, "session_no_date")
            else:
                session_keys.append((d, programme))
            sessions.append(row)
    ds.sheets["sessions"] = sessions

    # --- attendance (one row per child per session) ------------------------------------
    attendance: list[dict[str, str]] = []
    attendance_truth: list[int | None] = []
    by_programme = {
        p: [(i, c) for i, c in enumerate(children) if c["programme"] == p] for p in PROGRAMMES
    }
    for d, programme in session_keys:
        pool = by_programme[programme]
        for idx, c in rng.sample(pool, k=min(len(pool), rng.randint(8, 16))):
            name = f"{c['first']} {c['last']}"
            row = {"Date": _fmt_date(d, rng), "Programme": programme, "Attendee": name}
            r = rng.random()
            who: int | None = idx
            if r < 0.04:
                row["Attendee"] = f"{_typo(c['first'], rng)} {c['last']}"
                if row["Attendee"].lower() != name.lower():
                    ds.plant("attendance", len(attendance) + 2, "attendee_typo")
            elif r < 0.05:
                row["Attendee"] = f"{rng.choice(FIRST)} Visitor"
                ds.plant("attendance", len(attendance) + 2, "attendee_unknown")
                who = None
            attendance.append(row)
            attendance_truth.append(who)
    ds.sheets["attendance"] = attendance
    ds.truth["attendance"] = attendance_truth

    # --- donations (payment provider export) -------------------------------------------
    donations: list[dict[str, str]] = []
    for _ in range(140):
        when = datetime(2026, 1, 1, 8) + timedelta(minutes=rng.randrange(0, 60 * 24 * 180))
        amount = rng.choice([5, 10, 10, 20, 25, 50, 100, 250])
        row = {
            "Created (UTC)": when.strftime("%Y-%m-%d %H:%M"),
            "Amount": f"£{amount:,.2f}",
            "Currency": "gbp",
            "Customer Email": f"donor{rng.randint(1, 90)}@example.com",
            "Campaign": rng.choice(CAMPAIGNS),
            "Status": rng.choices(["Paid", "Refunded"], weights=[30, 1])[0],
        }
        if rng.random() < 0.02:
            row["Amount"] = rng.choice(["twenty", "tbc"])
            ds.plant("donations", len(donations) + 2, "amount_text")
        donations.append(row)
    ds.sheets["donations"] = donations
    return ds


def write(ds: Dataset, folder: Path) -> list[Path]:
    """Write one CSV per sheet plus the planted-error manifest."""
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, rows in ds.sheets.items():
        path = folder / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        paths.append(path)
    (folder / "planted_errors.json").write_text(json.dumps(ds.planted, indent=2))
    # spreadsheet row number -> synthetic child id; read only by the scoring scripts
    truth = {
        sheet: {str(i + 2): child for i, child in enumerate(ids)} for sheet, ids in ds.truth.items()
    }
    (folder / "truth.json").write_text(json.dumps(truth, indent=1))
    return paths
