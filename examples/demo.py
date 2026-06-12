"""
Minimal example for nekotk.

Run with: ``python -m examples.demo`` or ``python examples/demo.py`` from the
project root. The script adjusts ``sys.path`` so that the ``nekotk`` package can
be imported when the current working directory is the project root.
"""

import sys
from pathlib import Path

# Ensure the project root (parent of this file) is on ``sys.path``.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from nekotk import App, Button, Combobox, Entry, Frame, Label, Listbox, Notebook, Validator, font


def save():
    if not email.validate_value():
        return
    print({
        "name": name.text(),
        "email": email.text(),
        "role": role.text(),
        "skills": skills.selected(),
    })


app = App("Employee Form", size=(520, 360), resizable=False)
root = Frame(app, padding=12).grid(sticky="nsew")
app.root.columnconfigure(0, weight=1)
app.root.rowconfigure(0, weight=1)

Label(root, text="Employee Form").grid(row=0, column=0, columnspan=2, pady=(0, 12))

Label(root, text="Name:").grid(row=1, column=0, sticky="w")
name = Entry(root, width=35).grid(row=1, column=1, sticky="ew")
name.validate(Validator.required("Name is required."))

Label(root, text="Email:").grid(row=2, column=0, sticky="w")
email = Entry(root, width=35, validate_on=True).grid(row=2, column=1, sticky="ew")
email.validate(
    Validator.required("Email is required."),
    Validator.regex(r".+@.+\..+", "Enter a valid email."),
)

Label(root, text="Role:").grid(row=3, column=0, sticky="w")
role = Combobox(root, values=("Developer", "Designer", "Manager"), state="readonly").grid(row=3, column=1, sticky="ew")
role.set("Developer")

Label(root, text="Skills:").grid(row=4, column=0, sticky="nw")
skills = Listbox(root, values=("Python", "tkinter", "UI design"), height=4, selectmode="extended").grid(row=4, column=1, sticky="ew")
skills.selection_set(0)

tabs = Notebook(root).grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
notes = tabs.add_tab("Notes")
Entry(notes).pack(fill="x", padx=8, pady=8)

Button(root, text="Save", command=save, bg="#4f81bd", fg="white", width=12).grid(row=6, column=1, sticky="e", pady=(12, 0))
Button(root, text="Close", command=app.quit, width=12).grid(row=6, column=0, sticky="w", pady=(12, 0))

app.run()
