"""List view with inline create: a new entry is named in an editable row.

``add_pending`` appends an editable row and starts editing it in place; the
entry is created only when a non-empty name is committed (empty or Escape
discards it). Shared by the snippets, templates and views sidebars.
"""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2024-2026 Johannes Hermann
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

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QAbstractItemDelegate, QLineEdit, QListView, QMenu

#: Marks the transient "new entry" row awaiting a name.
_PENDING_ROLE = Qt.ItemDataRole.UserRole + 3
_REVERT = QAbstractItemDelegate.EndEditHint.RevertModelCache


class EditableListView(QListView):
    """List with inline create (add_pending), double-click activate, and delete."""

    item_activated = pyqtSignal(str)  # double-click an existing entry
    create_requested = pyqtSignal(str)  # a new row was named
    delete_requested = pyqtSignal(str)

    def __init__(self, *, activate_on_double_click: bool = True, parent=None):
        super().__init__(parent)
        self.setModel(self._create_model())
        self.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.setEditTriggers(QListView.EditTrigger.NoEditTriggers)  # edits are driven explicitly
        if activate_on_double_click:
            self.doubleClicked.connect(self._on_double_click)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._pending: QStandardItem | None = None

    def _create_model(self) -> QStandardItemModel:
        """Model factory (overridden by SnippetsListView for drag support)."""
        return QStandardItemModel(self)

    def set_items(self, names: list[str]) -> None:
        """Replace the listed entries with *names*."""
        model = self.model()
        model.clear()
        for name in names:
            item = QStandardItem(name)
            item.setEditable(False)
            model.appendRow(item)

    def add_pending(self, suggestion: str = "") -> None:
        """Append a new editable row (pre-filled with *suggestion*) and edit it."""
        item = QStandardItem(suggestion)
        item.setEditable(True)
        item.setData(True, _PENDING_ROLE)
        self.model().appendRow(item)
        self._pending = item
        self.setCurrentIndex(item.index())
        self.scrollTo(item.index())
        # Defer: when invoked from a context menu, edit() would run inside the
        # menu's modal loop and be aborted as the menu closes.
        QTimer.singleShot(0, self._start_pending_edit)

    def _start_pending_edit(self) -> None:
        if self._pending is None:
            return
        index = self._pending.index()
        if not index.isValid():
            return
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.edit(index)
        # Explicitly focus the inline editor: edit() alone does not reliably
        # grab keyboard focus on every platform (e.g. Wayland).
        editor = self.viewport().findChild(QLineEdit)
        if editor is not None:
            editor.setFocus(Qt.FocusReason.OtherFocusReason)
            editor.selectAll()

    def closeEditor(self, editor, hint) -> None:
        item = self._pending
        name = "" if (item is None or hint == _REVERT) else item.text()
        super().closeEditor(editor, hint)
        if item is not None:
            self._finalize_pending(name)

    def _finalize_pending(self, name: str) -> None:
        item = self._pending
        if item is None:
            return
        self._pending = None
        self.model().removeRow(item.row())
        if name.strip():
            self.create_requested.emit(name.strip())

    def _on_double_click(self, index) -> None:
        if index.isValid() and not index.data(_PENDING_ROLE):
            self.item_activated.emit(index.data(Qt.ItemDataRole.DisplayRole))

    def _show_context_menu(self, pos) -> None:
        index = self.indexAt(pos)
        if not index.isValid() or index.data(_PENDING_ROLE):
            return
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        if menu.exec(self.viewport().mapToGlobal(pos)) is delete_action:
            self.delete_requested.emit(index.data(Qt.ItemDataRole.DisplayRole))
