"""HL7v2 message parser and serializer.

Adapted from the owner's earlier hl7v2-interface-automater parser,
extended with serialization so
messages can be rewritten after anonymizing or mutation.
Handles standard delimiters and CR / LF / CRLF segment separators.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Segment:
    name: str
    fields: list[str]  # fields[num-1] is HL7 field num (1-based)

    def get(self, num: int, default: str = "") -> str:
        idx = num - 1
        return self.fields[idx] if 0 <= idx < len(self.fields) else default

    def set(self, num: int, value: str) -> None:
        idx = num - 1
        while len(self.fields) <= idx:
            self.fields.append("")
        self.fields[idx] = value

    def component(self, num: int, comp: int, default: str = "",
                  sep: str = "^") -> str:
        parts = self.get(num).split(sep)
        idx = comp - 1
        return parts[idx] if 0 <= idx < len(parts) else default


@dataclass
class Message:
    segments: list[Segment] = field(default_factory=list)
    field_sep: str = "|"
    comp_sep: str = "^"
    rep_sep: str = "~"

    @property
    def msg_type(self) -> str:
        msh = self.segment("MSH")
        return msh.get(9) if msh else ""

    @property
    def control_id(self) -> str:
        msh = self.segment("MSH")
        return msh.get(10) if msh else ""

    def segment(self, name: str) -> Segment | None:
        for seg in self.segments:
            if seg.name == name:
                return seg
        return None

    def segments_named(self, name: str) -> list[Segment]:
        return [s for s in self.segments if s.name == name]

    def get(self, seg_name: str, num: int, default: str = "") -> str:
        seg = self.segment(seg_name)
        return seg.get(num, default) if seg else default

    def to_hl7(self) -> str:
        lines = []
        for seg in self.segments:
            if seg.name == "MSH":
                # fields[0] holds the separator itself (MSH-1)
                body = self.field_sep.join(seg.fields[1:])
                lines.append("MSH" + self.field_sep + body)
            else:
                lines.append(seg.name + self.field_sep + self.field_sep.join(seg.fields))
        return "\r".join(lines) + "\r"


def _clean(raw: str) -> str:
    """Normalize capture text the way real interface engines emit it:
    strip a UTF-8 BOM (Windows tools add one, and it would hide the
    first MSH) and MLLP framing bytes (VT before a message, FS at its
    end) so framed captures parse like plain ones."""
    return raw.replace("\ufeff", "").replace("\x0b", "").replace("\x1c", "")


def _msh_parts(line: str):
    """Split a candidate MSH line into (field_sep, parts-after-MSH),
    or return None when the line cannot be a real MSH header.

    A real header has a non-alphanumeric separator as its fourth
    character, encoding characters in MSH-2, and fields running at
    least through MSH-9 with a non-empty message code. A line like
    "MSHgarbage" fails every part of that, which is the point: an
    MSH prefix alone must never promote garbage into a message.
    """
    if not line.startswith("MSH") or len(line) <= 4:
        return None
    sep = line[3]
    if sep.isalnum() or sep in " \t":
        return None
    parts = line[4:].split(sep)
    if len(parts) < 8 or not parts[0]:
        return None
    if not parts[7].split(parts[0][0])[0].strip():
        return None
    return sep, parts


def is_plausible_msh(line: str) -> bool:
    return _msh_parts(line) is not None


def parse_message(raw: str) -> Message:
    text = _clean(raw).replace("\r\n", "\r").replace("\n", "\r")
    msg = Message()
    for line in text.split("\r"):
        line = line.strip()
        if not line:
            continue
        if not msg.segments and line.startswith("MSH"):
            parsed = _msh_parts(line)
            if parsed is None:
                raise ValueError(
                    "malformed MSH header (no separator, encoding "
                    f"characters, or message type): {line[:40]!r}")
            msg.field_sep, parts = parsed
            enc = parts[0]
            msg.comp_sep = enc[0] if enc else "^"
            msg.rep_sep = enc[1] if len(enc) > 1 else "~"
            fields = [msg.field_sep] + parts
            name = "MSH"
        else:
            parts = line.split(msg.field_sep)
            name = parts[0]
            fields = parts[1:]
        msg.segments.append(Segment(name=name, fields=fields))
    return msg


def split_messages(raw: str) -> list[Message]:
    """Split a capture file that may hold many messages (MSH-started).

    Only MSH-started chunks count as messages. Lines before the first
    MSH (a banner, a stray note, plain garbage) are not a message, so
    an empty or non-HL7 file yields an empty list and callers can fail
    closed instead of reporting a clean pass on nothing.
    """
    text = _clean(raw).replace("\r\n", "\r").replace("\n", "\r")
    chunks: list[str] = []
    current: list[str] = []
    for line in text.split("\r"):
        if is_plausible_msh(line):
            if current:
                chunks.append("\r".join(current))
            current = [line]
        elif line.strip() and current:
            current.append(line)
    if current:
        chunks.append("\r".join(current))
    return [parse_message(c) for c in chunks if c.strip()]
