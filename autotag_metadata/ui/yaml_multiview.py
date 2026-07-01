"""Tiling container for ZoomView panels backed by a single YamlDocument."""
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

from PyQt6 import QtCore, QtWidgets

from autotag_metadata.core.yaml_document import YamlDocument
from autotag_metadata.ui.drop_overlay import DropEdge
from autotag_metadata.ui.zoom_view import ZoomView


class YamlMultiView(QtWidgets.QWidget):
    """Tiling layout of ZoomView panels sharing one YamlDocument.

    Any panel can be split right (⊢) or down (⊟), creating a nested QSplitter
    tree. Closing a panel collapses its parent splitter when only one sibling
    remains.

    Usage::

        multiview = YamlMultiView()
        multiview.document_changed.connect(on_doc_changed)
        multiview.set_document(parameters)
    """

    document_changed = QtCore.pyqtSignal(dict)
    snippet_capture_requested = QtCore.pyqtSignal(dict, str)
    snippet_dropped = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, view_factory=None, document: YamlDocument | None = None):
        super().__init__(parent)
        self._view_factory = view_factory or ZoomView
        self._doc = document if document is not None else YamlDocument({})
        self._all_views: list[ZoomView] = []
        self._active_view: ZoomView | None = None

        self._container = QtWidgets.QWidget()
        container_layout = QtWidgets.QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._container)

        view = self._make_view()
        self._container.layout().addWidget(view)
        view.refresh()
        self._set_active_view(view)

        # Track focus so the panel the user is working in is highlighted as the
        # active snippet source. Qt auto-disconnects when this widget is destroyed.
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._on_focus_changed)

    # ------------------------------------------------------------------

    def get_layout(self) -> dict:
        """Serialize the current tiling (paths + splitter structure) to a dict.

        Leaf nodes are ``{"path": ...}``; splitter nodes are
        ``{"orientation": "h"|"v", "sizes": [...], "children": [...]}``.
        """
        root = self._root_widget()
        return _serialize(root) if root is not None else {"path": ""}

    def set_layout(self, layout: dict | None) -> None:
        """Rebuild the tiling from a layout dict produced by :meth:`get_layout`."""
        self._clear_all()
        widget = _build_widget(layout or {"path": ""}, self._make_view)
        self._container.layout().addWidget(widget)
        for view in self._all_views:
            view.refresh()
        self._set_active_view(self._all_views[0] if self._all_views else None)

    def set_document(self, data: dict) -> None:
        """Push new document data to all panels."""
        self._doc.data = data if data is not None else {}
        for view in self._all_views:
            view.refresh()

    @property
    def active_view(self) -> ZoomView | None:
        """The panel currently marked active (snippet source), if any."""
        return self._active_view

    # -- active-panel tracking --------------------------------------------

    def _on_focus_changed(self, _old, now) -> None:
        view = self._zoomview_ancestor(now)
        if view is not None:
            self._set_active_view(view)

    def _zoomview_ancestor(self, widget) -> ZoomView | None:
        while widget is not None:
            if widget in self._all_views:
                return widget
            widget = widget.parentWidget() if hasattr(widget, "parentWidget") else None
        return None

    def _set_active_view(self, view: ZoomView | None) -> None:
        self._active_view = view if view in self._all_views else None
        self._refresh_active_highlight()

    def _refresh_active_highlight(self) -> None:
        # Only distinguish an active panel when there is more than one to choose.
        multiple = len(self._all_views) > 1
        for v in self._all_views:
            v.set_active(multiple and v is self._active_view)

    def _root_widget(self) -> QtWidgets.QWidget | None:
        layout = self._container.layout()
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget is not None:
                return widget
        return None

    # ------------------------------------------------------------------

    def refresh_all(self) -> None:
        """Refresh all panels from the shared document without emitting document_changed."""
        for view in self._all_views:
            view.refresh()

    def _make_view(self, path: str = "") -> ZoomView:
        view = self._view_factory(self._doc, initial_path=path)
        view.document_changed.connect(self._on_view_doc_changed)
        view.split_requested.connect(self._on_split_requested)
        view.close_requested.connect(self._on_close_requested)
        view.panel_dropped.connect(self._on_panel_dropped)
        view.snippet_capture_requested.connect(self.snippet_capture_requested)
        view.snippet_dropped.connect(self.snippet_dropped)
        self._all_views.append(view)
        return view

    def _on_split_requested(self, orientation: QtCore.Qt.Orientation) -> None:
        view = self.sender()
        new_view = self._make_view()
        splitter = QtWidgets.QSplitter(orientation)

        parent = view.parentWidget()
        if isinstance(parent, QtWidgets.QSplitter):
            idx = _splitter_index(parent, view)
            splitter.addWidget(view)  # reparents view, vacates idx in parent
            splitter.addWidget(new_view)
            parent.insertWidget(idx, splitter)
        else:
            layout = parent.layout()
            pos = layout.indexOf(view)
            layout.removeWidget(view)
            splitter.addWidget(view)
            splitter.addWidget(new_view)
            layout.insertWidget(pos, splitter)

        new_view.refresh()
        self._set_active_view(new_view)

    def _on_close_requested(self, view: ZoomView) -> None:
        if len(self._all_views) <= 1:
            return

        self._disconnect_view(view)
        self._all_views.remove(view)
        if self._active_view is view:
            self._active_view = self._all_views[0] if self._all_views else None
        self._refresh_active_highlight()

        parent = view.parentWidget()
        if not isinstance(parent, QtWidgets.QSplitter):
            view.deleteLater()
            return

        if parent.count() > 2:
            view.setParent(None)
            view.deleteLater()
            return

        # Collapse: replace parent splitter with the surviving sibling.
        idx = _splitter_index(parent, view)
        sibling = parent.widget(1 - idx)
        gp = parent.parentWidget()

        if isinstance(gp, QtWidgets.QSplitter):
            parent_pos = _splitter_index(gp, parent)
            sibling.setParent(None)
            view.setParent(None)
            parent.setParent(None)
            gp.insertWidget(parent_pos, sibling)
        else:
            layout = gp.layout()
            parent_pos = layout.indexOf(parent)
            sibling.setParent(None)
            view.setParent(None)
            parent.setParent(None)
            layout.insertWidget(parent_pos, sibling)

        view.deleteLater()
        parent.deleteLater()

    def _on_view_doc_changed(self, data: dict) -> None:
        sender = self.sender()
        for view in self._all_views:
            if view is not sender:
                view.refresh()
        self.document_changed.emit(data)

    def _on_panel_dropped(self, source_id: int, edge: str) -> None:
        """Move source panel next to target panel based on drop edge."""
        target: ZoomView = self.sender()
        source = next((v for v in self._all_views if id(v) == source_id), None)
        if source is None or source is target:
            return
        if edge == DropEdge.CENTER:
            return

        orientation = (
            QtCore.Qt.Orientation.Horizontal
            if edge in (DropEdge.LEFT, DropEdge.RIGHT)
            else QtCore.Qt.Orientation.Vertical
        )

        # Detach source from its current position (collapse if needed).
        self._detach_view(source)

        # Split the target: insert source on the correct side.
        new_splitter = QtWidgets.QSplitter(orientation)
        parent = target.parentWidget()
        if isinstance(parent, QtWidgets.QSplitter):
            idx = _splitter_index(parent, target)
            if edge in (DropEdge.LEFT, DropEdge.TOP):
                new_splitter.addWidget(source)
                new_splitter.addWidget(target)
            else:
                new_splitter.addWidget(target)
                new_splitter.addWidget(source)
            parent.insertWidget(idx, new_splitter)
        else:
            layout = parent.layout()
            pos = layout.indexOf(target)
            layout.removeWidget(target)
            if edge in (DropEdge.LEFT, DropEdge.TOP):
                new_splitter.addWidget(source)
                new_splitter.addWidget(target)
            else:
                new_splitter.addWidget(target)
                new_splitter.addWidget(source)
            layout.insertWidget(pos, new_splitter)

    def _detach_view(self, view: ZoomView) -> None:
        """Remove view from its current position, collapsing parent if needed."""
        parent = view.parentWidget()
        if not isinstance(parent, QtWidgets.QSplitter):
            return  # root-level single view — nothing to detach from

        if parent.count() > 2:
            view.setParent(None)
            return

        # Collapse: promote the sibling up.
        idx = _splitter_index(parent, view)
        sibling = parent.widget(1 - idx)
        gp = parent.parentWidget()

        if isinstance(gp, QtWidgets.QSplitter):
            parent_pos = _splitter_index(gp, parent)
            sibling.setParent(None)
            view.setParent(None)
            parent.setParent(None)
            gp.insertWidget(parent_pos, sibling)
        else:
            layout = gp.layout()
            parent_pos = layout.indexOf(parent)
            sibling.setParent(None)
            view.setParent(None)
            parent.setParent(None)
            layout.insertWidget(parent_pos, sibling)

        parent.deleteLater()

    def _disconnect_view(self, view: ZoomView) -> None:
        view.document_changed.disconnect(self._on_view_doc_changed)
        view.split_requested.disconnect(self._on_split_requested)
        view.close_requested.disconnect(self._on_close_requested)
        view.panel_dropped.disconnect(self._on_panel_dropped)
        view.snippet_capture_requested.disconnect(self.snippet_capture_requested)
        view.snippet_dropped.disconnect(self.snippet_dropped)

    def _clear_all(self) -> None:
        for view in list(self._all_views):
            self._disconnect_view(view)
        self._all_views.clear()
        layout = self._container.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()


# ---------------------------------------------------------------------------


def _splitter_index(splitter: QtWidgets.QSplitter, widget: QtWidgets.QWidget) -> int:
    for i in range(splitter.count()):
        if splitter.widget(i) is widget:
            return i
    return -1


def _serialize(widget: QtWidgets.QWidget) -> dict:
    """Serialize a ZoomView / QSplitter widget tree to a layout dict."""
    if isinstance(widget, QtWidgets.QSplitter):
        horizontal = widget.orientation() == QtCore.Qt.Orientation.Horizontal
        return {
            "orientation": "h" if horizontal else "v",
            "sizes": widget.sizes(),
            "children": [_serialize(widget.widget(i)) for i in range(widget.count())],
        }
    leaf = {"path": getattr(widget, "path", "")}
    if hasattr(widget, "get_scroll"):
        leaf["scroll"] = list(widget.get_scroll())
    return leaf


def _build_widget(node: dict, make_view) -> QtWidgets.QWidget:
    """Build a ZoomView / QSplitter tree from a layout dict.

    *make_view* is a ``path -> ZoomView`` factory (registers the view).
    """
    if "children" in node:
        horizontal = node.get("orientation", "h") == "h"
        orientation = QtCore.Qt.Orientation.Horizontal if horizontal else QtCore.Qt.Orientation.Vertical
        splitter = QtWidgets.QSplitter(orientation)
        for child in node["children"]:
            splitter.addWidget(_build_widget(child, make_view))
        sizes = node.get("sizes")
        if sizes:
            splitter.setSizes(sizes)
        return splitter
    view = make_view(node.get("path", ""))
    scroll = node.get("scroll")
    if scroll:
        view.set_scroll(scroll[0], scroll[1])
    return view
