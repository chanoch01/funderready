from __future__ import annotations

import pytest

from funderready import generator
from funderready.loader import csv_folder_rows, dataset_name, org_slug
from funderready.pseudonymise import Pseudonymiser


def test_org_slug_and_schema_name():
    assert org_slug("Leith Community Sports (SCIO)") == "leith_community_sports_scio"
    assert dataset_name("Leith Community Sports") == "org_leith_community_sports_raw"
    with pytest.raises(ValueError):
        org_slug("!!!")


def test_missing_sheet_is_reported(tmp_path):
    generator.write(generator.generate(seed=1), tmp_path)
    (tmp_path / "donations.csv").unlink()
    with pytest.raises(FileNotFoundError, match="donations"):
        csv_folder_rows(tmp_path)


def test_end_to_end_load_into_duckdb_is_repeatable(tmp_path):
    duckdb = pytest.importorskip("duckdb")
    from funderready.loader import load_org

    generator.write(generator.generate(seed=4), tmp_path / "csv")
    db = str(tmp_path / "wh.duckdb")
    p = Pseudonymiser("test-key-0123456789")
    for _ in range(2):  # a second load replaces, never duplicates
        load_org(
            "Test Org", csv_folder_rows(tmp_path / "csv"), p,
            destination="duckdb", credentials=db, pipelines_dir=str(tmp_path / "dlt"),
        )  # fmt: skip

    con = duckdb.connect(db)
    n = con.execute("select count(*) from org_test_org_raw.signups").fetchone()[0]
    rows = len(list(csv_folder_rows(tmp_path / "csv")["signups"]))
    assert n == rows
    cols = {r[0] for r in con.execute("describe org_test_org_raw.signups").fetchall()}
    assert {"person_token", "name_phonetic", "dob_month", "_row_number"} <= cols
    assert not cols & {"first_name", "last_name", "parent_carer_email", "phone"}
