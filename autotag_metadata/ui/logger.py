# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2024 Johannes Hermann
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


from PyQt5.QtCore import QObject, pyqtSignal

import logging

logger = logging.getLogger(__name__)


class LogHandler(QObject, logging.Handler):
    """PlainTextLogger"""

    new_record = pyqtSignal(object)

    def __init__(self, parent):
        super().__init__(parent)
        super(logging.Handler).__init__()
        logger.info("Starting logger")

    def emit(self, record):
        msg = self.format(record)
        self.new_record.emit(msg)
