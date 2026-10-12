"""Tiny vector icon set drawn with QPainter (no image assets needed).

Icons are authored on a 24x24 grid and scaled to whatever size is asked for,
so they stay crisp on high-DPI screens and can be recoloured for any theme.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen, QPixmap


def _polyline(p: QPainter, *pts: tuple[float, float]) -> None:
    path = QPainterPath(QPointF(*pts[0]))
    for x, y in pts[1:]:
        path.lineTo(x, y)
    p.drawPath(path)


def _home(p: QPainter) -> None:
    _polyline(p, (3, 11), (12, 3), (21, 11))
    _polyline(p, (5.5, 9.5), (5.5, 20), (10, 20), (10, 14), (14, 14), (14, 20), (18.5, 20), (18.5, 9.5))


def _search(p: QPainter) -> None:
    p.drawEllipse(QPointF(10.5, 10.5), 6.5, 6.5)
    p.drawLine(QPointF(15.3, 15.3), QPointF(21, 21))


def _cart(p: QPainter) -> None:
    _polyline(p, (2.5, 3.5), (5.2, 3.5), (7.8, 15.5), (18.8, 15.5), (20.8, 7), (6, 7))
    p.drawEllipse(QPointF(9.3, 19.8), 1.3, 1.3)
    p.drawEllipse(QPointF(17, 19.8), 1.3, 1.3)


def _bag(p: QPainter) -> None:
    _polyline(p, (6, 8), (18, 8), (19.2, 20.5), (4.8, 20.5), (6, 8))
    path = QPainterPath(QPointF(9, 8))
    path.lineTo(9, 6.5)
    path.arcTo(QRectF(9, 3.5, 6, 6), 180, -180)
    path.lineTo(15, 8)
    p.drawPath(path)


def _user(p: QPainter) -> None:
    p.drawEllipse(QPointF(12, 8), 4, 4)
    path = QPainterPath(QPointF(4.5, 20.5))
    path.cubicTo(4.5, 16.5, 8, 14.5, 12, 14.5)
    path.cubicTo(16, 14.5, 19.5, 16.5, 19.5, 20.5)
    p.drawPath(path)


def _lock(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(5, 10.5, 14, 10), 3, 3)
    path = QPainterPath(QPointF(8.2, 10.5))
    path.lineTo(8.2, 7.5)
    path.arcTo(QRectF(8.2, 3.7, 7.6, 7.6), 180, -180)
    path.lineTo(15.8, 10.5)
    p.drawPath(path)


def _face(p: QPainter) -> None:
    for pts in (
        [(3, 8), (3, 5), (3, 3), (5, 3), (8, 3)],
        [(16, 3), (19, 3), (21, 3), (21, 5), (21, 8)],
        [(3, 16), (3, 19), (3, 21), (5, 21), (8, 21)],
        [(16, 21), (19, 21), (21, 21), (21, 19), (21, 16)],
    ):
        path = QPainterPath(QPointF(*pts[0]))
        path.lineTo(*pts[1])
        path.quadTo(QPointF(*pts[2]), QPointF(*pts[3]))
        path.lineTo(*pts[4])
        p.drawPath(path)
    p.drawLine(QPointF(9, 10), QPointF(9, 11.5))
    p.drawLine(QPointF(15, 10), QPointF(15, 11.5))
    smile = QPainterPath(QPointF(8.8, 14.5))
    smile.quadTo(QPointF(12, 17.8), QPointF(15.2, 14.5))
    p.drawPath(smile)


def _chevron_left(p: QPainter) -> None:
    _polyline(p, (15, 5), (8, 12), (15, 19))


def _bubble(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(5, 4.5, 14, 12), 2.5, 2.5)
    _polyline(p, (8.5, 16.5), (8.5, 20.5), (12.5, 16.5))


def _check(p: QPainter) -> None:
    _polyline(p, (5, 12.5), (10, 17.5), (19, 7))


_ICONS = {
    "home": _home,
    "search": _search,
    "cart": _cart,
    "bag": _bag,
    "user": _user,
    "lock": _lock,
    "face": _face,
    "chevron_left": _chevron_left,
    "bubble": _bubble,
    "check": _check,
}


def paint_icon(p: QPainter, name: str, rect: QRectF, color: QColor, stroke: float = 2.0) -> None:
    """Draw icon ``name`` into ``rect`` using an already-active painter."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.translate(rect.topLeft())
    p.scale(rect.width() / 24.0, rect.height() / 24.0)
    p.setPen(QPen(color, stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    _ICONS[name](p)
    p.restore()


def pixmap(name: str, color: QColor, size: int = 22, stroke: float = 2.0) -> QPixmap:
    """Render icon ``name`` to a transparent pixmap of ``size`` logical pixels."""
    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    paint_icon(painter, name, QRectF(0, 0, size, size), color, stroke)
    painter.end()
    return pm
