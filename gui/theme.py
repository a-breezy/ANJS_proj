"""Colour themes for the bookstore GUI.

Two palettes are defined, taken from the wireframes:

* ``dark`` - navy background with yellow accents (wireframe set 1, the default)
* ``mint`` - light mint background with dark-green, yellow and coral accents
  (wireframe set 2)

Every colour used anywhere in the UI is a token on :class:`Palette`, so adding
a third theme (e.g. the purple/lime wireframe set 3) means adding one more
``Palette`` instance and registering it in ``PALETTES``.

Widgets that paint themselves read colours through :func:`c` and repaint when
``theme.changed`` fires. Everything else is styled by the global stylesheet
produced by :func:`build_qss`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from string import Template

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

FONT_FAMILIES = ["Inter", "DM Sans", "Segoe UI", "Helvetica Neue", "Arial"]


@dataclass(frozen=True)
class Palette:
    key: str
    label: str
    # surfaces
    bg: str
    surface: str
    field: str
    field_border: str
    border: str
    # text
    text: str
    muted: str
    error: str
    # buttons / accents
    primary: str
    on_primary: str
    highlight: str
    on_highlight: str
    banner_circle: str
    link: str
    outline: str
    chip: str
    chip_active: str
    on_chip_active: str
    seg_active: str
    on_seg_active: str
    price: str
    # bottom navigation
    nav_bg: str
    nav_active: str
    nav_inactive: str
    nav_pill: str  # "" = no pill behind the active item
    # cart badge, progress bar
    badge: str
    on_badge: str
    progress_track: str
    progress_fill: str
    # face-scan viewfinder
    vf_bg: str
    vf_ring: str
    vf_corner: str
    vf_ellipse: str
    vf_ellipse_fill: str
    vf_scan: str
    vf_text: str
    vf_dashed: bool
    # book covers: (background, circle, text-lines)
    covers: tuple


DARK = Palette(
    key="dark",
    label="Dark",
    bg="#0F1830",
    surface="#1B2A52",
    field="#1B2A52",
    field_border="#2A3B6E",
    border="#25356A",
    text="#F4F5FB",
    muted="#AAB5D6",
    error="#FF8A6B",
    primary="#FFB703",
    on_primary="#0F1830",
    highlight="#FFB703",
    on_highlight="#0F1830",
    banner_circle="#FFD166",
    link="#5BC0EB",
    outline="#5BC0EB",
    chip="#1B2A52",
    chip_active="#5BC0EB",
    on_chip_active="#0F1830",
    seg_active="#FFB703",
    on_seg_active="#0F1830",
    price="#FFB703",
    nav_bg="#1B2A52",
    nav_active="#FFB703",
    nav_inactive="#AAB5D6",
    nav_pill="",
    badge="#FFB703",
    on_badge="#0F1830",
    progress_track="#0F1830",
    progress_fill="#FFB703",
    vf_bg="#1B2A52",
    vf_ring="#2C3E75",
    vf_corner="#5BC0EB",
    vf_ellipse="#FFB703",
    vf_ellipse_fill="#0F1830",
    vf_scan="#FFB703",
    vf_text="#AAB5D6",
    vf_dashed=False,
    covers=(
        ("#FFB703", "#0F1830", "#0F1830"),
        ("#5BC0EB", "#0F1830", "#0F1830"),
        ("#F4F5FB", "#FFB703", "#FFB703"),
        ("#E4572E", "#F4F5FB", "#F4F5FB"),
    ),
)

MINT = Palette(
    key="mint",
    label="Mint",
    bg="#E6F4EC",
    surface="#FFFFFF",
    field="#FFFFFF",
    field_border="#BFDCCB",
    border="#D3EBDC",
    text="#0B3B36",
    muted="#3E6B63",
    error="#C0392B",
    primary="#0B3B36",
    on_primary="#FFFFFF",
    highlight="#FFD23F",
    on_highlight="#0B3B36",
    banner_circle="#FF7A59",
    link="#0B3B36",
    outline="#0B3B36",
    chip="#FFFFFF",
    chip_active="#0B3B36",
    on_chip_active="#FFFFFF",
    seg_active="#FFD23F",
    on_seg_active="#0B3B36",
    price="#0B3B36",
    nav_bg="#FFFFFF",
    nav_active="#FFD23F",
    nav_inactive="#3E6B63",
    nav_pill="#0B3B36",
    badge="#FFD23F",
    on_badge="#0B3B36",
    progress_track="#D3EBDC",
    progress_fill="#FF7A59",
    vf_bg="#0B3B36",
    vf_ring="#16524A",
    vf_corner="#FFD23F",
    vf_ellipse="#FFFFFF",
    vf_ellipse_fill="#0B3B36",
    vf_scan="#FFD23F",
    vf_text="#E6F4EC",
    vf_dashed=True,
    covers=(
        ("#FF7A59", "#FFD23F", "#FFD23F"),
        ("#B8A1FF", "#0B3B36", "#0B3B36"),
        ("#0B3B36", "#FFD23F", "#FFD23F"),
        ("#FFD23F", "#FF7A59", "#FF7A59"),
    ),
)

PALETTES = {DARK.key: DARK, MINT.key: MINT}


class ThemeManager(QObject):
    """Holds the active palette and announces changes."""

    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._key = DARK.key

    @property
    def key(self) -> str:
        return self._key

    @property
    def palette(self) -> Palette:
        return PALETTES[self._key]

    def set_theme(self, key: str) -> None:
        if key not in PALETTES:
            raise ValueError(f"Unknown theme {key!r}; choose from {sorted(PALETTES)}")
        if key != self._key:
            self._key = key
            self.changed.emit()

    def toggle(self) -> None:
        self.set_theme(MINT.key if self._key == DARK.key else DARK.key)


theme = ThemeManager()


def c(token: str) -> QColor:
    """Colour for a palette token in the active theme."""
    return QColor(getattr(theme.palette, token))


_QSS = Template(
    """
* { font-family: "Inter", "DM Sans", "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
QMainWindow { background: $bg; }
QWidget#page { background: $bg; }
QLabel { background: transparent; color: $text; font-size: 14px; }
QLabel[role="muted"] { color: $muted; }
QLabel[role="subtitle"] { color: $muted; font-size: 16px; }
QLabel[role="caption"] { color: $muted; font-size: 15px; }
QLabel[role="price"] { color: $price; font-weight: 700; font-size: 15px; }
QLabel[role="error"] { color: $error; font-size: 13px; }
QLabel[role="brand"] { font-size: 18px; font-weight: 800; }
QLabel[role="h1"] { font-size: 34px; font-weight: 800; }
QLabel[role="h2"] { font-size: 22px; font-weight: 800; }
QLabel[role="h3"] { font-size: 16px; font-weight: 800; }
QLabel[role="field"] { font-size: 14px; font-weight: 700; }
QLabel[role="book"] { font-size: 15px; font-weight: 800; }
QLabel[role="author"] { color: $muted; font-size: 13px; }
QLabel[role="onhighlight"] { color: $on_highlight; font-size: 16px; font-weight: 800; }
QLabel[role="bubble_user"] { background: $primary; color: $on_primary; border-radius: 16px; padding: 10px 14px; font-size: 15px; }
QLabel[role="bubble_bot"] { background: $surface; color: $text; border: 1px solid $border; border-radius: 16px; padding: 10px 14px; font-size: 15px; }
QLabel[role="bubble_error"] { background: transparent; color: $error; border: 1.5px solid $error; border-radius: 16px; padding: 10px 14px; font-size: 14px; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 6px; margin: 2px; }
QScrollBar::handle:vertical { background: $field_border; border-radius: 3px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar:horizontal { height: 0; }

QFrame[card="true"] { background: $surface; border: 1px solid $border; border-radius: 18px; }
QFrame#segment { background: $surface; border: 1px solid $border; border-radius: 27px; }
QFrame#navbar { background: $nav_bg; border: none; border-top: 1px solid $border; }

QPushButton { border: none; font-size: 15px; font-weight: 700; padding: 0 18px; }
QPushButton:disabled { background: $field_border; color: $muted; }
QPushButton[variant="primary"] { background: $primary; color: $on_primary; border-radius: 22px; }
QPushButton[variant="outline"] { background: transparent; color: $outline; border: 1.5px solid $outline; border-radius: 20px; padding: 0 10px; font-size: 14px; }
QPushButton[variant="dark"] { background: $on_highlight; color: $highlight; border-radius: 20px; }
QPushButton[variant="link"] { background: transparent; color: $link; font-weight: 500; text-decoration: underline; padding: 0; }
QPushButton[variant="linkbold"] { background: transparent; color: $link; font-weight: 800; text-decoration: underline; padding: 0; }
QPushButton[variant="round"] { background: $surface; border-radius: 22px; padding: 0; }
QPushButton[variant="chip"] { background: $chip; color: $text; border-radius: 19px; padding: 0 16px; font-size: 14px; font-weight: 600; }
QPushButton[variant="chip"]:checked { background: $chip_active; color: $on_chip_active; font-weight: 800; }
QPushButton[variant="segment"] { background: transparent; color: $muted; border-radius: 22px; }
QPushButton[variant="segment"]:checked { background: $seg_active; color: $on_seg_active; }
QPushButton[variant="small"] { background: transparent; color: $text; border: 1.5px solid $field_border; border-radius: 17px; font-size: 13px; padding: 0 14px; }

QLineEdit { background: $field; color: $text; border: 1.5px solid $field_border; border-radius: 22px;
            padding: 0 16px; font-size: 15px; selection-background-color: $link; selection-color: $bg;
            placeholder-text-color: $muted; }
QLineEdit:focus { border: 1.5px solid $link; }

QMenuBar { background: $nav_bg; color: $text; }
QMenuBar::item:selected { background: $field_border; }
QMenu { background: $surface; color: $text; border: 1px solid $border; }
QMenu::item:selected { background: $field_border; }
QToolTip { background: $surface; color: $text; border: 1px solid $border; }
"""
)


def build_qss(palette: Palette) -> str:
    """Global stylesheet for a palette."""
    return _QSS.safe_substitute(asdict(palette))
