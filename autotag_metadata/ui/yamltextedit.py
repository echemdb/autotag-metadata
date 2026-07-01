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

import re  # noqa: I001

from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFontDatabase,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPalette,
    QTextCharFormat,
    QTextCursor,
)
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from autotag_metadata.core.yaml_utils import yaml_ancestor_path, yaml_path_at_line
from .snippetslist import SNIPPET_MIME
from .yaml_highlighter import YamlHighlighter

_KEY_RE = re.compile(r"""^\s*([^:#\[\]{}&*!|>'"%@`]+):\s*""")


class _ZoomGutter(QWidget):
    """Right-side gutter: renders a clickable ⤢ on each YAML mapping-key line."""

    WIDTH = 18
    _GLYPH = "⤢"

    zoom_clicked = pyqtSignal(int)  # block number

    def __init__(self, editor: "YamlTextEdit") -> None:
        super().__init__(editor)
        self._editor = editor
        self._hovered_block = -1
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setToolTip("Click to filter to this key")

    def sizeHint(self) -> QSize:
        return QSize(self.WIDTH, 0)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        pal = self._editor.palette()
        highlight = pal.color(QPalette.ColorRole.Highlight)
        painter.fillRect(self.rect(), pal.color(QPalette.ColorRole.AlternateBase))
        painter.setFont(self._editor.font())
        block = self._editor.firstVisibleBlock()
        offset = self._editor.contentOffset()
        while block.isValid():
            geom = self._editor.blockBoundingGeometry(block).translated(offset)
            top = int(geom.top())
            if top > self.rect().bottom():
                break
            if block.isVisible() and geom.bottom() >= self.rect().top():
                if _KEY_RE.match(block.text()):
                    row = QRect(0, top, self.WIDTH, int(geom.height()))
                    if block.blockNumber() == self._hovered_block:
                        hl = QColor(highlight)
                        hl.setAlpha(55)
                        painter.fillRect(row, hl)
                        painter.setPen(highlight)
                    else:
                        painter.setPen(pal.color(QPalette.ColorRole.PlaceholderText))
                    painter.drawText(row, Qt.AlignmentFlag.AlignCenter, self._GLYPH)
            block = block.next()
        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        y = event.position().y()
        hovered = -1
        block = self._editor.firstVisibleBlock()
        offset = self._editor.contentOffset()
        while block.isValid():
            geom = self._editor.blockBoundingGeometry(block).translated(offset)
            if geom.top() <= y <= geom.bottom():
                if _KEY_RE.match(block.text()):
                    hovered = block.blockNumber()
                break
            if geom.top() > y:
                break
            block = block.next()
        if hovered != self._hovered_block:
            self._hovered_block = hovered
            self.update()
            self._editor.set_hover_highlight(hovered if hovered >= 0 else None)

    def leaveEvent(self, _event) -> None:
        if self._hovered_block != -1:
            self._hovered_block = -1
            self.update()
            self._editor.set_hover_highlight(None)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        y = event.position().y()
        block = self._editor.firstVisibleBlock()
        offset = self._editor.contentOffset()
        while block.isValid():
            geom = self._editor.blockBoundingGeometry(block).translated(offset)
            if geom.top() <= y <= geom.bottom():
                if _KEY_RE.match(block.text()):
                    self.zoom_clicked.emit(block.blockNumber())
                return
            if geom.top() > y:
                break
            block = block.next()


class YamlTextEdit(QPlainTextEdit):
    """Plain-text YAML editor: snippet drops, monospace font, syntax highlighting."""

    #: Emitted with (selected YAML text, dotted ancestor path) to save as a snippet.
    make_snippet_requested = pyqtSignal(str, str)
    #: Emitted with the clicked key's relative dotted path when a gutter ⤢ is
    #: clicked; only when show_zoom_gutter=True. Mirrors YamlFormView.zoom_requested.
    zoom_requested = pyqtSignal(str)

    _INDENT_N = 2  # YAML indentation unit (spaces); tabs are not allowed
    _INDENT = " " * _INDENT_N

    def __init__(self, *args, show_zoom_gutter: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._zoom_gutter: _ZoomGutter | None = None
        self.setAcceptDrops(True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.setTabStopDistance(self._INDENT_N * self.fontMetrics().horizontalAdvance(" "))
        # Theme (light/dark) is taken from the palette at construction. A live
        # re-theme hook is intentionally avoided: _validate_yaml() restyles this
        # widget on every keystroke, which would re-enter the highlighter.
        self._highlighter = YamlHighlighter(self.document(), self.palette())
        if show_zoom_gutter:
            self._zoom_gutter = _ZoomGutter(self)
            self._zoom_gutter.zoom_clicked.connect(self._emit_zoom_for_block)
            self.setViewportMargins(0, 0, _ZoomGutter.WIDTH, 0)
            self.updateRequest.connect(self._update_zoom_gutter)

    def _emit_zoom_for_block(self, block_no: int) -> None:
        """Translate a clicked gutter line into the same relative path the form emits."""
        rel_path = yaml_path_at_line(self.toPlainText(), block_no)
        if rel_path:
            self.zoom_requested.emit(rel_path)

    def set_hover_highlight(self, block_no: int | None) -> None:
        """Highlight the full line at *block_no* via an extra selection, or clear."""
        selections = []
        if block_no is not None:
            block = self.document().findBlockByNumber(block_no)
            if block.isValid():
                fmt = QTextCharFormat()
                color = self.palette().color(QPalette.ColorRole.Highlight)
                color.setAlpha(55)
                fmt.setBackground(color)
                sel = QTextEdit.ExtraSelection()
                sel.format = fmt
                sel.cursor = QTextCursor(block)
                sel.cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
                selections.append(sel)
        self.setExtraSelections(selections)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._zoom_gutter is not None:
            vp = self.viewport()
            self._zoom_gutter.setGeometry(vp.x() + vp.width(), vp.y(), _ZoomGutter.WIDTH, vp.height())

    def _update_zoom_gutter(self, rect: QRect, dy: int) -> None:
        if self._zoom_gutter is None:
            return
        if dy:
            self._zoom_gutter.scroll(0, dy)
        else:
            self._zoom_gutter.update(0, rect.y(), _ZoomGutter.WIDTH, rect.height())

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
