"""Ausgabefenster für „Website erzeugen“ und „Prüfen“.

Die Meldungen der Werkzeuge sind bereits auf Deutsch und in ganzen Sätzen
verfasst; sie werden deshalb unverändert gezeigt. Fehlerzeilen erscheinen rot,
damit man sie in einer langen Ausgabe findet.

Das Fenster ist die meiste Zeit im Weg: Es wird nur bei einem Werkzeuglauf
gebraucht, nimmt aber Höhe weg, die der Eingabemaske fehlt. Deshalb meldet es
sich mit ``output_arrived`` selbst zu Wort, sobald die erste Zeile eines Laufs
eintrifft – und nur dann. Wer es danach zuklappt, bekommt es nicht bei jeder
weiteren Zeile erneut aufgedrängt.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .theme import Color, icon

__all__ = ["ConsolePanel", "ConsoleTitleBar"]


class ConsoleTitleBar(QWidget):
    """Titelzeile des Ausgabefensters.

    Sie ersetzt die voreingestellte Titelzeile des ``QDockWidget`` vollständig.
    Das ist nicht nur eine Frage des Aussehens: die voreingestellte Titelzeile
    reißt das Fenster bei einem Doppelklick los, und ein frei schwebendes
    Ausgabefenster legt sich über die Eingabemaske.
    """

    collapse_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ausgabeTitel")

        caption = QLabel("Ausgabe der Werkzeuge")
        caption.setObjectName("ausgabeTitelText")

        self.collapse = QPushButton(icon("minus", Color.GREEN), "")
        self.collapse.setObjectName("ausgabeEinklappen")
        self.collapse.setToolTip("Ausgabe der Werkzeuge verbergen")
        self.collapse.setFlat(True)
        self.collapse.setFixedSize(26, 22)
        self.collapse.clicked.connect(self.collapse_requested)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 6, 4)
        layout.addWidget(caption, 1)
        layout.addWidget(self.collapse)


class ConsolePanel(QWidget):
    #: Die erste Zeile eines Laufs ist da – das Fenster möchte gezeigt werden.
    output_arrived = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._announced = True

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

        # Genug, um die Trennlinie und ein paar Zeilen zu sehen; mehr darf sich
        # das Fenster nicht vom mittleren Bereich nehmen.
        self.setMinimumHeight(110)

    # -- Ausgabe ----------------------------------------------------------- #

    def append(self, text: str, is_error: bool = False) -> None:
        color = Color.ERROR if is_error else Color.INK
        safe = (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
        )
        self.output.appendHtml(f'<span style="color:{color}">{safe or "&nbsp;"}</span>')
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        if not self._announced:
            self._announced = True
            self.output_arrived.emit()

    def begin(self, label: str) -> None:
        self.summary.setText(f"{label} läuft …")
        self._announced = False
        self.append("")
        self.append(f"── {label} ──")

    def end(self, label: str, ok: bool, code: int) -> None:
        if ok:
            self.summary.setText(f"{label}: erfolgreich abgeschlossen.")
            self.append(f"── {label}: fertig ──")
        else:
            self.summary.setText(f"{label}: fehlgeschlagen (Rückgabewert {code}).")
            self.append(f"── {label}: fehlgeschlagen, Rückgabewert {code} ──", True)
