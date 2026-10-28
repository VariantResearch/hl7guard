# HL7Guard Free

HL7v2 validation and de-identification for the command line.
Not another message viewer: a checker you can run in CI, with
exit codes a pipeline can gate on.

This repository is the **free edition**, complete as far as it
goes:

- `hl7guard validate <file>` validates the one message in a file
  against the built-in checks (structure plus the built-in ADT
  and ORU profiles with `--builtin`).
- `hl7guard anonymize <file>` de-identifies the one message in a
  file. Replacements are seeded and consistent: the same patient
  maps to the same fake patient for a given seed, and direct
  identifiers (names, IDs, dates of birth, addresses, phone
  numbers, and the rest of the covered fields) are replaced.

Exit codes are the contract: 0 clean, 1 validation errors found,
2 file or usage error. Input with no HL7 message in it exits 2,
never a clean pass.

Everything runs locally and offline. Python 3.10 or newer, no
third-party dependencies.

## Install

    pip install .

## Usage

    hl7guard validate message.hl7
    hl7guard validate message.hl7 --builtin adt_a01
    hl7guard anonymize message.hl7 --seed "my-seed" --out cleaned/

The `samples/` folder holds two synthetic messages (entirely
made up; no real patient data) to try it on.

## The full edition

Batch and folder mode, custom JSON profiles, field-by-field
capture diff matched by message control ID, labelled edge-case
message generation, a capture census, a residual-identifier
verify pass, live MLLP send and listen testing, a desktop GUI,
and JSON and HTML reports are the full edition, sold as a
one-time license (Solo and Team) at
https://hl7guard.variantresearchgroup.com

Support: hl7guard-support@variantresearchgroup.com

Plain notes: the anonymizer is a de-identification aid, not a
HIPAA certification, so review de-identified output before
sharing it.
