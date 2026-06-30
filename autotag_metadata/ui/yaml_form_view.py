"""Form-based YAML editor: dict nodes as collapsible sections, leaves as typed inputs."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2026 Johannes Hermann
#
#  autotag-metadata is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  autotag-metadata is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with autotag-metadata. If not, see
#  <https://www.gnu.org/licenses/>.
# ********************************************************************

from PyQt6 import QtCore, QtGui, QtWidgets

# ---------------------------------------------------------------------------
# Visual constants & palette helpers
# ---------------------------------------------------------------------------

# Semantic accent per value type, used only as a thin left border on inputs.
# Mid-tone hues chosen to read on both light and dark backgrounds; the input
# widget kind (checkbox/spinbox/lineedit) already conveys type, so colour is a
# secondary cue (never the only one).
_TYPE_BORDER: dict[type, str] = {
    bool: "#9b59b6",  # purple
    int: "#27ae60",  # green
    float: "#e67e22",  # orange
    list: "#e74c3c",  # red
    type(None): "#95a5a6",  # gray
}
_STR_BORDER = "#3498db"  # blue — default / str

_Role = QtGui.QPalette.ColorRole

#: Glyph for the per-row "filter to this subtree/value" button.
_ZOOM_GLYPH = "⤢"


def _border_color(val) -> str:
    return _TYPE_BORDER.get(type(val), _STR_BORDER)


def _child_path(prefix: str, key) -> str:
    """Dotted path of *key* under *prefix* (numeric keys address list indices)."""
    return f"{prefix}.{key}" if prefix else str(key)


def _shrinkable(widget: QtWidgets.QWidget) -> None:
    """Let *widget* shrink below its size hint (down to zero width).

    A narrow panel then squeezes the value/label/heading instead of overflowing,
    so the fixed-width filter button on the right is never clipped. ``Ignored``
    keeps the grow behaviour (the widget still fills available width) but drops
    the size-hint floor that would otherwise force the row wider than the panel.
    """
    policy = widget.sizePolicy()
    policy.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Ignored)
    widget.setSizePolicy(policy)


def _make_zoom_button(rel_path: str | None, on_zoom) -> QtWidgets.QToolButton:
    """Small button that filters the panel down to *rel_path* when clicked."""
    btn = QtWidgets.QToolButton()
    btn.setText(_ZOOM_GLYPH)
    btn.setAutoRaise(True)
    btn.setFixedWidth(22)
    btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    btn.setToolTip(f"Filter the view to “{rel_path}”")
    btn.clicked.connect(lambda: on_zoom(rel_path))
    return btn


def _blend(c1: QtGui.QColor, c2: QtGui.QColor, t: float) -> QtGui.QColor:
    """Linearly interpolate between two colours (t in 0..1)."""
    return QtGui.QColor(
        round(c1.red() * (1 - t) + c2.red() * t),
        round(c1.green() * (1 - t) + c2.green() * t),
        round(c1.blue() * (1 - t) + c2.blue() * t),
    )


def _row_color(palette: QtGui.QPalette, even: bool) -> QtGui.QColor:
    """Zebra-stripe background drawn from the active palette (theme-aware)."""
    return palette.color(_Role.AlternateBase if even else _Role.Base)


def _header_colors(palette: QtGui.QPalette, depth: int) -> tuple[str, str]:
    """Depth-shaded header background/foreground derived from the palette.

    Shades the neutral button colour toward the text colour as depth grows, so
    nested sections stay distinguishable in both light and dark themes.
    """
    neutral = palette.color(_Role.Button)
    text = palette.color(_Role.WindowText)
    fraction = min(0.12 + depth * 0.12, 0.6)
    bg = _blend(neutral, text, fraction)
    fg = "#ffffff" if bg.lightness() < 128 else "#000000"
    return bg.name(), fg


def _input_stylesheet(val, palette: QtGui.QPalette) -> str:
    accent = _border_color(val)
    edge = palette.color(_Role.Mid).name()
    base = (
        f"border-left: 3px solid {accent};"
        f" border-top: 1px solid {edge};"
        f" border-right: 1px solid {edge};"
        f" border-bottom: 1px solid {edge};"
        " border-radius: 0px;"
        " padding: 2px 4px;"
    )
    cls = type(val).__name__
    return f"Q{cls.capitalize()}Edit {{ {base} }} QSpinBox {{ {base} }} QDoubleSpinBox {{ {base} }}"


# ---------------------------------------------------------------------------
# _FieldRow
# ---------------------------------------------------------------------------


class _FieldRow(QtWidgets.QWidget):
    """One key/value row: colored background, right-aligned label, typed input."""

    def __init__(
        self,
        key: str,
        val,
        node: dict,
        even: bool,
        callback,
        zoom_path: str | None = None,
        on_zoom=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, _row_color(palette, even))
        self.setPalette(palette)

        label = QtWidgets.QLabel(str(key))
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        label.setFixedWidth(130)
        label.setStyleSheet("font-size: 12px; padding-right: 6px;")

        widget = _make_input_widget(val)
        widget.setStyleSheet(_input_stylesheet(val, widget.palette()))
        _connect_widget(widget, val, node, key, callback)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 6, 2)
        layout.setSpacing(0)
        layout.addWidget(label)
        layout.addWidget(widget, 1)
        if on_zoom is not None:
            layout.addWidget(_make_zoom_button(zoom_path, on_zoom))


# ---------------------------------------------------------------------------
# _ValueUnitRow
# ---------------------------------------------------------------------------


class _ValueUnitRow(QtWidgets.QWidget):
    """Inline row for scalar-only dicts that contain a 'value' key.

    Shows: key_label | value_widget (stretch) | unit_widget (narrow) | extra fields...
    """

    def __init__(self, key: str, val_dict: dict, even: bool, callback, zoom_path=None, on_zoom=None, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, _row_color(palette, even))
        self.setPalette(palette)

        key_label = QtWidgets.QLabel(str(key))
        key_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        key_label.setFixedWidth(130)
        key_label.setStyleSheet("font-size: 12px; padding-right: 6px;")

        # Order: value first, unit second, rest alphabetically.
        ordered = ["value"] if "value" in val_dict else []
        if "unit" in val_dict:
            ordered.append("unit")
        for k in val_dict:
            if k not in ordered:
                ordered.append(k)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 6, 2)
        layout.setSpacing(4)
        layout.addWidget(key_label)

        for k in ordered:
            v = val_dict[k]
            widget = _make_input_widget(v)
            widget.setStyleSheet(_input_stylesheet(v, widget.palette()))
            _connect_widget(widget, v, val_dict, k, callback)

            if k == "value":
                layout.addWidget(widget, 2)
            elif k == "unit":
                widget.setMaximumWidth(90)
                layout.addWidget(widget, 1)
            else:
                field_lbl = QtWidgets.QLabel(f"{k}:")
                field_lbl.setStyleSheet("font-size: 11px;")
                _shrinkable(field_lbl)
                widget.setMaximumWidth(80)
                layout.addWidget(field_lbl)
                layout.addWidget(widget, 1)

        if on_zoom is not None:
            layout.addWidget(_make_zoom_button(zoom_path, on_zoom))


# ---------------------------------------------------------------------------
# _CollapsibleBox
# ---------------------------------------------------------------------------


class _CollapsibleBox(QtWidgets.QWidget):
    """Collapsible section with depth-tinted header."""

    def __init__(self, title: str, depth: int = 0, zoom_path=None, on_zoom=None, parent=None):
        super().__init__(parent)
        bg, fg = _header_colors(self.palette(), depth)

        self._toggle_btn = QtWidgets.QToolButton()
        self._toggle_btn.setStyleSheet(
            f"QToolButton {{"
            f"  background: {bg}; color: {fg};"
            f"  border: none; font-weight: bold;"
            f"  text-align: left; padding: 5px 8px;"
            f"}}"
            f"QToolButton:hover {{ background: {bg}dd; }}"
        )
        self._toggle_btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle_btn.setArrowType(QtCore.Qt.ArrowType.DownArrow)
        self._toggle_btn.setText(title)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        # Let a long heading clip rather than widen the row past the panel, so the
        # trailing filter button is never pushed out of view.
        _shrinkable(self._toggle_btn)
        self._toggle_btn.clicked.connect(self._on_toggle)

        self._content = QtWidgets.QWidget()
        self._content.setContentsMargins(0, 0, 0, 0)

        # The toggle fills the header; an optional filter button sits at its right.
        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(0)
        header.addWidget(self._toggle_btn, 1)
        if on_zoom is not None:
            header.addWidget(_make_zoom_button(zoom_path, on_zoom))

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self._content)

    def set_content_layout(self, content_layout: QtWidgets.QLayout) -> None:
        old = self._content.layout()
        if old:
            QtWidgets.QWidget().setLayout(old)
        self._content.setLayout(content_layout)

    def _on_toggle(self, checked: bool) -> None:
        self._toggle_btn.setArrowType(QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow)
        self._content.setVisible(checked)


# ---------------------------------------------------------------------------
# YamlFormView
# ---------------------------------------------------------------------------


class YamlFormView(QtWidgets.QScrollArea):
    """Renders a nested dict as a form: collapsible sections per dict, typed rows per leaf.

    Emits ``data_changed`` with the full updated dict on any field edit.

    Usage::

        form = YamlFormView()
        form.data_changed.connect(on_changed)
        form.load({"measurement": {"name": "test", "rate": 10}})
    """

    data_changed = QtCore.pyqtSignal(object)  # dict, or list for a list-rooted subtree
    zoom_requested = QtCore.pyqtSignal(str)  # relative dotted path of a row's subtree/value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        # Never scroll horizontally: rows shrink to the viewport so the trailing
        # filter button stays visible at any panel width (it would otherwise be
        # the first thing scrolled out of view by a wide value or heading).
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._data: dict | list = {}
        self._zoom_enabled = True
        self._root_widget = QtWidgets.QWidget()
        self._root_layout = QtWidgets.QVBoxLayout(self._root_widget)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(2)
        self._root_layout.addStretch()
        self.setWidget(self._root_widget)
        # Restoring a saved scroll position must wait until the content has been
        # laid out and the scrollbar range exists, so apply it on rangeChanged.
        self._target_scroll: tuple[int, int] | None = None
        self.verticalScrollBar().rangeChanged.connect(self._apply_target_scroll)

    def scroll_position(self) -> tuple[int, int]:
        """Current (horizontal, vertical) scroll offset."""
        return (self.horizontalScrollBar().value(), self.verticalScrollBar().value())

    def set_scroll_position(self, horizontal: int, vertical: int) -> None:
        """Scroll to (horizontal, vertical), re-applying once the range is known."""
        self._target_scroll = (horizontal, vertical)
        self._apply_target_scroll()

    def _apply_target_scroll(self, *args) -> None:
        if self._target_scroll is None:
            return
        horizontal, vertical = self._target_scroll
        self.horizontalScrollBar().setValue(horizontal)
        self.verticalScrollBar().setValue(vertical)
        if self.verticalScrollBar().value() == vertical:
            self._target_scroll = None  # reached; stop forcing on later range changes

    def load(self, data: dict | list) -> None:
        """Replace current form with widgets built from *data*.

        *data* is usually a mapping, but a panel zoomed directly onto a
        list-valued path (e.g. ``electrolyte.components``) loads a list.
        """
        self._data = _deep_copy(data)
        self._rebuild()

    def collect(self) -> dict | list:
        """Return current form values as a nested dict (or list)."""
        return _deep_copy(self._data)

    def set_zoom_enabled(self, enabled: bool) -> None:
        """Whether rows carry a "filter to this row" button (takes effect on next load).

        Disabled for a scalar-leaf panel, whose synthetic single row has no
        meaningful subtree to drill into.
        """
        self._zoom_enabled = enabled

    # ------------------------------------------------------------------

    def _zoom_cb(self):
        """The per-row filter callback, or None when zoom buttons are suppressed."""
        return self._emit_zoom if self._zoom_enabled else None

    def _emit_zoom(self, rel_path: str) -> None:
        self.zoom_requested.emit(rel_path)

    def _rebuild(self) -> None:
        _clear_layout(self._root_layout)
        if isinstance(self._data, list):
            self._build_list_items(self._root_layout, self._data, depth=0, prefix="")
        else:
            self._build_rows(self._root_layout, self._data, depth=0, prefix="")
        self._root_layout.addStretch()

    def _build_rows(self, layout: QtWidgets.QVBoxLayout, node: dict, depth: int, prefix: str = "") -> None:
        """Populate *layout* with widgets for each key in *node*."""
        cb = self._zoom_cb()
        leaf_index = 0
        for key, val in node.items():
            child = _child_path(prefix, key)
            if _is_value_unit_dict(val):
                row = _ValueUnitRow(str(key), val, leaf_index % 2 == 0, self._on_value_changed, child, cb)
                layout.addWidget(row)
                leaf_index += 1
            elif isinstance(val, dict):
                box = _CollapsibleBox(str(key), depth, child, cb)
                inner = QtWidgets.QVBoxLayout()
                inner.setContentsMargins(depth * 4, 0, 0, 0)
                inner.setSpacing(1)
                self._build_rows(inner, val, depth + 1, child)
                box.set_content_layout(inner)
                layout.addWidget(box)
            elif isinstance(val, list) and _is_list_of_dicts(val):
                box = self._build_list_box(str(key), val, depth, child)
                layout.addWidget(box)
            else:
                row = _FieldRow(str(key), val, node, leaf_index % 2 == 0, self._on_value_changed, child, cb)
                layout.addWidget(row)
                leaf_index += 1

    def _build_list_box(self, title: str, items: list, depth: int, prefix: str) -> _CollapsibleBox:
        outer = _CollapsibleBox(title, depth, prefix, self._zoom_cb())
        inner_layout = QtWidgets.QVBoxLayout()
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(2)
        self._build_list_items(inner_layout, items, depth + 1, prefix)
        outer.set_content_layout(inner_layout)
        return outer

    def _build_list_items(self, layout: QtWidgets.QVBoxLayout, items: list, depth: int, prefix: str = "") -> None:
        """Populate *layout* with one collapsible box per dict item (or a label)."""
        cb = self._zoom_cb()
        for i, item in enumerate(items):
            child = _child_path(prefix, i)
            if isinstance(item, dict):
                label = item.get("name", str(i))
                heading = f"[{i}]  {label}" if label != str(i) else f"[{i}]"
                item_box = _CollapsibleBox(heading, depth, child, cb)
                item_inner = QtWidgets.QVBoxLayout()
                item_inner.setContentsMargins(0, 0, 0, 0)
                item_inner.setSpacing(1)
                self._build_rows(item_inner, item, depth + 1, child)
                item_box.set_content_layout(item_inner)
                layout.addWidget(item_box)
            else:
                layout.addWidget(_make_scalar_item_row(str(item), child, cb))

    def _on_value_changed(self) -> None:
        self.data_changed.emit(_deep_copy(self._data))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scalar_item_row(text: str, zoom_path: str, on_zoom) -> QtWidgets.QWidget:
    """A read-only scalar list element with an optional filter button."""
    row = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(row)
    layout.setContentsMargins(8, 2, 6, 2)
    layout.setSpacing(0)
    label = QtWidgets.QLabel(text)
    _shrinkable(label)  # clip long elements rather than push the button off-screen
    layout.addWidget(label, 1)
    if on_zoom is not None:
        layout.addWidget(_make_zoom_button(zoom_path, on_zoom))
    return row


def _make_input_widget(val) -> QtWidgets.QWidget:
    w = _build_input_widget(val)
    # Allow the input to shrink below its size hint so a narrow panel never
    # overflows (which would push the trailing filter button out of view).
    _shrinkable(w)
    return w


def _build_input_widget(val) -> QtWidgets.QWidget:
    if isinstance(val, bool):
        w = QtWidgets.QCheckBox()
        w.setChecked(bool(val))
        return w
    if isinstance(val, int):
        w = QtWidgets.QSpinBox()
        w.setRange(-2_147_483_648, 2_147_483_647)
        w.setValue(val)
        return w
    if isinstance(val, float):
        w = QtWidgets.QDoubleSpinBox()
        w.setRange(-1e18, 1e18)
        w.setDecimals(6)
        w.setValue(val)
        return w
    if isinstance(val, list):
        w = QtWidgets.QLineEdit()
        w.setText(", ".join(str(v) for v in val))
        w.setPlaceholderText("comma-separated values")
        return w
    w = QtWidgets.QLineEdit()
    w.setText(str(val) if val is not None else "")
    return w


def _connect_widget(widget, val, node: dict, key: str, callback) -> None:
    if isinstance(val, bool):
        widget.stateChanged.connect(lambda state, n=node, k=key: _update(n, k, bool(state), callback))
    elif isinstance(val, int):
        widget.valueChanged.connect(lambda v, n=node, k=key: _update(n, k, v, callback))
    elif isinstance(val, float):
        widget.valueChanged.connect(lambda v, n=node, k=key: _update(n, k, v, callback))
    elif isinstance(val, list):
        widget.editingFinished.connect(
            lambda w=widget, n=node, k=key: _update(n, k, _parse_list(w.text()), callback)
        )
    else:
        widget.editingFinished.connect(lambda w=widget, n=node, k=key: _update(n, k, w.text(), callback))


def _update(node: dict, key: str, value, callback) -> None:
    node[key] = value
    callback()


def _parse_list(text: str) -> list:
    if not text.strip():
        return []
    return [_coerce(item.strip()) for item in text.split(",")]


def _coerce(s: str):
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _is_list_of_dicts(lst: list) -> bool:
    return bool(lst) and any(isinstance(item, dict) for item in lst)


def _is_value_unit_dict(val) -> bool:
    """True when val is a flat dict (no nested dicts/lists) containing a 'value' key."""
    return isinstance(val, dict) and "value" in val and all(not isinstance(v, (dict, list)) for v in val.values())


def _deep_copy(obj):
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(v) for v in obj]
    return obj


def _clear_layout(layout: QtWidgets.QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
