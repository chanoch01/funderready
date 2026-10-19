from __future__ import annotations

from datetime import date

import pytest

from funderready.pseudonymise import (
    Pseudonymiser,
    dob_month,
    name_soundex,
    normalise_name,
    parse_date,
    postcode_district,
    soundex,
)

P = Pseudonymiser("test-key-0123456789")


@pytest.mark.parametrize(
    ("word", "code"),
    [("Robert", "R163"), ("Rupert", "R163"), ("Ashcraft", "A261"), ("Tymczak", "T522"),
     ("Pfister", "P236"), ("Honeyman", "H555"), ("Lee", "L000"), ("", "")],
)  # fmt: skip
def test_soundex_matches_reference_codes(word, code):
    assert soundex(word) == code


def test_typos_share_a_phonetic_token_but_not_a_name_token():
    assert P.name("Jon Smith") != P.name("John Smith")
    assert P.name_phonetic("Jon Smith") == P.name_phonetic("John Smith")
    assert P.name_phonetic("Freya Reid") != P.name_phonetic("Grace Reid")


def test_case_accents_and_spacing_do_not_change_tokens():
    assert normalise_name("  Zoë   O'Brien-Smith ") == "zoe obrien smith"
    assert P.name("ZOË o'brien-smith") == P.name("Zoe OBrien Smith")
    assert P.email(" Carer1@Example.org ") == P.email("carer1@example.org")
    assert P.phone("07700 900123") == P.phone("+44 7700 900123")


def test_tokens_depend_on_the_key_and_namespace():
    other = Pseudonymiser("another-key-0123456789")
    assert P.name("Ava Smith") != other.name("Ava Smith")
    assert P.token("name", "x") != P.token("email", "x")
    assert len(P.name("Ava Smith")) == 16


def test_blank_values_give_no_token_and_short_keys_are_refused():
    assert P.name("  ") is None and P.email(None) is None
    with pytest.raises(ValueError):
        Pseudonymiser("short")


def test_name_soundex_per_word():
    assert name_soundex("Mohammed Khan") == "M530 K500"


@pytest.mark.parametrize(
    ("text", "expected"),
    [("2014-03-09", date(2014, 3, 9)), ("09/03/2014", date(2014, 3, 9)),
     ("9 Mar 2014", date(2014, 3, 9)), ("9 March 2014", date(2014, 3, 9)),
     ("", None), ("next tuesday", None), ("31/02/2014", None)],
)  # fmt: skip
def test_parse_date_handles_volunteer_formats(text, expected):
    assert parse_date(text) == expected


def test_dob_kept_to_month_and_postcode_to_district():
    assert dob_month("09/03/2014") == "2014-03"
    assert dob_month("") is None
    assert postcode_district("eh6 7qd") == "EH6"
    assert postcode_district("G12 8QQ") == "G12"
    assert postcode_district("unknown") is None
