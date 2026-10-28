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


def validate_message(msg: Message, profile: dict) -> list[Finding]:
    findings: list[Finding] = []
    spec = profile.get(msg.msg_type) or profile.get("*") or {}
    for seg_name in spec.get("required_segments", []):
        if msg.segment(seg_name) is None:
            findings.append(Finding("error", f"missing required segment {seg_name}", seg_name))
    for path, label in spec.get("required_fields", {}).items():
        seg_name, num, _ = _parse_path(path)
        seg = msg.segment(seg_name)
        if seg is None:
            continue
        if not seg.get(num).strip():
            findings.append(Finding("error", f"empty required field ({label})", path))
    for path, allowed in spec.get("allowed_values", {}).items():
        seg_name, num, comp = _parse_path(path)
        for seg in msg.segments_named(seg_name):
            value = seg.component(num, comp) if comp else seg.get(num)
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
