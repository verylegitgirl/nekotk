"""Demo of the refactored ``auto_grid`` and zero‑configuration ``App``.

Running this script launches a small login‑style window without the caller
specifying any layout options or an explicit window size.
"""

import sys, os
# Ensure the project root (containing the ``nekotk`` package) is on ``sys.path``
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nekotk import App, Frame, Label, Entry, Button, auto_grid


def main():
    app = App("Login Demo")

    # Root container with a little padding and stretchable layout.
    root = Frame(app, padding=12).grid(row=0, column=0, sticky="nsew")


    # Simple login handler
    def handle_login():
        email = email_entry.get()
        password = password_entry.get()
        if email == "admin@example.com" and password == "secret":
            print("Login successful")
        else:
            print("Invalid credentials")

    # Create entry widgets first so we can reference them in the handler
    email_entry = Entry(root)
    password_entry = Entry(root, show="*")
    
    # Define widgets; ``None`` means we rely on the intelligent defaults.
    # Define widgets without explicit ``None`` layout options; ``auto_grid``
    # will treat missing options as an empty dict and apply its intelligent
    # defaults.
    widgets = [
        Label(root, text="Email:"),
        email_entry,
        Label(root, text="Password:"),
        password_entry,
        Button(root, text="Login", command=handle_login),
    ]

    # Place the widgets vertically; no per‑widget layout options are required.
    # Disable stretch to prevent the window from expanding indefinitely
    auto_grid(root, widgets, orientation="vertical", padding=8, stretch=False)

    app.run()


if __name__ == "__main__":
    main()

