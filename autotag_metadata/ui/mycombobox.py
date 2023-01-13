"""
UI elements for Autotag Metadata
"""
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

from PyQt5 import QtWidgets, QtCore


class MyComboBox(QtWidgets.QComboBox):
    """
    ComboBox
    """
    #textModified = QtCore.pyqtSignal(str, str) # (before, after)

    def __init__(self, contents='', parent=None):
        super(MyComboBox, self).__init__(contents)
        self.setEditable(True)
        self.lineEdit().textModified = QtCore.pyqtSignal(str, str)
        self.lineEdit().editingFinished.connect(self.__handleEditingFinished)
        self.lineEdit().textChanged.connect(self.__handleTextChanged)
        self._before = contents

    def __handleTextChanged(self, text):
        if not self.hasFocus():
            self._before = text

    def __handleEditingFinished(self):
        before, after = self._before, self.lineEdit().text()
        if before != after:
            self._before = after
            self.lineEdit().textModified.emit(before, after)
#main_design.QtWidgets.QComboBox = MyComboBox
