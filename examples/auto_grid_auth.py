"""Demo script showing a simple login form using ``auto_grid``.

Run the demo with ``python -m examples.auto_grid_auth`` or by importing the module
and calling :func:`run`.
"""

from nekotk import App, Frame, Label, Entry, Button, auto_grid


def run() -> None:
    """Create a window with username and password fields.

    The entered values are printed to the console when the *Login* button is
    pressed.
    """
    app = App("Login Demo", size=(300, 150))
    root = Frame(app, padding=10)
    # Place the root frame in the app window using grid so its children become visible
    root.grid(row=0, column=0, sticky="nsew")

    # Define widgets and optional grid options
    # Create entry widgets first so they can be referenced in the button callback
    username_entry = Entry(root)
    password_entry = Entry(root, show="*")

    widgets = [
        (Label(root, text="Username:"), {"sticky": "e"}),
        (username_entry, {}),
        (Label(root, text="Password:"), {"sticky": "e"}),
        (password_entry, {}),
        (Button(root, text="Login", command=lambda: _on_login(username_entry, password_entry),
        ),
            {"columnspan": 2, "sticky": "ew"},
        ),
    ]

    # Place widgets vertically with a small padding
    auto_grid(root, widgets, orientation="vertical", padding=5)

    # Keep references to the entry widgets for the callback (now stored in variables above)

    app.run()


def _on_login(username: Entry, password: Entry) -> None:
    """Callback for the *Login* button – prints entered credentials."""
    print("Username:", username.text())
    print("Password:", password.text())


if __name__ == "__main__":
    run()

