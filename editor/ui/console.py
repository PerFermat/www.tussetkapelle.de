"""Ausgabefenster für „Website erzeugen“ und „Prüfen“.

Die Meldungen der Werkzeuge sind bereits auf Deutsch und in ganzen Sätzen
verfasst; sie werden deshalb unverändert gezeigt. Fehlerzeilen erscheinen rot,
damit man sie in einer langen Ausgabe findet.
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .theme import Color

__all__ = ["ConsolePanel"]


class ConsolePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(4000)
        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        font.setPointSize(10)
        self.output.setFont(font)
        self.output.setPlaceholderText(
            "Hier erscheint die Ausgabe von „Website erzeugen“ und „Prüfen“."
        )

        self.summary = QLabel("Noch nichts ausgeführt.")
        self.summary.setProperty("rolle", "hinweis")

        self.clear_button = QPushButton("Leeren")
        self.clear_button.clicked.connect(self.output.clear)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addWidget(self.summary, 1)
        bar.addWidget(self.clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        layout.addLayout(bar)
        layout.addWidget(self.output, 1)

    # -- Ausgabe ----------------------------------------------------------- #

    def append(self, text: str, is_error: bool = False) -> None:
        color = Color.ERROR if is_error else Color.INK
        safe = (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
        )
        self.output.appendHtml(f'<span style="color:{color}">{safe or "&nbsp;"}</span>')
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    def begin(self, label: str) -> None:
        self.summary.setText(f"{label} läuft …")
        self.append("")
        self.append(f"── {label} ──")

    def end(self, label: str, ok: bool, code: int) -> None:
        if ok:
            self.summary.setText(f"{label}: erfolgreich abgeschlossen.")
            self.append(f"── {label}: fertig ──")
        else:
            self.summary.setText(f"{label}: fehlgeschlagen (Rückgabewert {code}).")
            self.append(f"── {label}: fehlgeschlagen, Rückgabewert {code} ──", True)
