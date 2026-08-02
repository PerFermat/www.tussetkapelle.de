"""Eingabemaske für die Startseite.

Die Startseite ist nicht aus Bausteinen aufgebaut, sondern aus festen Teilen:
dem großen Bild oben mit Titel und Schaltfläche, drei Kacheln, der Besuchskarte
und der Zeitleiste. Diese Struktur liegt in den Vorlagen fest – der Benutzer
kann die Texte ändern, nicht aber die Anordnung.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..model import ContentRepository, FieldKind, FieldSpec, Page
from .fields import ImageField, LongField, RichField
from .theme import Color, icon

__all__ = ["HomeEditor"]

#: Symbole, die src/templates/icons.mjs kennt.
ICON_CHOICES = [
    ("book", "Buch"),
    ("camera", "Kamera"),
    ("pin", "Ortsmarke"),
    ("chapel", "Kapelle"),
    ("hammer", "Hammer"),
    ("cross", "Kreuz"),
    ("people", "Menschen"),
    ("walking", "Weg"),
    ("clock", "Uhr"),
]


class HomeEditor(QWidget):
    """Alle Texte der Startseite in einer Maske."""

    changed = Signal()

    def __init__(self, repo: ContentRepository, lang: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._lang = lang
        self._page: Page | None = None
        self._loading = False
        self._widgets: dict[str, Any] = {}

        body = QWidget()
        self._body = QVBoxLayout(body)
        self._body.setContentsMargins(16, 14, 16, 14)
        self._body.setSpacing(14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    # -- Aufbau ------------------------------------------------------------ #

    def show_page(self, page: Page) -> None:
        self._loading = True
        self._page = page
        self._widgets.clear()
        while self._body.count():
            item = self._body.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        data = page.data
        self._build_hero(data.setdefault("hero", {}))
        self._build_tiles(data.setdefault("tiles", []))
        self._build_visit(data.setdefault("visit", {}))
        self._build_timeline(data.setdefault("timeline", {}))
        self._body.addStretch(1)
        self._loading = False

    # -- Abschnitte -------------------------------------------------------- #

    def _group(self, title: str, hint: str = "") -> QFormLayout:
        box = QGroupBox(title)
        outer = QVBoxLayout(box)
        outer.setSpacing(8)
        if hint:
            note = QLabel(hint)
            note.setProperty("rolle", "hinweis")
            note.setWordWrap(True)
            outer.addWidget(note)
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        form.setSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        outer.addLayout(form)
        self._body.addWidget(box)
        return form

    def _line(self, form: QFormLayout, label: str, holder: dict, key: str) -> None:
        edit = QLineEdit(str(holder.get(key, "")))
        edit.textChanged.connect(lambda text, h=holder, k=key: self._set(h, k, text))
        form.addRow(label, edit)

    def _rich(self, form: QFormLayout, label: str, holder: dict, key: str) -> None:
        field = RichField(FieldSpec(key, label, FieldKind.RICH), self._repo, self._lang)
        field.set_value(holder.get(key, ""))
        field.changed.connect(lambda h=holder, k=key, f=field: self._set(h, k, f.value()))
        form.addRow(label, field)

    def _long(self, form: QFormLayout, label: str, holder: dict, key: str) -> None:
        field = LongField(FieldSpec(key, label, FieldKind.LONG))
        field.set_value(holder.get(key, ""))
        field.changed.connect(lambda h=holder, k=key, f=field: self._set(h, k, f.value()))
        form.addRow(label, field)

    def _image(self, form: QFormLayout, label: str, holder: dict, key: str) -> None:
        field = ImageField(FieldSpec(key, label, FieldKind.IMAGE), self._repo)
        field.set_value(holder.get(key, ""))
        field.changed.connect(lambda h=holder, k=key, f=field: self._set(h, k, f.value()))
        form.addRow(label, field)

    def _page_choice(self, form: QFormLayout, label: str, holder: dict, key: str) -> None:
        combo = QComboBox()
        pages = self._repo.pages.get(self._lang, {})
        for page_id in self._repo.page_ids():
            page = pages.get(page_id)
            if page is not None:
                combo.addItem(page.title, page_id)
        index = combo.findData(holder.get(key, ""))
        combo.setCurrentIndex(max(index, 0))
        combo.currentIndexChanged.connect(
            lambda _, h=holder, k=key, c=combo: self._set(h, k, c.currentData())
        )
        form.addRow(label, combo)

    def _icon_choice(self, form: QFormLayout, label: str, holder: dict, key: str) -> None:
        combo = QComboBox()
        for value, text in ICON_CHOICES:
            combo.addItem(icon(value if value in ("book", "camera", "pin") else "page", Color.GREEN), text, value)
        index = combo.findData(holder.get(key, ""))
        if index < 0:
            combo.addItem(holder.get(key, ""), holder.get(key, ""))
            index = combo.count() - 1
        combo.setCurrentIndex(index)
        combo.currentIndexChanged.connect(
            lambda _, h=holder, k=key, c=combo: self._set(h, k, c.currentData())
        )
        form.addRow(label, combo)

    def _build_hero(self, hero: dict) -> None:
        form = self._group(
            "Großes Bild oben",
            "Das erste, was ein Besucher sieht. Das Bild wird über die volle "
            "Breite gezogen – dafür eignen sich nur die drei großen Aufnahmen "
            "des Bestands.",
        )
        self._image(form, "Bild", hero, "img")
        self._long(form, "Bildbeschreibung", hero, "alt")
        self._line(form, "Titel", hero, "title")
        self._line(form, "Untertitel", hero, "subtitle")
        self._rich(form, "Einleitung", hero, "lede")
        cta = hero.setdefault("cta", {})
        self._line(form, "Beschriftung der Schaltfläche", cta, "label")
        self._page_choice(form, "Schaltfläche führt zu", cta, "to")

    def _build_tiles(self, tiles: list) -> None:
        for n, tile in enumerate(tiles, 1):
            form = self._group(f"Kachel {n}")
            self._line(form, "Überschrift", tile, "title")
            self._long(form, "Text", tile, "text")
            self._image(form, "Bild", tile, "img")
            self._long(form, "Bildbeschreibung", tile, "alt")
            self._icon_choice(form, "Symbol", tile, "icon")
            self._line(form, "Beschriftung des Verweises", tile, "more")
            self._page_choice(form, "Kachel führt zu", tile, "to")

    def _build_visit(self, visit: dict) -> None:
        form = self._group("Besuchskarte", "Der grüne Kasten mit Öffnungszeiten.")
        self._line(form, "Überschrift", visit, "title")
        self._line(form, "Beschriftung Öffnungszeit", visit, "openLabel")
        self._line(form, "Öffnungszeit", visit, "hours")
        self._rich(form, "Ort", visit, "place")
        cta = visit.setdefault("cta", {})
        self._line(form, "Beschriftung der Schaltfläche", cta, "label")
        self._page_choice(form, "Schaltfläche führt zu", cta, "to")

    def _build_timeline(self, timeline: dict) -> None:
        box = QGroupBox("Zeitleiste")
        outer = QVBoxLayout(box)
        outer.setSpacing(10)

        head = QFormLayout()
        self._line(head, "Überschrift", timeline, "title")
        outer.addLayout(head)

        items = timeline.setdefault("items", [])
        self._timeline_host = QVBoxLayout()
        self._timeline_host.setSpacing(8)
        outer.addLayout(self._timeline_host)
        for n, entry in enumerate(items):
            self._timeline_host.addWidget(self._timeline_row(items, n))

        add = QPushButton("Station hinzufügen")
        add.setIcon(icon("add", Color.GREEN))
        add.clicked.connect(lambda: self._add_timeline(items))
        outer.addWidget(add)

        self._body.addWidget(box)

    def _timeline_row(self, items: list, index: int) -> QWidget:
        entry = items[index]
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        when = QLineEdit(str(entry.get("when", "")))
        when.setPlaceholderText("Wann?  z. B. „27. Juli 1985“")
        when.setMaximumWidth(210)
        when.textChanged.connect(lambda t, e=entry: self._set(e, "when", t))

        what = QLineEdit(str(entry.get("what", "")))
        what.setPlaceholderText("Was ist geschehen?")
        what.textChanged.connect(lambda t, e=entry: self._set(e, "what", t))

        combo = QComboBox()
        combo.setMaximumWidth(140)
        for value, text in ICON_CHOICES:
            combo.addItem(text, value)
        pos = combo.findData(entry.get("icon", ""))
        combo.setCurrentIndex(max(pos, 0))
        combo.currentIndexChanged.connect(
            lambda _, e=entry, c=combo: self._set(e, "icon", c.currentData())
        )

        remove = QToolButton()
        remove.setIcon(icon("remove", Color.ERROR))
        remove.setToolTip("Station entfernen")
        remove.clicked.connect(lambda: self._remove_timeline(items, entry))

        layout.addWidget(when)
        layout.addWidget(what, 1)
        layout.addWidget(combo)
        layout.addWidget(remove)
        return row

    def _add_timeline(self, items: list) -> None:
        items.append({"icon": "chapel", "when": "", "what": ""})
        self._touch()
        if self._page is not None:
            self.show_page(self._page)

    def _remove_timeline(self, items: list, entry: dict) -> None:
        if entry in items:
            items.remove(entry)
            self._touch()
            if self._page is not None:
                self.show_page(self._page)

    # -- Änderungen -------------------------------------------------------- #

    def _set(self, holder: dict, key: str, value: Any) -> None:
        if self._loading:
            return
        if value in ("", None):
            holder.pop(key, None)
        else:
            holder[key] = value
        self._touch()

    def _touch(self) -> None:
        if self._page is not None and not self._loading:
            self._page.dirty = True
            self.changed.emit()
