"""Qt logging handler — bridges Python logging records to a QPlainTextEdit widget."""
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

import logging

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class _RecordEmitter(QObject):
    """Tiny QObject that owns the Qt signal carrying formatted log records."""

    new_record = pyqtSignal(object)


class LogHandler(logging.Handler):
    """Logging handler that re-emits formatted records as a Qt signal.

    The handler itself is a plain ``logging.Handler`` (no Qt base class); the
    Qt signal lives on a contained ``QObject``. This matters at shutdown:
    ``logging.shutdown()`` iterates every handler, and if the handler were a
    QObject whose C++ peer had already been torn down with the QApplication, the
    attribute access would raise. Keeping the handler pure-Python avoids that.
    """

    def __init__(self, parent=None):
        super().__init__()
        self._emitter = _RecordEmitter(parent)
        self.new_record = self._emitter.new_record
        logger.info("Starting logger")

    def emit(self, record):
        try:
            self.new_record.emit(self.format(record))
        except RuntimeError:
            # The emitter's C++ object was deleted during teardown; drop it.
            pass
