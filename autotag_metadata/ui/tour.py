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

    *slug* is the step's stable identifier, independent of its position and of
    the section number in *title*. Screenshots are named after it, so inserting
    or renumbering a step does not rename (and thereby break) the images the
    documentation references.
    """

    title: str
    text: str
    targets: list[QtWidgets.QWidget | Callable[[], QtCore.QRect | None]] = field(default_factory=list)
    on_enter: Callable[[], None] | None = None
    slug: str = ""


class TourOverlay(QtWidgets.QWidget):
    """Full-window overlay that walks the user through *steps* one at a time.

    Paints a translucent scrim with a punched-out hole around the current
    target, and floats a palette-themed bubble (Back / Next / Skip) beside it.
    The overlay covers its parent, blocks input to the UI beneath, and tracks
    the parent's resizes so the highlight stays aligned.
    """

    finished = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget, steps: list[TourStep]) -> None:
        super().__init__(parent)
        self._steps = steps
        self._index = 0
        self._drag_offset: QtCore.QPoint | None = None
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

    def stop(self) -> None:
        """Cancel tour programmatically (e.g. app closing mid-tour)."""
        self._finish()

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
        for btn in (self._btn_skip, self._btn_back, self._btn_next):
            btn.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        self._btn_next.setDefault(True)
        self._btn_skip.clicked.connect(self._finish)
        self._btn_back.clicked.connect(self._go_back)
        self._btn_next.clicked.connect(self._go_next)
        row.addWidget(self._btn_skip)
        row.addWidget(self._btn_back)
        row.addWidget(self._btn_next)
        lay.addLayout(row)
        self._bubble.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        self._bubble.installEventFilter(self)

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
        self._drag_offset = None
        step = self._steps[self._index]
        if step.on_enter is not None:
            step.on_enter()
        self.raise_()
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
        # An on_enter that rebuilds widgets (e.g. re-tiling the form) only gets its
        # final geometry after this event-loop cycle; reposition/repaint once more then
        # so the spotlight lands on the settled target rather than a stale first paint.
        QtCore.QTimer.singleShot(0, self._reposition_and_repaint)

    def _reposition_and_repaint(self) -> None:
        self._reposition()
        self.update()

    # -- geometry ----------------------------------------------------------

    def _target_rects(self) -> list[QtCore.QRect]:
        """Individual rects for each target of the current step, in overlay coordinates."""
        step = self._steps[self._index]
        root = self.parentWidget()
        rects: list[QtCore.QRect] = []
        for item in step.targets:
            if callable(item):
                r = item()
                if r is not None:
                    rects.append(r)
            else:
                if item is None or not item.isVisible():
                    continue
                top_left = item.mapTo(root, QtCore.QPoint(0, 0))
                rects.append(QtCore.QRect(top_left, item.size()))
        return rects

    def _target_rect(self) -> QtCore.QRect | None:
        """Union of all target rects — used for bubble positioning."""
        rects = self._target_rects()
        if not rects:
            return None
        result = rects[0]
        for r in rects[1:]:
            result = result.united(r)
        return result

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

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:  # noqa: N802 (Qt override)
        if obj is self.parentWidget() and event.type() in (
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.Move,
        ):
            self.setGeometry(self.parentWidget().rect())
            self._reposition()
            self.update()
            return super().eventFilter(obj, event)

        if obj is self._bubble:
            t = event.type()
            if t == QtCore.QEvent.Type.MouseButtonPress and event.button() == QtCore.Qt.MouseButton.LeftButton:
                # pos() is already in _bubble coords (labels propagate up; buttons consume their own events)
                click_in_overlay = self._bubble.mapTo(self, event.pos())
                self._drag_offset = click_in_overlay - self._bubble.pos()
                self._bubble.grabMouse()
                return True
            if t == QtCore.QEvent.Type.MouseMove and self._drag_offset is not None:
                pos_in_overlay = self._bubble.mapTo(self, event.pos())
                new_tl = pos_in_overlay - self._drag_offset
                area = self.rect()
                bw, bh = self._bubble.width(), self._bubble.height()
                nx = max(area.left(), min(new_tl.x(), area.right() - bw))
                ny = max(area.top(), min(new_tl.y(), area.bottom() - bh))
                self._bubble.move(nx, ny)
                return True
            if t == QtCore.QEvent.Type.MouseButtonRelease and self._drag_offset is not None:
                self._bubble.releaseMouse()
                self._drag_offset = None
                return True

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

    def _forward_if_in_hole(self, event: QtGui.QMouseEvent) -> None:
        """Forward *event* to the real widget under the cursor when inside a target hole."""
        rects = self._target_rects()
        padded = [r.adjusted(-_PAD, -_PAD, _PAD, _PAD) for r in rects]
        if not any(r.contains(event.pos()) for r in padded):
            event.accept()
            return
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        target = QtWidgets.QApplication.widgetAt(event.globalPosition().toPoint())
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        if target is None or target is self:
            event.accept()
            return
        local = QtCore.QPointF(target.mapFromGlobal(event.globalPosition().toPoint()))
        forwarded = QtGui.QMouseEvent(
            event.type(),
            local,
            event.globalPosition(),
            event.button(),
            event.buttons(),
            event.modifiers(),
        )
        QtWidgets.QApplication.sendEvent(target, forwarded)
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            focus_target = target
            parent = target.parentWidget()
            if isinstance(parent, QtWidgets.QAbstractScrollArea) and parent.viewport() is target:
                focus_target = parent
            if focus_target.focusPolicy() != QtCore.Qt.FocusPolicy.NoFocus:
                focus_target.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        event.accept()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._forward_if_in_hole(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._forward_if_in_hole(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self._forward_if_in_hole(event)

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        scrim = QtGui.QColor(0, 0, 0, 160)
        rects = self._target_rects()
        if not rects:
            painter.fillRect(self.rect(), scrim)
            painter.end()
            return

        path = QtGui.QPainterPath()
        path.addRect(QtCore.QRectF(self.rect()))
        cut = QtGui.QPainterPath()
        cut.setFillRule(QtCore.Qt.FillRule.WindingFill)
        holes = [QtCore.QRectF(r.adjusted(-_PAD, -_PAD, _PAD, _PAD)) for r in rects]
        for hole in holes:
            cut.addRoundedRect(hole, 6, 6)
        painter.fillPath(path.subtracted(cut), scrim)

        painter.end()
