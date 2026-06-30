"""Autotag Metadata App — main window and application entry point."""
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

import logging
import os
import sys

from PyQt6 import QtCore, QtGui, QtWidgets, uic

from .config import Config
from .core.metadata_writer import build_metadata, write_metadata
from .core.yaml_utils import dump_yaml, dump_yaml_to_file, parse_yaml, validate_yaml_syntax
from .file_handling import FileMonitor
from .ui.logger import LogHandler
from .ui.template_dialog import TemplateDialog, TemplateDialogType
from .ui.templatetree import TemplateTree

logger = logging.getLogger(__name__)

path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)


class AutotagApp(QtWidgets.QMainWindow):
    """Main window — thin UI controller that delegates to core modules."""

    def __init__(self, *args, **kwargs):
        super(AutotagApp, self).__init__(*args, **kwargs)
        uic.loadUi(f"{dir_path}/ui/main_window.ui", self)

        self.setWindowTitle("Autotag Metadata")
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(f"{dir_path}/autotag_metadata.png"),
            QtGui.QIcon.Mode.Selected,
            QtGui.QIcon.State.On,
        )
        self.setWindowIcon(icon)

        self._setup_logger()
        self.config = Config()

        # signal wiring
        self.btnSelectTemporaryFile.clicked.connect(self.select_temporary_file)
        self.btnUseTemporaryFile.clicked.connect(self.toggle_watch_temporary_file)
        self.btnUseTemporaryFile.setDisabled(True)
        self.ledTemporaryLoc.textChanged.connect(self._enable_use)
        self.btnBrowse.clicked.connect(self.browse_folder)
        self.btnActivate.clicked.connect(self.toggle_watch)
        self.btnStore.clicked.connect(self.store_template)
        self.btnLoad.clicked.connect(self.load_template)

        self.template_tree = TemplateTree({})
        self.template_tree.model.dataChanged.connect(self._on_tree_data_change)
        self.scrollArea.setWidget(self.template_tree)

        self.ledFolder.textChanged.connect(self._enable_activate)
        self.btnActivate.setDisabled(True)
        self.yamlText.textChanged.connect(self._act_on_yaml_change)
        self.parameters = {}

        self._restore_settings()

        self._temporary_write_timer = QtCore.QTimer()
        self._temporary_write_timer.timeout.connect(self._reenable_temporary_file_watch)

    # -- settings persistence ----------------------------------------------

    def _restore_settings(self):
        """Populate widgets from saved config (tolerant of missing keys)."""
        geom = self.config.window_geometry
        if geom is not None:
            self.setGeometry(*geom)
        if self.config.watch_folder:
            self.ledFolder.setText(self.config.watch_folder)
        if self.config.temporary_file:
            self.ledTemporaryLoc.setText(self.config.temporary_file)
        if self.config.file_patterns:
            self.ledFilePatterns.setText(self.config.file_patterns)
        self.cbRecursiveWatch.setChecked(self.config.recursive_watching)

    def closeEvent(self, event):
        self.config.window_geometry = self.frameGeometry().getCoords()
        self.config.watch_folder = self.ledFolder.text()
        self.config.temporary_file = self.ledTemporaryLoc.text()
        self.config.file_patterns = self.ledFilePatterns.text()
        self.config.recursive_watching = self.cbRecursiveWatch.isChecked()
        self.config.save_settings()

        super().closeEvent(event)
        logging.getLogger().removeHandler(self._log_handler)

    # -- tree / yaml synchronization ---------------------------------------

    @QtCore.pyqtSlot()
    def _on_tree_data_change(self):
        mask_dict = self.template_tree.to_dict()
        if mask_dict:
            self.parameters = mask_dict
            self._populate_yamltextfield()
        else:
            self._populate_mask()
            logger.error("Value types can not be changed in the mask. Please use the text field or editor.")

    def _validate_yaml(self):
        """Validate the raw YAML text field and color it accordingly."""
        error = validate_yaml_syntax(self.yamlText.toPlainText())
        if error is None:
            self.yamlText.setStyleSheet("background-color: rgb(144, 238, 144);")
            return True
        else:
            self.yamlText.setStyleSheet("background-color: rgb(255, 106, 106);")
            return False

    def _act_on_yaml_change(self):
        """Update mask on change in raw yaml text field."""
        if self._validate_yaml():
            self.parameters = parse_yaml(self.yamlText.toPlainText())
            if isinstance(self.parameters, dict):
                self._populate_mask()
                if self.btnUseTemporaryFile.isChecked():
                    self._hidden_write_temporary_file()

    def _populate_yamltextfield(self):
        """Sync the raw YAML text field from the parameters dict."""
        # blocking of signals necessary to prevent regeneration of mask
        # which leads to a loss of focus of the currently edited mask field
        self.yamlText.blockSignals(True)
        self.yamlText.setPlainText(dump_yaml(self.parameters))
        self.yamlText.blockSignals(False)

    def _populate_mask(self):
        """Generate input tree from parameters dict."""
        self.template_tree.import_from_dict(self.parameters)

    # -- template management -----------------------------------------------

    def load_template(self):
        """Open the dialog for loading templates."""
        template_dialog = TemplateDialog(TemplateDialogType.Load)
        template_dialog.listWidget.addItems(self.config.template_names)

        if template_dialog.exec():
            yaml_text = self.config.load_template(template_dialog.template_name)
            self.parameters = parse_yaml(yaml_text)
            self._populate_yamltextfield()
            self._populate_mask()

    def store_template(self):
        """Open the dialog for storing templates."""
        template_dialog = TemplateDialog(TemplateDialogType.Store)
        template_dialog.listWidget.addItems(self.config.template_names)

        content = self.yamlText.toPlainText()
        if template_dialog.exec():
            self.config.save_template(template_dialog.template_name, content)

    # -- temporary file management -----------------------------------------

    def select_temporary_file(self):
        """Open a file dialog to select the temporary YAML file."""
        temporary_file, _ = QtWidgets.QFileDialog.getSaveFileName(self, "pushButton", os.getenv("HOME"), "*.yaml")
        if temporary_file:
            self.ledTemporaryLoc.setText(temporary_file)
            self._write_temporary_file()
            logger.info("changed temporary file to %s", temporary_file)

    def toggle_watch_temporary_file(self):
        """Toggle temporary file watching."""
        temporary_file = self.ledTemporaryLoc.text()
        if self.btnUseTemporaryFile.isChecked():
            if temporary_file:
                directory, filename = os.path.split(temporary_file)
                self._temporary_file_monitor = FileMonitor(patterns=[filename])
                self._temporary_file_monitor.getEmitter().modify_signal.connect(self._temporary_file_changed)

                self.btnUseTemporaryFile.setText("Do not use")
                self._temporary_file_monitor.observer.schedule(
                    self._temporary_file_monitor.event_handler, directory, recursive=False
                )
                self._temporary_file_monitor.observer.start()
                logger.info("watching %s", temporary_file)
            else:
                self.btnUseTemporaryFile.setChecked(False)

        elif not self.btnUseTemporaryFile.isChecked():
            self.btnUseTemporaryFile.setText("Use")
            self._temporary_file_monitor.observer.stop()
            logger.info("stop watching %s", temporary_file)

    def _temporary_file_changed(self):
        with open(self.ledTemporaryLoc.text()) as f:
            self.parameters = parse_yaml(f.read())
        if self.parameters is None:
            self.parameters = {}
        self._populate_yamltextfield()
        self._populate_mask()

    def _write_temporary_file(self):
        dump_yaml_to_file(self.parameters, self.ledTemporaryLoc.text())

    def _hidden_write_temporary_file(self):
        """Write the temporary file while suppressing the file-change signal."""
        if not self._temporary_write_timer.isActive():
            self._temporary_file_monitor.getEmitter().modify_signal.disconnect()
        self._write_temporary_file()
        self._temporary_write_timer.start(1000)

    @QtCore.pyqtSlot()
    def _reenable_temporary_file_watch(self):
        self._temporary_file_monitor.getEmitter().modify_signal.connect(self._temporary_file_changed)
        self._temporary_write_timer.stop()

    def _enable_use(self):
        """Enable the 'Use' button when the temporary file path is valid."""
        if os.path.exists(self.ledTemporaryLoc.text()):
            self.btnUseTemporaryFile.setEnabled(True)
        else:
            self.btnUseTemporaryFile.setDisabled(True)

    # -- folder watching ---------------------------------------------------

    def browse_folder(self):
        """Open a directory picker for the watched folder."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "pushButton")
        directory = os.sep.join(directory.split("/"))
        if directory:
            self.ledFolder.setText(directory)
            logger.info("changed watching folder to %s", directory)

    def _enable_activate(self):
        """Enable the Activate button when the folder path is valid."""
        if os.path.exists(self.ledFolder.text()):
            self.btnActivate.setEnabled(True)
        else:
            self.btnActivate.setDisabled(True)

    def toggle_watch(self):
        """Toggle folder watching."""
        watch_directory = self.ledFolder.text()
        if self.btnActivate.isChecked():
            if watch_directory:
                self.ledFolder.setDisabled(True)
                self.ledFilePatterns.setDisabled(True)
                self.cbRecursiveWatch.setDisabled(True)

                if self.ledFilePatterns.text() == "":
                    patterns = None
                else:
                    patterns = [p.strip() for p in self.ledFilePatterns.text().split(",")]

                self._file_monitor = FileMonitor(watch_directory, patterns=patterns)
                self._file_monitor.create_signal.connect(self._file_created)

                self.btnActivate.setText("Deactivate")
                self._file_monitor.start()

                logger.info("watching %s", watch_directory)
            else:
                self.btnActivate.setChecked(False)

        elif not self.btnActivate.isChecked():
            self.btnActivate.setText("Activate")
            self._file_monitor.stop()
            self._file_monitor.wait()
            self.ledFolder.setEnabled(True)
            self.ledFilePatterns.setEnabled(True)
            self.cbRecursiveWatch.setEnabled(True)
            logger.info("stop watching %s", watch_directory)

    def _on_files_submitted(self, paths):
        """Handle files dropped onto the dropzone"""
        for path in paths:
            self.file_created(path)

    def _file_created(self, msg):
        """Handle a newly created file — build and write metadata."""
        if not msg.endswith(".meta.yaml"):
            logger.info("created %s", msg)
            result = build_metadata(msg, self.parameters)
            if result is not None:
                write_metadata(msg, self.parameters)

    # -- logging -----------------------------------------------------------

    def _setup_logger(self):
        self._log_handler = LogHandler(self)
        self._log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(self._log_handler)
        self._log_handler.new_record.connect(self.pteLogging.appendPlainText)
        self.pteLogging.setReadOnly(True)
        logging.getLogger().setLevel(logging.INFO)
        logger.info("Starting autotag-metadata")


def run():
    """Start Application."""
    app = QtWidgets.QApplication(sys.argv)
    form = AutotagApp()
    form.show()
    app.exec()


if __name__ == "__main__":
    run()
