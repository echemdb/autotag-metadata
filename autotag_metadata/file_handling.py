"""Filesystem monitoring — watchfiles-based watcher with a callback API."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2021-2026 Johannes Hermann
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
import os
import threading

from PyQt6 import QtCore
from watchfiles import Change, watch


class FileMonitor(QtCore.QThread):
    """Watchdog event handler that emits Qt signals on file creation/modification."""

    create_signal = QtCore.pyqtSignal(str)
    modify_signal = QtCore.pyqtSignal(str)

    def __init__(self, path: str, patterns: list[str] | None = None) -> None:
        super().__init__()
        self.path = path
        self.patterns = patterns
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def _matches(self, file_path: str) -> bool:
        if self.patterns is None:
            return True
        name = os.path.basename(file_path)
        return any(fnmatch.fnmatch(name, pat) for pat in self.patterns)

    def run(self) -> None:
        for changes in watch(self.path, stop_event=self._stop_event):
            for change, file_path in changes:
                file_path = str(file_path)
                if not self._matches(file_path):
                    continue
                if change == Change.added:
                    self.create_signal.emit(file_path)
                elif change == Change.modified:
                    self.modify_signal.emit(file_path)
