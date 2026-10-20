"""Suchfeld der Werkzeugleiste.

Ein Wort eintippen, **Eingabetaste**, und der Editor springt zur ersten
Fundstelle nach der aktuellen Stelle – nicht an den Anfang des Bestandes. Wer
auf Seite zwölf arbeitet, meint in aller Regel den nächsten Treffer von dort
aus.

Gesucht wird erst auf die Eingabetaste, nicht schon beim Tippen. Bei jedem
Buchstaben zu springen hieße, nach „R“ irgendwohin zu springen, nach „Ri“
woandershin – und weil der Sprung den Abschnitt wechselt, wäre der Fokus nach
dem ersten Buchstaben aus dem Suchfeld verschwunden. Genau das ist passiert.

Weiter geht es mit Pfeil ab, zurück mit Pfeil auf, beides direkt im Suchfeld:
QLineEdit braucht die Pfeiltasten nicht, und die Hand muss die Tastatur nicht
verlassen. Der Fokus bleibt dabei im Feld – sonst wirkte die Pfeiltaste nur ein
einziges Mal. Esc legt ihn in das gefundene Feld, zum Weiterschreiben.

Das Widget kennt den Inhalt nicht. Es meldet nur, was der Benutzer will; gesucht
und gesprungen wird im Hauptfenster.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .theme import Color, icon

__all__ = ["SearchBar"]


class _SearchEdit(QLineEdit):
    """Eingabezeile, die die Pfeiltasten nicht für sich behält."""

    go_next = Signal()
    go_previous = Signal()
    escaped = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.go_next.emit()
        elif key == Qt.Key.Key_Up:
            self.go_previous.emit()
        elif key == Qt.Key.Key_Escape:
            self.escaped.emit()
        else:
            super().keyPressEvent(event)
            return
        event.accept()


class SearchBar(QWidget):
    """Suchfeld mit Zähler und zwei Richtungsknöpfen."""

    #: Der Benutzer hat getippt. **Kein** Suchbefehl – nur das Zeichen, dass
    #: ein angezeigter Zähler nicht mehr zum Feldinhalt passt.
    term_changed = Signal(str)
    #: Weiter bzw. zurück. Beim ersten Mal nach einer Änderung heißt das:
    #: neu suchen. Das entscheidet das Hauptfenster.
    next_hit = Signal()
    previous_hit = Signal()
    #: Esc im Suchfeld: der Benutzer will an der Fundstelle weiterschreiben.
    left = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.edit = _SearchEdit()
        self.edit.setPlaceholderText("Im Inhalt suchen …")
        self.edit.setClearButtonEnabled(True)
        self.edit.addAction(icon("search", Color.INK_SOFT), QLineEdit.ActionPosition.LeadingPosition)

        self.count = QLabel()
        self.count.setProperty("rolle", "hinweis")

        self.button_prev = self._button("up", "Vorheriger Treffer  (Pfeil auf)")
        self.button_next = self._button("down", "Nächster Treffer  (Pfeil ab)")

        # Zwei Zeilen statt einer: Das Feld steht in der linken Spalte neben dem
        # Seitenbaum, und die ist schmal. In der Werkzeugleiste war kein Platz –
        # dort stehen schon neun beschriftete Knöpfe.
        zeile = QHBoxLayout()
        zeile.setContentsMargins(0, 0, 0, 0)
        zeile.setSpacing(2)
        zeile.addWidget(self.edit, 1)
        zeile.addWidget(self.button_prev)
        zeile.addWidget(self.button_next)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addLayout(zeile)
        layout.addWidget(self.count)

        self.edit.textChanged.connect(self.term_changed)
        self.edit.go_next.connect(self.next_hit)
        self.edit.go_previous.connect(self.previous_hit)
        self.edit.escaped.connect(self.left)
        self.button_next.clicked.connect(self.next_hit)
        self.button_prev.clicked.connect(self.previous_hit)
        self.set_result(0, 0)

    def _button(self, name: str, hint: str) -> QToolButton:
        button = QToolButton()
        # Dunkel, nicht cremefarben: Die Knöpfe stehen in der hellen linken
        # Spalte, nicht auf der dunkelgrünen Werkzeugleiste.
        button.setIcon(icon(name, Color.GREEN))
        button.setToolTip(hint)
        button.setAutoRaise(True)
        # Ohne das nähme der Knopf beim Klicken den Fokus, und die Pfeiltasten
        # im Suchfeld wären danach wirkungslos.
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    # -- Anzeige ------------------------------------------------------------ #

    def set_result(self, index: int, total: int) -> None:
        """Zähler und Knöpfe an das Ergebnis angleichen.

        ``index`` ist einsbasiert; 0 heißt „nichts ausgewählt“.
        """
        if not self.edit.text().strip():
            self.count.setText("")
        elif total == 0:
            self.count.setText("nichts gefunden")
        else:
            self.count.setText(f"{index} von {total}")
        self.button_next.setEnabled(total > 0)
        self.button_prev.setEnabled(total > 0)

    def clear_result(self) -> None:
        """Zähler leeren, ohne etwas zu behaupten.

        Beim Tippen ist noch nichts gesucht worden – „nichts gefunden“ wäre dann
        eine Aussage über eine Suche, die gar nicht stattgefunden hat.
        """
        self.count.setText("")
        self.button_next.setEnabled(False)
        self.button_prev.setEnabled(False)

    def focus(self) -> None:
        self.edit.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.edit.selectAll()

    def term(self) -> str:
        return self.edit.text().strip()
