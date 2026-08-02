"""Kleine Dialoge für einzelne Listeneinträge.

Aufzählungspunkte, Begriffspaare und Bilder einer Bilderreihe werden nicht
direkt in der Liste bearbeitet, sondern in einem eigenen kleinen Fenster. Das
ist der einzige Weg, in einem Listeneintrag auch fetten Text oder einen Verweis
unterzubringen – eine Zeile in einer Liste kann das nicht.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..model import ContentRepository, FieldKind, FieldSpec
from .fields import ImageField, LongField, RichField

__all__ = ["TextItemDialog", "TermItemDialog", "FigureItemDialog"]


class _BaseItemDialog(QDialog):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(620)
        self._body = QVBoxLayout()
        self._body.setSpacing(10)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Übernehmen")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(self._body)
        layout.addWidget(buttons)

    def _add(self, label: str, widget: QWidget, hint: str = "") -> None:
        caption = QLabel(label)
        caption.setProperty("rolle", "feld")
        self._body.addWidget(caption)
        self._body.addWidget(widget)
        if hint:
            note = QLabel(hint)
            note.setProperty("rolle", "hinweis")
            note.setWordWrap(True)
            self._body.addWidget(note)


class TextItemDialog(_BaseItemDialog):
    """Ein Eintrag einer Aufzählung."""

    def __init__(
        self,
        repo: ContentRepository,
        lang: str,
        html: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Eintrag der Liste", parent)
        self.field = RichField(FieldSpec("html", "Text", FieldKind.RICH), repo, lang)
        self.field.set_value(html)
        self._add("Text des Eintrags", self.field)

    @property
    def html(self) -> str:
        return self.field.value()


class TermItemDialog(_BaseItemDialog):
    """Begriff und Erläuterung."""

    def __init__(
        self,
        repo: ContentRepository,
        lang: str,
        item: dict[str, str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Eintrag der Begriffsliste", parent)
        item = item or {}
        self.term = RichField(FieldSpec("term", "Begriff", FieldKind.RICH), repo, lang)
        self.body = RichField(FieldSpec("html", "Erläuterung", FieldKind.RICH), repo, lang)
        self.term.set_value(item.get("term", ""))
        self.body.set_value(item.get("html", ""))
        self._add(
            "Begriff",
            self.term,
            "Wird fett und in Grün gesetzt. Ein Doppelpunkt am Ende ist üblich, "
            "zum Beispiel „Betreuerin:“.",
        )
        self._add("Erläuterung", self.body)

    @property
    def item(self) -> dict[str, str]:
        return {"term": self.term.value(), "html": self.body.value()}


class FigureItemDialog(_BaseItemDialog):
    """Ein Bild einer Bilderreihe."""

    def __init__(
        self,
        repo: ContentRepository,
        lang: str,
        item: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Bild der Reihe", parent)
        item = item or {}
        self.image = ImageField(FieldSpec("src", "Bild", FieldKind.IMAGE), repo)
        self.alt = LongField(FieldSpec("alt", "Bildbeschreibung", FieldKind.LONG))
        self.caption = RichField(FieldSpec("caption", "Bildunterschrift", FieldKind.RICH), repo, lang)
        self.image.set_value(item.get("src", ""))
        self.alt.set_value(item.get("alt", ""))
        self.caption.set_value(item.get("caption", ""))

        self._add("Bild", self.image)
        self._add(
            "Bildbeschreibung",
            self.alt,
            "Was ist zu sehen? Wird blinden Besuchern vorgelesen und erscheint, "
            "wenn das Bild nicht lädt.",
        )
        self._add("Bildunterschrift", self.caption, "Steht sichtbar unter dem Bild. Darf leer bleiben.")

    @property
    def item(self) -> dict[str, Any]:
        out: dict[str, Any] = {"src": self.image.value(), "alt": self.alt.value()}
        caption = self.caption.value()
        if caption:
            out["caption"] = caption
        return out
