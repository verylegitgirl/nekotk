# Auto‑grid layout manager

`nekotk` provides a convenience function **`auto_grid`** that automatically
places a collection of widgets in a ``tkinter`` grid without the developer
having to specify ``row``/``column`` or other layout options for each widget.

The refactored implementation adds **intelligent defaults**:

* Widgets that normally expand horizontally (e.g. ``Entry``, ``Text``,
  ``Listbox``, ``Combobox``, ``Spinbox``, ``Scale`` and ``Canvas``) automatically
  receive ``sticky="ew"`` and a ``columnspan`` of ``2``.
* All other widgets default to ``sticky="nsew"`` when ``stretch=True``.
* Global ``padx``/``pady`` padding is applied unless overridden per widget.

These defaults make it possible to build interfaces with **zero‑configuration**

The `autosize` feature enhances this capability by automatically adjusting the grid layout to accommodate the content of the widgets, ensuring optimal use of space while maintaining readability and usability.
layout code.

## Usage example

```python
from nekotk import App, Frame, Label, Entry, Button, auto_grid

# No explicit size – the window will size itself to fit its children.
app = App("Login Demo")
root = Frame(app, padding=12).grid(row=0, column=0, sticky="nsew")

widgets = [
    (Label(root, "Email:"), None),
    (Entry(root), None),
    (Label(root, "Password:"), None),
    (Entry(root, show="*"), None),
    (Button(root, "Submit", command=lambda: print("Submitted")), None),
]

# Place the widgets vertically; no per‑widget layout options are required.
auto_grid(root, widgets, orientation="vertical", padding=8)

app.run()
```

## Parameters

* **`parent`** – The container widget (e.g., a :class:`Frame`).
* **`elements`** – An iterable of ``(widget, options)`` tuples. ``options`` may
  contain any arguments accepted by ``widget.grid`` such as ``row``, ``column``,
  ``rowspan``, ``columnspan``, ``padx`` or ``pady``. Missing coordinates are
  filled automatically based on the chosen *orientation*.
* **`orientation`** – ``"vertical"`` (default) arranges widgets row‑by‑row;
  ``"horizontal"`` arranges them column‑by‑column.
* **`padding`** – Global padding applied to both ``padx`` and ``pady`` when not
  overridden per widget.
* **`stretch`** – When ``True`` (default) the grid rows and columns are given a
  weight of ``1`` so they expand to fill the container.
* **`autosize`** – When ``True`` (default) the grid automatically adjusts the size of the widgets to fit their content, ensuring optimal use of space while maintaining readability and usability. This feature is particularly useful for widgets that contain dynamic content, such as labels or text fields, and helps to prevent unnecessary scrolling or truncation of content.

The function directly calls ``grid`` on each widget and configures the parent
grid for stretchability if requested.

