"""Farben, Schrift und Symbole – abgestimmt auf die Website.

Der Editor benutzt dieselbe Farbwelt wie die Seite selbst: Dunkelgrün, Creme
und Gold. Das ist keine Spielerei, sondern hilft beim Arbeiten – was im Editor
golden ist, ist auch auf der fertigen Seite golden.

Die Symbole werden als SVG mit ``currentColor`` gezeichnet und beim Einfärben
neu gerendert. Damit gibt es keine Bilddateien im Programm und die Symbole
bleiben auf hochauflösenden Bildschirmen scharf.
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

__all__ = ["Color", "icon", "STYLESHEET"]


class Color:
    GREEN = "#304332"
    GREEN_DEEP = "#22301F"
    GREEN_SOFT = "#3C5340"
    CREAM = "#F7F4ED"
    PAPER = "#FFFDF8"
    GOLD = "#B79A5C"
    GOLD_TEXT = "#8A6F32"
    INK = "#1F2A20"
    INK_SOFT = "#4A5A4C"
    LINE = "#D9D5C9"
    ERROR = "#8C2F26"
    WARNING = "#8A6F32"


#: 24×24-Raster, Strichstärke 1.8 – bewusst schlicht und einheitlich.
_PATHS: dict[str, str] = {
    "paragraph": "M5 6h14M5 11h14M5 16h9",
    "heading2": "M4 5v14M4 12h8M12 5v14M17 19h4M17 19c0-3 4-3 4-6s-4-2-4 0",
    "heading3": "M4 5v14M4 12h7M11 5v14M16 8h5l-3 4a2.5 2.5 0 1 1-2 3",
    "image": "M3 5h18v14H3zM3 16l5-5 4 4 3-3 6 6",
    "images": "M2 7h13v11H2zM6 4h13v11M2 15l4-4 3 3 3-3 3 4",
    "list": "M4 6h.01M4 12h.01M4 18h.01M9 6h11M9 12h11M9 18h11",
    "deflist": "M4 6h6M4 12h6M4 18h6M13 6h7M13 12h7M13 18h7",
    "table": "M3 5h18v14H3zM3 10h18M9 5v14M15 5v14",
    "quote": "M8 7c-2.5 0-4 2-4 4.5S5.5 16 8 16l-1 3M18 7c-2.5 0-4 2-4 4.5S15.5 16 18 16l-1 3",
    "letter": "M3 6h18v13H3zM3 6l9 7 9-7",
    "note": "M12 3l9 16H3zM12 9v5M12 17h.01",
    "sources": "M6 4h9l4 4v12H6zM15 4v4h4M9 13h7M9 16h5",
    "explain": "M12 3a9 9 0 100 18 9 9 0 000-18M9.5 9.5a2.6 2.6 0 115 1c0 1.7-2.5 1.8-2.5 3.5M12 17h.01",
    "chapters": "M4 5h7v14H4zM13 5h7v14h-7M6.5 9h2M15.5 9h2",
    "station": "M12 3v18M8 7h8M4 21h16",
    # Oberfläche
    "page": "M6 3h8l4 4v14H6zM14 3v4h4M9 12h6M9 16h4",
    "pages": "M7 3h7l4 4v11H7zM4 6v15h11",
    "home": "M4 11l8-7 8 7M6 10v10h12V10M10 20v-6h4v6",
    "save": "M4 4h12l4 4v12H4zM8 4v5h7M8 20v-6h8v6",
    "build": "M4 20l6-6M8 8l4-4 3 3-4 4zM13 13l4 4 3-3-4-4z",
    "check": "M4 12l5 5L20 6",
    "add": "M12 5v14M5 12h14",
    "minus": "M5 12h14",
    "remove": "M6 7h12M9 7V5h6v2M8 7l1 13h6l1-13",
    "up": "M12 19V6M6 12l6-6 6 6",
    "down": "M12 5v13M6 12l6 6 6-6",
    "undo": "M9 8H4V3M4 8a9 9 0 113 8",
    "redo": "M15 8h5V3M20 8a9 9 0 10-3 8",
    "lock": "M6 11h12v9H6zM9 11V8a3 3 0 016 0v3",
    "language": "M12 3a9 9 0 100 18 9 9 0 000-18M3 12h18M12 3c2.5 3 2.5 15 0 18M12 3c-2.5 3-2.5 15 0 18",
    "preview": "M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7M12 15a3 3 0 100-6 3 3 0 000 6",
    "link": "M10 14a4 4 0 006 0l3-3a4 4 0 10-6-6l-1 1M14 10a4 4 0 00-6 0l-3 3a4 4 0 106 6l1-1",
    "bold": "M7 5h6a3.5 3.5 0 010 7H7zM7 12h7a3.5 3.5 0 010 7H7z",
    "italic": "M15 5h-5M14 19H9M13 5l-2 14",
    "nbsp": "M5 15v3h14v-3M8 12h8",
    "warning": "M12 3l9 16H3zM12 9v5M12 17h.01",
}


@lru_cache(maxsize=512)
def _pixmap(name: str, color: str, size: int, ratio: float) -> QPixmap:
    path = _PATHS.get(name, _PATHS["paragraph"])
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round"><path d="{path}"/></svg>'
    )
    px = QPixmap(QSize(int(size * ratio), int(size * ratio)))
    px.setDevicePixelRatio(ratio)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Das Zielrechteck muss angegeben werden, und zwar in logischen Einheiten.
    # Ohne Rechteck zeichnet QSvgRenderer in den Gerätebereich der Pixmap,
    # ignoriert dabei aber deren Bildpunktdichte – sichtbar wurde nur die
    # linke obere Ecke jedes Symbols.
    QSvgRenderer(svg.encode("utf-8")).render(painter, QRectF(0, 0, size, size))
    painter.end()
    return px


def icon(name: str, color: str = Color.GREEN, size: int = 20) -> QIcon:
    """Symbol in der gewünschten Farbe. Ergebnisse werden zwischengespeichert."""
    result = QIcon()
    normal = _pixmap(name, color, size, 2.0)
    result.addPixmap(normal, QIcon.Mode.Normal)
    result.addPixmap(_pixmap(name, Color.INK_SOFT, size, 2.0), QIcon.Mode.Disabled)
    return result


def color_of(hex_color: str) -> QColor:
    return QColor(hex_color)


# --------------------------------------------------------------------------- #
# Gestaltung                                                                   #
# --------------------------------------------------------------------------- #

STYLESHEET = f"""
QMainWindow, QDialog {{ background: {Color.CREAM}; }}

QWidget {{
    color: {Color.INK};
    font-size: 14px;
}}

/* --- Werkzeugleiste --- */
QToolBar {{
    background: {Color.GREEN};
    border: none;
    padding: 6px 10px;
    spacing: 4px;
}}
QToolBar QToolButton {{
    color: {Color.CREAM};
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: 500;
}}
QToolBar QToolButton:hover  {{ background: {Color.GREEN_SOFT}; }}
QToolBar QToolButton:pressed{{ background: {Color.GREEN_DEEP}; }}
QToolBar QToolButton:disabled {{ color: #7E8C7F; }}
QToolBar QLabel {{ color: {Color.GOLD}; padding: 0 8px; font-weight: 600; }}
QToolBar::separator {{ background: {Color.GREEN_SOFT}; width: 1px; margin: 6px 8px; }}

QComboBox {{
    background: {Color.PAPER};
    border: 1px solid {Color.LINE};
    border-radius: 6px;
    padding: 5px 10px;
    min-height: 20px;
}}
QComboBox:focus {{ border-color: {Color.GOLD_TEXT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {Color.PAPER};
    selection-background-color: {Color.GREEN};
    selection-color: {Color.CREAM};
    border: 1px solid {Color.LINE};
    padding: 4px;
}}

/* --- Listen und Bäume --- */
QTreeWidget, QListWidget, QTableWidget {{
    background: {Color.PAPER};
    border: 1px solid {Color.LINE};
    border-radius: 8px;
    outline: none;
    padding: 4px;
}}
QTreeWidget::item, QListWidget::item {{
    padding: 6px 4px;
    border-radius: 5px;
}}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {Color.GREEN};
    color: {Color.CREAM};
}}
QTreeWidget::item:hover:!selected, QListWidget::item:hover:!selected {{
    background: {Color.CREAM};
}}
QHeaderView::section {{
    background: {Color.CREAM};
    border: none;
    border-bottom: 1px solid {Color.LINE};
    padding: 6px;
    font-weight: 600;
}}

/* --- Eingabefelder --- */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox {{
    background: {Color.PAPER};
    border: 1px solid {Color.LINE};
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: {Color.GOLD};
    selection-color: {Color.INK};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus {{
    border-color: {Color.GOLD_TEXT};
}}
QLineEdit[fehlt="true"], QPlainTextEdit[fehlt="true"], QTextEdit[fehlt="true"] {{
    border-color: {Color.ERROR};
    background: #FDF6F4;
}}

/* --- Schaltflächen --- */
QPushButton {{
    background: {Color.PAPER};
    border: 1px solid {Color.LINE};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
}}
QPushButton:hover {{ border-color: {Color.GOLD_TEXT}; }}
QPushButton:default, QPushButton[wichtig="true"] {{
    background: {Color.GREEN};
    border-color: {Color.GREEN};
    color: {Color.CREAM};
}}
QPushButton:default:hover, QPushButton[wichtig="true"]:hover {{ background: {Color.GREEN_SOFT}; }}
QPushButton:disabled {{ color: #9AA69B; background: {Color.CREAM}; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border: 1px solid {Color.LINE};
    border-radius: 4px;
    background: {Color.PAPER};
}}
QCheckBox::indicator:checked {{
    background: {Color.GREEN};
    border-color: {Color.GREEN};
    image: none;
}}

/* --- Gruppen und Beschriftungen --- */
QGroupBox {{
    border: 1px solid {Color.LINE};
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 12px 12px 12px;
    background: {Color.PAPER};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {Color.GREEN};
    font-weight: 600;
}}
QLabel[rolle="titel"]  {{ font-size: 19px; font-weight: 600; color: {Color.GREEN}; }}
QLabel[rolle="hinweis"]{{ color: {Color.INK_SOFT}; font-size: 12px; }}
QLabel[rolle="feld"]   {{ font-weight: 600; color: {Color.GREEN}; }}
QLabel[rolle="warnung"]{{ color: {Color.ERROR}; font-weight: 600; }}

/* --- Reiter, Aufteiler, Leisten --- */
QTabWidget::pane {{ border: 1px solid {Color.LINE}; border-radius: 8px; background: {Color.PAPER}; }}
QTabBar::tab {{
    background: transparent;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    color: {Color.INK_SOFT};
}}
QTabBar::tab:selected {{ background: {Color.PAPER}; color: {Color.GREEN}; font-weight: 600; }}

QSplitter::handle {{ background: {Color.LINE}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical   {{ height: 1px; }}

QStatusBar {{ background: {Color.GREEN_DEEP}; color: {Color.CREAM}; }}
QStatusBar QLabel {{ color: {Color.CREAM}; padding: 0 10px; }}
QStatusBar::item {{ border: none; }}
QToolButton#ausgabeSchalter {{
    background: transparent; border: none; border-radius: 4px; padding: 2px 8px; margin-right: 4px;
}}
QToolButton#ausgabeSchalter:hover {{ background: {Color.GREEN}; }}

/* Das Ausgabefenster hat eine eigene Titelzeile (ConsoleTitleBar); die
   voreingestellte wird nicht verwendet und deshalb hier auch nicht gestaltet. */
QWidget#ausgabeTitel {{ background: {Color.CREAM}; border-bottom: 1px solid {Color.LINE}; }}
QLabel#ausgabeTitelText {{ color: {Color.GREEN}; font-weight: 600; }}
QPushButton#ausgabeEinklappen {{ background: transparent; border: none; border-radius: 4px; }}
QPushButton#ausgabeEinklappen:hover {{ background: {Color.PAPER}; }}

QScrollBar:vertical   {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle {{ background: #CFCABB; border-radius: 5px; min-height: 30px; min-width: 30px; }}
QScrollBar::handle:hover {{ background: {Color.GOLD}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QScrollArea {{ border: none; background: transparent; }}
QToolTip {{
    background: {Color.GREEN_DEEP};
    color: {Color.CREAM};
    border: none;
    padding: 6px 9px;
    border-radius: 5px;
}}
"""
