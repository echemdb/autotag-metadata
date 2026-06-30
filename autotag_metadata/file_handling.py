"""Filesystem monitoring — event handler and observer lifecycle management."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2021-2022 Johannes Hermann
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

import fnmatch
import threading
from typing import Optional

from PyQt6 import QtCore
from watchfiles import Change, watch


class FileMonitor(QtCore.QThread):
    """Watchdog event handler that emits Qt signals on file creation/modification."""

    create_signal = QtCore.pyqtSignal(str)
    modify_signal = QtCore.pyqtSignal(str)

    def __init__(self, path: str, patterns: Optional[list[str]] = None) -> None:
        super().__init__()
        self.path = path
        self.patterns = patterns
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        for changes in watch(self.path, stop_event=self._stop_event):
            for change, file_path in changes:
                file_path = str(file_path)

                if self.patterns:
                    if not any(fnmatch.fnmatch(file_path, p) for p in self.patterns):
                        continue

                if change == Change.added:
                    self.create_signal.emit(file_path)
                elif change == Change.modified:
                    self.modify_signal.emit(file_path)
