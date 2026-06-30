"""Lightweight, theme-aware YAML syntax highlighter for QPlainTextEdit.

Regex-based (no third-party dependency). Colours are chosen from the active
palette's lightness so the highlighting reads on both light and dark themes,
matching the app's "follow the OS theme" styling.
"""
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

from PyQt6 import QtCore, QtGui

# Foreground palettes (One-Dark-ish) for light and dark backgrounds.
_LIGHT = {
    "key": "#1a5fb4",
    "string": "#2e7d32",
    "number": "#aa5d00",
    "constant": "#8e44ad",
    "comment": "#6a737d",
    "marker": "#c0392b",
}
_DARK = {
    "key": "#56b6c2",
    "string": "#98c379",
    "number": "#d19a66",
    "constant": "#c678dd",
    "comment": "#7f848e",
    "marker": "#e06c75",
}


def _format(color: str, *, italic: bool = False, bold: bool = False) -> QtGui.QTextCharFormat:
    fmt = QtGui.QTextCharFormat()
    fmt.setForeground(QtGui.QColor(color))
    if italic:
        fmt.setFontItalic(True)
    if bold:
        fmt.setFontWeight(QtGui.QFont.Weight.Bold)
    return fmt


class YamlHighlighter(QtGui.QSyntaxHighlighter):
    """Highlights YAML keys, strings, numbers, constants, anchors and comments."""

    def __init__(self, document: QtGui.QTextDocument, palette: QtGui.QPalette | None = None):
        super().__init__(document)
        self._rules: list[tuple[QtCore.QRegularExpression, int, QtGui.QTextCharFormat]] = []
        self.set_palette(palette or QtGui.QGuiApplication.palette())

    def set_palette(self, palette: QtGui.QPalette) -> None:
        """Rebuild the colour rules for the given palette and re-highlight."""
        dark = palette.color(QtGui.QPalette.ColorRole.Base).lightness() < 128
        colors = _DARK if dark else _LIGHT

        key = _format(colors["key"], bold=True)
        string = _format(colors["string"])
        number = _format(colors["number"])
        constant = _format(colors["constant"])
        comment = _format(colors["comment"], italic=True)
        marker = _format(colors["marker"], bold=True)

        regex = QtCore.QRegularExpression
        ignore_case = QtCore.QRegularExpression.PatternOption.CaseInsensitiveOption

        # (pattern, captured-group to format, format). Comments come last so a
        # trailing "# ..." wins over anything matched earlier on the line.
        self._rules = [
            (regex(r'^\s*(?:-\s+)?("(?:[^"\\]|\\.)*"|\'[^\']*\'|[^\s:#][^:#]*?)\s*:(?:\s|$)'), 1, key),
            (regex(r"^\s*(-)\s"), 1, marker),
            (regex(r'"(?:[^"\\]|\\.)*"'), 0, string),
            (regex(r"'[^']*'"), 0, string),
            (regex(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?(?![\w.])"), 0, number),
            (regex(r"\b(?:true|false|yes|no|on|off|null|none|~)\b", ignore_case), 0, constant),
            (regex(r"[&*][^\s,\]}]+"), 0, marker),
            (regex(r"!{1,2}[^\s]+"), 0, marker),
            (regex(r"^(?:---|\.\.\.)\s*$"), 0, marker),
            (regex(r"(?:^|\s)(#.*)$"), 1, comment),
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
                    self.setFormat(start, length, fmt)
