"""Guided coach-mark tour — content, choreography, and state save/restore for AutotagApp.

This module keeps everything tour-specific (the example document, the seeded library
items, the step scripts, and the save/restore of the user's document and settings) out of
:class:`~autotag_metadata.app.AutotagApp`. :class:`GuidedTour` is a companion controller:
it drives the app's own widgets so the coach marks point at the real chrome.
"""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2026 Johannes Hermann
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

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QTextCursor

from ..core.yaml_utils import parse_yaml
from .tour import TourOverlay, TourStep
from .yaml_multi_view import YamlMultiView

if TYPE_CHECKING:
    from ..app import AutotagApp

# Editor tab order — mirrors AutotagApp._setup_editor_area (Form, YAML, JSON).
_FORM_TAB = 0
_YAML_TAB = 1
_JSON_TAB = 2

_EXAMPLE_YAML = """\
echemdbSchemaVersion: 0.7.1
curation:
  process:
    - role: experimentalist
      name: J. Smith
      orcid: https://orcid.org/0000-0000-0000-0000
experimental:
  notes: |
    ## Sample preparation

    Au(111) single crystal **flame-annealed**, then:

    - 10 min sonication in ultrapure water
    - dried under N2

    Electrolyte prepared fresh; see [echemdb](https://echemdb.org).
  tags:
    - BCV
  instrumentation:
    - type: potentiostat
      manufacturer: Biologic
      name: Poti1
  operationParameters:
    temperature:
      value: 298.15
      unit: K
figureDescription:
  type: raw
  fields:
    - name: E [V]
      unit: V
      dimension: E
    - name: I / [A cm-2]
      unit: A cm-2
      dimension: j
system:
  type: electrochemical
  electrolyte:
    type: aqueous
    components:
      - name: water
        type: solvent
        purity:
          grade: ultrapure water
  electrodes:
    - name: WE
      function: working electrode
      material: Au
      crystallographicOrientation: "111"
      geometricElectrolyteContactArea:
        value: 1
        unit: cm-2
"""
# Same document, but with `function:` under electrodes over-indented by one space —
# a block-mapping sibling must align exactly, so this reliably raises a YAMLError.
_BROKEN_LINE = "       function: working electrode"
_BROKEN_YAML = _EXAMPLE_YAML.replace("      function: working electrode", _BROKEN_LINE)
_SNIPPET_YAML = """\
curation:
  process:
    - role: co-experimentalist
      name: A. Müller
      orcid: https://orcid.org/0000-0000-0000-0001
"""
_SNIPPET_NAME = "tour: co-experimentalist"
_TEMPLATE_NAME = "tour: EC-Lab experiment"
_VIEW_NAME = "tour: three tiles"
_VIEW_LAYOUT = {
    "orientation": "h",
    "sizes": [],
    "children": [{"path": "curation"}, {"path": "experimental"}, {"path": "system"}],
}


class GuidedTour:
    """Runs the coach-mark tour over :class:`AutotagApp`'s live chrome.

    On :meth:`start` it saves the user's document and watch settings, loads an example
    document, and seeds a temporary snippet/template/view into the library so the
    interactive steps have something to apply. On finish (or :meth:`stop`) it deletes
    those temporary items and restores everything it changed.
    """

    def __init__(self, app: "AutotagApp") -> None:
        self._app = app
        self._overlay: TourOverlay | None = None
        self._saved_parameters: object = None
        self._saved_patterns = ""
        self._saved_recursive = False
        self._saved_suffix = ""
        self._saved_watching = False

    # -- lifecycle ---------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._overlay is not None

    def start(self) -> None:
        """Save app state, load the example, and launch the overlay over the real chrome."""
        app = self._app
        if self._overlay is not None:
            return
        app.config.tour_seen = True
        self._saved_parameters = app.parameters
        self._saved_patterns = app.ledFilePatterns.text()
        self._saved_recursive = app.cbRecursiveWatch.isChecked()
        self._saved_suffix = app.ledMetaSuffix.text()
        self._saved_watching = app.btnActivate.isChecked()
        if self._saved_watching:
            app.btnActivate.setChecked(False)
            app.toggle_watch()
        self._load_example()
        self._overlay = TourOverlay(app, self._build_steps())
        self._overlay.finished.connect(self._on_finished)
        self._overlay.start()

    def stop(self) -> None:
        """Cancel a running tour (e.g. the window is closing); runs the finish cleanup."""
        if self._overlay is not None:
            self._overlay.stop()

    # -- screenshot support (used by doc/generate_tour_screenshots.py) -----

    @property
    def step_titles(self) -> list[str]:
        return [step.title for step in self._overlay._steps] if self._overlay is not None else []

    @property
    def step_slugs(self) -> list[str]:
        """Stable per-step identifiers, in tour order. Screenshots are named after these."""
        return [step.slug for step in self._overlay._steps] if self._overlay is not None else []

    def show_step(self, index: int) -> None:
        """Jump the running tour to *index* and run that step's ``on_enter``."""
        if self._overlay is not None:
            self._overlay._index = index
            self._overlay._show_step()

    # -- example document + temporary library items ------------------------

    def _load_example(self) -> None:
        app = self._app
        app.parameters = parse_yaml(_EXAMPLE_YAML)
        app._text_multiview.set_document(app.parameters)
        app._form_multiview.set_document(app.parameters)
        app.ledFilePatterns.setText("*.csv,*.tsv")
        app.cbRecursiveWatch.setChecked(False)
        app.ledMetaSuffix.setText("")
        # Seed tour items into config so apply operations can load them.
        app.config.save_snippet(_SNIPPET_NAME, _SNIPPET_YAML)
        app.config.save_template(_TEMPLATE_NAME, _EXAMPLE_YAML)
        app.config.save_view(_VIEW_NAME, _VIEW_LAYOUT)
        # Show only the tour items — the user's own library is temporarily hidden.
        app._snippet_list.set_snippets({_SNIPPET_NAME: _SNIPPET_YAML})
        app._templates_panel.set_items([_TEMPLATE_NAME])
        app._views_panel.set_items([_VIEW_NAME])

    def _on_finished(self) -> None:
        app = self._app
        self._overlay = None
        app.parameters = self._saved_parameters
        app._text_multiview.set_document(app.parameters)
        app._form_multiview.set_document(app.parameters)
        app.config.delete_snippet(_SNIPPET_NAME)
        app._refresh_snippet_dock()
        app.config.delete_template(_TEMPLATE_NAME)
        app._refresh_templates_panel()
        app.config.delete_view(_VIEW_NAME)
        app._refresh_views_panel()
        app._form_multiview.set_layout(None)
        app.ledFilePatterns.setText(self._saved_patterns)
        app.cbRecursiveWatch.setChecked(self._saved_recursive)
        app.ledMetaSuffix.setText(self._saved_suffix)
        if self._saved_watching:
            app.btnActivate.setChecked(True)
            app.toggle_watch()

    # -- per-step choreography (TourStep.on_enter callbacks) ---------------

    def _show_form(self) -> None:
        self._app._view_tabs.setCurrentIndex(_FORM_TAB)

    def _show_yaml(self) -> None:
        self._app._view_tabs.setCurrentIndex(_YAML_TAB)

    def _show_json(self) -> None:
        self._app._view_tabs.setCurrentIndex(_JSON_TAB)

    def _show_prose(self) -> None:
        """Zoom the Form onto `experimental`, where the example's prose field lives."""
        app = self._app
        app._view_tabs.setCurrentIndex(_FORM_TAB)
        app._form_multiview.set_layout({"path": "experimental"})

    def _show_broken_yaml(self) -> None:
        """Inject a syntax error (over-indented list-item key) for the user to spot and fix."""
        app = self._app
        app._view_tabs.setCurrentIndex(_YAML_TAB)
        panel = app._text_multiview.active_view
        if panel is None:
            return
        editor = panel.body
        editor.setPlainText(_BROKEN_YAML)
        # Scroll the mis-indented line into view so its red highlight is visible.
        line_no = _BROKEN_YAML.splitlines().index(_BROKEN_LINE)
        editor.setTextCursor(QTextCursor(editor.document().findBlockByNumber(line_no)))
        editor.centerCursor()

    def _open_library(self) -> None:
        """Reveal the library with Templates active — the first library step the tour uses."""
        app = self._app
        # Restore valid YAML in case the error from the previous step was left unfixed.
        from ..app import _IDX_YAML

        app._sync_all_editors()
        app._set_tab_status(_IDX_YAML, True, "YAML")
        app._act_sidebar.setChecked(True)
        app._templates_dock.raise_()

    def _prep_templates(self) -> None:
        """Empty the document and show Templates — the user loads the tour template themselves."""
        app = self._app
        app.parameters = {}
        app._text_multiview.set_document({})
        app._form_multiview.set_document({})
        app._view_tabs.setCurrentIndex(_FORM_TAB)
        app._templates_dock.show()
        app._templates_dock.raise_()

    def _ensure_example_loaded(self) -> None:
        """Reload the example if the document is empty.

        In a live tour the user has loaded the template (step 4.3) and applied the
        snippet (4.4) by now; when those interactive steps are skipped — notably the
        screenshot run — the document is still empty, which would leave the panel steps
        showing a blank editor. Loading the example keeps every panel step meaningful.
        """
        app = self._app
        if not app.parameters:
            app.parameters = parse_yaml(_EXAMPLE_YAML)
            app._text_multiview.set_document(app.parameters)
            app._form_multiview.set_document(app.parameters)

    def _show_snippets(self) -> None:
        self._ensure_example_loaded()
        app = self._app
        app._view_tabs.setCurrentIndex(_FORM_TAB)
        app._snippet_dock.show()
        app._snippet_dock.raise_()

    def _prep_panels(self) -> None:
        """Reset the Form to one content-filled panel — a clean start for a panel step.

        Loads the example if needed, switches to the Form tab, and collapses any split
        or zoom from a later step, so entering the zoom/split steps (forward or via
        Back) always starts from a single panel showing the whole document.
        """
        self._ensure_example_loaded()
        app = self._app
        app._view_tabs.setCurrentIndex(_FORM_TAB)
        app._form_multiview.set_layout(None)

    def _show_views(self) -> None:
        self._prep_panels()
        app = self._app
        app._views_dock.show()
        app._views_dock.raise_()

    def _reveal_dropzone(self) -> None:
        self._app._dropzone_dock.show()
        self._app._dropzone_dock.raise_()

    def _reveal_log(self) -> None:
        self._app._log_dock.show()

    # -- spotlight geometry (rects in main-window coordinates) -------------

    def _library_tab_bar_rect(self) -> QtCore.QRect | None:
        """Rect of the tabified library dock tab bar in main-window coordinates."""
        app = self._app
        for bar in app.findChildren(QtWidgets.QTabBar):
            if bar.count() >= 3 and bar.tabText(0) in ("Snippets", "Templates", "Views"):
                tl = bar.mapTo(app, QtCore.QPoint(0, 0))
                return QtCore.QRect(tl, bar.size())
        return None

    def _tab_rect_supplier(self, idx: int) -> Callable[[], QtCore.QRect | None]:
        """Return a callable that gives the view-tab header rect in main-window coordinates."""
        app = self._app

        def _rect() -> QtCore.QRect | None:
            tr = app._view_tabs.tabRect(idx)
            tl = app._view_tabs.mapTo(app, tr.topLeft())
            return QtCore.QRect(tl, tr.size())

        return _rect

    def _editor_stack_rect(self) -> QtCore.QRect | None:
        """Rect of the editor stack (below the view/live-file bar) in main-window coordinates."""
        app = self._app
        tl = app._stack.mapTo(app, QtCore.QPoint(0, 0))
        return QtCore.QRect(tl, app._stack.size())

    def _panel_body_rect(self, multiview: YamlMultiView) -> QtCore.QRect | None:
        """Rect of *multiview*'s active panel body only — excludes its header/path-filter bar."""
        app = self._app
        panel = multiview.active_view
        if panel is None:
            return None
        tl = panel.body.mapTo(app, QtCore.QPoint(0, 0))
        return QtCore.QRect(tl, panel.body.size())

    def _form_body_rect(self) -> QtCore.QRect | None:
        return self._panel_body_rect(self._app._form_multiview)

    def _yaml_body_rect(self) -> QtCore.QRect | None:
        return self._panel_body_rect(self._app._text_multiview)

    # -- step definitions --------------------------------------------------

    def _build_steps(self) -> list[TourStep]:
        """Steps pointing at the real toolbar/editor/library chrome."""
        app = self._app
        sidebar_btn = app._settings_toolbar.widgetForAction(app._act_sidebar)
        dropzone_btn = app._settings_toolbar.widgetForAction(app._dropzone_toggle)
        log_btn = app._settings_toolbar.widgetForAction(app._log_toggle)
        return [
            TourStep(
                "Welcome to Autotag Metadata",
                "This tool watches a folder and writes a <code>.metadata.yaml</code> sidecar next to "
                "every new file, using the metadata you prepare here. Let's walk through it.",
                slug="welcome",
            ),
            TourStep(
                "1. Choose a folder to watch",
                "Pick the folder to watch with <b>Browse…</b>, then press <b>Activate</b>. While "
                "active, every new file in it is tagged with your metadata.",
                [app.ledFolder, app.btnBrowse, app.btnActivate],
                slug="choose-folder",
            ),
            TourStep(
                "2.1 Filter which files",
                "Restrict tagging to matching files with comma-separated globs "
                "(e.g. <code>*.csv,*.tsv</code>), and tick <b>Recursive</b> to include sub-folders.",
                [app._patterns_label, app.ledFilePatterns, app.cbRecursiveWatch],
                slug="filter-files",
            ),
            TourStep(
                "2.2 Sidecar suffix",
                "The <b>Suffix</b> field controls the sidecar file name. Leave it empty for the "
                "default <code>.metadata.yaml</code>, or type a custom extension "
                "(e.g. <code>.ec-lab.metadata.yaml</code>) to distinguish sidecar families.",
                [app._suffix_label, app.ledMetaSuffix],
                slug="sidecar-suffix",
            ),
            TourStep(
                "2.6 Output format",
                "The <b>Format</b> combo picks the sidecar's serialization — <b>YAML</b> or "
                "<b>JSON</b> — independently of the suffix. YAML stays human-friendly; choose JSON "
                "when a downstream tool consumes the sidecar.",
                [app._format_label, app.cbMetaFormat],
                slug="output-format",
            ),
            TourStep(
                "3.1 Switch between views",
                "Edit metadata as a structured <b>Form</b>, as raw <b>YAML</b>, or as raw <b>JSON</b>. "
                "These tabs switch between them — all three edit the same document, so you can move "
                "freely between them.",
                [app._view_tabs],
                on_enter=self._show_form,
                slug="switch-views",
            ),
            TourStep(
                "3.2 The Form editor",
                "The Form shows your metadata as editable fields, grouped into collapsible "
                "sections that mirror the document structure.",
                [self._form_body_rect, self._tab_rect_supplier(_FORM_TAB)],
                on_enter=self._show_form,
                slug="form-editor",
            ),
            TourStep(
                "3.3 Prose fields",
                "A field holding more than one line of text — like <code>experimental.notes</code> "
                "here — is edited as <b>Markdown</b>, formatted as you type: start a line with "
                "<code>## </code> for a heading or <code>- </code> for a bullet, and use "
                "<b>Ctrl+B</b> / <b>Ctrl+I</b> or the small toolbar. Click <b>⤢</b> on the row to "
                "open it as a full-height editor, or <b>Source</b> to see the raw Markdown.",
                [self._form_body_rect, self._tab_rect_supplier(_FORM_TAB)],
                on_enter=self._show_prose,
                slug="prose-fields",
            ),
            TourStep(
                "3.4 The YAML editor",
                "The YAML tab is the same document as raw text, with syntax highlighting. Its tab "
                "blinks red when the YAML has a syntax error.",
                [self._yaml_body_rect, self._tab_rect_supplier(_YAML_TAB)],
                on_enter=self._show_yaml,
                slug="yaml-editor",
            ),
            TourStep(
                "3.5 Fixing a syntax error",
                "This document now has a mistake: a line under <code>system.electrodes</code> is "
                "indented one space too far. The tab blinks red and the exact line is highlighted — "
                "hover over the tab for the details. Fix the indentation so it lines up with its "
                "sibling keys, then press Next.",
                [self._yaml_body_rect, self._tab_rect_supplier(_YAML_TAB)],
                on_enter=self._show_broken_yaml,
                slug="fixing-syntax-error",
            ),
            TourStep(
                "3.6 The JSON editor",
                "The JSON tab mirrors the whole document as raw JSON — the same content, a different "
                "serialization. Edits sync back into the Form and YAML views, and its tab blinks red "
                "on a syntax error, just like YAML.",
                [app._json_edit, self._tab_rect_supplier(_JSON_TAB)],
                on_enter=self._show_json,
                slug="json-editor",
            ),
            TourStep(
                "4.1 Open the Library",
                "This <b>☰ Library</b> button shows or hides the library sidebar of reusable "
                "Snippets, Templates, and Views.",
                [sidebar_btn],
                on_enter=self._open_library,
                slug="open-library",
            ),
            TourStep(
                "4.2 The Library panel",
                "The Library holds <b>Snippets</b> (reusable sub-trees), <b>Templates</b> (whole "
                "documents), and <b>Views</b> (saved panel layouts). Save from here and "
                "double-click to apply.",
                [self._library_tab_bar_rect, app._snippet_dock, app._templates_dock, app._views_dock],
                slug="library-panel",
            ),
            TourStep(
                "4.3 Load a Template",
                "The document is now empty. Double-click <i>tour: EC-Lab experiment</i> in the "
                "Templates list to load it as the whole document — great for starting a fresh "
                "measurement from a known structure. Try it now, then press Next.",
                [self._library_tab_bar_rect, app._templates_dock, self._form_body_rect],
                on_enter=self._prep_templates,
                slug="load-template",
            ),
            TourStep(
                "4.4 Extend with a Snippet",
                "Snippets are reusable sub-trees anchored to their origin path. Switch to "
                "<b>Snippets</b> and double-click <i>tour: co-experimentalist</i> to add a second "
                "entry to <code>curation.process</code> without overwriting existing fields. "
                "Try it now, then press Next.",
                [self._library_tab_bar_rect, app._snippet_dock, self._form_body_rect],
                on_enter=self._show_snippets,
                slug="extend-snippet",
            ),
            TourStep(
                "4.5 Zoom into a subtree",
                "Every form row has a <b>⤢</b> button on the right — click it to narrow the panel "
                "to that subtree or value. The panel header shows the current path; the <b>↑</b> "
                "button steps back up. Try zooming into a section, then press Next.",
                [self._editor_stack_rect],
                on_enter=self._prep_panels,
                slug="zoom-subtree",
            ),
            TourStep(
                "4.6 Split into panels",
                "The Form is a tiling multi-view. Click <b>⊢</b> (split right) or <b>⊟</b> "
                "(split down) on the panel header to open a second panel, so you can edit two "
                "distant parts of the document side by side — each panel zooms independently. "
                "Add a panel now, then press Next.",
                [self._editor_stack_rect],
                on_enter=self._prep_panels,
                slug="split-panels",
            ),
            TourStep(
                "4.7 Save the layout as a View",
                "Views remember how the Form is tiled. Switch to <b>Views</b> and double-click "
                "<i>tour: three tiles</i> to restore a saved three-panel layout — zoomed onto "
                "<b>curation</b>, <b>experimental</b>, and <b>system</b> at once. "
                "Try it now, then press Next.",
                [self._library_tab_bar_rect, app._views_dock, self._editor_stack_rect],
                on_enter=self._show_views,
                slug="save-view",
            ),
            TourStep(
                "5. The live file",
                "The <b>Live file</b> is a YAML file kept in sync with the editor. Press "
                "<b>Select…</b> to choose one, <b>Use</b> to watch it — then edits in your "
                "external editor flow back into this document and vice versa — and <b>Open</b> "
                "to launch it in your default editor.",
                [
                    app.ledTemporaryLoc,
                    app.btnSelectTemporaryFile,
                    app.btnOpenTemporaryFile,
                    app.btnUseTemporaryFile,
                ],
                on_enter=self._show_form,
                slug="live-file",
            ),
            TourStep(
                "6. Drop files on demand",
                "The <b>Drop files</b> toggle opens a drop zone for tagging individual files "
                "without watching a folder. Drag files onto the zone and they are tagged with "
                "the current metadata. The <b>Log</b> panel shows what happened.",
                [dropzone_btn, app._dropzone_dock],
                on_enter=self._reveal_dropzone,
                slug="drop-files",
            ),
            TourStep(
                "7. The Log",
                "The <b>Log</b> toggle reveals the log panel at the bottom. Every tagging event, "
                "warning, and error is recorded here so you can see exactly what happened and "
                "which files were processed.",
                [log_btn, app._log_dock],
                on_enter=self._reveal_log,
                slug="log",
            ),
            TourStep(
                "You're ready",
                "That's the tour. Re-open it any time from <b>Help → Show Tour</b>. Happy tagging!",
                slug="ready",
            ),
        ]
