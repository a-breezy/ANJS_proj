"""Reusable widgets shared by the screens."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .theme import c, theme

AA = QPainter.RenderHint.Antialiasing
_PILL_VARIANTS = {"primary", "outline", "dark", "chip", "segment", "small"}


def make_label(text: str = "", role: str | None = None, align=None, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    if role:
        label.setProperty("role", role)
    if align is not None:
        label.setAlignment(align)
    label.setWordWrap(wrap)
    return label


class Page(QWidget):
    """A full-size screen that paints the themed background."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


class Column(QWidget):
    """Vertical layout whose content is capped at ``max_width`` and centred.

    On a phone-sized window it behaves like a plain QVBoxLayout with the given
    margins; on a wide desktop window the extra width becomes side margins so
    lines of text and forms don't stretch across the whole screen.
    """

    def __init__(self, max_width: int, margins=(16, 14, 16, 18), spacing: int = 12, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._max_width = max_width
        self._margins = margins
        self.col = QVBoxLayout(self)
        self.col.setContentsMargins(*margins)
        self.col.setSpacing(spacing)

    def resizeEvent(self, event) -> None:
        left, top, right, bottom = self._margins
        extra = max(0, (self.width() - left - right - self._max_width) // 2)
        self.col.setContentsMargins(left + extra, top, right + extra, bottom)
        super().resizeEvent(event)


def scroll_column(max_width: int = 1200, margins=(16, 14, 16, 18), spacing: int = 12) -> tuple[QScrollArea, QVBoxLayout]:
    """A vertical scroll area holding a :class:`Column`; returns (scroll area, content layout)."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    content = Column(max_width, margins, spacing)
    scroll.setWidget(content)
    return scroll, content.col


class IconButton(QPushButton):
    """Push button whose icon is recoloured whenever the theme changes."""

    def __init__(
        self,
        text: str = "",
        icon: str | None = None,
        token: str = "text",
        *,
        size: int = 20,
        variant: str | None = None,
        height: int | None = None,
        token_checked: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon = icon
        self._token = token
        self._token_checked = token_checked
        self._size = size
        self.setText(text)
        if variant:
            self.setProperty("variant", variant)
        if height:
            self.setFixedHeight(height)
            if variant in _PILL_VARIANTS:
                # Qt ignores a border-radius larger than half the height, so
                # size the radius to the button to get a true pill shape.
                self.setStyleSheet(f"border-radius: {height // 2}px;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(size, size))
        theme.changed.connect(self._refresh)
        self.toggled.connect(self._refresh)
        self._refresh()

    def setText(self, text: str) -> None:  # noqa: N802 (Qt naming)
        # A small gap between the icon and the label.
        super().setText(" " + text if (self._icon and text) else text)

    def set_icon_name(self, icon: str) -> None:
        self._icon = icon
        self._refresh()

    def _refresh(self, *_args) -> None:
        if not self._icon:
            return
        token = self._token_checked if (self._token_checked and self.isChecked()) else self._token
        self.setIcon(QIcon(icons.pixmap(self._icon, c(token), self._size)))


def make_button(text: str, variant: str, height: int = 44, icon: str | None = None, token: str = "text") -> IconButton:
    return IconButton(text, icon, token, variant=variant, height=height)


class SearchField(QLineEdit):
    def __init__(self, placeholder: str = "Search books", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(46)
        self.setClearButtonEnabled(True)
        self._action = self.addAction(QIcon(), QLineEdit.ActionPosition.LeadingPosition)
        theme.changed.connect(self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        self._action.setIcon(QIcon(icons.pixmap("search", c("muted"), 20)))


class Logo(QWidget):
    """Rounded square app mark with a speech-bubble glyph."""

    def __init__(self, size: int = 36, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        theme.changed.connect(self.update)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        r = QRectF(self.rect())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c("highlight"))
        p.drawRoundedRect(r, r.width() * 0.28, r.width() * 0.28)
        inset = r.width() * 0.18
        icons.paint_icon(p, "bubble", r.adjusted(inset, inset, -inset, -inset), c("on_highlight"), 2.2)


class Avatar(QWidget):
    """Circle with the user's initial."""

    def __init__(self, initial: str = "N", size: int = 44, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._initial = initial
        self.setFixedSize(size, size)
        theme.changed.connect(self.update)

    def set_initial(self, initial: str) -> None:
        self._initial = initial
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        r = QRectF(self.rect())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c("highlight"))
        p.drawEllipse(r)
        font = QFont(self.font())
        font.setPixelSize(int(r.height() * 0.42))
        font.setWeight(QFont.Weight.ExtraBold)
        p.setFont(font)
        p.setPen(c("on_highlight"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self._initial)


class BookCover(QWidget):
    """Placeholder cover art: coloured block, corner circle and two text bars."""

    def __init__(self, cover: int, height: int, square: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cover = cover
        self._square = square
        self.setFixedHeight(height)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        theme.changed.connect(self.update)

    def paintEvent(self, _event) -> None:
        covers = theme.palette.covers
        bg, circle, bars = covers[self._cover % len(covers)]
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(AA)
        clip = QPainterPath()
        radius = 14
        clip.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        p.setClipPath(clip)
        p.fillPath(clip, QColor(bg))

        d = min(w, h) * 0.5
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(circle))
        p.drawEllipse(QRectF(w - d, 0, d, d))

        short, long_ = (0.26, 0.44) if self._square else (0.19, 0.29)
        bar_h = max(4.0, h * (0.06 if self._square else 0.058))
        left = w * (0.09 if self._square else 0.065)
        bottom = h * 0.13
        p.setBrush(QColor(bars))
        long_rect = QRectF(left, h - bottom - bar_h, w * long_, bar_h)
        short_rect = QRectF(left, long_rect.top() - bar_h * 1.6, w * short, bar_h)
        p.drawRoundedRect(long_rect, bar_h / 2, bar_h / 2)
        p.drawRoundedRect(short_rect, bar_h / 2, bar_h / 2)


class ProgressBar(QWidget):
    def __init__(self, value: float = 0.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = value
        self.setFixedHeight(8)
        theme.changed.connect(self.update)

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        r = QRectF(self.rect())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c("progress_track"))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.setBrush(c("progress_fill"))
        p.drawRoundedRect(QRectF(0, 0, max(r.height(), r.width() * self._value), r.height()), r.height() / 2, r.height() / 2)


class Banner(QWidget):
    """Highlight-coloured call-to-action strip with a decorative circle."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        theme.changed.connect(self.update)

    def paintEvent(self, _event) -> None:
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(AA)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), 20, 20)
        p.setClipPath(clip)
        p.fillPath(clip, c("highlight"))
        r = h * 0.55
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c("banner_circle"))
        p.drawEllipse(QPointF(w * 0.70, h * 0.12), r, r)


class BadgeButton(QPushButton):
    """Round cart button with an item-count badge."""

    def __init__(self, icon: str = "cart", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon = icon
        self._count = 0
        self.setProperty("variant", "round")
        self.setFixedSize(46, 46)
        self.setStyleSheet("border-radius: 23px;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        theme.changed.connect(self._refresh)
        self._refresh()

    def set_count(self, count: int) -> None:
        self._count = count
        self.update()

    def _refresh(self) -> None:
        self.setIcon(QIcon(icons.pixmap(self._icon, c("text"), 22)))
        self.setIconSize(QSize(22, 22))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._count <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(AA)
        d = 19
        rect = QRectF(self.width() - d - 1, 1, d, d)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c("badge"))
        p.drawEllipse(rect)
        font = QFont(self.font())
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.ExtraBold)
        p.setFont(font)
        p.setPen(c("on_badge"))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(min(self._count, 9)) + ("+" if self._count > 9 else ""))


class NavButton(QAbstractButton):
    """Bottom-navigation item: icon above a label."""

    def __init__(self, key: str, label: str, icon: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.key = key
        self._label = label
        self._icon = icon
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(58)
        theme.changed.connect(self.update)

    def sizeHint(self) -> QSize:
        return QSize(70, 58)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        active = self.isChecked()
        color = c("nav_active" if active else "nav_inactive")
        pill = theme.palette.nav_pill
        if active and pill:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(pill))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(4, 2, -4, -2), 22, 22)
        icons.paint_icon(p, self._icon, QRectF(self.width() / 2 - 11, 8, 22, 22), color, 2.0)
        font = QFont(self.font())
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.ExtraBold if active else QFont.Weight.DemiBold)
        p.setFont(font)
        p.setPen(color)
        p.drawText(QRectF(0, 33, self.width(), 18), Qt.AlignmentFlag.AlignCenter, self._label)


class NavBar(QFrame):
    """Exclusive row of NavButtons, centred and capped in width on desktop."""

    selected = Signal(str)
    MAX_ITEM_WIDTH = 120

    def __init__(self, items: list[tuple[str, str, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navbar")
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(8, 4, 8, 6)
        self._row.setSpacing(0)
        self._buttons: dict[str, NavButton] = {}
        self.set_items(items)

    def set_items(self, items: list[tuple[str, str, str]]) -> None:
        while self._row.count():
            widget = self._row.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._buttons = {}
        self._row.addStretch()
        for key, label, icon in items:
            btn = NavButton(key, label, icon)
            btn.setMaximumWidth(self.MAX_ITEM_WIDTH)
            btn.clicked.connect(lambda _=False, k=key: self.selected.emit(k))
            self._buttons[key] = btn
            self._row.addWidget(btn, 1)
        self._row.addStretch()

    def keys(self) -> list[str]:
        return list(self._buttons)

    def set_current(self, key: str) -> None:
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)


class SegmentedControl(QFrame):
    """Pill-shaped row of mutually exclusive options (e.g. Tracking | History)."""

    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], height: int = 44, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("segment")
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 4, 4, 4)
        row.setSpacing(4)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self._buttons: dict[str, IconButton] = {}
        for key, label in options:
            btn = IconButton(label, variant="segment", height=height)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, k=key: self.set_current(k))
            group.addButton(btn)
            row.addWidget(btn, 1)
            self._buttons[key] = btn
        self._current = options[0][0]
        self._buttons[self._current].setChecked(True)

    @property
    def current(self) -> str:
        return self._current

    def set_current(self, key: str) -> None:
        self._buttons[key].setChecked(True)
        if key != self._current:
            self._current = key
            self.changed.emit(key)


class Viewfinder(QWidget):
    """Face-scan camera frame: corner brackets, rings, face oval, scan line.

    This only draws the placeholder. To show a live camera feed, render the
    frames behind the oval in ``paintEvent`` (see ``auth.authenticate_face``).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(290)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._t = 0.5  # scan-line position, 0 (top of oval) .. 1 (bottom)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(1300)
        self._anim.setLoopCount(-1)
        self._anim.setKeyValueAt(0.0, 0.0)
        self._anim.setKeyValueAt(0.5, 1.0)
        self._anim.setKeyValueAt(1.0, 0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.valueChanged.connect(self._on_tick)
        theme.changed.connect(self.update)

    def start(self) -> None:
        self._anim.start()

    def stop(self) -> None:
        self._anim.stop()
        self._t = 0.5
        self.update()

    def _on_tick(self, value) -> None:
        self._t = float(value)
        self.update()

    def paintEvent(self, _event) -> None:
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(AA)
        card = QPainterPath()
        card.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 24, 24)
        p.fillPath(card, c("vf_bg"))
        p.setClipPath(card)

        cx, cy = w / 2, h / 2 - 4
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(c("vf_ring"), 1))
        for radius in (h * 0.47, h * 0.37):
            p.drawEllipse(QPointF(cx, cy + 4), radius, radius)

        oh = h * 0.69
        ow = oh * 0.76
        oval = QRectF(cx - ow / 2, cy - oh / 2, ow, oh)
        p.setBrush(c("vf_ellipse_fill"))
        pen = QPen(c("vf_ellipse"), 3)
        if theme.palette.vf_dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawEllipse(oval)

        scan_y = oval.top() + 10 + (oval.height() - 20) * self._t
        p.setPen(QPen(c("vf_scan"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(oval.left() - 18, scan_y), QPointF(oval.right() + 18, scan_y))

        p.setPen(QPen(c("vf_corner"), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
        inset, length = 16, 27
        for sx, sy, ax, ay in ((inset, inset, 1, 1), (w - inset, inset, -1, 1), (inset, h - inset, 1, -1), (w - inset, h - inset, -1, -1)):
            p.drawLine(QPointF(sx, sy), QPointF(sx + ax * length, sy))
            p.drawLine(QPointF(sx, sy), QPointF(sx, sy + ay * length))

        font = QFont(self.font())
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(c("vf_text"))
        p.drawText(QRectF(0, h - 34, w, 18), Qt.AlignmentFlag.AlignCenter, "Camera preview")


class ThemeSwitch(QPushButton):
    """Button that flips between the dark and mint themes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("variant", "outline")
        self.setFixedHeight(48)
        self.setStyleSheet("border-radius: 24px;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(theme.toggle)
        theme.changed.connect(self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        self.setText("Switch to mint theme" if theme.key == "dark" else "Switch to dark theme")
