"""Eingabemaske für einen Baustein.

Die Maske wird nicht von Hand gebaut, sondern aus der Beschreibung des
Blocktyps erzeugt (``editor/model/blockspec.py``). Damit kann kein Feld
vergessen werden und die Beschriftungen bleiben überall dieselben.

Geschrieben wird nur, was auch einen Wert hat: leere Felder und abgewählte
Kästchen verschwinden aus der JSON-Datei, statt als ``""`` oder ``false``
stehen zu bleiben. So bleibt der Bestand so knapp, wie er von Hand angelegt
wurde.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..model import BlockSpec, ContentRepository, FieldKind, spec_for
from .fields import FieldWidget, build_field

__all__ = ["BlockEditor"]


class BlockEditor(QWidget):
    """Zeigt und bearbeitet genau einen Baustein."""

    changed = Signal()

    def __init__(self, repo: ContentRepository, lang: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._lang = lang
        self._block: dict[str, Any] | None = None
        self._spec: BlockSpec | None = None
        self._fields: dict[str, FieldWidget] = {}
        self._loading = False
        self._read_only = False

        self.title = QLabel()
        self.title.setProperty("rolle", "titel")
        self.hint = QLabel()
        self.hint.setProperty("rolle", "hinweis")
        self.hint.setWordWrap(True)

        self.form_host = QWidget()
        self.form = QVBoxLayout(self.form_host)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.form.setSpacing(14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.form_host)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        layout.addWidget(self.title)
        layout.addWidget(self.hint)
        layout.addSpacing(8)
        layout.addWidget(scroll, 1)

        self.clear()

    # -- Anzeige ----------------------------------------------------------- #

    def clear(self) -> None:
        self._block = None
        self._spec = None
        self._clear_form()
        self.title.setText("Kein Abschnitt ausgewählt")
        self.hint.setText("Wählen Sie links einen Abschnitt aus, um ihn zu bearbeiten.")

    def _clear_form(self) -> None:
        self._fields.clear()
        while self.form.count():
            item = self.form.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def set_read_only(self, read_only: bool) -> None:
        self._read_only = read_only
        self.form_host.setEnabled(not read_only)

    def show_block(self, block: dict[str, Any]) -> None:
        spec = spec_for(block.get("t", ""))
        self._loading = True
        self._clear_form()
        self._block = block
        self._spec = spec

        if spec is None:
            self.title.setText("Unbekannte Art von Abschnitt")
            self.hint.setText(
                f"Der Abschnitt hat die Kennung „{block.get('t')}“, die dieses "
                "Programm nicht kennt. Er bleibt beim Speichern unverändert."
            )
            self._loading = False
            return

        self.title.setText(spec.label)
        self.hint.setText(spec.hint)

        for field_spec in spec.fields:
            caption = QLabel(field_spec.label + ("  ·  erforderlich" if field_spec.required else ""))
            caption.setProperty("rolle", "feld")
            widget = build_field(field_spec, self._repo, self._lang)
            widget.set_value(block.get(field_spec.key))
            widget.changed.connect(self._collect)
            self._fields[field_spec.key] = widget

            if field_spec.kind is not FieldKind.BOOL:
                self.form.addWidget(caption)
            self.form.addWidget(widget)

            if field_spec.help:
                note = QLabel(field_spec.help)
                note.setProperty("rolle", "hinweis")
                note.setWordWrap(True)
                self.form.addWidget(note)

        # Die Spaltenzahl der Tabelle folgt den Spaltenköpfen.
        if "head" in self._fields and "rows" in self._fields:
            self._fields["head"].changed.connect(self._sync_table_headers)
            self._sync_table_headers()

        self.form.addStretch(1)
        self._loading = False
        self._mark_missing()

    def _sync_table_headers(self) -> None:
        headers = [
            _plain(h) for h in self._fields["head"].value()
        ]
        self._fields["rows"].set_headers(headers)

    # -- Übernehmen -------------------------------------------------------- #

    def _collect(self) -> None:
        """Schreibt die Eingaben in den Baustein zurück."""
        if self._loading or self._block is None or self._spec is None or self._read_only:
            return
        for spec in self._spec.fields:
            widget = self._fields.get(spec.key)
            if widget is None:
                continue
            value = widget.value()
            if value in (None, "", [], {}) and not spec.required:
                self._block.pop(spec.key, None)
            else:
                self._block[spec.key] = value
        self._mark_missing()
        self.changed.emit()

    def _mark_missing(self) -> None:
        if self._spec is None:
            return
        for spec in self._spec.fields:
            widget = self._fields.get(spec.key)
            if widget is not None and spec.required:
                widget.mark_missing(not widget.value())


def _plain(html: str) -> str:
    from ..richtext import plain_text

    return plain_text(html)
