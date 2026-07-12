"""Lightweight, theme-aware Markdown syntax highlighter for the Source mode.

Regex-based (no third-party dependency), and colour-picked from the active
palette's lightness like :mod:`autotag_metadata.ui.yaml_highlighter`, so the
highlighting reads on both light and dark themes.
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

from PyQt6 import QtCore, QtGui

# Same two foreground palettes as the YAML highlighter, so the two source
# editors in the app look like siblings.
_LIGHT = {
    "heading": "#1a5fb4",
    "code": "#2e7d32",
    "link": "#8e44ad",
    "marker": "#c0392b",
    "quote": "#6a737d",
}
_DARK = {
    "heading": "#56b6c2",
    "code": "#98c379",
    "link": "#c678dd",
    "marker": "#e06c75",
    "quote": "#7f848e",
}


def _format(
    color: str | None = None, *, italic: bool = False, bold: bool = False, mono: bool = False
) -> QtGui.QTextCharFormat:
    fmt = QtGui.QTextCharFormat()
    if color is not None:
        fmt.setForeground(QtGui.QColor(color))
    if italic:
        fmt.setFontItalic(True)
    if bold:
        fmt.setFontWeight(QtGui.QFont.Weight.Bold)
    if mono:
        fmt.setFontFamilies([QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont).family()])
    return fmt


class MarkdownHighlighter(QtGui.QSyntaxHighlighter):
    """Highlights headings, emphasis, code, links, list markers and quotes."""

    def __init__(self, document: QtGui.QTextDocument, palette: QtGui.QPalette | None = None) -> None:
        super().__init__(document)
        self._rules: list[tuple[QtCore.QRegularExpression, int, QtGui.QTextCharFormat]] = []
        self.set_palette(palette or QtGui.QGuiApplication.palette())

    def set_palette(self, palette: QtGui.QPalette) -> None:
        """Rebuild the colour rules for the given palette and re-highlight."""
        dark = palette.color(QtGui.QPalette.ColorRole.Base).lightness() < 128
        colors = _DARK if dark else _LIGHT

        regex = QtCore.QRegularExpression
        # (pattern, captured group to format, format)
        self._rules = [
            (regex(r"^\s{0,3}#{1,6}\s.*$"), 0, _format(colors["heading"], bold=True)),
            (regex(r"^\s{0,3}(?:[-*+]|\d+[.)])\s"), 0, _format(colors["marker"], bold=True)),
            (regex(r"^\s{0,3}>\s?.*$"), 0, _format(colors["quote"], italic=True)),
            (regex(r"^\s{0,3}(?:```|~~~).*$"), 0, _format(colors["marker"])),
            (regex(r"(\*\*|__)(?=\S)(.+?[*_]*)(?<=\S)\1"), 0, _format(bold=True)),
            (regex(r"(?<![*\w])(\*|_)(?=\S)(.+?)(?<=\S)\1(?![*\w])"), 0, _format(italic=True)),
            (regex(r"`[^`\n]+`"), 0, _format(colors["code"], mono=True)),
            (regex(r"!?\[[^\]\n]*\]\([^)\n]*\)"), 0, _format(colors["link"])),
            (regex(r"^\s{0,3}(?:---+|\*\*\*+|___+)\s*$"), 0, _format(colors["marker"], bold=True)),
        ]
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        for regex, group, fmt in self._rules:
            iterator = regex.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                start = match.capturedStart(group)
                length = match.capturedLength(group)
                if start >= 0 and length > 0:
                    # merge, not replace: emphasis inside a heading keeps the heading colour
                    self.setFormat(start, length, self._merged(start, fmt))

    def _merged(self, position: int, fmt: QtGui.QTextCharFormat) -> QtGui.QTextCharFormat:
        merged = QtGui.QTextCharFormat(self.format(position))
        merged.merge(fmt)
        return merged
