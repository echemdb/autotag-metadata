"""Sidebar panel: a list with inline naming plus a Save button.

Used identically by the Snippets, Templates and Views sidebars. Saving adds a
new editable row to the list (named in place); for snippets a capture seeds
that row via :meth:`prime`.
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

from PyQt6 import QtCore, QtWidgets

from .editable_list import EditableListView


class LibraryPanel(QtWidgets.QWidget):
    """A list view (inline naming) wrapped with a Save button."""

    #: Emitted when the Save button is pressed, before inline naming begins, so a
    #: host can stash what to save (e.g. snippet capture from the active panel).
    save_started = QtCore.pyqtSignal()

    def __init__(self, list_view: EditableListView, save_text: str, parent=None):
        super().__init__(parent)
        self._list = list_view

        # Re-expose the list's signals so the host connects to the panel.
        self.activated = list_view.item_activated  # entry double-clicked
        self.save_requested = list_view.create_requested  # new row named
        self.delete_requested = list_view.delete_requested

        self._save_btn = QtWidgets.QPushButton(save_text)
        self._save_btn.clicked.connect(self._on_save_clicked)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._save_btn)

    @property
    def list_view(self) -> EditableListView:
        return self._list

    def set_items(self, names: list[str]) -> None:
        self._list.set_items(names)

    def _on_save_clicked(self) -> None:
        self.save_started.emit()
        self.start_new()

    def start_new(self) -> None:
        """Begin a new entry: an editable row with an empty name."""
        self._list.add_pending()

    def prime(self, default: str = "") -> None:
        """Begin a new entry pre-filled with *default* (used by snippet capture)."""
        self._list.add_pending(default)
