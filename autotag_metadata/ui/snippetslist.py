"""Drag-enabled list view and model for YAML snippets."""
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

from PyQt6.QtCore import QByteArray, QMimeData, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel

from .editable_list import EditableListView

#: MIME type carrying a snippet's raw YAML text during drag-and-drop.
SNIPPET_MIME = "application/x-yaml-snippet"

#: Item-data role storing the snippet's YAML content on each model item.
_CONTENT_ROLE = Qt.ItemDataRole.UserRole + 1


class SnippetsItemModel(QStandardItemModel):
    """Item model that drags a snippet's content as :data:`SNIPPET_MIME`."""

    def mimeTypes(self):
        return [SNIPPET_MIME]

    def mimeData(self, indexes):
        mime = QMimeData()
        if indexes:
            content = self.data(indexes[0], _CONTENT_ROLE) or ""
            mime.setData(SNIPPET_MIME, QByteArray(content.encode("utf-8")))
            mime.setText(content)
        return mime


class SnippetsListView(EditableListView):
    """Snippets: drag to apply elsewhere, double-click to apply at the captured path."""

    def __init__(self, parent=None):
        super().__init__(activate_on_double_click=True, parent=parent)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(False)

    def _create_model(self) -> QStandardItemModel:
        return SnippetsItemModel(self)

    def set_snippets(self, items: dict[str, str]) -> None:
        """Replace the list with *items* (name -> YAML content)."""
        model = self.model()
        model.clear()
        for name, content in items.items():
            item = QStandardItem(name)
            item.setEditable(False)
            item.setData(content, _CONTENT_ROLE)
            item.setToolTip(content)
            model.appendRow(item)
