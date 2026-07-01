"""Drop target for tagging individual files by dragging them in."""
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

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QLabel


class LabelDropzone(QLabel):
    """A label that emits the local paths of files dropped onto it."""

    files_submitted = pyqtSignal(list)  # list[str] of local file paths

    def __init__(self, parent=None):
        super().__init__("Drop files here\nto write their .meta.yaml", parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setAcceptDrops(True)
        self.setMinimumHeight(64)
        self._restyle(active=False)

    def _restyle(self, active: bool) -> None:
        role = QPalette.ColorRole.Highlight if active else QPalette.ColorRole.Mid
        color = self.palette().color(role).name()
        self.setStyleSheet(
            f"QLabel {{ border: 2px dashed {color}; border-radius: 6px; margin: 4px; padding: 8px; }}"
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self._restyle(active=True)
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._restyle(active=False)

    def dropEvent(self, event):
        self._restyle(active=False)
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.files_submitted.emit(paths)
