"""Profile-driven validation.

A profile is JSON so teams can keep it in their own repo and run it in CI:
{
  "ADT^A01": {
    "required_segments": ["MSH", "PID", "PV1"],
    "required_fields": {"PID-5": "patient name", "PV1-2": "patient class"},
    "allowed_values": {"OBX-3.1": ["718-7", "4544-3"]}
  },
  "*": { ... fallback for any message type ... }
}
Findings are structured so reports can be JSON or plain text.

Profile sections are matched on the message code and trigger
event (the first two MSH-9 components), so a message whose MSH-9
also carries a message structure (ADT^A01^ADT_A01) still matches
its ADT^A01 section. A supplied profile with no section for a
message's type, and no "*" fallback, is an error finding: the
message was not validated, and saying so beats a clean pass that
never checked anything.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .parser import Message


@dataclass
class Finding:
    severity: str  # "error" or "warning"
    message: str
    location: str = ""

    def __str__(self) -> str:
        loc = f" at {self.location}" if self.location else ""
        return f"[{self.severity}] {self.message}{loc}"


def load_profile(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _parse_path(path: str) -> tuple[str, int, int | None]:
    # "OBX-3" or "OBX-3.1"
    seg_field, _, comp = path.partition(".")
    seg, _, num = seg_field.partition("-")
    return seg.strip(), int(num), (int(comp) if comp else None)


def _type_key(msg: Message) -> str:
    """The profile lookup key for a message: code and trigger
    event from MSH-9, joined the way profile files write them,
    whatever component separator the message itself uses."""
    parts = [p.strip() for p in msg.msg_type.split(msg.comp_sep)]
    return "^".join(p for p in parts[:2] if p)


def validate_message(msg: Message, profile: dict) -> list[Finding]:
    findings: list[Finding] = []
    if not profile:
        return findings
    key = _type_key(msg)
    if key in profile:
        spec = profile[key]
    elif "*" in profile:
        spec = profile["*"]
    else:
        findings.append(Finding(
            "error",
            f"no profile section for message type {key or msg.msg_type!r}; "
            "the message was not validated against this profile", "MSH-9"))
        return findings
    for seg_name in spec.get("required_segments", []):
        if msg.segment(seg_name) is None:
            findings.append(Finding("error", f"missing required segment {seg_name}", seg_name))
    for path, label in spec.get("required_fields", {}).items():
        seg_name, num, _ = _parse_path(path)
        for i, seg in enumerate(msg.segments_named(seg_name), 1):
            if not seg.get(num).strip():
                loc = path if i == 1 else f"{path} (occurrence {i})"
                findings.append(Finding("error", f"empty required field ({label})", loc))
    for path, allowed in spec.get("allowed_values", {}).items():
        seg_name, num, comp = _parse_path(path)
        for seg in msg.segments_named(seg_name):
            value = seg.component(num, comp, sep=msg.comp_sep) if comp else seg.get(num)
            value = value.strip()
            if value and value not in allowed:
                findings.append(
                    Finding("error", f"value {value!r} not in allowed list {allowed}", path)
                )
    return findings


BUILTIN_PROFILES: dict[str, dict] = {
    "adt_a01": {
        "ADT^A01": {
            "required_segments": ["MSH", "EVN", "PID", "PV1"],
            "required_fields": {"PID-3": "patient identifier", "PID-5": "patient name",
                                "PV1-2": "patient class"},
        }
    },
    "adt_a02": {
        "ADT^A02": {
            "required_segments": ["MSH", "EVN", "PID", "PV1"],
            "required_fields": {"PID-3": "patient identifier", "PID-5": "patient name",
                                "PV1-2": "patient class",
                                "PV1-3": "assigned patient location"},
        }
    },
    "adt_a03": {
        "ADT^A03": {
            "required_segments": ["MSH", "EVN", "PID", "PV1"],
            "required_fields": {"PID-3": "patient identifier", "PID-5": "patient name",
                                "PV1-2": "patient class",
                                "PV1-45": "discharge date/time"},
        }
    },
    "adt_a08": {
        "ADT^A08": {
            "required_segments": ["MSH", "EVN", "PID", "PV1"],
            "required_fields": {"PID-3": "patient identifier", "PID-5": "patient name",
                                "PV1-2": "patient class"},
        }
    },
    "orm_o01": {
        "ORM^O01": {
            "required_segments": ["MSH", "PID", "ORC", "OBR"],
            "required_fields": {"PID-3": "patient identifier", "PID-5": "patient name",
                                "ORC-1": "order control",
                                "ORC-2": "placer order number",
                                "OBR-4": "universal service ID"},
        }
    },
    "oru_r01": {
        "ORU^R01": {
            "required_segments": ["MSH", "PID", "OBR", "OBX"],
            "required_fields": {"PID-3": "patient identifier", "PID-5": "patient name",
                                "OBR-4": "universal service ID", "OBX-3": "observation ID",
                                "OBX-5": "observation value"},
        }
    },
}
