"""Consistent de-identification.

The point other simple maskers miss: consistency across a whole capture.
The same source MRN, name, account number, or DOB maps to the same fake
value in every message anonymized with the same Anonymizer instance, so
multi-message patient flow (admit, order, result, discharge) still tests
correctly. Mappings are derived from a seed with HMAC-SHA256, so the same
seed reproduces the same fakes and no mapping table with real values ever
needs to be stored.

Consistency is by identifier, not by exact spelling. The same person is
written differently across real captures: an MRN carries assigning
authority components in one message and stands bare in another, a DOB
arrives as a date in one message and a datetime in the next, a phone
number changes punctuation, a name gains a middle initial. Token keys
are therefore normalized before hashing (first repetition, first
component for ID fields; family and given for names; the date part for
DOBs; digits only for phones and SSNs), so those variants map to one
fake instead of several.

Covered fields: patient identifiers (including the legacy PID-2
and alternate PID-4 identifiers), names (including mother maiden
name and patient alias), DOB, address, home and business phones,
account number, SSN, driver license, and mother identifier on PID;
visit number on PV1; insured name, insured address, and policy holder
identifier on IN1; next-of-kin name, address, and phones on NK1;
guarantor name, address, phones, and SSN on GT1.

This is a de-identification AID, not a HIPAA certification. Free-text
fields (NTE, OBX-5 narrative, TXA, etc.) can contain identifiers this
field-based pass does not see. Always review output before sharing.
"""
from __future__ import annotations

import hashlib
import hmac

from .parser import Message

FAKE_FAMILY = ["Smith", "Johnson", "Brown", "Taylor", "Miller", "Davis",
               "Garcia", "Wilson", "Moore", "Anderson", "Thomas", "Lee"]
FAKE_GIVEN = ["Alex", "Jordan", "Taylor", "Casey", "Jamie", "Robin",
              "Pat", "Sam", "Chris", "Drew", "Morgan", "Avery"]
FAKE_STREETS = ["100 Main St", "200 Oak Ave", "300 Pine Rd", "400 Elm Dr",
                "500 Cedar Ln", "600 Maple Way"]


def _first_component(value: str, rep_sep: str = "~",
                     comp_sep: str = "^") -> str:
    """First repetition, first component: the ID itself, without the
    assigning authority and other components real senders attach.
    Separators come from the message being anonymized, so a capture
    that declares different encoding characters normalizes the same
    way it is written."""
    return value.split(rep_sep)[0].split(comp_sep)[0].strip()


def _digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


class Anonymizer:
    def __init__(self, seed: str = "hl7guard-default-seed"):
        self._key = seed.encode("utf-8")

    def _token(self, kind: str, value: str) -> int:
        digest = hmac.new(self._key, f"{kind}:{value}".encode("utf-8"),
                          hashlib.sha256).hexdigest()
        return int(digest[:8], 16)

    def fake_mrn(self, value: str, rep_sep: str = "~",
                 comp_sep: str = "^") -> str:
        return f"MRN{self._token('mrn', _first_component(value, rep_sep, comp_sep)) % 9000000 + 1000000}"

    def fake_account(self, value: str, rep_sep: str = "~",
                     comp_sep: str = "^") -> str:
        return f"ACCT{self._token('acct', _first_component(value, rep_sep, comp_sep)) % 9000000 + 1000000}"

    def fake_license(self, value: str, rep_sep: str = "~",
                     comp_sep: str = "^") -> str:
        return f"DL{self._token('license', _first_component(value, rep_sep, comp_sep)) % 9000000 + 1000000}"

    def fake_name(self, value: str, comp_sep: str = "^",
                  rep_sep: str = "~") -> str:
        # PID-5 format: Family^Given^Middle... Identity for consistency
        # is family and given only, so a middle initial appearing in
        # one message and not another still maps to the same fake.
        parts = value.split(rep_sep)[0].split(comp_sep)
        key = comp_sep.join(p.strip() for p in parts[:2])
        t = self._token("name", key)
        return comp_sep.join([FAKE_FAMILY[t % len(FAKE_FAMILY)],
                              FAKE_GIVEN[(t >> 4) % len(FAKE_GIVEN)]])

    def fake_dob(self, value: str) -> str:
        # Keep year plausible and stable; shift day/month deterministically.
        # The token key is the date part only, so a date form and a
        # datetime form of the same DOB map to the same fake.
        key = value[:8] if len(value) >= 8 and value[:8].isdigit() else value
        t = self._token("dob", key)
        year = value[:4] if len(value) >= 4 and value[:4].isdigit() else "1980"
        return f"{year}{(t % 12) + 1:02d}{(t % 28) + 1:02d}"

    def fake_phone(self, value: str) -> str:
        # Punctuation is not identity: key on digits so the same number
        # written with dashes, spaces, or parentheses maps to one fake.
        key = _digits(value) or value
        return f"555-{self._token('phone', key) % 900 + 100:03d}-{self._token('phone2', key) % 9000 + 1000}"

    def fake_address(self, value: str, comp_sep: str = "^",
                     rep_sep: str = "~") -> str:
        t = self._token("addr", value.split(rep_sep)[0])
        return comp_sep.join([FAKE_STREETS[t % len(FAKE_STREETS)], "",
                              "Anytown", "ST", f"{36000 + t % 999:05d}"])

    def fake_ssn(self, value: str) -> str:
        key = _digits(value) or value
        return f"999-99-{self._token('ssn', key) % 9000 + 1000}"

    def anonymize(self, msg: Message) -> Message:
        # Replacements are built with the message's own declared
        # encoding characters. Writing caret composites into a
        # message that uses a different component separator would
        # corrupt field positions on reparse.
        cs, rs = msg.comp_sep, msg.rep_sep
        for seg in msg.segments:
            if seg.name == "PID":
                if seg.get(2):  # PID-2 legacy patient identifier
                    seg.set(2, self.fake_mrn(seg.get(2), rs, cs))
                if seg.get(3):
                    seg.set(3, self.fake_mrn(seg.get(3), rs, cs)
                            + cs.join(["", "", "", "RC", "MR"]))
                if seg.get(4):  # PID-4 alternate patient identifier
                    seg.set(4, self.fake_mrn(seg.get(4), rs, cs))
                if seg.get(5):
                    seg.set(5, self.fake_name(seg.get(5), cs, rs))
                if seg.get(6):  # PID-6 mother maiden name
                    seg.set(6, self.fake_name(seg.get(6), cs, rs))
                if seg.get(7):
                    seg.set(7, self.fake_dob(seg.get(7)))
                if seg.get(9):  # PID-9 patient alias
                    seg.set(9, self.fake_name(seg.get(9), cs, rs))
                if seg.get(11):
                    seg.set(11, self.fake_address(seg.get(11), cs, rs))
                if seg.get(13):
                    seg.set(13, self.fake_phone(seg.get(13)))
                if seg.get(14):  # PID-14 business phone
                    seg.set(14, self.fake_phone(seg.get(14)))
                if seg.get(18):  # PID-18 patient account number
                    seg.set(18, self.fake_account(seg.get(18), rs, cs))
                if seg.get(19):  # PID-19 SSN
                    seg.set(19, self.fake_ssn(seg.get(19)))
                if seg.get(20):  # PID-20 driver license number
                    seg.set(20, self.fake_license(seg.get(20), rs, cs))
                if seg.get(21):  # PID-21 mother identifier
                    seg.set(21, self.fake_mrn(seg.get(21), rs, cs))
            elif seg.name == "PV1":
                if seg.get(19):
                    seg.set(19, self.fake_account(seg.get(19), rs, cs))
            elif seg.name == "IN1":
                if seg.get(16):  # IN1-16 name of insured
                    seg.set(16, self.fake_name(seg.get(16), cs, rs))
                if seg.get(19):  # IN1-19 insured address
                    seg.set(19, self.fake_address(seg.get(19), cs, rs))
                if seg.get(36):
                    seg.set(36, self.fake_mrn(seg.get(36), rs, cs))
            elif seg.name == "NK1":
                if seg.get(2):
                    seg.set(2, self.fake_name(seg.get(2), cs, rs))
                if seg.get(4):  # NK1-4 next-of-kin address
                    seg.set(4, self.fake_address(seg.get(4), cs, rs))
                if seg.get(5):
                    seg.set(5, self.fake_phone(seg.get(5)))
                if seg.get(6):  # NK1-6 business phone
                    seg.set(6, self.fake_phone(seg.get(6)))
            elif seg.name == "GT1":
                if seg.get(3):  # GT1-3 guarantor name
                    seg.set(3, self.fake_name(seg.get(3), cs, rs))
                if seg.get(5):  # GT1-5 guarantor address
                    seg.set(5, self.fake_address(seg.get(5), cs, rs))
                if seg.get(6):  # GT1-6 guarantor phone, home
                    seg.set(6, self.fake_phone(seg.get(6)))
                if seg.get(7):  # GT1-7 guarantor phone, business
                    seg.set(7, self.fake_phone(seg.get(7)))
                if seg.get(12):  # GT1-12 guarantor SSN
                    seg.set(12, self.fake_ssn(seg.get(12)))
        return msg
