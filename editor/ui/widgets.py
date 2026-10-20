"""Bedienelemente, die beim Scrollen nicht ihren Wert ändern.

Qt schickt Mausrad-Ereignisse an das Widget unter dem Zeiger – auch dann, wenn
es gar keinen Fokus hat. In einer langen Eingabemaske genügt es deshalb, beim
Scrollen über ein Auswahlfeld zu fahren, und sein Wert springt. Lautlos: keine
Rückfrage, kein sichtbarer Unterschied zu einer gewollten Änderung.

Gemeldet wurde genau das – auf der Startseite stand nach dem Scrollen im Feld
„Schaltfläche führt zu" ein anderes Ziel. Der Schaden wäre erst auf der fertigen
Website aufgefallen.

Diese Klassen reichen das Rad deshalb weiter, statt es zu verarbeiten:
``ignore()`` gibt das Ereignis an den darüberliegenden Scrollbereich, der dann
wie erwartet scrollt. Werte ändert man mit Klick, Tastatur oder aufgeklappter
Liste – nie im Vorbeifahren. Das aufgeklappte Auswahlfeld bleibt unberührt, es
ist ein eigenes Fenster mit eigener Behandlung.
"""

from __future__ import annotations

from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox, QSpinBox

__all__ = ["ComboBox", "SpinBox"]


class ComboBox(QComboBox):
    """Auswahlfeld, das das Mausrad an den Scrollbereich durchreicht."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class SpinBox(QSpinBox):
    """Zahlenfeld, das das Mausrad an den Scrollbereich durchreicht."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()
