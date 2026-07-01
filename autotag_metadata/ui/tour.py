"""Guided tour overlay — dims the window, highlights one control at a time."""
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

from collections.abc import Callable
from dataclasses import dataclass, field

from PyQt6 import QtCore, QtGui, QtWidgets

_PAD = 6  # padding around the highlighted target, px
_GAP = 12  # gap between the highlight and the bubble, px


@dataclass
class TourStep:
    """One tour step: text plus the widget(s) it points at.

    *targets* may be empty (a centred bubble with no highlight, for intro/outro)
    or hold several widgets whose union rectangle is highlighted together.
    *on_enter* runs when the step is shown — e.g. to reveal a hidden panel so it
    can be highlighted.
    """

    title: str
    text: str
    targets: list[QtWidgets.QWidget] = field(default_factory=list)
    on_enter: Callable[[], None] | None = None


class TourOverlay(QtWidgets.QWidget):
    """Full-window overlay that walks the user through *steps* one at a time.

    Paints a translucent scrim with a punched-out hole around the current
    target, and floats a palette-themed bubble (Back / Next / Skip) beside it.
    The overlay covers its parent, blocks input to the UI beneath, and tracks
    the parent's resizes so the highlight stays aligned.
    """

    finished = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget, steps: list[TourStep]):
        super().__init__(parent)
        self._steps = steps
        self._index = 0
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self._build_bubble()
        parent.installEventFilter(self)
        self.setGeometry(parent.rect())

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        if not self._steps:
            self.finished.emit()
            self.deleteLater()
            return
        self._index = 0
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.setFocus()
        self._show_step()

    def _finish(self) -> None:
        self.hide()
        self.finished.emit()
        self.deleteLater()

    # -- bubble ------------------------------------------------------------

    def _build_bubble(self) -> None:
        self._bubble = QtWidgets.QFrame(self)
        self._bubble.setObjectName("tourBubble")
        self._bubble.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self._bubble.setMaximumWidth(360)

        pal = self._bubble.palette()
        # A stylesheet disables autoFillBackground, so the opaque fill must live
        # in the stylesheet itself — otherwise the scrim shows through the text.
        base = pal.color(QtGui.QPalette.ColorRole.Base).name()
        border = pal.color(QtGui.QPalette.ColorRole.Highlight).name()
        self._bubble.setStyleSheet(
            f"#tourBubble {{ background-color: {base}; border: 2px solid {border}; border-radius: 6px; }}"
        )

        lay = QtWidgets.QVBoxLayout(self._bubble)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        self._title = QtWidgets.QLabel(self._bubble)
        title_font = self._title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 1)
        self._title.setFont(title_font)
        lay.addWidget(self._title)

        self._body = QtWidgets.QLabel(self._bubble)
        self._body.setWordWrap(True)
        self._body.setTextFormat(QtCore.Qt.TextFormat.RichText)
        lay.addWidget(self._body)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        self._progress = QtWidgets.QLabel(self._bubble)
        self._progress.setEnabled(False)
        row.addWidget(self._progress)
        row.addStretch(1)
        self._btn_skip = QtWidgets.QPushButton("Skip", self._bubble)
        self._btn_back = QtWidgets.QPushButton("Back", self._bubble)
        self._btn_next = QtWidgets.QPushButton("Next", self._bubble)
        self._btn_next.setDefault(True)
        self._btn_skip.clicked.connect(self._finish)
        self._btn_back.clicked.connect(self._go_back)
        self._btn_next.clicked.connect(self._go_next)
        row.addWidget(self._btn_skip)
        row.addWidget(self._btn_back)
        row.addWidget(self._btn_next)
        lay.addLayout(row)

    # -- navigation --------------------------------------------------------

    def _go_next(self) -> None:
        if self._index >= len(self._steps) - 1:
            self._finish()
            return
        self._index += 1
        self._show_step()

    def _go_back(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._show_step()

    def _show_step(self) -> None:
        step = self._steps[self._index]
        if step.on_enter is not None:
            step.on_enter()
        self._title.setText(step.title)
        self._body.setText(step.text)
        self._progress.setText(f"{self._index + 1} / {len(self._steps)}")
        self._btn_back.setEnabled(self._index > 0)
        last = self._index >= len(self._steps) - 1
        self._btn_next.setText("Done" if last else "Next")
        self._btn_skip.setVisible(not last)
        self._bubble.adjustSize()
        self._reposition()
        self.update()

    # -- geometry ----------------------------------------------------------

    def _target_rect(self) -> QtCore.QRect | None:
        """Union rect of the current step's targets, in overlay coordinates."""
        step = self._steps[self._index]
        root = self.parentWidget()
        rect: QtCore.QRect | None = None
        for widget in step.targets:
            if widget is None or not widget.isVisible():
                continue
            top_left = widget.mapTo(root, QtCore.QPoint(0, 0))
            r = QtCore.QRect(top_left, widget.size())
            rect = r if rect is None else rect.united(r)
        return rect

    def _reposition(self) -> None:
        target = self._target_rect()
        bubble = self._bubble
        bw, bh = bubble.width(), bubble.height()
        area = self.rect()

        if target is None:
            bubble.move(area.center().x() - bw // 2, area.center().y() - bh // 2)
            return

        hole = target.adjusted(-_PAD, -_PAD, _PAD, _PAD)
        # Prefer below the target, then above, then right, then left.
        if hole.bottom() + _GAP + bh <= area.bottom():
            y = hole.bottom() + _GAP
            x = min(max(area.left() + _GAP, hole.left()), area.right() - bw - _GAP)
        elif hole.top() - _GAP - bh >= area.top():
            y = hole.top() - _GAP - bh
            x = min(max(area.left() + _GAP, hole.left()), area.right() - bw - _GAP)
        elif hole.right() + _GAP + bw <= area.right():
            x = hole.right() + _GAP
            y = min(max(area.top() + _GAP, hole.top()), area.bottom() - bh - _GAP)
        else:
            x = max(area.left() + _GAP, hole.left() - _GAP - bw)
            y = min(max(area.top() + _GAP, hole.top()), area.bottom() - bh - _GAP)
        bubble.move(int(x), int(y))

    # -- events ------------------------------------------------------------

    def eventFilter(self, obj, event):  # noqa: N802 (Qt override)
        if obj is self.parentWidget() and event.type() in (
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.Move,
        ):
            self.setGeometry(self.parentWidget().rect())
            self._reposition()
            self.update()
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        key = event.key()
        if key == QtCore.Qt.Key.Key_Escape:
            self._finish()
        elif key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Right):
            self._go_next()
        elif key == QtCore.Qt.Key.Key_Left:
            self._go_back()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        # Swallow clicks so the UI beneath stays inert while the tour runs.
        event.accept()

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        scrim = QtGui.QColor(0, 0, 0, 160)
        target = self._target_rect()
        if target is None:
            painter.fillRect(self.rect(), scrim)
            painter.end()
            return

        hole = QtCore.QRectF(target.adjusted(-_PAD, -_PAD, _PAD, _PAD))
        path = QtGui.QPainterPath()
        path.addRect(QtCore.QRectF(self.rect()))
        cut = QtGui.QPainterPath()
        cut.addRoundedRect(hole, 6, 6)
        painter.fillPath(path.subtracted(cut), scrim)

        accent = self.palette().color(QtGui.QPalette.ColorRole.Highlight)
        painter.setPen(QtGui.QPen(accent, 2))
        painter.drawRoundedRect(hole, 6, 6)
        painter.end()
