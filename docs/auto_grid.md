# Auto‑grid layout manager

`nekotk` provides a convenience function **`auto_grid`** that automatically
assigns grid positions for a collection of widgets, removing the need to
specify ``row`` and ``column`` for every element manually.

## Usage example

```python
from nekotk import App, Frame, Label, Entry, Button, auto_grid

app = App("Demo", size=(300, 200))
root = Frame(app, padding=10)

widgets = [
    (Label(root, "Username:"), {"sticky": "e"}),
    (Entry(root), {}),
    (Label(root, "Password:"), {"sticky": "e"}),
    (Entry(root, show="*"), {}),
    (Button(root, "Login", command=lambda: print("login")), {"columnspan": 2}),
]

# Place the widgets vertically with a global padding of 8 pixels.
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

The function directly calls ``grid`` on each widget and configures the parent
grid for stretchability if requested.

