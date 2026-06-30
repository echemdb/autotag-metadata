"""Custom QPlainTextEdit with drag-and-drop support for YAML snippets."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2024-2026 Johannes Hermann
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

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFontDatabase, QPainter, QPalette, QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit

from autotag_metadata.core.yaml_utils import yaml_ancestor_path

from .snippetslist import SNIPPET_MIME
from .yaml_highlighter import YamlHighlighter


class YamlTextEdit(QPlainTextEdit):
    """Plain-text YAML editor: snippet drops, monospace font, syntax highlighting."""

    #: Emitted with (selected YAML text, dotted ancestor path) to save as a snippet.
    make_snippet_requested = pyqtSignal(str, str)

    _INDENT_N = 2  # YAML indentation unit (spaces); tabs are not allowed
    _INDENT = " " * _INDENT_N

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.setTabStopDistance(self._INDENT_N * self.fontMetrics().horizontalAdvance(" "))
        # Theme (light/dark) is taken from the palette at construction. A live
        # re-theme hook is intentionally avoided: _validate_yaml() restyles this
        # widget on every keystroke, which would re-enter the highlighter.
        self._highlighter = YamlHighlighter(self.document(), self.palette())

    # -- indentation: guide lines + tab/enter behaviour --------------------

    def paintEvent(self, event):
        """Draw the text, then faint vertical guides at each indent level."""
        super().paintEvent(event)
        space_w = self.fontMetrics().horizontalAdvance(" ")
        if space_w <= 0:
            return
        color = self.palette().color(QPalette.ColorRole.Text)
        color.setAlpha(45)
        painter = QPainter(self.viewport())
        painter.setPen(QColor(color))
        x_origin = self.contentOffset().x() + self.document().documentMargin()
        block = self.firstVisibleBlock()
        while block.isValid():
            geometry = self.blockBoundingGeometry(block).translated(self.contentOffset())
            if geometry.top() > event.rect().bottom():
                break
            if block.isVisible() and geometry.bottom() >= event.rect().top():
                text = block.text()
                leading = len(text) - len(text.lstrip(" "))
                level = self._INDENT_N
                while level <= leading:
                    x = round(x_origin + level * space_w)
                    painter.drawLine(x, round(geometry.top()), x, round(geometry.bottom()) - 1)
                    level += self._INDENT_N
            block = block.next()
        painter.end()

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        key = event.key()
        if key == Qt.Key.Key_Backtab:
            self._shift_lines(-1)
            return
        if key == Qt.Key.Key_Tab:
            if cursor.hasSelection() and self._spans_multiple_lines(cursor):
                self._shift_lines(+1)
            else:
                cursor.insertText(self._INDENT)
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            line = cursor.block().text()
            indent = line[: len(line) - len(line.lstrip(" "))]
            cursor.insertText("\n" + indent)
            self.setTextCursor(cursor)
            return
        super().keyPressEvent(event)

    @staticmethod
    def _spans_multiple_lines(cursor) -> bool:
        doc = cursor.document()
        return (
            doc.findBlock(cursor.selectionStart()).blockNumber()
            != doc.findBlock(cursor.selectionEnd()).blockNumber()
        )

    def _shift_lines(self, direction: int) -> None:
        """Indent (+1) or dedent (-1) every line touched by the selection."""
        cursor = self.textCursor()
        doc = cursor.document()
        first = doc.findBlock(cursor.selectionStart()).blockNumber()
        last = doc.findBlock(cursor.selectionEnd()).blockNumber()
        cursor.beginEditBlock()
        edit = self.textCursor()
        block = doc.findBlockByNumber(first)
        for _ in range(first, last + 1):
            edit.setPosition(block.position())
            edit.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            if direction > 0:
                edit.insertText(self._INDENT)
            else:
                stripped = len(block.text()) - len(block.text().lstrip(" "))
                for _i in range(min(self._INDENT_N, stripped)):
                    edit.deleteChar()
            block = block.next()
            if not block.isValid():
                break
        cursor.endEditBlock()

    # ----------------------------------------------------------------------

    def contextMenuEvent(self, event):
        """Add a 'Save selection as snippet' entry to the standard menu."""
        menu = self.createStandardContextMenu()
        if self.textCursor().hasSelection():
            menu.addSeparator()
            action = menu.addAction("Save selection as snippet…")
            action.triggered.connect(self._emit_make_snippet)
        menu.exec(event.globalPos())

    def _emit_make_snippet(self) -> None:
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return
        start_line, end_line = self._selected_line_range(cursor)
        full = self.toPlainText()
        # Use the full lines the selection spans (not the raw selectedText, which
        # may start/end mid-line), so selecting only part of a sub-level still
        # dedents to a valid YAML mapping.
        text = "\n".join(full.split("\n")[start_line : end_line + 1])
        if not text.strip():
            return
        path = yaml_ancestor_path(full, start_line, end_line)
        self.make_snippet_requested.emit(text, path)

    def _selected_line_range(self, cursor) -> tuple[int, int]:
        """Return the (start, end) line numbers the selection spans.

        A selection ending at the very start of a line (trailing newline
        included) does not count that following line.
        """
        doc = self.document()
        start_line = doc.findBlock(cursor.selectionStart()).blockNumber()
        end_block = doc.findBlock(cursor.selectionEnd())
        end_line = end_block.blockNumber()
        if end_line > start_line and cursor.selectionEnd() == end_block.position():
            end_line -= 1
        return start_line, end_line

    def _snippet_text(self, mime) -> str | None:
        if mime.hasFormat(SNIPPET_MIME):
            return bytes(mime.data(SNIPPET_MIME)).decode("utf-8")
        return None

    def dragEnterEvent(self, event):
        if self._snippet_text(event.mimeData()) is not None:
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._snippet_text(event.mimeData()) is not None:
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        snippet = self._snippet_text(event.mimeData())
        if snippet is not None:
            cursor = self.cursorForPosition(event.position().toPoint())
            cursor.insertText(snippet if snippet.endswith("\n") else snippet + "\n")
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
