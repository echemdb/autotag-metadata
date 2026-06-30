"""Single-path zoom view into a shared YamlDocument."""
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

from autotag_metadata.core.yaml_document import YamlDocument, nest_at_path
from autotag_metadata.ui.drop_overlay import DropEdge, DropOverlay, edge_for_pos
from autotag_metadata.ui.snippetslist import SNIPPET_MIME
from autotag_metadata.ui.yaml_form_view import YamlFormView

DRAG_MIME = "application/x-zoomview-id"


class _DragHandle(QtWidgets.QLabel):
    """Drag-initiation handle in the panel header."""

    drag_started = QtCore.pyqtSignal(object)  # emits the ZoomView

    def __init__(self, parent=None):
        super().__init__("⠿", parent)
        self.setFixedWidth(18)
        self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        self.setToolTip("Drag to move panel")
        self.setStyleSheet("color: #888; font-size: 14px;")
        self._drag_start: QtCore.QPoint | None = None

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_start is None:
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 6:
            return
        self._drag_start = None
        zoom_view = self.parent().parent()  # _DragHandle → header_widget → ZoomView
        self.drag_started.emit(zoom_view)


class ZoomView(QtWidgets.QWidget):
    """Displays and edits a subtree of a shared YamlDocument at a dotted path.

    The path is committed on Return / focus-out. Editing any field in the form
    writes the change back into the shared document and emits *document_changed*
    with the full updated dict.
    """

    document_changed = QtCore.pyqtSignal(dict)
    close_requested = QtCore.pyqtSignal(object)
    split_requested = QtCore.pyqtSignal(QtCore.Qt.Orientation)
    panel_dropped = QtCore.pyqtSignal(object, str)  # (source_view, DropEdge)
    snippet_capture_requested = QtCore.pyqtSignal(dict, str)  # (path-anchored data, path)
    snippet_dropped = QtCore.pyqtSignal(str)  # dropped snippet YAML text

    def __init__(self, document: YamlDocument, initial_path: str = "", parent=None):
        super().__init__(parent)
        self._doc = document
        self._path = initial_path
        self._syncing = False
        self._scalar_key: str | None = None
        self._active = False
        # Named so the active-panel border targets only this widget, not children.
        self.setObjectName("zoomPanel")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

        self._drag_handle = _DragHandle()
        self._drag_handle.drag_started.connect(self._start_drag)

        self._split_h_btn = QtWidgets.QPushButton("⊢")
        self._split_h_btn.setFixedWidth(24)
        self._split_h_btn.setToolTip("Split right")

        self._split_v_btn = QtWidgets.QPushButton("⊟")
        self._split_v_btn.setFixedWidth(24)
        self._split_v_btn.setToolTip("Split down")

        self._snippet_btn = QtWidgets.QPushButton("⊕")
        self._snippet_btn.setFixedWidth(24)
        self._snippet_btn.setToolTip("Save this panel's subtree as a snippet")

        self._up_btn = QtWidgets.QPushButton("↑")
        self._up_btn.setFixedWidth(24)
        self._up_btn.setToolTip("Filter up one level")

        self._path_edit = QtWidgets.QLineEdit(initial_path)
        self._path_edit.setPlaceholderText("Path (e.g. instrument.settings or components.0) — empty = full doc")

        self._close_btn = QtWidgets.QPushButton("×")
        self._close_btn.setFixedWidth(28)
        self._close_btn.setToolTip("Close this panel")

        # Use a QWidget for the header so _DragHandle.parent().parent() resolves correctly.
        self._header_widget = QtWidgets.QWidget()
        header = QtWidgets.QHBoxLayout(self._header_widget)
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self._drag_handle)
        header.addWidget(self._split_h_btn)
        header.addWidget(self._split_v_btn)
        header.addWidget(self._snippet_btn)
        header.addWidget(self._up_btn)
        header.addWidget(self._path_edit)
        header.addWidget(self._close_btn)

        self._warning_bar = QtWidgets.QLabel()
        self._warning_bar.setStyleSheet("background: #c0392b; color: white; padding: 2px 6px; border-radius: 2px;")
        self._warning_bar.setVisible(False)

        self._form = YamlFormView()
        self._form.data_changed.connect(self._on_form_edit)
        self._form.zoom_requested.connect(self._on_zoom_requested)

        self._overlay = DropOverlay(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._header_widget)
        layout.addWidget(self._warning_bar)
        layout.addWidget(self._form)

        self._path_edit.editingFinished.connect(self._on_path_committed)
        self._up_btn.clicked.connect(self._go_up)
        self._close_btn.clicked.connect(lambda: self.close_requested.emit(self))
        self._split_h_btn.clicked.connect(lambda: self.split_requested.emit(QtCore.Qt.Orientation.Horizontal))
        self._split_v_btn.clicked.connect(lambda: self.split_requested.emit(QtCore.Qt.Orientation.Vertical))
        self._snippet_btn.clicked.connect(self._emit_capture)

        self.setAcceptDrops(True)
        self._apply_active_style()

    @property
    def path(self) -> str:
        return self._path

    @property
    def is_active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        """Mark this as the active panel — the one new snippets are captured from.

        The active panel gets a highlighted border (from the palette, so it
        tracks the OS theme); inactive panels keep a same-width transparent
        border so toggling never shifts the layout.
        """
        if active == self._active:
            return
        self._active = active
        self._apply_active_style()
        self._snippet_btn.setToolTip(
            "Save this (active) panel's subtree as a snippet"
            if active
            else "Save this panel's subtree as a snippet"
        )

    def _apply_active_style(self) -> None:
        if self._active:
            color = self.palette().color(QtGui.QPalette.ColorRole.Highlight).name()
        else:
            color = "transparent"
        self.setStyleSheet(f"#zoomPanel {{ border: 2px solid {color}; border-radius: 3px; }}")

    def get_scroll(self) -> tuple[int, int]:
        """Current (horizontal, vertical) scroll offset of the form."""
        return self._form.scroll_position()

    def set_scroll(self, horizontal: int, vertical: int) -> None:
        """Restore the form's scroll offset (applied once the form is laid out)."""
        self._form.set_scroll_position(horizontal, vertical)

    def refresh(self) -> None:
        """Re-read the node from the shared document and update the form.

        A dict/list subtree is shown directly; a scalar leaf (e.g.
        ``components.0.type``) is shown as a single editable field keyed by the
        last path segment.
        """
        found, node = self._doc.resolve(self._path)
        path_missing = bool(self._path) and not found
        self._warning_bar.setText(f"Path '{self._path}' not found in document")
        self._warning_bar.setVisible(path_missing)
        self._syncing = True
        if found and isinstance(node, (dict, list)):
            self._scalar_key = None
            self._form.set_zoom_enabled(True)
            self._form.load(node)
        elif found:
            # A scalar leaf has no subtree to drill into; its row's filter button
            # would re-append the leaf key, so suppress it here.
            self._scalar_key = self._path.split(".")[-1]
            self._form.set_zoom_enabled(False)
            self._form.load({self._scalar_key: node})
        else:
            self._scalar_key = None
            self._form.set_zoom_enabled(True)
            self._form.load({})
        self._syncing = False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())

    # ------------------------------------------------------------------
    # Drag source

    def _start_drag(self, view: "ZoomView") -> None:
        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setData(DRAG_MIME, QtCore.QByteArray(str(id(view)).encode()))
        drag.setMimeData(mime)
        drag.exec(QtCore.Qt.DropAction.MoveAction)

    # ------------------------------------------------------------------
    # Drop target

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(SNIPPET_MIME):
            event.acceptProposedAction()
        elif event.mimeData().hasFormat(DRAG_MIME) and not self._is_self_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(SNIPPET_MIME):
            self._overlay.show_edge(DropEdge.CENTER)
            event.acceptProposedAction()
            return
        if not event.mimeData().hasFormat(DRAG_MIME) or self._is_self_drag(event):
            event.ignore()
            return
        edge = edge_for_pos(self, event.position().toPoint())
        self._overlay.show_edge(edge)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event: QtGui.QDragLeaveEvent) -> None:
        self._overlay.show_edge(DropEdge.NONE)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        self._overlay.show_edge(DropEdge.NONE)
        if event.mimeData().hasFormat(SNIPPET_MIME):
            text = bytes(event.mimeData().data(SNIPPET_MIME)).decode("utf-8")
            self.snippet_dropped.emit(text)
            event.acceptProposedAction()
            return
        if not event.mimeData().hasFormat(DRAG_MIME) or self._is_self_drag(event):
            event.ignore()
            return
        source_id = int(bytes(event.mimeData().data(DRAG_MIME)).decode())
        edge = edge_for_pos(self, event.position().toPoint())
        self.panel_dropped.emit(source_id, edge)
        event.acceptProposedAction()

    def _is_self_drag(self, event) -> bool:
        if not event.mimeData().hasFormat(DRAG_MIME):
            return False
        source_id = int(bytes(event.mimeData().data(DRAG_MIME)).decode())
        return source_id == id(self)

    # ------------------------------------------------------------------

    def _on_path_committed(self) -> None:
        self._path = self._path_edit.text().strip()
        self.refresh()

    def _on_zoom_requested(self, rel_path: str) -> None:
        """Filter the panel to a row's subtree/value, clicked instead of typed.

        *rel_path* is relative to the panel's current path, so the new path is the
        two joined — letting the user drill down by repeated clicks.
        """
        rel_path = rel_path.strip(".")
        if not rel_path:
            return
        self._path = f"{self._path}.{rel_path}" if self._path else rel_path
        self._path_edit.setText(self._path)
        self.refresh()

    def _go_up(self) -> None:
        """Filter to the parent of the current path (undo one drill-down)."""
        if not self._path:
            return
        self._path = self._path.rpartition(".")[0]
        self._path_edit.setText(self._path)
        self.refresh()

    def _on_form_edit(self, data) -> None:
        if self._syncing:
            return
        # In scalar-leaf mode the form wraps the value as {key: value}; unwrap it
        # so the raw scalar is written back to the leaf path.
        if self._scalar_key is not None and isinstance(data, dict):
            self._doc.set_subtree(self._path, data.get(self._scalar_key))
        else:
            self._doc.set_subtree(self._path, data)
        self.document_changed.emit(self._doc.data)

    def capture_payload(self) -> tuple[object, str]:
        """Return ``(path-anchored data, path)`` for capturing this panel.

        Captures the current node — a subtree or a scalar leaf — anchored at the
        panel's path, ready to store as a snippet.
        """
        found, node = self._doc.resolve(self._path)
        value = node if found else {}
        return nest_at_path(self._path, value), self._path

    def _emit_capture(self) -> None:
        """Capture the current node (subtree or scalar leaf) as a snippet."""
        data, path = self.capture_payload()
        self.snippet_capture_requested.emit(data, path)
