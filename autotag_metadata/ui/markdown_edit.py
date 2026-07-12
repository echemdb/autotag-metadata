"""WYSIWYG markdown editor for prose-valued metadata fields."""
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

import re

from PyQt6 import QtCore, QtGui, QtWidgets

from autotag_metadata.core.markdown_text import normalize_markdown
from autotag_metadata.ui.markdown_highlighter import MarkdownHighlighter

#: Heights (px) of the editor body when embedded as one row of a form.
_COMPACT_MIN_HEIGHT = 96
_COMPACT_MAX_HEIGHT = 260

_LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])(\s+)")

#: Block markers that turn into real formatting when the following space is typed.
#: Without this, typing "## Title" in the rich editor leaves literal text that Qt's
#: writer then escapes to "\## Title" — a heading in neither the editor nor the file.
_AUTOFORMAT_RE = re.compile(r"^(#{1,6}|[-*+]|\d+[.)]|>)$")


class _Body(QtWidgets.QTextEdit):
    """The text area. Rich text in Rich mode, plain markdown in Source mode.

    A single QTextEdit backs both modes — Qt's own ``setMarkdown``/``toMarkdown``
    are the parser and writer, so the rendered document *is* the editing surface
    (no separate preview widget, no HTML layer, no extra dependency).
    """

    focus_lost = QtCore.pyqtSignal()

    def __init__(self, owner: "MarkdownEdit") -> None:
        super().__init__(owner)
        self._owner = owner

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusOutEvent(event)
        self.focus_lost.emit()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        ctrl = event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        if ctrl and event.key() == QtCore.Qt.Key.Key_B:
            self._owner.toggle_bold()
            return
        if ctrl and event.key() == QtCore.Qt.Key.Key_I:
            self._owner.toggle_italic()
            return
        if ctrl and event.key() == QtCore.Qt.Key.Key_K:
            self._owner.insert_link()
            return
        if event.key() == QtCore.Qt.Key.Key_Space and self._autoformat_block():
            return
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            if self._owner.is_source_mode():
                if self._continue_list():
                    return
            elif self._end_heading():
                return
        super().keyPressEvent(event)

    def _autoformat_block(self) -> bool:
        """Turn a just-typed block marker into real formatting (Rich mode).

        ``## `` becomes a heading, ``- `` / ``1. `` a list, ``> `` a quote — the
        marker text is consumed, so the document carries the *structure* and Qt's
        writer emits the markdown for it.
        """
        if self._owner.is_source_mode():
            return False
        cursor = self.textCursor()
        if cursor.hasSelection() or cursor.block().blockFormat().headingLevel():
            return False
        prefix = cursor.block().text()[: cursor.positionInBlock()]
        match = _AUTOFORMAT_RE.match(prefix.strip())
        if match is None:
            return False
        marker = match.group(1)

        cursor.beginEditBlock()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        self.setTextCursor(cursor)
        if marker.startswith("#"):
            self._owner.set_heading(len(marker))
        elif marker == ">":
            self._owner.set_quote()
        else:
            self._owner.insert_list(ordered=marker[:-1].isdigit())
        cursor.endEditBlock()
        return True

    def _end_heading(self) -> bool:
        """Return at the end of a heading starts a *body* paragraph, not another heading."""
        cursor = self.textCursor()
        if not cursor.block().blockFormat().headingLevel():
            return False
        if cursor.positionInBlock() != len(cursor.block().text()):
            return False
        cursor.insertBlock()
        self.setTextCursor(cursor)
        self._owner.set_heading(0)
        return True

    def _continue_list(self) -> bool:
        """Carry a ``- `` / ``1. `` marker onto the next line (Source mode only)."""
        cursor = self.textCursor()
        match = _LIST_ITEM_RE.match(cursor.block().text())
        if match is None:
            return False
        indent, marker, spacing = match.groups()
        if marker[:-1].isdigit():
            marker = f"{int(marker[:-1]) + 1}{marker[-1]}"
        cursor.insertText(f"\n{indent}{marker}{spacing}")
        self.setTextCursor(cursor)
        return True


class MarkdownEdit(QtWidgets.QWidget):
    """Edit a markdown string as formatted text, with a raw-source fallback.

    Rich mode is a live rendering of the markdown: **bold** is bold, lists are
    lists, and the formatting buttons act on the document. Source mode shows the
    markdown text itself, syntax-highlighted. Both modes read and write the same
    string, emitted via *text_committed* when the editor loses focus.

    The text is only ever rewritten when the user actually edited it: merely
    looking at (or scrolling through) a field never round-trips it through Qt's
    markdown writer, so untouched values keep their original formatting
    byte-for-byte.

    Usage::

        editor = MarkdownEdit("## Prep\\nRinsed in **DI water**.\\n")
        editor.text_committed.connect(on_commit)
    """

    #: Emitted with the new markdown text when an edit is committed (focus-out).
    text_committed = QtCore.pyqtSignal(str)

    def __init__(self, text: str = "", compact: bool = True, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self._dirty = False
        self._loading = False
        self._source_mode = False
        self._compact = compact

        self._body = _Body(self)
        self._body.setAcceptRichText(True)
        self._body.setTabChangesFocus(True)
        self._body.textChanged.connect(self._on_text_changed)
        self._body.focus_lost.connect(self._on_body_focus_lost)
        self._highlighter: MarkdownHighlighter | None = None

        self._toolbar = self._build_toolbar()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._body, 1)

        if compact:
            self._body.setMinimumHeight(_COMPACT_MIN_HEIGHT)
            self._body.setMaximumHeight(_COMPACT_MAX_HEIGHT)
            self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        else:
            self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Expanding)

        self._load(text)

    # -- public API --------------------------------------------------------

    def markdown(self) -> str:
        """The current markdown text.

        Returns the text exactly as loaded unless the user edited it — Qt's
        markdown writer normalizes whitespace and table padding, and an
        unmodified field must not be rewritten just because it was displayed.
        """
        if self._source_mode:
            return self._body.toPlainText()
        if not self._dirty:
            return self._text
        return self._body.toMarkdown()

    def set_markdown(self, text: str) -> None:
        """Replace the content with *text* (no commit signal)."""
        if normalize_markdown(text) == normalize_markdown(self.markdown()):
            return
        self._load(text)

    def commit(self) -> None:
        """Emit *text_committed* if the user actually changed the text.

        Both sides are compared normalized: a value loaded from a YAML ``|`` block
        carries a trailing newline that normalization drops, and focusing a field
        without touching it must not rewrite the document over that difference.
        """
        text = normalize_markdown(self.markdown())
        if text == normalize_markdown(self._text):
            return
        self._text = text
        self._dirty = False
        self.text_committed.emit(text)

    def is_source_mode(self) -> bool:
        return self._source_mode

    # -- mode --------------------------------------------------------------

    def _set_source_mode(self, enabled: bool) -> None:
        if enabled == self._source_mode:
            return
        text = self.markdown()  # capture in the outgoing mode's representation
        self._source_mode = enabled
        self._source_btn.setChecked(enabled)
        for button in self._format_buttons:
            button.setToolTip(button.property("tip_source") if enabled else button.property("tip_rich"))
        self._loading = True
        if enabled:
            self._body.setAcceptRichText(False)
            self._body.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont))
            self._body.setPlainText(text)
            self._highlighter = MarkdownHighlighter(self._body.document(), self.palette())
        else:
            if self._highlighter is not None:
                self._highlighter.setDocument(None)
                self._highlighter = None
            self._body.setAcceptRichText(True)
            self._body.setFont(QtGui.QGuiApplication.font())
            self._body.setMarkdown(text)
        self._loading = False

    def _load(self, text: str) -> None:
        self._loading = True
        self._text = text
        self._dirty = False
        if self._source_mode:
            self._body.setPlainText(text)
        else:
            self._body.setMarkdown(text)
        self._loading = False

    def _on_text_changed(self) -> None:
        if not self._loading:
            self._dirty = True

    # -- formatting actions ------------------------------------------------

    def toggle_bold(self) -> None:
        self._apply("**", QtGui.QFont.Weight.Bold)

    def toggle_italic(self) -> None:
        self._apply("*", italic=True)

    def toggle_code(self) -> None:
        self._apply("`", mono=True)

    def _apply(
        self,
        marker: str,
        weight: QtGui.QFont.Weight | None = None,
        italic: bool = False,
        mono: bool = False,
    ) -> None:
        """Toggle an inline style: a char format in Rich mode, markers in Source mode."""
        if self._source_mode:
            self._wrap_selection(marker)
            return
        cursor = self._body.textCursor()
        current = cursor.charFormat()
        fmt = QtGui.QTextCharFormat()
        if weight is not None:
            on = current.fontWeight() >= QtGui.QFont.Weight.Bold
            fmt.setFontWeight(QtGui.QFont.Weight.Normal if on else weight)
        if italic:
            fmt.setFontItalic(not current.fontItalic())
        if mono:
            # Qt's markdown writer emits `backticks` for a fixed-pitch run, so the
            # family alone is not enough — fontFixedPitch is what it inspects.
            on = current.fontFixedPitch()
            fmt.setFontFixedPitch(not on)
            mono_family = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont).family()
            fmt.setFontFamilies([QtGui.QGuiApplication.font().family() if on else mono_family])
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        else:
            self._body.mergeCurrentCharFormat(fmt)
        self._body.setFocus()

    def _wrap_selection(self, marker: str) -> None:
        cursor = self._body.textCursor()
        selected = cursor.selectedText() or "text"
        cursor.insertText(f"{marker}{selected}{marker}")
        self._body.setFocus()

    def set_heading(self, level: int) -> None:
        """Make the current block a heading of *level* (0 = plain paragraph)."""
        if self._source_mode:
            self._set_source_line_prefix("#" * level + " " if level else "")
            return
        block_fmt = self._body.textCursor().blockFormat()
        block_fmt.setHeadingLevel(level)
        # Qt sizes a heading from the char format, matching what setMarkdown() builds
        # for the same level (h1 largest, h6 body-sized).
        char_fmt = QtGui.QTextCharFormat()
        char_fmt.setFontWeight(QtGui.QFont.Weight.Bold if level else QtGui.QFont.Weight.Normal)
        char_fmt.setProperty(QtGui.QTextFormat.Property.FontSizeAdjustment, (4 - level) if level else 0)
        self._format_block(block_fmt, char_fmt)

    def set_quote(self, level: int = 1) -> None:
        """Make the current block a block quote (0 = plain paragraph)."""
        if self._source_mode:
            self._set_source_line_prefix("> " if level else "")
            return
        block_fmt = self._body.textCursor().blockFormat()
        block_fmt.setProperty(QtGui.QTextFormat.Property.BlockQuoteLevel, level)
        block_fmt.setIndent(level)
        self._format_block(block_fmt, QtGui.QTextCharFormat())

    def _format_block(self, block_fmt: QtGui.QTextBlockFormat, char_fmt: QtGui.QTextCharFormat) -> None:
        """Apply *block_fmt*/*char_fmt* to the whole current block, keeping the caret put."""
        block = self._body.textCursor().block()
        edit = QtGui.QTextCursor(block)
        edit.setPosition(block.position())
        edit.setPosition(block.position() + len(block.text()), QtGui.QTextCursor.MoveMode.KeepAnchor)
        edit.setBlockFormat(block_fmt)
        edit.mergeCharFormat(char_fmt)
        # An empty block has nothing to merge into, so the style must also go on the
        # *current* format — otherwise text typed right after "## " comes out as body.
        self._body.mergeCurrentCharFormat(char_fmt)
        self._body.setFocus()

    def insert_link(self) -> None:
        cursor = self._body.textCursor()
        text = cursor.selectedText() or "link"
        url, ok = QtWidgets.QInputDialog.getText(self, "Insert Link", "URL:", text="https://")
        if not ok or not url:
            return
        if self._source_mode:
            cursor.insertText(f"[{text}]({url})")
        else:
            fmt = QtGui.QTextCharFormat()
            fmt.setAnchor(True)
            fmt.setAnchorHref(url)
            fmt.setForeground(self.palette().color(QtGui.QPalette.ColorRole.Link))
            fmt.setFontUnderline(True)
            cursor.insertText(text, fmt)
        self._body.setFocus()

    def insert_list(self, ordered: bool) -> None:
        if self._source_mode:
            self._set_source_line_prefix("1. " if ordered else "- ")
            return
        style = QtGui.QTextListFormat.Style.ListDecimal if ordered else QtGui.QTextListFormat.Style.ListDisc
        cursor = self._body.textCursor()
        list_fmt = QtGui.QTextListFormat()
        list_fmt.setStyle(style)
        cursor.createList(list_fmt)
        self._body.setFocus()

    def _set_source_line_prefix(self, prefix: str) -> None:
        """Replace any heading/list marker on the current Source-mode line with *prefix*."""
        cursor = self._body.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock, QtGui.QTextCursor.MoveMode.KeepAnchor)
        line = cursor.selectedText()
        stripped = re.sub(r"^\s{0,3}(?:#{1,6}\s+|(?:[-*+]|\d+[.)])\s+)", "", line)
        cursor.insertText(prefix + stripped)
        self._body.setFocus()

    # -- chrome ------------------------------------------------------------

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        # One plain field row tall, so the toolbar lines up with the row's key label
        # instead of making the prose row visibly taller than its neighbours.
        self._row_height = QtWidgets.QLineEdit().sizeHint().height()
        bar.setFixedHeight(self._row_height)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        self._format_buttons: list[QtWidgets.QToolButton] = []
        specs = [
            ("B", "Bold (Ctrl+B)", "Wrap selection in ** (Ctrl+B)", self.toggle_bold, True),
            ("I", "Italic (Ctrl+I)", "Wrap selection in * (Ctrl+I)", self.toggle_italic, False),
            ("<>", "Inline code", "Wrap selection in backticks", self.toggle_code, False),
            # Spelled out, not a chain emoji: the emoji has no glyph in the default
            # UI font on several platforms and renders as a tofu box.
            ("Link", "Insert link (Ctrl+K)", "Insert a [text](url) link (Ctrl+K)", self.insert_link, False),
            ("•", "Bullet list", "Start a - list item", lambda: self.insert_list(False), False),
            ("1.", "Numbered list", "Start a 1. list item", lambda: self.insert_list(True), False),
        ]
        for label, tip_rich, tip_source, slot, bold in specs:
            button = self._tool_button(label, tip_rich, slot)
            button.setProperty("tip_rich", tip_rich)
            button.setProperty("tip_source", tip_source)
            if bold:
                font = button.font()
                font.setBold(True)
                button.setFont(font)
            self._format_buttons.append(button)
            layout.addWidget(button)

        heading = self._tool_button("H", "Heading level", None)
        menu = QtWidgets.QMenu(heading)
        for level in (1, 2, 3):
            menu.addAction(f"Heading {level}", lambda _=False, n=level: self.set_heading(n))
        menu.addAction("Body text", lambda: self.set_heading(0))
        heading.setMenu(menu)
        heading.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self._format_buttons.append(heading)
        heading.setProperty("tip_rich", "Heading level")
        heading.setProperty("tip_source", "Heading level")
        layout.addWidget(heading)

        layout.addStretch()

        self._source_btn = self._tool_button("Source", "Edit the raw markdown text", None)
        self._source_btn.setCheckable(True)
        self._source_btn.setFixedWidth(52)
        self._source_btn.toggled.connect(self._set_source_mode)
        layout.addWidget(self._source_btn)
        return bar

    def _tool_button(self, label: str, tooltip: str, slot) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton()
        button.setText(label)
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        button.setFixedHeight(self._row_height)
        # Never take focus: clicking a button must not focus-out the body (which
        # would commit the edit, and in compact mode hide the toolbar mid-click).
        button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        if slot is not None:
            button.clicked.connect(slot)
        return button

    # -- compact-mode toolbar reveal ---------------------------------------

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusInEvent(event)
        self._body.setFocus()

    def _on_body_focus_lost(self) -> None:
        self.commit()
