"""Viewer / editor, included in the free edition.

Open a file and read each message as labelled segments and
fields (the categories below), make a minor edit, and save it.

The model half of this module (describe_message, set_field) is
headless and tested; the Tk window is a thin shell over it.
"""
from __future__ import annotations

from .parser import Message

SEGMENT_LABELS = {
    "MSH": "Message Header", "EVN": "Event Type", "PID": "Patient Identification",
    "PV1": "Patient Visit", "PV2": "Patient Visit - Additional",
    "ORC": "Common Order", "OBR": "Observation Request",
    "OBX": "Observation Result", "NK1": "Next of Kin",
    "GT1": "Guarantor", "IN1": "Insurance", "DG1": "Diagnosis",
    "AL1": "Allergy", "MSA": "Message Acknowledgment",
    "ERR": "Error", "NTE": "Notes and Comments", "SPM": "Specimen",
}

FIELD_LABELS: dict[str, dict[int, str]] = {
    "MSH": {2: "Encoding Characters", 3: "Sending Application",
            4: "Sending Facility", 5: "Receiving Application",
            6: "Receiving Facility", 7: "Date/Time of Message",
            9: "Message Type", 10: "Message Control ID",
            11: "Processing ID", 12: "Version ID"},
    "EVN": {1: "Event Type Code", 2: "Recorded Date/Time",
            6: "Event Occurred"},
    "PID": {1: "Set ID", 2: "Patient ID", 3: "Patient Identifier List",
            5: "Patient Name", 6: "Mother's Maiden Name",
            7: "Date/Time of Birth", 8: "Administrative Sex",
            9: "Patient Alias", 10: "Race", 11: "Patient Address",
            13: "Phone Number - Home", 14: "Phone Number - Business",
            18: "Patient Account Number", 19: "SSN",
            20: "Driver's License Number", 21: "Mother's Identifier",
            22: "Ethnic Group", 29: "Patient Death Date/Time",
            30: "Patient Death Indicator"},
    "PV1": {1: "Set ID", 2: "Patient Class", 3: "Assigned Patient Location",
            4: "Admission Type", 7: "Attending Doctor",
            8: "Referring Doctor", 17: "Admitting Doctor",
            19: "Visit Number", 36: "Discharge Disposition",
            44: "Admit Date/Time", 45: "Discharge Date/Time"},
    "ORC": {1: "Order Control", 2: "Placer Order Number",
            3: "Filler Order Number", 5: "Order Status",
            7: "Quantity/Timing", 9: "Date/Time of Transaction",
            12: "Ordering Provider"},
    "OBR": {1: "Set ID", 2: "Placer Order Number",
            3: "Filler Order Number", 4: "Universal Service Identifier",
            7: "Observation Date/Time", 8: "Observation End Date/Time",
            14: "Specimen Received Date/Time", 16: "Ordering Provider",
            22: "Results Rpt/Status Change - Date/Time",
            25: "Result Status", 32: "Principal Result Interpreter"},
    "OBX": {1: "Set ID", 2: "Value Type", 3: "Observation Identifier",
            4: "Observation Sub-ID", 5: "Observation Value",
            6: "Units", 7: "References Range", 8: "Interpretation Codes",
            11: "Observation Result Status", 14: "Date/Time of the Observation"},
    "NK1": {1: "Set ID", 2: "Name", 3: "Relationship", 4: "Address",
            5: "Phone Number", 6: "Business Phone Number"},
    "GT1": {1: "Set ID", 3: "Guarantor Name", 5: "Guarantor Address",
            6: "Guarantor Phone - Home", 7: "Guarantor Phone - Business",
            12: "Guarantor Insurance Number"},
    "IN1": {1: "Set ID", 2: "Insurance Plan ID", 3: "Insurance Company ID",
            4: "Insurance Company Name", 16: "Name of Insured",
            19: "Insured's Address", 36: "Policy Number"},
    "DG1": {1: "Set ID", 3: "Diagnosis Code", 4: "Diagnosis Description",
            6: "Diagnosis Type"},
    "AL1": {1: "Set ID", 2: "Allergen Type Code", 3: "Allergen Code",
            5: "Allergy Reaction Code"},
    "MSA": {1: "Acknowledgment Code", 2: "Message Control ID",
            6: "Error Condition"},
    "ERR": {3: "HL7 Error Code", 4: "Severity", 8: "User Message"},
    "NTE": {1: "Set ID", 2: "Source of Comment", 3: "Comment"},
    "SPM": {1: "Set ID", 2: "Specimen ID", 4: "Specimen Type",
            17: "Specimen Collection Date/Time"},
}


def field_label(segment: str, num: int) -> str:
    return FIELD_LABELS.get(segment, {}).get(num, f"Field {num}")


def describe_message(msg: Message) -> dict:
    """A message as labelled segments and fields, for display."""
    segments = []
    counters: dict[str, int] = {}
    for seg in msg.segments:
        counters[seg.name] = counters.get(seg.name, 0) + 1
        fields = []
        for num, value in enumerate(seg.fields, start=1):
            fields.append({
                "ref": f"{seg.name}-{num}",
                "num": num,
                "label": field_label(seg.name, num),
                "value": value,
                "components": value.split("^") if "^" in value else [],
            })
        segments.append({
            "name": seg.name,
            "instance": counters[seg.name],
            "label": SEGMENT_LABELS.get(seg.name, seg.name),
            "fields": fields,
        })
    return {"type": msg.msg_type, "control_id": msg.control_id,
            "segments": segments}


def set_field(msg: Message, segment: str, instance: int, num: int,
              value: str) -> bool:
    """Set one field on the instance-th segment with that name.
    Returns False when no such segment exists."""
    matches = msg.segments_named(segment)
    if instance < 1 or instance > len(matches):
        return False
    matches[instance - 1].set(num, value)
    return True


def open_viewer(parent, path: str) -> None:
    """Open the viewer/editor window for a file. Tk is imported
    here so the headless model never needs a display."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    from .parser import split_messages

    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            messages = split_messages(fh.read())
    except OSError as exc:
        messagebox.showerror("HL7Guard viewer", f"Cannot open {path}: {exc}",
                             parent=parent)
        return
    if not messages:
        messagebox.showinfo("HL7Guard viewer",
                            f"No HL7 messages found in {path}", parent=parent)
        return

    win = tk.Toplevel(parent)
    win.title(f"HL7Guard viewer - {path}")
    win.geometry("920x600")

    state = {"index": 0, "selection": None}

    picker = tk.Frame(win)
    picker.pack(fill="x", padx=8, pady=6)
    tk.Label(picker, text="Message:").pack(side="left")
    choices = [f"{i + 1}. {m.msg_type or '?'}  {m.control_id or ''}"
               for i, m in enumerate(messages)]
    pick_var = tk.StringVar(value=choices[0])
    menu = tk.OptionMenu(picker, pick_var, *choices)
    menu.pack(side="left", fill="x", expand=True, padx=4)

    tree = ttk.Treeview(win, columns=("label", "value"),
                        show="tree headings")
    tree.heading("#0", text="Field")
    tree.heading("label", text="Category")
    tree.heading("value", text="Value")
    tree.column("#0", width=110)
    tree.column("label", width=240)
    tree.column("value", width=520)
    tree.pack(fill="both", expand=True, padx=8)

    edit = tk.Frame(win)
    edit.pack(fill="x", padx=8, pady=6)
    tk.Label(edit, text="Edit value:").pack(side="left")
    value_var = tk.StringVar()
    tk.Entry(edit, textvariable=value_var).pack(
        side="left", fill="x", expand=True, padx=4)

    def render():
        for item in tree.get_children():
            tree.delete(item)
        state["selection"] = None
        value_var.set("")
        desc = describe_message(messages[state["index"]])
        for seg in desc["segments"]:
            seg_id = tree.insert(
                "", "end",
                text=f"{seg['name']} ({seg['instance']})",
                values=(seg["label"], ""))
            for fld in seg["fields"]:
                tree.insert(
                    seg_id, "end",
                    text=fld["ref"],
                    values=(fld["label"], fld["value"]),
                    tags=(f"{seg['name']}|{seg['instance']}|{fld['num']}",))

    def on_pick(*_args):
        state["index"] = choices.index(pick_var.get())
        render()

    def on_select(_event=None):
        sel = tree.selection()
        if not sel:
            return
        tags = tree.item(sel[0], "tags")
        if not tags:
            state["selection"] = None
            return
        name, instance, num = tags[0].split("|")
        state["selection"] = (name, int(instance), int(num))
        seg = messages[state["index"]].segments_named(name)[int(instance) - 1]
        value_var.set(seg.get(int(num)))

    def apply_edit():
        if not state["selection"]:
            return
        name, instance, num = state["selection"]
        set_field(messages[state["index"]], name, instance, num,
                  value_var.get())
        render()

    def save():
        target = filedialog.asksaveasfilename(
            parent=win, initialfile=path.split("/")[-1],
            defaultextension=".hl7")
        if not target:
            return
        with open(target, "w", encoding="utf-8", newline="") as fh:
            for m in messages:
                fh.write(m.to_hl7())
        messagebox.showinfo("HL7Guard viewer",
                            f"Saved {len(messages)} message(s) to {target}",
                            parent=win)

    pick_var.trace_add("write", on_pick)
    tree.bind("<<TreeviewSelect>>", on_select)
    tk.Button(edit, text="Apply edit", command=apply_edit).pack(side="left")
    tk.Button(edit, text="Save as...", command=save).pack(side="left", padx=6)
    render()
