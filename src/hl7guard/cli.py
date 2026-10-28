"""HL7Guard Free - command-line interface.

The free edition, complete: validate one HL7v2 message at a time
against the built-in checks, and de-identify one message at a time
with seeded, consistent replacements. Exit codes are the contract:

    0  clean / done
    1  validation findings (errors in the message)
    2  file or usage error (including "not HL7 at all")

Batch and folder mode, custom profiles, capture diff, edge-case
generation, the capture census, residual-identifier verify, MLLP
send/listen, the desktop GUI, and JSON/HTML reports are the full
edition: https://hl7guard.variantresearchgroup.com
"""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .anonymize import Anonymizer
from .parser import split_messages
from .validate import BUILTIN_PROFILES, validate_message

FULL_EDITION = ("This is a free-edition limit. Batch mode, custom "
                "profiles, and the rest of the full edition are at "
                "https://hl7guard.variantresearchgroup.com")


def _load_single(path: str):
    """Read a file that must hold exactly one HL7 message.
    Returns (message, None) or (None, exit_code)."""
    if os.path.isdir(path):
        print(f"error: {path} is a folder; the free edition reads "
              f"one file with one message. {FULL_EDITION}",
              file=sys.stderr)
        return None, 2
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        return None, 2
    msgs = split_messages(text)
    if not msgs:
        print(f"error: no HL7 messages found in {path}", file=sys.stderr)
        return None, 2
    if len(msgs) > 1:
        print(f"error: {path} holds {len(msgs)} messages; the free "
              f"edition handles one at a time. {FULL_EDITION}",
              file=sys.stderr)
        return None, 2
    return msgs[0], None


def cmd_validate(args) -> int:
    msg, err = _load_single(args.path)
    if err is not None:
        return err
    profile = BUILTIN_PROFILES[args.builtin] if args.builtin else {}
    findings = validate_message(msg, profile)
    for finding in findings:
        print(f"{os.path.basename(args.path)} "
              f"{msg.control_id or '?'}: {finding}")
    errors = [f for f in findings if f.severity == "error"]
    print(f"1 message(s), {1 if errors else 0} with errors")
    return 1 if errors else 0


def cmd_anonymize(args) -> int:
    msg, err = _load_single(args.path)
    if err is not None:
        return err
    anon = Anonymizer(seed=args.seed)
    out_dir = args.out or "."
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, os.path.basename(args.path))
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(anon.anonymize(msg).to_hl7())
    print(f"{args.path} -> {out_path}")
    print("1 message(s) anonymized (seeded, consistent)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="hl7guard",
        description="HL7Guard Free: HL7v2 validation and "
                    "de-identification for the command line.")
    parser.add_argument("--version", action="version",
                        version=f"hl7guard {__version__} (free edition)")
    sub = parser.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate",
                       help="validate one message in a file")
    v.add_argument("path")
    v.add_argument("--builtin", choices=sorted(BUILTIN_PROFILES),
                   help="built-in profile to validate against")
    v.set_defaults(func=cmd_validate)

    a = sub.add_parser("anonymize",
                       help="de-identify the one message in a file")
    a.add_argument("path")
    a.add_argument("--seed", default="hl7guard-default-seed",
                   help="seed text: the same seed maps the same "
                        "patient to the same fake patient")
    a.add_argument("--out", default=None,
                   help="output directory (default: current)")
    a.set_defaults(func=cmd_anonymize)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
