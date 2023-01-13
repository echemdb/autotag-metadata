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

import logging

from PyQt5 import QtCore


class QPlainTextEditLogger(logging.Handler, QtCore.QThread):
    """PlainTextLogger"""
    def __init__(self, _parent, loggingwindow):
        super().__init__()
        #self.setLevel('INFO')
        #self.setLevel('DEBUG')
        self.widget = loggingwindow
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)

        #optinal reverse logging
        #cursor = self.widget.textCursor()
        #cursor.movePosition(QtGui.QTextCursor.Start, QtGui.QTextCursor.MoveAnchor)
        #self.widget.setTextCursor(cursor)
        #self.widget.setCursor()
        #self.widget.textCursor().insertText(msg + '\n')

    def write(self, msg):
        pass
