"""Semi-transparent edge overlay drawn over a drop target panel."""
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

from PyQt6 import QtCore, QtGui, QtWidgets

EDGE_ZONE = 0.25  # fraction of panel width/height that counts as an edge


def _overlay_colors(palette: QtGui.QPalette) -> tuple[QtGui.QColor, QtGui.QColor]:
    """Fill/border highlight colours drawn from the active palette."""
    accent = palette.color(QtGui.QPalette.ColorRole.Highlight)
    fill = QtGui.QColor(accent)
    fill.setAlpha(100)
    border = QtGui.QColor(accent)
    border.setAlpha(220)
    return fill, border


class DropEdge:
    NONE = "none"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"


def edge_for_pos(widget: QtWidgets.QWidget, pos: QtCore.QPoint) -> str:
    """Return which edge zone *pos* (in widget-local coords) falls in."""
    w, h = widget.width(), widget.height()
    x, y = pos.x(), pos.y()
    zone_x = int(w * EDGE_ZONE)
    zone_y = int(h * EDGE_ZONE)

    if x < zone_x:
        return DropEdge.LEFT
    if x > w - zone_x:
        return DropEdge.RIGHT
    if y < zone_y:
        return DropEdge.TOP
    if y > h - zone_y:
        return DropEdge.BOTTOM
    return DropEdge.CENTER


def highlight_rect(widget: QtWidgets.QWidget, edge: str) -> QtCore.QRect:
    """Return the rect to highlight for *edge* on *widget*."""
    r = widget.rect()
    half_w = r.width() // 2
    half_h = r.height() // 2
    if edge == DropEdge.LEFT:
        return QtCore.QRect(r.x(), r.y(), half_w, r.height())
    if edge == DropEdge.RIGHT:
        return QtCore.QRect(r.x() + half_w, r.y(), half_w, r.height())
    if edge == DropEdge.TOP:
        return QtCore.QRect(r.x(), r.y(), r.width(), half_h)
    if edge == DropEdge.BOTTOM:
        return QtCore.QRect(r.x(), r.y() + half_h, r.width(), half_h)
    return r  # CENTER — full rect


class DropOverlay(QtWidgets.QWidget):
    """Transparent overlay painted on top of a drop-target ZoomView."""

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground)
        self._edge = DropEdge.NONE
        self.hide()

    def show_edge(self, edge: str) -> None:
        if edge == DropEdge.NONE:
            self.hide()
            return
        self._edge = edge
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.update()

    def paintEvent(self, _event) -> None:
        if self._edge == DropEdge.NONE:
            return
        rect = highlight_rect(self, self._edge)
        fill, border = _overlay_colors(self.palette())
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(rect, fill)
        pen = QtGui.QPen(border, 2)
        painter.setPen(pen)
        painter.drawRect(rect.adjusted(1, 1, -1, -1))
        painter.end()
