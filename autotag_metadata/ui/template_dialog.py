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
import sys
import yaml

from PyQt5 import QtWidgets, uic

if sys.platform == "win32":
    appdata_folder = os.path.join(os.getenv("APPDATA"), "autotag_metadata")
elif sys.platform == "linux":
    appdata_folder = os.path.join(os.getenv("HOME"), ".config", "autotag_metadata")

templates_file = os.path.join(appdata_folder, "templates.yaml")

path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)


class TemplateDialog(QtWidgets.QDialog):
    """The template dialog window"""
    def __init__(self):
        super(TemplateDialog, self).__init__()
        uic.loadUi(f"{dir_path}/template_dialog.ui", self)

        self.buttonBox.accepted.connect(self.accept)
        #self.close.connect(self.clear_dialog)
        self.buttonBox.rejected.connect(self.reject)
        self.listWidget.selectionModel().selectionChanged.connect(self.updatelineedit)
        self.toolTip(   )

    # def closeEvent(self, event):
    #     pass
    #     #print("X is clicked")

    # def cleardialog(self):
    #     """"""
    #     self.lineEdit.clear()
    #     self.listWidget.clear()

    def accept(self):
        """Read or write templates"""
        super().accept()

        if self.windowTitle() == 'Load Template' and self.listWidget.currentItem() is not None:
            self.parameters = self.templates[self.listWidget.currentItem().text()]
        elif self.windowTitle() == 'Store Template' and self.lineEdit.text() != '':
            self.templates[self.lineEdit.text()] = self.parameters

            with open(templates_file, 'w', encoding="utf-8") as file:
                yaml.dump(self.templates, file, sort_keys=False)

    def updatelineedit(self):
        """Update template name when selected in list"""
        self.lineEdit.setText(self.listWidget.currentItem().text())
