"""Custom QPainter-based chart widgets with dark-theme palette."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QLinearGradient
from PyQt6.QtWidgets import QWidget

_BG      = "#111827"
_GRID    = "#1e2d45"
_LINE    = "#2563eb"
_FILL    = "#1d3461"
_TEXT2   = "#64748b"
_GREEN   = "#10b981"
_RED     = "#ef4444"


class ChartPlaceholder(QWidget):
    def __init__(self, label: str, chart_type: str = "line") -> None:
        super().__init__()
        self.label       = label
        self.chart_type  = chart_type
        self.line_values: list[float] = []
        self.setMinimumHeight(200)

    def set_line_values(self, values: list[float]) -> None:
        self.line_values = values
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(_BG))
        self._draw_line(painter)
        painter.end()

    # ── line chart ────────────────────────────────────────────────────────────

    def _draw_line(self, painter: QPainter) -> None:
        m = 40
        rect = self.rect().adjusted(m, m // 2, -m // 2, -m)

        # grid lines
        painter.setPen(QPen(QColor(_GRID), 1))
        for i in range(1, 5):
            y = rect.top() + i * rect.height() / 5
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        if len(self.line_values) < 2:
            self._empty(painter, rect, self.label)
            return

        lo   = min(self.line_values)
        hi   = max(self.line_values)
        span = hi - lo or 1.0

        def _pt(i: int, v: float) -> tuple[int, int]:
            x = rect.left() + rect.width()  * i / (len(self.line_values) - 1)
            y = rect.bottom() - rect.height() * (v - lo) / span
            return int(x), int(y)

        points = [_pt(i, v) for i, v in enumerate(self.line_values)]
        last_v = self.line_values[-1]
        color  = _GREEN if last_v >= self.line_values[0] else _RED

        # fill area under line
        grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
        grad.setColorAt(0.0, QColor(color.replace("#", "#60") if len(color) == 7 else color))
        grad.setColorAt(1.0, QColor(_BG))

        from PyQt6.QtGui import QPainterPath, QBrush
        path = QPainterPath()
        path.moveTo(points[0][0], rect.bottom())
        for x, y in points:
            path.lineTo(x, y)
        path.lineTo(points[-1][0], rect.bottom())
        path.closeSubpath()
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        # line
        painter.setPen(QPen(QColor(color), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            painter.drawLine(x1, y1, x2, y2)

        # dots
        painter.setBrush(QColor(color))
        painter.setPen(QPen(QColor(_BG), 2))
        for x, y in points:
            painter.drawEllipse(x - 4, y - 4, 8, 8)

        # min / max labels
        painter.setPen(QColor(_TEXT2))
        f = QFont()
        f.setPointSize(9)
        painter.setFont(f)
        painter.drawText(rect.left() - 35, rect.bottom() + 2, f"{lo:,.0f}")
        painter.drawText(rect.left() - 35, rect.top() + 10,   f"{hi:,.0f}")

        # label
        painter.drawText(
            rect.adjusted(0, 0, 0, m - 4),
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            self.label,
        )

    # ── empty state ───────────────────────────────────────────────────────────

    def _empty(self, painter: QPainter, rect, msg: str) -> None:
        painter.setPen(QColor(_TEXT2))
        f = QFont()
        f.setPointSize(10)
        painter.setFont(f)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, msg)
