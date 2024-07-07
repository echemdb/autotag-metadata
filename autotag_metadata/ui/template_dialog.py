"""Module containing everthing related to the template dialog."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2022      Albert Engstfeld
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

import os
from enum import Enum

from PyQt6 import QtWidgets, uic


path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)


class TemplateDialogType(Enum):
    Store = "Store Template"
    Load = "Load Template"


class TemplateDialog(QtWidgets.QDialog):
    """The template dialog window"""

    def __init__(self, dialog_type: TemplateDialogType):
        super(TemplateDialog, self).__init__()
        uic.loadUi(f"{dir_path}/template_dialog.ui", self)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(
            False
        )
        self.listWidget.selectionModel().selectionChanged.connect(self.updatelineedit)
        self.lineEdit.textChanged.connect(self.updatelineedit_text)
        self.toolTip()
        self.setWindowTitle(dialog_type.value)
        # only allow to load existing templates
        if dialog_type == TemplateDialogType.Load:
            self.lineEdit.setEnabled(False)

    def accept(self):
        """Read or write templates"""
        super().accept()

        self.template_name = self.lineEdit.text()

    def updatelineedit(self):
        """Update template name when selected in list"""
        self.lineEdit.setText(self.listWidget.currentItem().text())

    def updatelineedit_text(self):
        if self.lineEdit.text() != "":
            self.buttonBox.button(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
            ).setEnabled(True)
        else:
            self.buttonBox.button(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
            ).setEnabled(False)
