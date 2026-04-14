"""Dropzone label"""

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
from PyQt6.QtWidgets import QLabel


class LabelDropzone(QLabel):
    """A QLabel drop target that emits the list of dropped file paths."""

    files_submitted = pyqtSignal(list)

    def __init__(self, parent=None):
        QLabel.__init__(self, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        filelist = event.mimeData().text().strip().split(" /")
        filelist = filelist[0:1] + ["/" + filename for filename in filelist[1:]]
        filelist = [filename.replace("file:///", "/") for filename in filelist]
        event.acceptProposedAction()
        self.files_submitted.emit(filelist)
