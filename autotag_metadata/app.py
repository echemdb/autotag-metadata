"""Autotag Metadata App"""
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
import re
import time
import datetime
import logging

import hashlib
import toml
import yaml
from yamllint import linter, config


import pint

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from autotag_metadata.file_handling import FileMonitor, MyEventHandler
from autotag_metadata.ui.template_dialog import TemplateDialog
from autotag_metadata.ui.qplaintexteditlogger import QPlainTextEditLogger

if sys.platform == "win32":
    appdata_folder = os.path.join(os.getenv("APPDATA"), "autotag_metadata")
elif sys.platform == "linux":
    appdata_folder = os.path.join(os.getenv("HOME"), ".config", "autotag_metadata")

if not os.path.exists(appdata_folder):
    os.mkdir(appdata_folder)
elif not os.path.isdir(appdata_folder):
    raise FileExistsError("Config path is not a folder.")

yaml_config_str = """---

yaml-files:
  - "*.yaml"
  - "*.yml"
  - ".yamllint"

rules:
  braces: enable
  brackets: enable
  colons: enable
  commas: enable
  comments:
    level: warning
  comments-indentation:
    level: warning
  document-end: disable
  document-start:
    level: warning
  empty-lines: enable
  empty-values: disable
  hyphens: enable
  indentation: enable
  key-duplicates: enable
  key-ordering: disable
  line-length: enable
  new-line-at-end-of-file: enable
  new-lines: enable
  octal-values: disable
  quoted-strings: disable
  trailing-spaces: enable
  truthy:
    level: warning"""



settings_file = os.path.join(appdata_folder, "settings.toml")
templates_file = os.path.join(appdata_folder, "templates.yaml")

logger = logging.getLogger(__name__)
#logger.setLevel("INFO")

path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)

class AutotagApp(QtWidgets.QMainWindow):
    """Main window class"""
    def __init__(self, *args, **kwargs):
        super(AutotagApp, self).__init__(*args, **kwargs)
        uic.loadUi(f"{dir_path}/ui/main_window.ui", self)

        # replace standard QLineEdit with custom one which fires signals
        # QtWidgets.QLineEdit = MyLineEdit
        # set window title and icon
        title = "Autotag Metadata"
        self.setWindowTitle(title)
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(f"{os.path.abspath(os.path.dirname(__file__))}/autotag_metadata.png"),
            QtGui.QIcon.Selected,
            QtGui.QIcon.On
            )
        self.setWindowIcon(icon)

        try:
            self.load_settings(settings_file)
        except FileNotFoundError:
            self.settings = {}
        # It sets up layout and widgets that are defined
        self.btnBrowse.clicked.connect(self.browse_folder)  # When the button is pressed
        # Execute browse_folder function
        self.btnActivate.clicked.connect(self.toggle_watch)
        # Template management
        self.btnStore.clicked.connect(self.store_template)
        self.btnLoad.clicked.connect(self.load_template)
        self.template_dialog = TemplateDialog()

        logTextBox = QPlainTextEditLogger(self, self.pteLogging)
        # You can format what is printed to text box
        logTextBox.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(logTextBox)
        # You can control the logging level
        logging.getLogger().setLevel(logging.INFO)
        logger.info("template file in %s", templates_file)

        for widget in self.findChildren((QtWidgets.QLineEdit,QtWidgets.QComboBox)):
       #     print(widget.objectName())
       #     if isinstance(widget, QtWidgets.QComboBox ):
       #         widget.__handleTextChanged = handleTextChanged
        #        widget.__handleEditingFinished = handleEditingFinished
        #        widget.lineEdit().editingFinished.connect(widget.__handleEditingFinished)
         #       widget.lineEdit().textChanged.connect(widget.__handleTextChanged)
                #self.settings.
                #widget._before = contents

        #QtWidgets.QComboBox.item
            completer = QtWidgets.QCompleter()
            widget.setCompleter(completer)
            model = QtCore.QStringListModel()
            completer.setModel(model)
            self.get_data(model,widget.objectName())

        #self.watch_directory = None

        #self.file_monitor = FileMonitor()
        #self.thread = QtCore.QThread(self)
        #self.file_monitor.getEmitter().create_signal.connect(self.file_created)
        #self.file_monitor.moveToThread(self.thread)
        #self.thread.started.connect(self.file_monitor.getEmitter().create_signal)
        #self.thread.start()
        self.ledFolder.textChanged.connect(self.enable_activate)
        self.btnActivate.setDisabled(True)
        self.yamlText.textChanged.connect(self.act_on_yaml_change)
        self.parameters = {}

    def validate_yaml(self):
        """Change color of raw yaml text field according to validation"""
        # yaml_error = linter.run(self.yamlText.toPlainText(),
        # config.YamlLintConfig(content=yaml_config_str))
        yaml_error = linter.get_syntax_error(self.yamlText.toPlainText())
        if yaml_error is None:
            self.yamlText.setStyleSheet("background-color: rgb(255, 255, 255);")
            return True
        else:
            self.yamlText.setStyleSheet("background-color: rgb(85, 85, 127);")
            return False

    def act_on_yaml_change(self):
        """Update mask on change in raw yaml text field"""
        if self.validate_yaml():
            self.parameters = yaml.load(self.yamlText.toPlainText(), Loader=yaml.FullLoader)
            if isinstance(self.parameters, dict):
                self.populate_mask()

    # def __handleTextChanged(self, text):
    #     #print("fired handled text")
    #     if not self.hasFocus():
    #         self._before = text

    # def __handleEditingFinished(self):
    #     #print("fired finished editing")
    #     before, after = self._before, self.text()
    #     if before != after:
    #         self._before = after
    #         self.textModified.emit(before, after)

    def check_input(self):
        """Extended input checking of raw yaml input possibly schema"""

    #@QtCore.pyqtSlot(str)
    def load_template(self, filepath):
        """Open the dialog for loading templates"""
        self.template_dialog.setWindowTitle("Load Template")
        try:
            with open(templates_file, encoding="utf-8") as file:
                self.template_dialog.templates = yaml.load(file, Loader=yaml.FullLoader)
        except FileNotFoundError:
            self.template_dialog.templates = {}

        if not isinstance(self.template_dialog.templates, dict):
            self.template_dialog.templates = {}

        self.template_dialog.listWidget.clear()
        self.template_dialog.lineEdit.clear()
        self.template_dialog.listWidget.addItems(self.template_dialog.templates.keys())
        if self.template_dialog.exec_() and hasattr(self.template_dialog, "parameters"):
            self.parameters = self.template_dialog.parameters
            self.populate_mask()
            self.populate_yamltextfield()

    #@QtCore.pyqtSlot(str)
    def store_template(self, filepath):
        """Open the dialog for storing templates"""
        self.template_dialog.setWindowTitle("Store Template")
        try:
            with open(templates_file, encoding="utf-8") as file:
                self.template_dialog.templates = yaml.load(file, Loader=yaml.FullLoader)
        except FileNotFoundError:
            self.template_dialog.templates = {}

        if not isinstance(self.template_dialog.templates, dict):
            self.template_dialog.templates = {}

        self.template_dialog.parameters = self.parameters
        self.template_dialog.listWidget.clear()
        self.template_dialog.lineEdit.clear()

        self.template_dialog.listWidget.addItems(self.template_dialog.templates.keys())
        self.template_dialog.exec_()

    def browse_folder(self):
        """Open the dialog for selecting the folder to be watched"""
        # self.ledFolder.clear()  # In case there are any existing elements in the list
        directory = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                               "pushButton")
        # execute getExistingDirectory dialog and set the directory variable to be equal
        # to the user selected directory
        directory = os.sep.join(directory.split("/"))
        if directory:  # if user didn't pick a directory don't continue
            self.ledFolder.setText(directory)
            self.watch_directory = directory
            logger.info("changed watching folder to %s", directory)

    def enable_activate(self):
        """Enable activate button"""
        if os.path.exists(self.ledFolder.text()):
            self.btnActivate.setEnabled(True)
        else:
            self.btnActivate.setDisabled(True)

    def toggle_watch(self):
        """Toggle folder watching"""
        if self.btnActivate.isChecked():
            if self.watch_directory:
                # create new instance of watcher potential
                self.file_monitor = FileMonitor()
                self.thread = QtCore.QThread(self)
                self.file_monitor.getEmitter().create_signal.connect(self.file_created)
                self.file_monitor.moveToThread(self.thread)

                self.btnActivate.setText("Deactivate")
                self.file_monitor.observer.schedule(
                    self.file_monitor.event_handler,
                    self.watch_directory, 
                    recursive=False
                ) # permission problems with subfolders
                self.file_monitor.observer.start()
                logger.info("watching %s", self.watch_directory)
            else:
                self.btnActivate.setChecked(False)


        elif not self.btnActivate.isChecked():
            self.btnActivate.setText("Activate")
            self.file_monitor.observer.stop()

            logger.info("stop watching %s", self.watch_directory)

    def file_created(self, msg):
        """Create the metadata file with timestamp and hash"""
        if not msg.endswith(".metadata"): # metadata files
            logger.info("created %s", msg)
            self.parameters["time metadata"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            self.parameters["measurement file name"] = os.path.split(msg)[-1]

            hash_str = self.hash_file(msg)
            self.parameters["measurement file sha512"] = hash_str
            
            self.write_metadata(msg)

    def hash_file(self, filename):
        """Generate sha512 hash of the measurement file
        TODO improve and remove recursion
        """
        try:
            sha512_hash = hashlib.sha512()
            with open(filename, "rb", encoding="utf-8") as file:
                # Read and update hash string value in blocks of 4K
                for byte_block in iter(lambda: file.read(4096), b""):
                    sha512_hash.update(byte_block)
            return sha512_hash.hexdigest()
        # while file is created it is locked or doesnot exist yet??
        except (PermissionError, FileNotFoundError) as err: 
            time.sleep(1)
            return self.hash_file(filename)

    def populate_yamltextfield(self):
        """Change the text of the raw yaml field when field text is changed in the mask"""
        # blocking of signals necessary to prevent regeneration of mask
        # which leads to a loose of focus of the currently edited mask field
        self.yamlText.blockSignals(True)
        self.yamlText.setPlainText(yaml.dump(self.parameters,sort_keys=False))
        self.yamlText.blockSignals(False)

    def recursively_something(self, parameters, parent=""):
        """Rudimentary generation of the mask.
        Should be replaced by a proper model in the future.
        """
        for key, val in parameters.items():
            if isinstance(val, dict):
                if parent == "":
                    self.recursively_something(val, key)
                else:
                    self.recursively_something(val, f"{parent}.{key}")
            else:
                label = QtWidgets.QLabel(self.centralwidget)
                lineEdit = QtWidgets.QLineEdit(self.centralwidget)
                if parent == "":
                    label.setText(f"{key}")
                    lineEdit.setObjectName(f"{key}")
                else:
                    label.setText(f"{parent}.{key}")
                    lineEdit.setObjectName(f"{parent}.{key}")

                self.verticalLayout_2.addWidget(label)
                lineEdit.setText(str(val))
                lineEdit.textChanged.connect(self.update_yaml)
                self.verticalLayout_2.addWidget(lineEdit)

    def update_yaml(self):
        """Prepare the parameters dict and start population of the raw yaml text field"""
        self.recurse_dict(
            self.parameters,
            self.sender().objectName().split("."),
            self.sender().text()
        )
        self.populate_yamltextfield()


    def recurse_dict(self, deep_dict, listofkeys, text):
        """
        Recurse dict
        Needs test case
        """
        if len(listofkeys) > 1:
            self.recurse_dict(deep_dict[listofkeys[0]], listofkeys[1:], text)
        else:
            deep_dict[listofkeys[0]] = text

    def populate_mask(self):
        """Generate input from parameters dict"""
        while self.verticalLayout_2.count():
            child = self.verticalLayout_2.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.recursively_something(self.parameters)
        spacerItem = QtWidgets.QSpacerItem(
            20,
            40,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout_2.addItem(spacerItem)

    def write_metadata(self, file):
        """Write out metadata in file with file name corresponding to measurement file"""
        with open(file + ".metadata", "w", encoding="utf-8") as metadata_file:
            yaml.dump(self.parameters, metadata_file, sort_keys=False)
        logger.info("wrote metadata for %s", metadata_file)

    def get_data(self, model, text_objectname):
        """TODO"""
        try:
            model.setStringList(self.settings[text_objectname])
        except KeyError:
            model.setStringList([])

    def load_settings(self, file = settings_file):
        """Load settings file"""
        self.settings = toml.load(file)

    def write_settings(self, file = settings_file):
        """Write settings file"""
        with open(file, "w", encoding="utf-8") as file:
            toml.dump(self.settings, file)


def run():
    """Start Application"""
    app = QtWidgets.QApplication(sys.argv)  # A new instance of QApplication

    form = AutotagApp()  # We set the form to be our ExampleApp (design)
    # Set up logging to use your widget as a handler

    # log_handler = QPlainTextEditLogger()
    # logger.addHandler(log_handler)
    form.show()  # Show the form
    app.exec_()  # and execute the app


if __name__ == "__main__":  # if we're running file directly and not importing it
    run()  # run the main function
