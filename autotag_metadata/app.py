"""Autotag Metadata App — main window and application entry point."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2022      Albert Engstfeld
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
import logging
import sys
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets, uic

from .config import Config
from .core.metadata_writer import build_metadata, write_metadata
from .core.yaml_document import non_destructive_merge, overwrite_merge
from .core.yaml_utils import dump_yaml, dump_yaml_to_file, parse_yaml
from .file_handling import FileMonitor
from .ui.editable_list import EditableListView
from .ui.label_dropzone import LabelDropzone
from .ui.library_panel import LibraryPanel
from .ui.logger import LogHandler
from .ui.snippets_list import SnippetsListView
from .ui.yaml_multi_view import YamlMultiView
from .ui.zoom_panels import ZoomFormView, ZoomTextView

logger = logging.getLogger(__name__)

_DIR = Path(__file__).parent
_ICON = _DIR / "autotag_metadata.png"

_IDX_FORM = 0
_IDX_YAML = 1

# Validity indicator colours for the YAML tab button (read on light and dark).
_YAML_OK = "#27ae60"
_YAML_ERR = "#e74c3c"


def _default_snippet_name(data) -> str:
    """Default name for a captured snippet: its top-level key, else 'snippet'."""
    if isinstance(data, dict) and data:
        return str(next(iter(data)))
    return "snippet"


class AutotagApp(QtWidgets.QMainWindow):
    """Main window — thin UI controller that delegates to core modules."""

    def __init__(self, *args, **kwargs):
        super(AutotagApp, self).__init__(*args, **kwargs)
        uic.loadUi(_DIR / "ui" / "main_window.ui", self)

        self.setWindowTitle("Autotag Metadata")
        self.setWindowIcon(QtGui.QIcon(str(_ICON)))

        self._setup_logger()
        self.config = Config()

        # Watch / live-file controls — kept under their original attribute names
        # so the handler methods stay unchanged. They live in the toolbars.
        self.ledTemporaryLoc = QtWidgets.QLineEdit()
        self.ledTemporaryLoc.setPlaceholderText("YAML file kept in sync with the editor")
        self.btnUseTemporaryFile = QtWidgets.QPushButton("Use")
        self.btnUseTemporaryFile.setCheckable(True)
        self.btnSelectTemporaryFile = QtWidgets.QPushButton("Select…")
        self.ledFilePatterns = QtWidgets.QLineEdit()
        self.ledFilePatterns.setPlaceholderText("*.csv,*.tsv (empty = all)")
        self.cbRecursiveWatch = QtWidgets.QCheckBox("Recursive")

        self.ledFolder = QtWidgets.QLineEdit()
        self.btnBrowse = QtWidgets.QPushButton("Browse…")
        self.btnActivate = QtWidgets.QPushButton("Activate")
        self.btnActivate.setCheckable(True)

        # signal wiring
        self.btnSelectTemporaryFile.clicked.connect(self.select_temporary_file)
        self.btnUseTemporaryFile.clicked.connect(self.toggle_watch_temporary_file)
        self.btnUseTemporaryFile.setDisabled(True)
        self.ledTemporaryLoc.textChanged.connect(self._enable_use)
        self.btnBrowse.clicked.connect(self.browse_folder)
        self.btnActivate.clicked.connect(self.toggle_watch)

        # menu actions and keyboard shortcuts
        self.actExit.triggered.connect(self.close)
        self.actExit.setShortcut(QtGui.QKeySequence("Ctrl+Q"))

        self._form_multiview = YamlMultiView(view_factory=ZoomFormView)
        self._form_multiview.document_changed.connect(self._on_form_multiview_changed)
        self._form_multiview.snippet_capture_requested.connect(self.capture_snippet)
        self._form_multiview.snippet_dropped.connect(self._apply_snippet_text)

        self._text_multiview = YamlMultiView(view_factory=ZoomTextView)
        self._text_multiview.document_changed.connect(self._on_text_multiview_changed)
        self._text_multiview.snippet_capture_requested.connect(self.capture_snippet)
        self._text_multiview.snippet_dropped.connect(self._apply_snippet_text)
        self._form_multiview.set_layout(self.config.multiview_layout)

        self._setup_snippet_dock()
        self._setup_dropzone()  # split below before the library docks tabify
        self._setup_library_docks()

        # The editor (form + raw YAML) fills the central area.
        container_layout = self.editorContainer.layout()
        self._stack = QtWidgets.QStackedWidget()
        self._stack.addWidget(self._form_multiview)  # index 0 — form
        self._stack.addWidget(self._text_multiview)  # index 1 — raw YAML
        container_layout.addWidget(self._stack)

        self._setup_menus()
        self._setup_toolbar()
        self._setup_settings_toolbar()

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Tab"), self).activated.connect(self._toggle_view)

        self.ledFolder.textChanged.connect(self._enable_activate)
        self.btnActivate.setDisabled(True)
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
        self.config.multiview_layout = self._form_multiview.get_layout()
        self.config.save_settings()

        super().closeEvent(event)
        logging.getLogger().removeHandler(self._log_handler)
        # Drop the handler from logging's registry so logging.shutdown() at
        # interpreter exit does not touch the now-deleted Qt C++ object.
        self._log_handler.close()

    # -- tree / yaml synchronization ---------------------------------------

    def _validate_yaml(self):
        """Reflect YAML validity on the tab button (document is always valid when maintained via the UI)."""
        self._set_yaml_status(True)
        return True

    def _set_yaml_status(self, valid: bool, detail: str | None = None) -> None:
        """Tint the YAML tab green/red to signal syntax validity."""
        self._view_tabs.setTabTextColor(_IDX_YAML, QtGui.QColor(_YAML_OK if valid else _YAML_ERR))
        self._view_tabs.setTabToolTip(_IDX_YAML, "YAML is valid" if valid else f"YAML syntax error:\n{detail}")

    def _populate_yamltextfield(self):
        """Sync both multiviews from the parameters dict."""
        self._text_multiview.set_document(self.parameters)
        self._form_multiview.set_document(self.parameters)

    @QtCore.pyqtSlot(dict)
    def _on_form_multiview_changed(self, data: dict) -> None:
        self.parameters = data
        self._text_multiview.set_document(data)

    @QtCore.pyqtSlot(dict)
    def _on_text_multiview_changed(self, data: dict) -> None:
        self.parameters = data
        self._form_multiview.set_document(data)
        self._set_yaml_status(True)
        if self.btnUseTemporaryFile.isChecked():
            self._hidden_write_temporary_file()

    # -- menus / docks -----------------------------------------------------

    def _setup_menus(self) -> None:
        """Build Template / View menus (reused by the toolbar) and shortcuts."""
        bar = self.menuBar()

        self._template_menu = bar.addMenu("&Template")
        act_store = self._template_menu.addAction("&Save Template")
        act_store.setShortcut(QtGui.QKeySequence("Ctrl+S"))
        act_store.triggered.connect(lambda: self._focus_save(self._templates_dock, self._templates_panel))

        self._view_menu = bar.addMenu("&View")
        self._dropzone_toggle = self._dropzone_dock.toggleViewAction()
        self._dropzone_toggle.setText("&Drop files")
        self._view_menu.addAction(self._dropzone_toggle)
        self._log_toggle = self._log_dock.toggleViewAction()
        self._log_toggle.setText("&Log")
        self._log_toggle.setShortcut(QtGui.QKeySequence("Ctrl+L"))
        self._view_menu.addAction(self._log_toggle)
        self._view_menu.addSeparator()
        self._view_menu.addAction("Save &View", lambda: self._focus_save(self._views_dock, self._views_panel))

    def _focus_save(self, dock: QtWidgets.QDockWidget, panel: LibraryPanel) -> None:
        """Reveal a library dock and focus its name field (Save shortcut)."""
        dock.show()
        dock.raise_()
        panel.start_new()

    def _setup_toolbar(self) -> None:
        """Build the editor-centric top toolbar."""
        tb = QtWidgets.QToolBar("Main")
        tb.setObjectName("mainToolbar")
        tb.setMovable(False)
        tb.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, tb)
        self._toolbar = tb

        # -- library sidebar toggle --
        self._act_sidebar = QtGui.QAction("☰ Library", self, checkable=True)
        self._act_sidebar.setChecked(True)
        self._act_sidebar.setToolTip("Show or hide the library sidebar")
        self._act_sidebar.toggled.connect(self._set_library_visible)
        tb.addAction(self._act_sidebar)

        # -- Form / YAML view switch: sits at the far left, above the sidebar --
        self._view_tabs = QtWidgets.QTabBar()
        self._view_tabs.setDocumentMode(True)
        self._view_tabs.setDrawBase(False)
        self._view_tabs.addTab("⊞ Form")
        self._view_tabs.addTab("{ } YAML")
        self._view_tabs.setTabToolTip(_IDX_FORM, "Structured form editor")
        self._view_tabs.setTabToolTip(_IDX_YAML, "Raw YAML editor")
        self._view_tabs.currentChanged.connect(self._stack.setCurrentIndex)
        tb.addWidget(self._view_tabs)
        tb.addSeparator()

        # -- watch controls --
        tb.addWidget(QtWidgets.QLabel("Folder: "))
        self.ledFolder.setMinimumWidth(280)
        self.ledFolder.setPlaceholderText("Folder to watch for new files")
        self.ledFolder.setToolTip("Folder watched for newly created files")
        tb.addWidget(self.ledFolder)
        tb.addWidget(self.btnBrowse)
        tb.addWidget(self.btnActivate)

        # -- push panel toggles to the right --
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        tb.addAction(self._dropzone_toggle)
        tb.addAction(self._log_toggle)

        self._set_yaml_status(True)

    def _setup_settings_toolbar(self) -> None:
        """Second toolbar row: watch patterns/recursive and the live-file controls."""
        self.addToolBarBreak(QtCore.Qt.ToolBarArea.TopToolBarArea)
        tb = QtWidgets.QToolBar("Watch & live file")
        tb.setObjectName("settingsToolbar")
        tb.setMovable(False)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, tb)
        self._settings_toolbar = tb

        tb.addWidget(QtWidgets.QLabel("Patterns: "))
        self.ledFilePatterns.setMinimumWidth(150)
        self.ledFilePatterns.setToolTip("Comma-separated, e.g. *.csv,*.tsv (empty = all files)")
        tb.addWidget(self.ledFilePatterns)
        tb.addWidget(self.cbRecursiveWatch)
        tb.addSeparator()
        tb.addWidget(QtWidgets.QLabel("Live file: "))
        self.ledTemporaryLoc.setMinimumWidth(240)
        tb.addWidget(self.ledTemporaryLoc)
        tb.addWidget(self.btnSelectTemporaryFile)
        tb.addWidget(self.btnUseTemporaryFile)

    def _toggle_view(self) -> None:
        """Flip between Form and YAML (bound to Ctrl+Tab)."""
        nxt = _IDX_YAML if self._view_tabs.currentIndex() == _IDX_FORM else _IDX_FORM
        self._view_tabs.setCurrentIndex(nxt)

    def _set_library_visible(self, visible: bool) -> None:
        """Show or hide the whole library sidebar (Snippets/Templates/Views)."""
        for dock in (self._snippet_dock, self._templates_dock, self._views_dock):
            dock.setVisible(visible)
        if visible:
            self._snippet_dock.raise_()

    def _setup_snippet_dock(self) -> None:
        """Create the snippets dock (part of the always-visible library rail)."""
        self._pending_snippet: dict | None = None
        self._snippet_panel = LibraryPanel(SnippetsListView(), "Save snippet")
        self._snippet_list = self._snippet_panel.list_view
        self._snippet_list.setToolTip(
            "Double-click to add (keep existing) · Ctrl+double-click to overwrite · drag to apply"
        )
        self._snippet_panel.activated.connect(self._apply_snippet)
        self._snippet_panel.delete_requested.connect(self._delete_snippet)
        self._snippet_panel.save_requested.connect(self._save_named_snippet)
        # The Save button has nothing to store on its own, so seed the pending
        # snippet from the active multi-view panel (the ⊕ source) on each press.
        self._snippet_panel.save_started.connect(self._seed_snippet_from_active_panel)

        self._snippet_dock = QtWidgets.QDockWidget("Snippets", self)
        self._snippet_dock.setObjectName("snippetDock")
        self._snippet_dock.setWidget(self._snippet_panel)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self._snippet_dock)
        self._refresh_snippet_dock()

    def _refresh_snippet_dock(self) -> None:
        self._snippet_list.set_snippets(
            {name: self.config.load_snippet(name) for name in self.config.snippet_names}
        )

    def _setup_library_docks(self) -> None:
        """Create the Templates and Views sidebars, tabbed with Snippets."""
        self._templates_panel = LibraryPanel(EditableListView(), "Save current as template")
        self._templates_panel.activated.connect(self._apply_template)
        self._templates_panel.save_requested.connect(self.store_template)
        self._templates_panel.delete_requested.connect(self._delete_template)
        self._templates_dock = QtWidgets.QDockWidget("Templates", self)
        self._templates_dock.setObjectName("templatesDock")
        self._templates_dock.setWidget(self._templates_panel)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self._templates_dock)

        self._views_panel = LibraryPanel(EditableListView(), "Save current view")
        self._views_panel.activated.connect(self._apply_view)
        self._views_panel.save_requested.connect(self.save_view)
        self._views_panel.delete_requested.connect(self._delete_view)
        self._views_dock = QtWidgets.QDockWidget("Views", self)
        self._views_dock.setObjectName("viewsDock")
        self._views_dock.setWidget(self._views_panel)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self._views_dock)

        # Stack the three library panels as tabs in the left rail, tabs on top.
        self.tabifyDockWidget(self._snippet_dock, self._templates_dock)
        self.tabifyDockWidget(self._templates_dock, self._views_dock)
        self.setTabPosition(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
            QtWidgets.QTabWidget.TabPosition.North,
        )
        self.setDocumentMode(True)  # flat dock tabs, matching the Form/YAML tabs
        # The tab already labels each panel — drop the duplicate dock title bar.
        for dock in (self._snippet_dock, self._templates_dock, self._views_dock):
            dock.setTitleBarWidget(QtWidgets.QWidget(dock))
        # Equal minimum width so the rail keeps a stable width across tabs.
        for panel in (self._snippet_panel, self._templates_panel, self._views_panel):
            panel.setMinimumWidth(200)

        # The rail stays visible; Snippets is the default active tab.
        self._snippet_dock.raise_()

        self._refresh_templates_panel()
        self._refresh_views_panel()

    def _refresh_templates_panel(self) -> None:
        self._templates_panel.set_items(self.config.template_names)

    def _refresh_views_panel(self) -> None:
        self._views_panel.set_items(self.config.view_names)

    def _setup_dropzone(self) -> None:
        """Create the (hidden by default) file drop zone below the library rail."""
        self._dropzone = LabelDropzone()
        self._dropzone.files_submitted.connect(self._on_files_dropped)
        self._dropzone_dock = QtWidgets.QDockWidget("Drop files", self)
        self._dropzone_dock.setObjectName("dropzoneDock")
        self._dropzone_dock.setWidget(self._dropzone)
        self.splitDockWidget(self._snippet_dock, self._dropzone_dock, QtCore.Qt.Orientation.Vertical)
        self._dropzone_dock.hide()

    def _on_files_dropped(self, paths: list[str]) -> None:
        """Tag each dropped file; recurse into dropped folders (honoring file patterns).

        A directly dropped file is tagged regardless of the pattern filter; files
        found inside a dropped folder must match it. ``.meta.yaml`` files are
        skipped.
        """
        patterns = self._file_pattern_list()
        targets: list[Path] = []
        for path in paths:
            p = Path(path)
            if p.is_file() and not p.name.endswith(".meta.yaml"):
                targets.append(p)
            elif p.is_dir():
                targets += [
                    child
                    for child in sorted(p.rglob("*"))
                    if child.is_file()
                    and not child.name.endswith(".meta.yaml")
                    and self._matches_pattern(child.name, patterns)
                ]
        for target in targets:
            self._file_created(str(target))
        logger.info("tagged %d dropped file(s)", len(targets))

    def _file_pattern_list(self) -> list[str] | None:
        """The watch file patterns as a list, or None when none are set (= all)."""
        text = self.ledFilePatterns.text().strip()
        return [p.strip() for p in text.split(",") if p.strip()] or None

    @staticmethod
    def _matches_pattern(name: str, patterns: list[str] | None) -> bool:
        return patterns is None or any(fnmatch.fnmatch(name, pat) for pat in patterns)

    # -- snippet management ------------------------------------------------

    @QtCore.pyqtSlot(dict, str)
    def capture_snippet(self, data: dict, name_hint: str = "") -> None:
        """Stash a captured subtree and focus the snippet name field to save it."""
        self._pending_snippet = data
        self._snippet_dock.show()
        self._snippet_dock.raise_()
        self._snippet_panel.prime(name_hint or _default_snippet_name(data))

    def _seed_snippet_from_active_panel(self) -> None:
        """Capture the active multi-view panel so the Save button has data to store.

        The snippet panel's Save button starts inline naming but carries nothing
        itself; pull the subtree (or leaf) from the active panel — the same thing
        that panel's ⊕ button would capture.
        """
        view = self._form_multiview.active_view
        if view is None:
            return
        data, _path = view.capture_payload()
        self._pending_snippet = data

    def _save_named_snippet(self, name: str) -> None:
        data = self._pending_snippet
        if data is None:
            return
        try:
            self.config.save_snippet(self._unique_snippet_name(name), dump_yaml(data))
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Save Snippet Failed", str(exc))
            return
        self._pending_snippet = None
        self._refresh_snippet_dock()

    def _apply_snippet(self, name: str) -> None:
        """Apply snippet *name* — plain double-click adds, Ctrl+double-click overwrites."""
        ctrl = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.KeyboardModifier.ControlModifier)
        self._apply_snippet_text(self.config.load_snippet(name), overwrite=ctrl)

    def _apply_snippet_text(self, text: str, overwrite: bool = False) -> None:
        """Merge a snippet (YAML text) into the document.

        Non-destructive by default (adds only what's missing); *overwrite* lets
        the snippet win on conflicts. The snippet is path-anchored, so it lands
        at its origin.
        """
        data = parse_yaml(text)
        if not isinstance(data, dict):
            return
        merge = overwrite_merge if overwrite else non_destructive_merge
        self.parameters = merge(self.parameters or {}, data)
        self._populate_yamltextfield()
        self._form_multiview.set_document(self.parameters)

    def _unique_snippet_name(self, base: str) -> str:
        existing = set(self.config.snippet_names)
        if base not in existing:
            return base
        i = 2
        while f"{base}-{i}" in existing:
            i += 1
        return f"{base}-{i}"

    def _delete_snippet(self, name: str) -> None:
        if (
            QtWidgets.QMessageBox.question(self, "Delete Snippet", f'Delete snippet "{name}"?')
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return
        self.config.delete_snippet(name)
        self._refresh_snippet_dock()

    # -- view (layout) management ------------------------------------------

    def save_view(self, name: str) -> None:
        """Save the current multi-view tiling under *name* (from the sidebar)."""
        try:
            self.config.save_view(name, self._form_multiview.get_layout())
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Save View Failed", str(exc))
            return
        self._refresh_views_panel()

    def _apply_view(self, name: str) -> None:
        """Load the named layout *name* into the multi-view."""
        try:
            layout = self.config.load_view(name)
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Load View Failed", str(exc))
            return
        self._form_multiview.set_layout(layout)

    def _delete_view(self, name: str) -> None:
        if (
            QtWidgets.QMessageBox.question(self, "Delete View", f'Delete view "{name}"?')
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return
        self.config.delete_view(name)
        self._refresh_views_panel()

    # -- template management -----------------------------------------------

    def _apply_template(self, name: str) -> None:
        """Load the template *name* into the editor."""
        try:
            yaml_text = self.config.load_template(name)
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Load Template Failed", str(exc))
            return
        self.parameters = parse_yaml(yaml_text)
        self._populate_yamltextfield()
        self._form_multiview.set_document(self.parameters)

    def store_template(self, name: str) -> None:
        """Save the current document as a template under *name* (from the sidebar)."""
        try:
            self.config.save_template(name, dump_yaml(self.parameters))
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Store Template Failed", str(exc))
            return
        self._refresh_templates_panel()

    def _delete_template(self, name: str) -> None:
        if (
            QtWidgets.QMessageBox.question(self, "Delete Template", f'Delete template "{name}"?')
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return
        self.config.delete_template(name)
        self._refresh_templates_panel()

    # -- temporary file management -----------------------------------------

    def select_temporary_file(self):
        """Open a file dialog to select the temporary YAML file."""
        temporary_file, _ = QtWidgets.QFileDialog.getSaveFileName(self, "pushButton", str(Path.home()), "*.yaml")
        if temporary_file:
            self.ledTemporaryLoc.setText(temporary_file)
            self._write_temporary_file()
            logger.info("changed temporary file to %s", temporary_file)

    def toggle_watch_temporary_file(self):
        """Toggle temporary file watching."""
        temporary_file = self.ledTemporaryLoc.text()
        if self.btnUseTemporaryFile.isChecked():
            if temporary_file:
                tmp = Path(temporary_file)
                self._temporary_file_monitor = FileMonitor(str(tmp.parent), patterns=[tmp.name])
                self._temporary_file_monitor.modify_signal.connect(self._temporary_file_changed)
                self.btnUseTemporaryFile.setText("Do not use")
                self._temporary_file_monitor.start()
                logger.info("watching %s", temporary_file)
            else:
                self.btnUseTemporaryFile.setChecked(False)

        elif not self.btnUseTemporaryFile.isChecked():
            self.btnUseTemporaryFile.setText("Use")
            self._temporary_file_monitor.stop()
            self._temporary_file_monitor.wait()
            logger.info("stop watching %s", temporary_file)

    def _temporary_file_changed(self, _path: str = "") -> None:
        try:
            with open(self.ledTemporaryLoc.text()) as f:
                self.parameters = parse_yaml(f.read())
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Temporary File Error", str(exc))
            return
        if self.parameters is None:
            self.parameters = {}
        self._populate_yamltextfield()
        self._form_multiview.set_document(self.parameters)

    def _write_temporary_file(self):
        dump_yaml_to_file(self.parameters, self.ledTemporaryLoc.text())

    def _hidden_write_temporary_file(self):
        """Write the temporary file while suppressing the file-change signal."""
        if not self._temporary_write_timer.isActive():
            self._temporary_file_monitor.modify_signal.disconnect()
        self._write_temporary_file()
        self._temporary_write_timer.start(1000)

    @QtCore.pyqtSlot()
    def _reenable_temporary_file_watch(self):
        self._temporary_file_monitor.modify_signal.connect(self._temporary_file_changed)
        self._temporary_write_timer.stop()

    def _enable_use(self):
        """Enable the 'Use' button when the temporary file path is valid."""
        if Path(self.ledTemporaryLoc.text()).exists():
            self.btnUseTemporaryFile.setEnabled(True)
        else:
            self.btnUseTemporaryFile.setDisabled(True)

    # -- folder watching ---------------------------------------------------

    def browse_folder(self):
        """Open a directory picker for the watched folder."""
        directory = str(Path(QtWidgets.QFileDialog.getExistingDirectory(self, "pushButton")))
        if directory:
            self.ledFolder.setText(directory)
            logger.info("changed watching folder to %s", directory)

    def _enable_activate(self):
        """Enable the Activate button when the folder path is valid."""
        if Path(self.ledFolder.text()).exists():
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
                self.setWindowTitle(f"Autotag Metadata — {watch_directory}")
                self._file_monitor.start()

                logger.info("watching %s", watch_directory)
            else:
                self.btnActivate.setChecked(False)

        elif not self.btnActivate.isChecked():
            self.btnActivate.setText("Activate")
            self.setWindowTitle("Autotag Metadata")
            self._file_monitor.stop()
            self._file_monitor.wait()
            self.ledFolder.setEnabled(True)
            self.ledFilePatterns.setEnabled(True)
            self.cbRecursiveWatch.setEnabled(True)
            logger.info("stop watching %s", watch_directory)

    def _file_created(self, msg):
        """Handle a newly created file — build and write metadata."""
        if not msg.endswith(".meta.yaml"):
            logger.info("created %s", msg)
            result = build_metadata(msg, self.parameters)
            if result is not None:
                write_metadata(msg, self.parameters)

    # -- logging -----------------------------------------------------------

    def _setup_logger(self):
        self.pteLogging = QtWidgets.QPlainTextEdit()
        self.pteLogging.setReadOnly(True)
        self.pteLogging.setMaximumBlockCount(2000)

        self._log_dock = QtWidgets.QDockWidget("Log", self)
        self._log_dock.setObjectName("logDock")
        self._log_dock.setWidget(self.pteLogging)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)
        self.resizeDocks([self._log_dock], [140], QtCore.Qt.Orientation.Vertical)

        self._log_handler = LogHandler(self)
        self._log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(self._log_handler)
        self._log_handler.new_record.connect(self.pteLogging.appendPlainText)
        logging.getLogger().setLevel(logging.INFO)
        logger.info("Starting autotag-metadata")


def run():
    """Start Application."""
    # Silence a benign Qt-Wayland text-input protocol warning ("Got leave event
    # for surface 0x0 ..."). It is emitted by Qt's Wayland plugin on focus
    # changes, not by this app, and is pure console noise.
    QtCore.QLoggingCategory.setFilterRules("qt.qpa.wayland.textinput.warning=false")
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Autotag Metadata")
    app.setApplicationDisplayName("Autotag Metadata")
    # The taskbar/window list uses the application icon; on Wayland the icon is
    # matched via the desktop-file name (app_id) to an installed .desktop entry.
    app.setWindowIcon(QtGui.QIcon(str(_ICON)))
    app.setDesktopFileName("autotag-metadata")
    form = AutotagApp()
    form.show()
    app.exec()


if __name__ == "__main__":
    run()
