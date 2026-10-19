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
    while len(children) < n_children:
        first, last = rng.choice(FIRST), rng.choice(LAST)
        if (first, last) in seen:
            continue
        seen.add((first, last))
        programme = rng.choice(PROGRAMMES)
        age = rng.randint(9, 11) if programme == "Football U12" else rng.randint(12, 15)
        dob = date(2026 - age, rng.randint(1, 12), rng.randint(1, 28))
        children.append(
            {"first": first, "last": last, "dob": dob, "programme": programme,
             "district": rng.choice(POSTCODE_DISTRICTS)}
        )  # fmt: skip

    signups: list[dict[str, str]] = []
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
            "Parent/carer email": f"carer{idx}@example.org",
            "Phone": f"07700 900{idx % 1000:03d}",  # Ofcom drama range, never a real number
            "Consent to photos": rng.choice(["Yes", "No", "yes", "Y"]),
        }
        if rng.random() < 0.08:
            row["Date of birth"] = ""
            ds.plant("signups", len(signups) + 2, "missing_dob")
        signups.append(row)
        if rng.random() < 0.06:  # parent fills the form in again
            dup = dict(row)
            dup["First name"] = _typo(c["first"], rng)
            dup["Timestamp"] = (submitted + timedelta(days=rng.randint(1, 20))).strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            signups.append(dup)
            ds.plant("signups", len(signups) + 1, "duplicate_person")
    ds.sheets["signups"] = signups

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
    by_programme = {p: [c for c in children if c["programme"] == p] for p in PROGRAMMES}
    for d, programme in session_keys:
        pool = by_programme[programme]
        for c in rng.sample(pool, k=min(len(pool), rng.randint(8, 16))):
            name = f"{c['first']} {c['last']}"
            row = {"Date": _fmt_date(d, rng), "Programme": programme, "Attendee": name}
            r = rng.random()
            if r < 0.04:
                row["Attendee"] = f"{_typo(c['first'], rng)} {c['last']}"
                if row["Attendee"].lower() != name.lower():
                    ds.plant("attendance", len(attendance) + 2, "attendee_typo")
            elif r < 0.05:
                row["Attendee"] = f"{rng.choice(FIRST)} Visitor"
                ds.plant("attendance", len(attendance) + 2, "attendee_unknown")
            attendance.append(row)
    ds.sheets["attendance"] = attendance

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
    return paths
