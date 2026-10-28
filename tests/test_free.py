"""Free-edition tests: the free features work, the paid features
are absent (not locked - not present), and input fails closed."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hl7guard.cli import main  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
SAMPLE = os.path.join(ROOT, "samples", "synthetic_oru_r01.hl7")
ADT = os.path.join(ROOT, "samples", "synthetic_adt_a01.hl7")


def test_validate_clean_sample_exits_zero(capsys):
    assert main(["validate", SAMPLE]) == 0


def test_validate_with_builtin_profile(capsys):
    assert main(["validate", ADT, "--builtin", "adt_a01"]) == 0


def test_validate_broken_message_exits_one(tmp_path):
    # An ADT^A01 with no PID or PV1 fails the built-in ADT profile.
    f = tmp_path / "broken.hl7"
    f.write_text("MSH|^~\\&|A|B|C|D|20260101||ADT^A01|1|P|2.5\rEVN|A01|20260101\r")
    assert main(["validate", str(f), "--builtin", "adt_a01"]) == 1


def test_multi_message_file_is_a_free_limit_not_a_pass(tmp_path):
    text = open(SAMPLE, encoding="utf-8").read()
    f = tmp_path / "two.hl7"
    f.write_text(text + "\r" + text)
    assert main(["validate", str(f)]) == 2


def test_garbage_input_fails_closed(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("just some meeting notes\n")
    assert main(["validate", str(f)]) == 2


def test_anonymize_removes_identifiers_and_is_consistent(tmp_path):
    out = tmp_path / "out"
    assert main(["anonymize", SAMPLE, "--seed", "s1",
                 "--out", str(out)]) == 0
    text = (out / os.path.basename(SAMPLE)).read_text(encoding="utf-8")
    for identifier in ("SYN12345", "Synthetic", "Sample", "198001010000",
                       "Fictional St", "555-010-2000", "999-99-9999"):
        assert identifier not in text, identifier
    assert "OBX" in text  # the clinical content survives


def test_paid_modules_are_not_in_this_edition():
    pkg = os.path.join(ROOT, "src", "hl7guard")
    for name in ("diff.py", "generate.py", "census.py", "verify.py",
                 "mllp.py", "report.py", "gui.py", "license.py"):
        assert not os.path.exists(os.path.join(pkg, name)), name


def test_no_license_machinery_anywhere_in_the_source():
    pkg = os.path.join(ROOT, "src", "hl7guard")
    for name in os.listdir(pkg):
        if name.endswith(".py"):
            text = open(os.path.join(pkg, name),
                        encoding="utf-8").read()
            assert "HL7G2" not in text, name
            assert "PUBLIC_KEY" not in text, name
