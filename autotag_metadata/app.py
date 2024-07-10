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

import datetime
import hashlib
import logging
import os
import sys
import time

import yaml
from PyQt6 import QtCore, QtGui, QtWidgets, uic
from yamllint import linter

from .config import Config
from .file_handling import FileMonitor
from .ui.logger import LogHandler
from .ui.template_dialog import TemplateDialog, TemplateDialogType
from .ui.templatetree import TemplateTree

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


logger = logging.getLogger(__name__)
# logger.setLevel("INFO")

path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)


class AutotagApp(QtWidgets.QMainWindow):
    """Main window class"""

    def __init__(self, *args, **kwargs):
        super(AutotagApp, self).__init__(*args, **kwargs)
        uic.loadUi(f"{dir_path}/ui/main_window.ui", self)

        # set window title and icon
        title = "Autotag Metadata"
        self.setWindowTitle(title)
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(
                f"{os.path.abspath(os.path.dirname(__file__))}/autotag_metadata.png"
            ),
            QtGui.QIcon.Mode.Selected,
            QtGui.QIcon.State.On,
        )
        self.setWindowIcon(icon)

        self.setup_logger()
        self.config = Config()

        self.btnSelectTemporaryFile.clicked.connect(self.select_temporary_file)
        self.btnUseTemporaryFile.clicked.connect(self.toggle_watch_temporary_file)
        self.btnUseTemporaryFile.setDisabled(True)
        self.ledTemporaryLoc.textChanged.connect(self.enable_use)
        # It sets up layout and widgets that are defined
        self.btnBrowse.clicked.connect(self.browse_folder)  # When the button is pressed
        # Execute browse_folder function
        self.btnActivate.clicked.connect(self.toggle_watch)
        # Template management
        self.btnStore.clicked.connect(self.store_template)
        self.btnLoad.clicked.connect(self.load_template)

        self.template_tree = TemplateTree({})
        self.template_tree.model.dataChanged.connect(self.on_tree_data_change)
        self.scrollArea.setWidget(self.template_tree)

        self.ledFolder.textChanged.connect(self.enable_activate)
        self.btnActivate.setDisabled(True)
        self.yamlText.textChanged.connect(self.act_on_yaml_change)
        self.parameters = {}

        try:
            self.setGeometry(*self.config._config["windowGeometry"])
            self.ledFolder.setText(self.config._config["watchFolder"])
            self.ledTemporaryLoc.setText(self.config._config["temporaryFile"])
            self.ledFilePatterns.setText(self.config._config["filePatterns"])
            self.cbRecursiveWatch.setChecked(bool(self.config._config["recursiveWatching"]))
        except KeyError:
            print("failed")

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.reenable_temporary_file_watch)

    @QtCore.pyqtSlot()
    def on_tree_data_change(self):
        mask_dict = self.template_tree.to_dict()
        if mask_dict:
            self.parameters = mask_dict
            self.populate_yamltextfield()
        else:
            self.populate_mask()
            logger.error(
                "Value types can not be changed in the mask. Please use the text field or editor."
            )

    def validate_yaml(self):
        """Change color of raw yaml text field according to validation"""
        # yaml_error = linter.run(self.yamlText.toPlainText(),
        # config.YamlLintConfig(content=yaml_config_str))
        yaml_error = linter.get_syntax_error(self.yamlText.toPlainText())
        if yaml_error is None:
            self.yamlText.setStyleSheet("background-color: rgb(144, 238, 144);")
            return True
        else:
            self.yamlText.setStyleSheet("background-color: rgb(255, 106, 106);")
            return False

    def act_on_yaml_change(self):
        """Update mask on change in raw yaml text field"""
        if self.validate_yaml():
            self.parameters = yaml.load(
                self.yamlText.toPlainText(), Loader=yaml.FullLoader
            )
            if isinstance(self.parameters, dict):
                self.populate_mask()
                if self.btnUseTemporaryFile.isChecked():
                    self.hidden_write_temporary_file()

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

    def load_template(self):
        """Open the dialog for loading templates"""
        template_dialog = TemplateDialog(TemplateDialogType.Load)
        template_dialog.listWidget.addItems(self.config._config["templates"].keys())

        if template_dialog.exec():
            yaml_text = self.config.load_template(template_dialog.template_name)
            self.parameters = yaml.load(yaml_text, Loader=yaml.FullLoader)
            self.populate_yamltextfield()
            self.populate_mask()

    # @QtCore.pyqtSlot(str)
    # def load_template(self, filepath):
    #     """Open the dialog for loading templates"""
    #     self.template_dialog.setWindowTitle("Load Template")
    #     try:
    #         with open(templates_file, encoding="utf-8") as file:
    #             self.template_dialog.templates = yaml.load(file, Loader=yaml.FullLoader)
    #     except FileNotFoundError:
    #         self.template_dialog.templates = {}

    #     if not isinstance(self.template_dialog.templates, dict):
    #         self.template_dialog.templates = {}

    #     self.template_dialog.listWidget.clear()
    #     self.template_dialog.lineEdit.clear()
    #     self.template_dialog.listWidget.addItems(self.template_dialog.templates.keys())
    #     if self.template_dialog.exec_() and hasattr(self.template_dialog, "parameters"):
    #         self.parameters = self.template_dialog.parameters
    #         self.populate_mask()
    #         self.populate_yamltextfield()

    # @QtCore.pyqtSlot(str)
    # def store_template(self, filepath):
    #     """Open the dialog for storing templates"""
    #     self.template_dialog.setWindowTitle("Store Template")
    #     try:
    #         with open(templates_file, encoding="utf-8") as file:
    #             self.template_dialog.templates = yaml.load(file, Loader=yaml.FullLoader)
    #     except FileNotFoundError:
    #         self.template_dialog.templates = {}

    #     if not isinstance(self.template_dialog.templates, dict):
    #         self.template_dialog.templates = {}

    #     self.template_dialog.parameters = self.parameters
    #     self.template_dialog.listWidget.clear()
    #     self.template_dialog.lineEdit.clear()

    #     self.template_dialog.listWidget.addItems(self.template_dialog.templates.keys())
    #     self.template_dialog.exec_()

    def store_template(self):
        """Open the dialog for storing templates"""
        template_dialog = TemplateDialog(TemplateDialogType.Store)
        template_dialog.listWidget.addItems(self.config._config["templates"].keys())

        content = self.yamlText.toPlainText()

        if template_dialog.exec():
            self.config.save_template(template_dialog.template_name, content)

    def select_temporary_file(self):
        """Open the dialog for selecting the temporary to be watched"""
        # self.ledFolder.clear()  # In case there are any existing elements in the list

        temporary_file, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "pushButton", os.getenv("HOME"), "*.yaml"
        )

        if temporary_file:  # if user didn't pick a directory don't continue
            self.ledTemporaryLoc.setText(temporary_file)
            self.write_temporary_file()
            logger.info("changed temporary file to %s", temporary_file)

    def toggle_watch_temporary_file(self):
        """Toggle temporary file watching"""
        temporary_file = self.ledTemporaryLoc.text()
        if self.btnUseTemporaryFile.isChecked():
            if temporary_file:
                # create new instance of watcher potential
                splitted = os.path.split(temporary_file)
                path = os.path.join(*splitted[:-1])
                file = splitted[-1]
                self.temporary_file_monitor = FileMonitor(patterns=[file])
                self.thread_temporary_file = QtCore.QThread(self)
                self.temporary_file_monitor.getEmitter().modify_signal.connect(
                    self.temporary_file_changed
                )
                self.temporary_file_monitor.moveToThread(self.thread_temporary_file)

                self.btnUseTemporaryFile.setText("Do not use")
                self.temporary_file_monitor.observer.schedule(
                    self.temporary_file_monitor.event_handler, path, recursive=False
                )  # permission problems with subfolders
                self.temporary_file_monitor.observer.start()
                logger.info("watching %s", temporary_file)
            else:
                self.btnUseTemporaryFile.setChecked(False)

        elif not self.btnUseTemporaryFile.isChecked():
            self.btnUseTemporaryFile.setText("Use")
            self.temporary_file_monitor.observer.stop()

            logger.info("stop watching %s", temporary_file)

    def temporary_file_changed(self):
        with open(self.ledTemporaryLoc.text()) as f:
            self.parameters = yaml.load(f.read(), Loader=yaml.FullLoader)
        if self.parameters is None:
            self.parameters = {}
        self.populate_yamltextfield()
        self.populate_mask()

    def write_temporary_file(self):
        with open(self.ledTemporaryLoc.text(), "w", encoding="utf-8") as metadata_file:
            yaml.dump(
                self.parameters, metadata_file, sort_keys=False, allow_unicode=True
            )

    def hidden_write_temporary_file(self):
        # prevent unintended reload
        if not self.timer.isActive():
            self.temporary_file_monitor.getEmitter().modify_signal.disconnect()
        self.write_temporary_file()
        self.timer.start(1000)

    @QtCore.pyqtSlot()
    def reenable_temporary_file_watch(self):
        self.temporary_file_monitor.getEmitter().modify_signal.connect(
            self.temporary_file_changed
        )
        self.timer.stop()

    def enable_use(self):
        """Enable use button"""
        if os.path.exists(self.ledTemporaryLoc.text()):
            self.btnUseTemporaryFile.setEnabled(True)
        else:
            self.btnUseTemporaryFile.setDisabled(True)

    def browse_folder(self):
        """Open the dialog for selecting the folder to be watched"""
        # self.ledFolder.clear()  # In case there are any existing elements in the list
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "pushButton")
        # execute getExistingDirectory dialog and set the directory variable to be equal
        # to the user selected directory
        directory = os.sep.join(directory.split("/"))
        if directory:  # if user didn't pick a directory don't continue
            self.ledFolder.setText(directory)
            logger.info("changed watching folder to %s", directory)

    def enable_activate(self):
        """Enable activate button"""
        if os.path.exists(self.ledFolder.text()):
            self.btnActivate.setEnabled(True)
        else:
            self.btnActivate.setDisabled(True)

    def toggle_watch(self):
        """Toggle folder watching"""
        watch_directory = self.ledFolder.text()
        if self.btnActivate.isChecked():
            if watch_directory:
                self.ledFolder.setDisabled(True)
                self.ledFilePatterns.setDisabled(True)
                self.cbRecursiveWatch.setDisabled(True)
                # create new instance of watcher potential
                if self.ledFilePatterns.text() == "":
                    patterns = None
                else:
                    patterns = [
                        p.strip() for p in self.ledFilePatterns.text().split(",")
                    ]
                self.file_monitor = FileMonitor(patterns=patterns)
                self.thread = QtCore.QThread(self)
                self.file_monitor.getEmitter().create_signal.connect(self.file_created)
                self.file_monitor.moveToThread(self.thread)

                self.btnActivate.setText("Deactivate")
                self.file_monitor.observer.schedule(
                    self.file_monitor.event_handler,
                    watch_directory,
                    recursive=self.cbRecursiveWatch.isChecked(),
                )  # permission problems with subfolders
                self.file_monitor.observer.start()
                logger.info("watching %s", watch_directory)
            else:
                self.btnActivate.setChecked(False)

        elif not self.btnActivate.isChecked():
            self.btnActivate.setText("Activate")
            self.file_monitor.observer.stop()
            self.ledFolder.setEnabled(True)
            self.ledFilePatterns.setEnabled(True)
            self.cbRecursiveWatch.setEnabled(True)
            logger.info("stop watching %s", watch_directory)

    def file_created(self, msg):
        """Create the metadata file with timestamp and hash"""
        if not msg.endswith(".meta.yaml"):  # metadata files
            logger.info("created %s", msg)
            self.parameters["time metadata"] = datetime.datetime.now().strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
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
            with open(filename, "rb") as file:
                # Read and update hash string value in blocks of 4K
                for byte_block in iter(lambda: file.read(4096), b""):
                    sha512_hash.update(byte_block)
            return sha512_hash.hexdigest()
        # while file is created it is locked or doesnot exist yet??
        except (PermissionError, FileNotFoundError) as err:
            time.sleep(1)
            logger.exception("wrote metadata for %s", err)
            return self.hash_file(filename)

    def populate_yamltextfield(self):
        """Change the text of the raw yaml field when field text is changed in the mask"""
        # blocking of signals necessary to prevent regeneration of mask
        # which leads to a loss of focus of the currently edited mask field
        self.yamlText.blockSignals(True)
        self.yamlText.setPlainText(
            yaml.dump(self.parameters, sort_keys=False, allow_unicode=True)
        )
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
            self.parameters, self.sender().objectName().split("."), self.sender().text()
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
        """Generate input tree from parameters dict"""
        self.template_tree.import_from_dict(self.parameters)

    def write_metadata(self, file):
        """Write out metadata in file with file name corresponding to measurement file"""
        with open(file + ".meta.yaml", "w", encoding="utf-8") as metadata_file:
            yaml.dump(
                self.parameters, metadata_file, sort_keys=False, allow_unicode=True
            )
        logger.info("wrote metadata for %s", file + ".meta.yaml")

    def setup_logger(self):
        self.log_handler = LogHandler(self)
        self.log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(self.log_handler)
        self.log_handler.new_record.connect(self.pteLogging.appendPlainText)
        self.pteLogging.setReadOnly(True)
        # logging level
        logging.getLogger().setLevel(logging.INFO)
        logger.info("Starting autotag-metadata")

    def closeEvent(self, event):
        self.config._config["windowGeometry"] = self.frameGeometry().getCoords()
        self.config._config["watchFolder"] = self.ledFolder.text()
        self.config._config["temporaryFile"] = self.ledTemporaryLoc.text()
        self.config._config["filePatterns"] = self.ledFilePatterns.text()
        self.config._config["recursiveWatching"] = self.cbRecursiveWatch.isChecked()
        self.config.save_settings()
        
        super().closeEvent(event)
        logging.getLogger().removeHandler(self.log_handler)


def run():
    """Start Application"""
    app = QtWidgets.QApplication(sys.argv)  # A new instance of QApplication

    form = AutotagApp()  # We set the form to be our ExampleApp (design)
    # Set up logging to use your widget as a handler

    # log_handler = QPlainTextEditLogger()
    # logger.addHandler(log_handler)
    form.show()  # Show the form
    app.exec()  # and execute the app


if __name__ == "__main__":  # if we're running file directly and not importing it
    run()  # run the main function
