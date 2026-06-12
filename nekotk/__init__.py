"""
nekotk — a tiny fluent wrapper around tkinter.

The module keeps the standard tkinter API available, but makes the common
workflow shorter: create an :class:`App`, add widgets, call ``pack``, ``grid`` or
``place``, and start the event loop with :meth:`App.run`.

Only the Python standard library is required. The package is compatible with
Python 3.10+.
"""

from __future__ import annotations

import re
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any, Callable, Iterable, Sequence


__all__ = [
    "App",
    "Window",
    "Frame",
    "Label",
    "Button",
    "Entry",
    "Text",
    "Listbox",
    "Combobox",
    "Spinbox",
    "Checkbutton",
    "Radiobutton",
    "Scale",
    "LabelFrame",
    "PanedWindow",
    "Separator",
    "Progressbar",
    "Canvas",
    "Menu",
    "Notebook",
    "Tab",
    "Widget",
    "Validator",
    "ValidationRule",
    "font",
    "use_theme",
]


@dataclass(frozen=True)
class ValidationRule:
    """
    One validation rule used by :class:`Validator`.

    ``check`` may return ``None``/``True`` when the value is valid, ``False`` to
    use the rule message, or a string containing a custom error message.
    """

    name: str
    check: Callable[[Any], Any]
    message: str = ""

    def __call__(self, value: Any) -> str | None:
        result = self.check(value)
        if result is None or result is True:
            return None
        if isinstance(result, str):
            return result
        return self.message or f"{self.name} validation failed"


class Validator:
    """
    Small chainable validator for widget values.

    Rules can be supplied directly to the constructor or added later with
    :meth:`add`. Widgets call :meth:`validate_value` to run all rules and show
    the first error message through ``error_var`` or ``error_label``.
    """

    def __init__(self, *rules: ValidationRule) -> None:
        self.rules: list[ValidationRule] = list(rules)

    def add(self, rule: ValidationRule) -> "Validator":
        """Append a rule and return the validator for chaining."""
        self.rules.append(rule)
        return self

    def validate(self, value: Any) -> tuple[bool, str]:
        """Return ``(is_valid, message)`` for *value*."""
        for rule in self.rules:
            message = rule(value)
            if message:
                return False, message
        return True, ""

    def is_valid(self, value: Any) -> bool:
        """Return ``True`` when *value* satisfies every rule."""
        return self.validate(value)[0]

    @staticmethod
    def required(message: str = "Field is required.") -> ValidationRule:
        """Reject ``None`` and empty strings."""

        def check(value: Any) -> str | None:
            if value is None or str(value).strip() == "":
                return message
            return None

        return ValidationRule("required", check, message)

    @staticmethod
    def min_length(length: int, message: str | None = None) -> ValidationRule:
        """Reject values shorter than *length* characters."""
        msg = message or f"Minimum length is {length}."

        def check(value: Any) -> str | None:
            if len(str(value)) < length:
                return msg
            return None

        return ValidationRule("min_length", check, msg)

    @staticmethod
    def max_length(length: int, message: str | None = None) -> ValidationRule:
        """Reject values longer than *length* characters."""
        msg = message or f"Maximum length is {length}."

        def check(value: Any) -> str | None:
            if len(str(value)) > length:
                return msg
            return None

        return ValidationRule("max_length", check, msg)

    @staticmethod
    def regex(pattern: str, message: str | None = None, flags: int = 0) -> ValidationRule:
        """Reject values that do not fully match *pattern*."""
        compiled = re.compile(pattern, flags)
        msg = message or f"Value must match {pattern!r}."

        def check(value: Any) -> str | None:
            if compiled.fullmatch(str(value)) is None:
                return msg
            return None

        return ValidationRule("regex", check, msg)

    @staticmethod
    def one_of(choices: Iterable[Any], message: str | None = None) -> ValidationRule:
        """Reject values that are not present in *choices*."""
        allowed = tuple(choices)
        msg = message or f"Value must be one of: {', '.join(map(str, allowed))}."

        def check(value: Any) -> str | None:
            if value not in allowed and str(value) not in {str(item) for item in allowed}:
                return msg
            return None

        return ValidationRule("one_of", check, msg)

    @staticmethod
    def predicate(func: Callable[[Any], Any], message: str = "Invalid value.") -> ValidationRule:
        """Run *func(value)*; ``False`` or an exception marks the value invalid."""

        def check(value: Any) -> str | None:
            try:
                result = func(value)
            except Exception as exc:  # validation should never crash the UI
                return message or str(exc)
            if result is False:
                return message
            if isinstance(result, str):
                return result
            return None

        return ValidationRule("predicate", check, message)


def font(
    family: str | None = None,
    size: int | None = None,
    weight: str | None = None,
    slant: str | None = None,
    underline: bool = False,
    overstrike: bool = False,
) -> tuple[Any, ...]:
    """Return a ``tkinter`` font specification tuple.

    ``tkinter`` requires explicit strings for *weight* and *slant* – empty
    strings are interpreted as an unknown style and raise ``TclError``. The
    helper therefore supplies the conventional defaults ``"normal"`` and
    ``"roman"`` when the caller does not specify them.
    """
    return (
        family if family is not None else "TkDefaultFont",
        size,
        weight if weight is not None else "normal",
        slant if slant is not None else "roman",
        underline,
        overstrike,
    )


def use_theme(name: str) -> str | None:
    """
    Switch the ttk theme if *name* is available.

    Returns the active theme name or ``None`` when the requested theme is not
    installed.
    """
    style = ttk.Style()
    if name in style.theme_names():
        style.theme_use(name)
        return name
    return None


class Widget:
    """
    Base wrapper for tkinter widgets.

    The wrapper stores the native widget in :attr:`widget` and delegates unknown
    attributes to it. Layout methods intentionally return the wrapper, so calls
    such as ``Button(...).grid(...)`` remain chainable.
    """

    _registry: dict[str, Callable[..., "Widget"]] = {}

    def __init__(self, parent: Any = None, **options: Any) -> None:
        self._error_var: tk.Variable[Any] | None = options.pop("error_var", None)
        self._error_label: Widget | tk.Misc | None = options.pop("error_label", None)
        self._validate_on: Any = options.pop("validate_on", None)
        self.validator: Validator | None = None
        self._validation_sequence: str | None = None
        self.parent = self._resolve_parent(parent)
        self.widget = self._create_widget(self.parent, **options)
        self._install_validation()

    @staticmethod
    def _resolve_parent(parent: Any) -> Any:
        if parent is None:
            root = getattr(tk, "_default_root", None)
            return root or tk.Tk()
        if isinstance(parent, Widget):
            return parent.widget
        return parent

    @staticmethod
    def as_widget(value: Any) -> Any:
        """Return ``value.widget`` for wrappers, otherwise *value* itself."""
        return value.widget if isinstance(value, Widget) else value

    def _create_widget(self, parent: Any, **options: Any) -> Any:
        raise NotImplementedError("Subclasses must implement _create_widget().")

    def __getattr__(self, name: str) -> Any:
        return getattr(self.widget, name)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} widget={self.widget!r}>"

    def pack(self, **options: Any) -> "Widget":
        """Pack the native widget and return the wrapper."""
        self.widget.pack(**options)
        return self

    def grid(self, **options: Any) -> "Widget":
        """Grid the native widget and return the wrapper."""
        self.widget.grid(**options)
        return self

    def place(self, **options: Any) -> "Widget":
        """Place the native widget and return the wrapper."""
        self.widget.place(**options)
        return self

    def layout(self, manager: str, **options: Any) -> "Widget":
        """Apply ``pack``, ``grid`` or ``place`` by manager name."""
        getattr(self, manager)(**options)
        return self

    def configure(self, **options: Any) -> "Widget":
        """Configure the native widget and return the wrapper."""
        self.widget.configure(**options)
        return self

    config = configure

    def bind(self, sequence: str, handler: Callable[..., Any], add: str | None = None) -> "Widget":
        """Bind *sequence* to *handler* and return the wrapper."""
        if handler is None:
            raise ValueError("handler is required")
        self.widget.bind(sequence, handler, add)
        return self

    def bind_token(self, sequence: str, handler: Callable[..., Any], add: str | None = None) -> str:
        """Bind *sequence* and return tkinter's bind token."""
        if handler is None:
            raise ValueError("handler is required")
        return self.widget.bind(sequence, handler, add)

    def unbind(self, sequence: str, funcid: str | None = None) -> "Widget":
        """Unbind *sequence* and return the wrapper."""
        self.widget.unbind(sequence, funcid)
        return self

    def on(self, sequence: str, handler: Callable[..., Any], add: str | None = None) -> "Widget":
        """Alias for :meth:`bind`."""
        return self.bind(sequence, handler, add)

    def destroy(self) -> "Widget":
        """Destroy the native widget and return the wrapper."""
        self.widget.destroy()
        return self

    def focus(self) -> "Widget":
        """Focus the native widget and return the wrapper."""
        self.widget.focus()
        return self

    def get(self) -> Any:
        """Return the widget value when the native widget supports ``get``."""
        if hasattr(self.widget, "get"):
            return self.widget.get()
        if self._has_option("text"):
            return self.widget.cget("text")
        return self.widget

    def set(self, value: Any) -> "Widget":
        """Set the widget value using ``set``, text configuration, or insertion."""
        if hasattr(self.widget, "set"):
            self.widget.set(value)
        elif hasattr(self.widget, "delete") and hasattr(self.widget, "insert"):
            self.widget.delete(0, tk.END)
            self.widget.insert(0, str(value))
        elif self._has_option("text"):
            self.widget.configure(text=value)
        else:
            raise AttributeError(f"{type(self).__name__} does not support set()")
        return self

    def text(self) -> str:
        """Return the displayed text or current value as a string."""
        if isinstance(self.widget, (tk.Text, tk.Listbox, tk.Canvas, tk.Menu, tk.PanedWindow)):
            return str(self.get())
        if hasattr(self.widget, "get") and not self._has_option("text"):
            return str(self.widget.get())
        if self._has_option("text"):
            return str(self.widget.cget("text"))
        return str(self.get())

    def set_text(self, value: Any) -> "Widget":
        """Set text when supported, otherwise delegate to :meth:`set`."""
        if self._has_option("text"):
            self.widget.configure(text=value)
        else:
            self.set(value)
        return self

    def value(self) -> Any:
        """Alias for :meth:`get`."""
        return self.get()

    def set_state(self, state: str) -> "Widget":
        """Set the widget state when supported."""
        try:
            self.widget.configure(state=state)
        except tk.TclError:
            self.widget.state([state])
        return self

    def enable(self) -> "Widget":
        """Enable the widget when supported."""
        return self.set_state("normal")

    def disable(self) -> "Widget":
        """Disable the widget when supported."""
        return self.set_state("disabled")

    def validate(self, *rules: ValidationRule) -> Validator | "Widget":
        """
        Attach validation rules to the widget.

        Passing no rules returns the current validator. Call
        :meth:`validate_value` to run the rules.
        """
        if not rules:
            return self.validator
        self.validator = Validator(*rules)
        self._install_validation()
        return self

    def clear_validation(self) -> "Widget":
        """Remove validation rules and any active validation binding."""
        self.validator = None
        if self._validation_sequence:
            self.unbind(self._validation_sequence)
            self._validation_sequence = None
        return self

    def validate_value(self, value: Any = None) -> bool:
        """Run validation and return ``True`` when the value is valid."""
        return self.validate_with_message(value)[0]

    def validate_with_message(self, value: Any = None) -> tuple[bool, str]:
        """Run validation and return ``(is_valid, message)``."""
        if self.validator is None:
            return True, ""
        current = self.get() if value is None else value
        is_valid, message = self.validator.validate(current)
        self.show_error("" if is_valid else message)
        return is_valid, message

    def is_valid(self) -> bool:
        """Return ``True`` when attached validation passes."""
        return self.validate_value()

    def show_error(self, message: str) -> "Widget":
        """Display *message* through ``error_var`` or ``error_label`` when set."""
        if self._error_var is not None:
            self._error_var.set(message)
        if self._error_label is not None:
            if isinstance(self._error_label, Widget):
                self._error_label.set_text(message)
            else:
                try:
                    self._error_label.configure(text=message)
                except tk.TclError:
                    pass
        return self

    def set_error_var(self, variable: tk.Variable[Any]) -> "Widget":
        """Use *variable* for validation error messages."""
        self._error_var = variable
        return self

    def set_error_label(self, label: Widget | tk.Misc) -> "Widget":
        """Use *label* for validation error messages."""
        self._error_label = label
        return self

    @classmethod
    def register(
        cls,
        name: str,
        factory: Callable[..., "Widget"] | None = None,
    ) -> Callable[..., "Widget"] | None:
        """
        Register a custom widget factory.

        ``Widget.create("Header", parent, text="Title")`` can then construct it
        without modifying the core classes.
        """
        if factory is None:
            def decorator(func: Callable[..., "Widget"]) -> Callable[..., "Widget"]:
                cls._registry[name] = func
                return func

            return decorator
        cls._registry[name] = factory
        return factory

    @classmethod
    def create(cls, name: str, parent: Any = None, **options: Any) -> "Widget":
        """Create a registered custom widget by name."""
        try:
            factory = cls._registry[name]
        except KeyError as exc:
            raise ValueError(f"Unknown widget factory: {name!r}") from exc
        return factory(parent, **options)

    def _has_option(self, name: str) -> bool:
        try:
            return name in self.widget.keys()
        except (tk.TclError, AttributeError):
            return False

    def _install_validation(self) -> None:
        sequence = self._validate_on
        if sequence in (True, 1, "true"):
            sequence = "<FocusOut>"
        elif isinstance(sequence, str) and not sequence.startswith("<"):
            sequence = f"<{sequence}>"
        if not sequence:
            return
        if self._validation_sequence:
            self.unbind(self._validation_sequence)
        self._validation_sequence = sequence
        self.bind(sequence, lambda _event: self.validate_value())


def auto_grid(
    parent: Any,
    elements: Sequence[tuple[Widget | Any, dict[str, Any] | None]],
    *,
    orientation: str = "vertical",
    padding: int = 5,
    stretch: bool = True,
) -> None:
    """Place *elements* in a grid without manually specifying positions.

    Parameters
    ----------
    parent:
        The container widget (e.g., a :class:`Frame`).
    elements:
        An iterable of ``(widget, options)`` tuples. ``options`` may contain any
        ``grid`` arguments such as ``row``, ``column``, ``rowspan``, ``columnspan``,
        ``padx`` or ``pady``. If ``options`` is ``None`` or missing a coordinate,
        the function assigns it automatically based on *orientation*.
    orientation:
        ``"vertical"`` (default) places widgets row‑by‑row, ``"horizontal"``
        places them column‑by‑column.
    padding:
        Global padding applied to both ``padx`` and ``pady`` when not overridden
        by per‑widget options.
    stretch:
        When ``True`` configure the grid to expand rows/columns with weight ``1``.
    """

    # Normalise the iterable
    items = []
    for entry in elements:
        if isinstance(entry, tuple) and len(entry) == 2:
            widget, opts = entry
        else:
            widget, opts = entry, {}
        items.append((Widget.as_widget(widget), opts or {}))

    # Determine placement indices
    row, col = 0, 0
    max_row, max_col = 0, 0
    for w, opts in items:
        # Use explicit coordinates if provided
        r = opts.get("row")
        c = opts.get("column")
        if r is None or c is None:
            if orientation == "vertical":
                r, c = row, 0
                row += 1
            else:
                r, c = 0, col
                col += 1
        opts.setdefault("row", r)
        opts.setdefault("column", c)
        # Intelligent defaults based on widget type
        widget_type = type(w)
        # Widgets that usually expand horizontally
        if widget_type.__name__ in {"Entry", "Text", "Listbox", "Combobox", "Spinbox", "Scale", "Canvas"}:
            opts.setdefault("sticky", "ew")
            # Give them a larger columnspan when possible (default 2)
            opts.setdefault("columnspan", 2)
        else:
            opts.setdefault("sticky", "nsew" if stretch else "")
        # Apply global padding if not overridden
        opts.setdefault("padx", padding)
        opts.setdefault("pady", padding)
        w.grid(**opts)
        max_row = max(max_row, r)
        max_col = max(max_col, c)

    # Configure stretchability
    if stretch:
        for i in range(max_row + 1):
            parent.widget.grid_rowconfigure(i, weight=1 if stretch else 0)
        for i in range(max_col + 1):
            parent.widget.grid_columnconfigure(i, weight=1 if stretch else 0)


class App(Widget):
    """
    Main application window.

    ``App`` owns the tkinter root and provides :meth:`run` to start the event
    loop. It also stores the native root widget in :attr:`widget`.
    """

    def __init__(
        self,
        title: str | None = None,
        size: tuple[int, int] | str | None = None,
        resizable: bool | tuple[bool, bool] = True,
        min_size: tuple[int, int] | None = None,
        max_size: tuple[int, int] | None = None,
        theme: str | None = None,
        **options: Any,
    ) -> None:
        super().__init__(None, **options)
        if title:
            self.widget.title(title)
        # Automatic window sizing is disabled due to known bugs. Size must be
        # provided explicitly by the caller.
        self._auto_size = False
        if size:
            self.geometry(size)
        if resizable is not None:
            if isinstance(resizable, bool):
                self.widget.resizable(resizable, resizable)
            else:
                self.widget.resizable(*resizable)
        if min_size:
            self.widget.minsize(*min_size)
        if max_size:
            self.widget.maxsize(*max_size)
        if theme:
            self.set_theme(theme)

    def _apply_auto_size(self) -> None:
        """Resize the window to fit its children respecting constraints.

        Called after the widget hierarchy has been built or when the layout
        changes at runtime. It uses ``winfo_reqwidth``/``winfo_reqheight`` to
        obtain the natural size, then clamps the result to any ``minsize`` or
        ``maxsize`` that may have been set.
        """
        if not self._auto_size:
            return
        self.widget.update_idletasks()
        width = self.widget.winfo_reqwidth()
        height = self.widget.winfo_reqheight()
        # Apply min/max constraints if they exist.
        try:
            min_w, min_h = self.widget.minsize()
        except Exception:
            min_w = min_h = None
        try:
            max_w, max_h = self.widget.maxsize()
        except Exception:
            max_w = max_h = None
        if min_w is not None:
            width = max(width, min_w)
        if min_h is not None:
            height = max(height, min_h)
        if max_w is not None and max_w > 0:
            width = min(width, max_w)
        if max_h is not None and max_h > 0:
            height = min(height, max_h)
        self.geometry((width, height))

    def _create_widget(self, parent: Any, **options: Any) -> tk.Tk:
        root = getattr(tk, "_default_root", None)
        return root or tk.Tk(**options)

    @property
    def root(self) -> tk.Tk:
        """The native tkinter root widget."""
        return self.widget

    def geometry(self, geometry: str | tuple[int, int] | None = None) -> str | "App":
        """Get or set the root geometry."""
        if geometry is None:
            return self.widget.geometry()
        if isinstance(geometry, tuple):
            width, height = geometry
            geometry = f"{width}x{height}"
        self.widget.geometry(geometry)
        return self

    def title(self, title: str | None = None) -> str | "App":
        """Get or set the window title."""
        if title is None:
            return self.widget.title()
        self.widget.title(title)
        return self

    def set_theme(self, name: str) -> str | None:
        """Switch the ttk theme and return the active theme name."""
        return use_theme(name)

    def center(self) -> "App":
        """Center the window on the primary monitor."""
        self.widget.update_idletasks()
        width = self.widget.winfo_reqwidth()
        height = self.widget.winfo_reqheight()
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.widget.geometry(f"{width}x{height}+{x}+{y}")
        return self

    def protocol(self, name: str | None = None, func: Callable[..., Any] | None = None) -> Any:
        """Get or set a window-manager protocol handler."""
        if name is None:
            return self.widget.protocol()
        self.widget.protocol(name, func)
        return self

    def option_add(self, pattern: str, value: Any, priority: int | None = None) -> "App":
        """Add a tkinter option database entry."""
        if priority is None:
            self.widget.option_add(pattern, value)
        else:
            self.widget.option_add(pattern, value, priority)
        return self

    def run(self) -> "App":
        """Start the tkinter main loop and return the app when it exits."""
        self.widget.mainloop()
        return self

    mainloop = run

    def quit(self) -> "App":
        """Stop the main loop."""
        self.widget.quit()
        return self

    def destroy(self) -> "App":
        """Destroy the root window."""
        self.widget.destroy()
        return self


class Window(Widget):
    """Secondary top-level window."""

    def __init__(
        self,
        parent: Any = None,
        title: str | None = None,
        size: tuple[int, int] | str | None = None,
        resizable: bool | tuple[bool, bool] = True,
        min_size: tuple[int, int] | None = None,
        max_size: tuple[int, int] | None = None,
        transient: bool = True,
        **options: Any,
    ) -> None:
        super().__init__(parent, **options)
        if title:
            self.widget.title(title)
        if size:
            self.geometry(size)
        if resizable is not None:
            if isinstance(resizable, bool):
                self.widget.resizable(resizable, resizable)
            else:
                self.widget.resizable(*resizable)
        if min_size:
            self.widget.minsize(*min_size)
        if max_size:
            self.widget.maxsize(*max_size)
        if transient and isinstance(parent, (App, Window)):
            self.widget.transient(parent.widget)

    def _create_widget(self, parent: Any, **options: Any) -> tk.Toplevel:
        return tk.Toplevel(parent, **options)

    def geometry(self, geometry: str | tuple[int, int] | None = None) -> str | "Window":
        if geometry is None:
            return self.widget.geometry()
        if isinstance(geometry, tuple):
            width, height = geometry
            geometry = f"{width}x{height}"
        self.widget.geometry(geometry)
        return self

    def title(self, title: str | None = None) -> str | "Window":
        if title is None:
            return self.widget.title()
        self.widget.title(title)
        return self

    def protocol(self, name: str | None = None, func: Callable[..., Any] | None = None) -> Any:
        if name is None:
            return self.widget.protocol()
        self.widget.protocol(name, func)
        return self

    def center(self) -> "Window":
        self.widget.update_idletasks()
        width = self.widget.winfo_reqwidth()
        height = self.widget.winfo_reqheight()
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.widget.geometry(f"{width}x{height}+{x}+{y}")
        return self


class Frame(Widget):
    """Container widget for grouping other widgets."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Frame:
        padding = options.pop("padding", None)
        if padding is not None:
            if isinstance(padding, (tuple, list)) and len(padding) == 4:
                options.setdefault("padx", (padding[0], padding[2]))
                options.setdefault("pady", (padding[1], padding[3]))
            else:
                options.setdefault("padx", padding)
                options.setdefault("pady", padding)
        return tk.Frame(parent, **options)

    def add(self, child: Widget | tk.Misc, **layout_options: Any) -> Widget | tk.Misc:
        """Add a child and optionally lay it out with ``pack``, ``grid`` or ``place``."""
        child_widget = self.as_widget(child)
        if layout_options:
            manager = layout_options.pop("manager", "pack")
            getattr(child_widget, manager)(**layout_options)
        return child


class Label(Widget):
    """Text or image label."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Label:
        return tk.Label(parent, **options)


class Button(Widget):
    """Clickable button with a ``command`` callback."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Button:
        return tk.Button(parent, **options)

    def invoke(self) -> "Button":
        """Invoke the button command programmatically."""
        self.widget.invoke()
        return self


class Entry(Widget):
    """Single-line text input."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Entry:
        return tk.Entry(parent, **options)

    def clear(self) -> "Entry":
        """Delete all text."""
        self.widget.delete(0, tk.END)
        return self

    def select_all(self) -> "Entry":
        """Select the whole content and move the cursor to the end."""
        self.widget.selection_range(0, tk.END)
        self.widget.icursor(tk.END)
        return self


class Text(Widget):
    """Multi-line text widget."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Text:
        return tk.Text(parent, **options)

    def get(self) -> str:
        """Return the full text content without trailing newline."""
        return self.widget.get("1.0", tk.END).rstrip("\n")

    def clear(self) -> "Text":
        """Delete all text."""
        self.widget.delete("1.0", tk.END)
        return self

    def append(self, value: Any, newline: bool = False) -> "Text":
        """Append text at the end and scroll to it."""
        suffix = "\n" if newline else ""
        self.widget.insert(tk.END, f"{value}{suffix}")
        self.widget.see(tk.END)
        return self


class Listbox(Widget):
    """Listbox with optional initial values."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Listbox:
        values = options.pop("values", None)
        widget = tk.Listbox(parent, **options)
        if values is not None:
            if isinstance(values, str):
                values = (values,)
            for value in values:
                widget.insert(tk.END, value)
        return widget

    def add(self, *items: Any) -> "Listbox":
        """Append items."""
        for item in items:
            self.widget.insert(tk.END, item)
        return self

    def clear(self) -> "Listbox":
        """Remove all items."""
        self.widget.delete(0, tk.END)
        return self

    def selected(self) -> list[Any]:
        """Return selected items."""
        return [self.widget.get(index) for index in self.widget.curselection()]

    def get(self) -> list[Any]:
        """Return all items in the listbox."""
        return list(self.widget.get(0, tk.END))


class Combobox(Widget):
    """``ttk.Combobox`` with optional values."""

    def _create_widget(self, parent: Any, **options: Any) -> ttk.Combobox:
        values = options.pop("values", None)
        widget = ttk.Combobox(parent, **options)
        if values is not None:
            widget.configure(values=(values,) if isinstance(values, str) else tuple(values))
        return widget

    def values(self) -> tuple[Any, ...]:
        """Return configured values."""
        return tuple(self.widget.cget("values"))

    def set_values(self, values: Iterable[Any]) -> "Combobox":
        """Replace configured values."""
        self.widget.configure(values=tuple(values))
        return self


class Spinbox(Widget):
    """Numeric or value spinbox."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Spinbox:
        return tk.Spinbox(parent, **options)


class Checkbutton(Widget):
    """Checkbutton with a boolean-like value."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Checkbutton:
        return tk.Checkbutton(parent, **options)

    def checked(self) -> bool:
        """Return whether the checkbutton is selected."""
        return bool(int(self.widget.get()))


class Radiobutton(Widget):
    """Radiobutton for grouped choices."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Radiobutton:
        return tk.Radiobutton(parent, **options)

    def selected(self) -> bool:
        """Return whether the radiobutton is selected."""
        return bool(int(self.widget.get()))


class Scale(Widget):
    """Slider scale."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Scale:
        return tk.Scale(parent, **options)


class LabelFrame(Widget):
    """Labeled container frame."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.LabelFrame:
        padding = options.pop("padding", None)
        if padding is not None:
            if isinstance(padding, (tuple, list)) and len(padding) == 4:
                options.setdefault("padx", (padding[0], padding[2]))
                options.setdefault("pady", (padding[1], padding[3]))
            else:
                options.setdefault("padx", padding)
                options.setdefault("pady", padding)
        return tk.LabelFrame(parent, text=options.pop("text", ""), **options)


class PanedWindow(Widget):
    """Container with draggable panes."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.PanedWindow:
        return tk.PanedWindow(parent, **options)

    def add(self, child: Widget | tk.Misc, **options: Any) -> "PanedWindow":
        self.widget.add(self.as_widget(child), **options)
        return self

    def remove(self, child: Widget | tk.Misc) -> "PanedWindow":
        self.widget.remove(self.as_widget(child))
        return self


class Separator(Widget):
    """``ttk.Separator``."""

    def _create_widget(self, parent: Any, **options: Any) -> ttk.Separator:
        return ttk.Separator(parent, **options)


class Progressbar(Widget):
    """``ttk.Progressbar``."""

    def _create_widget(self, parent: Any, **options: Any) -> ttk.Progressbar:
        return ttk.Progressbar(parent, **options)

    def start(self, interval: int | None = None) -> "Progressbar":
        self.widget.start(interval)
        return self

    def stop(self) -> "Progressbar":
        self.widget.stop()
        return self

    def step(self, amount: int = 1) -> "Progressbar":
        self.widget.step(amount)
        return self


class Canvas(Widget):
    """Drawing canvas."""

    def _create_widget(self, parent: Any, **options: Any) -> tk.Canvas:
        return tk.Canvas(parent, **options)

    def clear(self) -> "Canvas":
        """Delete all canvas items."""
        self.widget.delete("all")
        return self


class Menu(Widget):
    """
    Menu wrapper.

    Use :meth:`add_command`, :meth:`add_separator` and :meth:`add_cascade`, then
    call :meth:`attach` to install it on an :class:`App` or :class:`Window`.
    """

    def _create_widget(self, parent: Any, **options: Any) -> tk.Menu:
        if parent is None:
            parent = getattr(tk, "_default_root", None) or tk.Tk()
        elif isinstance(parent, Widget):
            parent = parent.widget
        return tk.Menu(parent, **options)

    def add_command(self, label: str | None = None, command: Callable[..., Any] | None = None, **options: Any) -> "Menu":
        if label is not None:
            options["label"] = label
        if command is not None:
            options["command"] = command
        self.widget.add_command(**options)
        return self

    def add_checkbutton(
        self,
        label: str | None = None,
        variable: tk.Variable[Any] | None = None,
        command: Callable[..., Any] | None = None,
        **options: Any,
    ) -> "Menu":
        if label is not None:
            options["label"] = label
        if variable is not None:
            options["variable"] = variable
        if command is not None:
            options["command"] = command
        self.widget.add_checkbutton(**options)
        return self

    def add_radiobutton(
        self,
        label: str | None = None,
        variable: tk.Variable[Any] | None = None,
        value: Any = None,
        command: Callable[..., Any] | None = None,
        **options: Any,
    ) -> "Menu":
        if label is not None:
            options["label"] = label
        if variable is not None:
            options["variable"] = variable
        if value is not None:
            options["value"] = value
        if command is not None:
            options["command"] = command
        self.widget.add_radiobutton(**options)
        return self

    def add_separator(self, **options: Any) -> "Menu":
        self.widget.add_separator(**options)
        return self

    def add_cascade(self, label: str, menu: Widget | tk.Menu, **options: Any) -> "Menu":
        options["label"] = label
        options["menu"] = self.as_widget(menu)
        self.widget.add_cascade(**options)
        return self

    def attach(self, parent: Any = None) -> "Menu":
        """Attach the menu to a root/top-level window."""
        target = self._resolve_parent(parent) if parent is not None else self.widget.master
        try:
            target.configure(menu=self.widget)
        except tk.TclError:
            pass
        return self

    def popup(self, event: tk.Event[Any]) -> "Menu":
        """Show the menu as a context menu at a tkinter event position."""
        self.widget.tk_popup(event.x_root, event.y_root)
        return self


class Notebook(Widget):
    """``ttk.Notebook`` tab container."""

    def _create_widget(self, parent: Any, **options: Any) -> ttk.Notebook:
        return ttk.Notebook(parent, **options)

    def add(self, child: Widget | tk.Misc, **options: Any) -> "Notebook":
        """Add a tab child to the notebook."""
        self.widget.add(self.as_widget(child), **options)
        return self

    def add_tab(self, title: str, *, factory: Callable[..., Widget] = Frame, **options: Any) -> Widget:
        """Create a tab, add it to the notebook and return the tab wrapper."""
        tab = factory(self, **options)
        self.add(tab, text=title)
        return tab

    def select(self, index_or_widget: Widget | tk.Misc | int | str | None = None) -> str | "Notebook":
        """Get the selected tab id or select a tab."""
        if index_or_widget is None:
            return self.widget.select()
        self.widget.select(self.as_widget(index_or_widget))
        return self

    def forget(self, index_or_widget: Widget | tk.Misc | int | str) -> "Notebook":
        """Remove a tab."""
        self.widget.forget(self.as_widget(index_or_widget))
        return self


class Tab(Frame):
    """Convenience tab frame automatically added to a notebook."""

    def __init__(self, parent: Notebook | ttk.Notebook, title: str, **options: Any) -> None:
        super().__init__(parent, **options)
        notebook = self.as_widget(parent)
        notebook.add(self.widget, text=title)


# Backwards-friendly aliases for users who prefer lowercase constructors.
FrameWidget = Frame
LabelWidget = Label
ButtonWidget = Button
EntryWidget = Entry
TextWidget = Text
ListboxWidget = Listbox
ComboboxWidget = Combobox
