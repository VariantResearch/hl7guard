"""HL7Guard Free - desktop window.

The free edition's GUI: single-message validate and anonymize
(the same operations and exit codes as the free command line),
plus the viewer/editor, which the free edition includes: open a
file, read each message as labelled segments and fields, make a
minor edit, and save it. Batch work and the paid operations are
the full edition.
"""
from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace

from . import viewer
from .cli import cmd_anonymize, cmd_validate

OPERATIONS = ("validate", "anonymize")


def run_free_operation(op: str, cfg: dict) -> tuple[int, str]:
    """Headless core the window calls; returns (exit_code, text)."""
    if op not in OPERATIONS:
        return 2, f"error: unknown operation {op}"
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            if op == "validate":
                args = SimpleNamespace(
                    path=cfg.get("path", ""),
                    builtin=cfg.get("builtin") or None)
                code = cmd_validate(args)
            else:
                args = SimpleNamespace(
                    path=cfg.get("path", ""),
                    seed=cfg.get("seed") or "hl7guard-default-seed",
                    out=cfg.get("out") or None)
                code = cmd_anonymize(args)
    except Exception as exc:  # a GUI must report, never traceback
        return 2, f"error: {exc}"
    return code, buf.getvalue()


def launch() -> int:
    import tkinter as tk
    from tkinter import filedialog, scrolledtext

    from .validate import BUILTIN_PROFILES

    root = tk.Tk()
    root.title("HL7Guard Free")
    root.geometry("880x620")

    tk.Label(root, text="HL7Guard Free edition: single-message "
                        "validate and anonymize, plus the "
                        "viewer/editor.", anchor="w").pack(
        fill="x", padx=10, pady=(10, 2))

    path_var = tk.StringVar()
    seed_var = tk.StringVar(value="hl7guard-default-seed")
    out_var = tk.StringVar()
    builtin_var = tk.StringVar(value="")
    op_var = tk.StringVar(value="validate")

    def row(label):
        frame = tk.Frame(root)
        frame.pack(fill="x", padx=10, pady=3)
        tk.Label(frame, text=label, width=16, anchor="w").pack(side="left")
        return frame

    f = row("File")
    tk.Entry(f, textvariable=path_var).pack(
        side="left", fill="x", expand=True)
    tk.Button(f, text="File...",
              command=lambda: path_var.set(
                  filedialog.askopenfilename() or path_var.get())
              ).pack(side="left", padx=4)

    f = row("Operation")
    for op in OPERATIONS:
        tk.Radiobutton(f, text=op, variable=op_var, value=op).pack(
            side="left")

    f = row("Viewer / editor")
    tk.Button(f, text="Open viewer / editor for the file above",
              command=lambda: viewer.open_viewer(root, path_var.get())
              ).pack(side="left")

    f = row("Builtin profile")
    tk.OptionMenu(f, builtin_var, "",
                  *sorted(BUILTIN_PROFILES)).pack(side="left")

    f = row("Seed (anonymize)")
    tk.Entry(f, textvariable=seed_var).pack(
        side="left", fill="x", expand=True)
    tk.Label(f, text="Output folder:").pack(side="left", padx=(12, 2))
    tk.Entry(f, textvariable=out_var, width=28).pack(side="left")
    tk.Button(f, text="Folder...",
              command=lambda: out_var.set(
                  filedialog.askdirectory() or out_var.get())
              ).pack(side="left", padx=4)

    status = tk.Label(root, text="", anchor="w")
    output = scrolledtext.ScrolledText(root, wrap="word", height=20)

    def run():
        cfg = {"path": path_var.get(),
               "builtin": builtin_var.get() or None,
               "seed": seed_var.get(), "out": out_var.get() or None}
        code, text = run_free_operation(op_var.get(), cfg)
        output.delete("1.0", "end")
        output.insert("end", text)
        status.config(
            text=f"exit code: {code} "
                 f"({'clean' if code == 0 else 'findings' if code == 1 else 'error'})")

    tk.Button(root, text="Run", command=run, height=2).pack(
        fill="x", padx=10, pady=8)
    status.pack(fill="x", padx=10)
    output.pack(fill="both", expand=True, padx=10, pady=(2, 10))
    root.mainloop()
    return 0


def main() -> int:
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
