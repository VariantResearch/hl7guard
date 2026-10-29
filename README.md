# HL7Guard Free

HL7v2 validation and de-identification for the command line.
Not another message viewer: a checker you can script and run
in CI, with exit codes a pipeline can gate on.

## What the free edition does

- `hl7guard validate <file>` validates the one HL7v2 message in
  a file: message structure, plus the built-in ADT, ORM, and ORU
  profiles with `--builtin`.
- `hl7guard anonymize <file>` de-identifies the one message in
  a file. Names, patient IDs, dates of birth, addresses, phone
  numbers, and the other covered identifier fields are replaced.
  Replacements are seeded and consistent: with the same seed,
  the same patient maps to the same fake patient.
- `hl7guard-gui` opens a desktop window with the same two
  operations, plus a viewer/editor: open a file and read each
  message as labelled segments and fields (PID-5 shown as
  Patient Name, and so on), make a minor edit, and save it.

Exit codes: 0 clean, 1 validation errors found, 2 file or usage
error. A file with no HL7 message in it exits 2, never a clean
pass.

Everything runs locally and offline. Python 3.10 or newer, no
third-party dependencies.

## Install

You need Python 3.10 or newer. Install straight from GitHub:

    pip install "git+https://github.com/VariantResearch/hl7guard.git"

Or download the source first (the green Code button on the
GitHub page, then Download ZIP), unzip it, open a terminal in
the unzipped folder, and run:

    pip install .

Either way, check the install worked:

    hl7guard --version

If the `hl7guard` command is not found on your machine, run it
through Python instead, which works the same:

    python -m hl7guard --version

## Usage

    hl7guard validate message.hl7
    hl7guard validate message.hl7 --builtin adt_a01
    hl7guard anonymize message.hl7 --seed "my-seed" --out cleaned/

The `samples/` folder holds two synthetic messages (entirely
made up; no real patient data) to try it on.

## The full edition

Batch and folder mode, custom JSON profiles, field-by-field
capture diff matched by message control ID, labelled edge-case
message generation, a capture census, profile drafting, watch
mode, a residual-identifier verify pass, live MLLP send and
listen testing, and JSON and HTML reports are the full edition,
sold as a one-time license (Solo and Team) at
https://hl7guard.variantresearchgroup.com

Support: hl7guard-support@variantresearchgroup.com

One plain note: the anonymizer is a de-identification aid, not
a HIPAA certification, so review de-identified output before
sharing it.
