"""Pseudonymise personal data at ingestion, before anything reaches the warehouse.

What leaves this module:
  * names, emails, phones  -> keyed HMAC tokens (stable per organisation, not reversible
                              without the organisation's key)
  * names, additionally    -> a token of their *Soundex* code, so "Jon Smith" and
                              "John Smith" can still be linked without storing either name
  * date of birth          -> year and month only (enough for age bands)
  * postcode               -> outward code / district only (e.g. "EH6")

This is pseudonymisation, not anonymisation: under UK GDPR the output is still personal
data, so access controls and retention still apply. The point is that analysts and funders'
reports never need the raw identifiers.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import unicodedata
from datetime import date, datetime

TOKEN_HEX_CHARS = 16  # 64 bits: ample for one charity's records


def normalise_name(text: str | None) -> str:
    """Lower-case, strip accents and punctuation, collapse spaces."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z\s-]", "", text.lower()).replace("-", " ")
    return " ".join(text.split())


def soundex(word: str) -> str:
    """American Soundex (as used by the US census): R163 for Robert and Rupert."""
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return ""
    codes = {
        **dict.fromkeys("bfpv", "1"),
        **dict.fromkeys("cgjkqsxz", "2"),
        **dict.fromkeys("dt", "3"),
        "l": "4",
        **dict.fromkeys("mn", "5"),
        "r": "6",
    }
    first, out, prev = word[0].upper(), [], codes.get(word[0], "")
    for ch in word[1:]:
        code = codes.get(ch, "")
        if code and code != prev:
            out.append(code)
        if ch not in "hw":  # h and w do not separate letters with the same code
            prev = code
    return (first + "".join(out) + "000")[:4]


def name_soundex(full_name: str | None) -> str:
    return " ".join(soundex(part) for part in normalise_name(full_name).split())


class Pseudonymiser:
    def __init__(self, key: str | bytes) -> None:
        if not key or len(key) < 16:
            raise ValueError("Use a pseudonymisation key of at least 16 characters")
        self._key = key.encode() if isinstance(key, str) else key

    def token(self, kind: str, value: str | None) -> str | None:
        """Keyed, deterministic token. `kind` separates namespaces (name vs email)."""
        if value is None or not str(value).strip():
            return None
        msg = f"{kind}:{value}".encode()
        return hmac.new(self._key, msg, hashlib.sha256).hexdigest()[:TOKEN_HEX_CHARS]

    def name(self, full_name: str | None) -> str | None:
        return self.token("name", normalise_name(full_name))

    def name_phonetic(self, full_name: str | None) -> str | None:
        return self.token("soundex", name_soundex(full_name))

    def email(self, email: str | None) -> str | None:
        return self.token("email", (email or "").strip().lower())

    def phone(self, phone: str | None) -> str | None:
        digits = re.sub(r"\D", "", phone or "")
        return self.token("phone", digits[-10:])


DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d %b %Y", "%d %B %Y", "%d-%m-%Y"]


def parse_date(text: str | None) -> date | None:
    """Parse the date formats volunteers actually type. Unknown formats return None."""
    if not text or not text.strip():
        return None
    cleaned = " ".join(text.strip().split())
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def dob_month(text: str | None) -> str | None:
    """Keep only year and month of a date of birth, e.g. '2014-03'."""
    parsed = parse_date(text)
    return parsed.strftime("%Y-%m") if parsed else None


def postcode_district(postcode: str | None) -> str | None:
    """'EH6 7QD' -> 'EH6'. Returns None when no UK outward code is found."""
    match = re.match(r"^\s*([A-Z]{1,2}\d[A-Z\d]?)\b", (postcode or "").upper())
    return match.group(1) if match else None
