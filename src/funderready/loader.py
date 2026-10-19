"""Load one organisation's sheets into its own schema with dlt.

Each organisation gets a separate schema (`org_<slug>_raw`), so one charity's data can
never appear in another's query, and an organisation can be deleted with one DROP SCHEMA.
Spreadsheets are edited in place, so each load replaces the previous snapshot.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from pathlib import Path

from funderready.pseudonymise import Pseudonymiser
from funderready.sources import Row, pseudonymised_records, read_csv_file

SHEETS = ("signups", "sessions", "attendance", "donations")

# Declared so a sheet with an all-blank column still gets the column (dbt reads them all).
COLUMN_HINTS: dict[str, dict[str, dict[str, str]]] = {
    "signups": {
        c: {"data_type": "text"}
        for c in [
            "submitted_at",
            "person_token",
            "name_phonetic",
            "dob_month",
            "postcode_district",
            "programme",
            "carer_email_token",
            "carer_phone_token",
            "photo_consent",
        ]
    }
    | {"dob_provided": {"data_type": "bool"}},
    "sessions": {c: {"data_type": "text"} for c in ["date", "programme", "venue", "coach"]},
    "attendance": {
        c: {"data_type": "text"} for c in ["date", "programme", "person_token", "name_phonetic"]
    },
    "donations": {
        c: {"data_type": "text"}
        for c in ["created_at", "amount", "currency", "donor_token", "campaign", "status"]
    },
}


def org_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not slug:
        raise ValueError(f"Organisation name gives an empty slug: {name!r}")
    return slug[:40]


def dataset_name(org: str) -> str:
    return f"org_{org_slug(org)}_raw"


def csv_folder_rows(folder: Path) -> dict[str, Iterator[Row]]:
    missing = [s for s in SHEETS if not (folder / f"{s}.csv").exists()]
    if missing:
        raise FileNotFoundError(f"Missing sheets in {folder}: {', '.join(missing)}")
    return {s: read_csv_file(folder / f"{s}.csv") for s in SHEETS}


def load_org(
    org: str,
    sheets: Mapping[str, Iterator[Row]],
    pseudonymiser: Pseudonymiser,
    *,
    destination: str = "postgres",
    pipelines_dir: str | None = None,
    **destination_kwargs,
):
    import dlt  # lazy: the core package works without the loading extra

    resources = []
    for sheet, rows in sheets.items():
        resources.append(
            dlt.resource(
                pseudonymised_records(sheet, rows, pseudonymiser),
                name=sheet,
                write_disposition="replace",
                columns=COLUMN_HINTS[sheet],
            )
        )

    dest = dlt.destinations.duckdb(**destination_kwargs) if destination == "duckdb" else destination
    pipeline = dlt.pipeline(
        pipeline_name=f"funderready_{org_slug(org)}",
        destination=dest,
        dataset_name=dataset_name(org),
        pipelines_dir=pipelines_dir,
    )
    return pipeline.run(resources)
