"""Bedienelemente für die Feldarten aus der Blocktyp-Registry.

Jede Feldart aus ``FieldKind`` bekommt hier genau ein Bedienelement. Die
Eingabemasken entstehen daraus vollständig automatisch – wer einen neuen
Blocktyp einträgt, muss keinen Dialog bauen.

Alle Elemente haben dieselbe schmale Schnittstelle:
``value()``, ``set_value()`` und das Signal ``changed``.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..model import ContentRepository, FieldKind, FieldSpec
from ..richtext import plain_text
from .imagepicker import ImagePickerDialog, thumbnail
from .richtextedit import RichTextEdit
from .theme import Color, icon

__all__ = ["build_field", "FieldWidget"]


class FieldWidget(QWidget):
    """Gemeinsame Grundlage aller Feldelemente."""

    changed = Signal()

    def value(self) -> Any:  # pragma: no cover - abstrakt
        raise NotImplementedError

    def set_value(self, value: Any) -> None:  # pragma: no cover - abstrakt
        raise NotImplementedError

    def mark_missing(self, missing: bool) -> None:
        """Färbt das Feld, wenn eine Pflichtangabe fehlt."""
        children = self.findChildren(QLineEdit) + self.findChildren(QPlainTextEdit)
        for child in children:
            child.setProperty("fehlt", "true" if missing else "false")
            child.style().unpolish(child)
            child.style().polish(child)


# --------------------------------------------------------------------------- #
# Einfache Felder                                                              #
# --------------------------------------------------------------------------- #


class PlainField(FieldWidget):
    def __init__(self, spec: FieldSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.edit = QLineEdit()
        # Kein Platzhalter aus dem Hilfetext: der steht ohnehin unter dem Feld,
        # und doppelt gelesen wirkt er wie zwei verschiedene Anweisungen.
        self.edit.setPlaceholderText("" if spec.required else "darf leer bleiben")
        self.edit.textChanged.connect(self.changed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit)

    def value(self) -> str:
        return self.edit.text().strip()

    def set_value(self, value: Any) -> None:
        self.edit.setText("" if value is None else str(value))


class LongField(FieldWidget):
    def __init__(self, spec: FieldSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.edit = QPlainTextEdit()
        self.edit.setMinimumHeight(74)
        self.edit.setMaximumHeight(110)
        self.edit.setTabChangesFocus(True)
        self.edit.textChanged.connect(self.changed)
        self.counter = QLabel()
        self.counter.setProperty("rolle", "hinweis")
        self.counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.edit.textChanged.connect(self._count)
        self._show_count = spec.key == "description"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.edit)
        if self._show_count:
            layout.addWidget(self.counter)

    def _count(self) -> None:
        n = len(self.edit.toPlainText())
        self.counter.setText(f"{n} von 160 Zeichen" + ("  –  wird abgeschnitten" if n > 160 else ""))

    def value(self) -> str:
        return self.edit.toPlainText().strip()

    def set_value(self, value: Any) -> None:
        self.edit.setPlainText("" if value is None else str(value))
        self._count()


class RichField(FieldWidget):
    def __init__(
        self, spec: FieldSpec, repo: ContentRepository, lang: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        single = spec.key in ("text", "title", "caption", "word")
        self.editor = RichTextEdit(repo, lang, single_line=single)
        self.editor.changed.connect(self.changed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)

    def value(self) -> str:
        return self.editor.html()

    def set_value(self, value: Any) -> None:
        self.editor.set_html("" if value is None else str(value))

    def mark_missing(self, missing: bool) -> None:
        self.editor.edit.setProperty("fehlt", "true" if missing else "false")
        self.editor.edit.style().unpolish(self.editor.edit)
        self.editor.edit.style().polish(self.editor.edit)


class BoolField(FieldWidget):
    def __init__(self, spec: FieldSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.box = QCheckBox(spec.label)
        self.box.toggled.connect(self.changed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.box)

    def value(self) -> bool | None:
        # False wird nicht gespeichert – im Bestand steht nur, was zutrifft.
        return True if self.box.isChecked() else None

    def set_value(self, value: Any) -> None:
        self.box.setChecked(bool(value))


class ChoiceField(FieldWidget):
    def __init__(self, spec: FieldSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.combo = QComboBox()
        for value, label in spec.choices:
            self.combo.addItem(label, value)
        self.combo.currentIndexChanged.connect(self.changed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.combo)

    def value(self) -> str:
        return self.combo.currentData()

    def set_value(self, value: Any) -> None:
        index = self.combo.findData(value)
        self.combo.setCurrentIndex(index if index >= 0 else 0)


class IntField(FieldWidget):
    def __init__(self, spec: FieldSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spin = QSpinBox()
        self.spin.setRange(0, 4000)
        self.spin.setSpecialValueText("automatisch")
        self.spin.setSuffix(" px")
        self.spin.valueChanged.connect(self.changed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spin)

    def value(self) -> int | None:
        return self.spin.value() or None

    def set_value(self, value: Any) -> None:
        self.spin.setValue(int(value) if value else 0)


# --------------------------------------------------------------------------- #
# Bild                                                                         #
# --------------------------------------------------------------------------- #


class ImageField(FieldWidget):
    def __init__(
        self, spec: FieldSpec, repo: ContentRepository, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._src = ""

        self.preview = QLabel()
        self.preview.setFixedSize(150, 112)
        self.preview.setFrameShape(QFrame.Shape.StyledPanel)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.caption = QLabel("Kein Bild gewählt.")
        self.caption.setProperty("rolle", "hinweis")
        self.caption.setWordWrap(True)

        self.choose_button = QPushButton("Bild auswählen …")
        self.choose_button.setIcon(icon("image", Color.GREEN))
        self.choose_button.clicked.connect(self._choose)

        right = QVBoxLayout()
        right.setSpacing(6)
        right.addWidget(self.choose_button)
        right.addWidget(self.caption, 1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.preview)
        layout.addLayout(right, 1)

    def _choose(self) -> None:
        dialog = ImagePickerDialog(self._repo.manifest, self._src, self._used(), self)
        if dialog.exec() == ImagePickerDialog.DialogCode.Accepted and dialog.selected:
            self.set_value(dialog.selected)
            self.changed.emit()

    def _used(self) -> set[str]:
        """Bereits eingebundene Bilder – für den Filter im Auswahldialog."""
        used: set[str] = set()

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                src = node.get("src")
                if isinstance(src, str):
                    used.add(src)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        for pages in self._repo.pages.values():
            for page in pages.values():
                walk(page.data)
        return used

    def value(self) -> str:
        return self._src

    def set_value(self, value: Any) -> None:
        self._src = str(value or "")
        if not self._src:
            self.preview.clear()
            self.caption.setText("Kein Bild gewählt.")
            return
        self.preview.setPixmap(thumbnail(self._repo.manifest, self._src, QSize(150, 112)))
        info = self._repo.manifest.get(self._src)
        if info is None:
            self.caption.setText(
                f"<span style='color:{Color.ERROR}'>{self._src}<br>"
                "Dieses Bild steht nicht im Bildbestand.</span>"
            )
        else:
            self.caption.setText(f"{info.src}<br>{info.dimensions} · {info.size_label}")


# --------------------------------------------------------------------------- #
# Listen                                                                       #
# --------------------------------------------------------------------------- #


class _ListBase(FieldWidget):
    """Liste mit Hinzufügen, Löschen und Verschieben."""

    def __init__(self, add_label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.setMinimumHeight(130)
        self.list.model().rowsMoved.connect(self.changed)
        self.list.itemChanged.connect(self.changed)

        self.add_button = QPushButton(add_label)
        self.add_button.setIcon(icon("add", Color.GREEN))
        self.add_button.clicked.connect(self._add)

        self.edit_button = QToolButton()
        self.edit_button.setIcon(icon("paragraph", Color.GREEN))
        self.edit_button.setToolTip("Eintrag bearbeiten")
        self.edit_button.clicked.connect(self._edit_current)

        self.remove_button = QToolButton()
        self.remove_button.setIcon(icon("remove", Color.ERROR))
        self.remove_button.setToolTip("Eintrag löschen")
        self.remove_button.clicked.connect(self._remove)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addWidget(self.add_button)
        bar.addStretch(1)
        bar.addWidget(self.edit_button)
        bar.addWidget(self.remove_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.list)
        layout.addLayout(bar)

    def _remove(self) -> None:
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)
            self.changed.emit()

    def _add(self) -> None:  # pragma: no cover - in Unterklassen
        raise NotImplementedError

    def _edit_current(self) -> None:  # pragma: no cover - in Unterklassen
        raise NotImplementedError


class TextListField(_ListBase):
    """Einträge einer Aufzählung. Auszeichnung ist erlaubt."""

    def __init__(self, repo: ContentRepository, lang: str, parent: QWidget | None = None) -> None:
        super().__init__("Eintrag hinzufügen", parent)
        self._repo, self._lang = repo, lang
        self.list.itemDoubleClicked.connect(lambda _: self._edit_current())

    def _add(self) -> None:
        from .itemdialogs import TextItemDialog

        dialog = TextItemDialog(self._repo, self._lang, "", parent=self)
        if dialog.exec() == TextItemDialog.DialogCode.Accepted:
            self._append(dialog.html)
            self.changed.emit()

    def _edit_current(self) -> None:
        from .itemdialogs import TextItemDialog

        item = self.list.currentItem()
        if item is None:
            return
        dialog = TextItemDialog(
            self._repo, self._lang, item.data(Qt.ItemDataRole.UserRole), parent=self
        )
        if dialog.exec() == TextItemDialog.DialogCode.Accepted:
            item.setData(Qt.ItemDataRole.UserRole, dialog.html)
            item.setText(plain_text(dialog.html) or "(leer)")
            self.changed.emit()

    def _append(self, html: str) -> None:
        item = QListWidgetItem(plain_text(html) or "(leer)")
        item.setData(Qt.ItemDataRole.UserRole, html)
        self.list.addItem(item)

    def value(self) -> list[str]:
        return [
            self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())
        ]

    def set_value(self, value: Any) -> None:
        self.list.clear()
        for entry in value or []:
            self._append(str(entry))


class TermListField(_ListBase):
    """Begriff und Erläuterung."""

    def __init__(self, repo: ContentRepository, lang: str, parent: QWidget | None = None) -> None:
        super().__init__("Eintrag hinzufügen", parent)
        self._repo, self._lang = repo, lang
        self._items: list[dict[str, str]] = []
        self.list.itemDoubleClicked.connect(lambda _: self._edit_current())

    def _add(self) -> None:
        from .itemdialogs import TermItemDialog

        dialog = TermItemDialog(self._repo, self._lang, {}, parent=self)
        if dialog.exec() == TermItemDialog.DialogCode.Accepted:
            self._append(dialog.item)
            self.changed.emit()

    def _edit_current(self) -> None:
        from .itemdialogs import TermItemDialog

        row = self.list.currentRow()
        if row < 0:
            return
        dialog = TermItemDialog(self._repo, self._lang, self._items[row], parent=self)
        if dialog.exec() == TermItemDialog.DialogCode.Accepted:
            self._items[row] = dialog.item
            self._refresh()
            self.changed.emit()

    def _append(self, entry: dict[str, str]) -> None:
        self._items.append(entry)
        self._refresh()

    def _refresh(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for entry in self._items:
            term = plain_text(entry.get("term", ""))
            body = plain_text(entry.get("html", ""))
            self.list.addItem(f"{term}  {body}"[:110])
        self.list.blockSignals(False)

    def value(self) -> list[dict[str, str]]:
        order = [self.list.item(i).text() for i in range(self.list.count())]
        return self._items if len(order) == len(self._items) else self._items

    def set_value(self, value: Any) -> None:
        self._items = [dict(entry) for entry in (value or [])]
        self._refresh()


class FigureListField(_ListBase):
    """Bilderreihe."""

    def __init__(self, repo: ContentRepository, lang: str, parent: QWidget | None = None) -> None:
        super().__init__("Bild hinzufügen", parent)
        self._repo, self._lang = repo, lang
        self._items: list[dict[str, Any]] = []
        self.list.setIconSize(QSize(72, 54))
        self.list.itemDoubleClicked.connect(lambda _: self._edit_current())

    def _add(self) -> None:
        from .itemdialogs import FigureItemDialog

        dialog = FigureItemDialog(self._repo, self._lang, {}, parent=self)
        if dialog.exec() == FigureItemDialog.DialogCode.Accepted and dialog.item.get("src"):
            self._items.append(dialog.item)
            self._refresh()
            self.changed.emit()

    def _edit_current(self) -> None:
        from .itemdialogs import FigureItemDialog

        row = self.list.currentRow()
        if row < 0:
            return
        dialog = FigureItemDialog(self._repo, self._lang, self._items[row], parent=self)
        if dialog.exec() == FigureItemDialog.DialogCode.Accepted:
            self._items[row] = dialog.item
            self._refresh()
            self.changed.emit()

    def _refresh(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for entry in self._items:
            src = entry.get("src", "")
            text = plain_text(entry.get("caption", "")) or src.rsplit("/", 1)[-1]
            item = QListWidgetItem(QIcon(thumbnail(self._repo.manifest, src, QSize(72, 54))), text)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def value(self) -> list[dict[str, Any]]:
        return self._items

    def set_value(self, value: Any) -> None:
        self._items = [dict(entry) for entry in (value or [])]
        self._refresh()


class TableField(FieldWidget):
    """Zeilen einer Tabelle. Die Spaltenzahl folgt den Spaltenköpfen."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table = QTableWidget(0, 2)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setMinimumHeight(170)
        self.table.itemChanged.connect(self.changed)

        add_row = QPushButton("Zeile hinzufügen")
        add_row.setIcon(icon("add", Color.GREEN))
        add_row.clicked.connect(self._add_row)

        remove_row = QPushButton("Zeile löschen")
        remove_row.setIcon(icon("remove", Color.ERROR))
        remove_row.clicked.connect(self._remove_row)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addWidget(add_row)
        bar.addWidget(remove_row)
        bar.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.table)
        layout.addLayout(bar)

    def set_headers(self, headers: list[str]) -> None:
        self.table.setColumnCount(max(1, len(headers)))
        self.table.setHorizontalHeaderLabels(headers or ["Spalte 1"])

    def _add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col in range(self.table.columnCount()):
            self.table.setItem(row, col, QTableWidgetItem(""))
        self.changed.emit()

    def _remove_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.changed.emit()

    def value(self) -> list[list[str]]:
        return [
            [
                (self.table.item(r, c).text() if self.table.item(r, c) else "")
                for c in range(self.table.columnCount())
            ]
            for r in range(self.table.rowCount())
        ]

    def set_value(self, value: Any) -> None:
        rows = value or []
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        width = max((len(r) for r in rows), default=self.table.columnCount())
        self.table.setColumnCount(max(1, width))
        for r, row in enumerate(rows):
            for c in range(self.table.columnCount()):
                self.table.setItem(r, c, QTableWidgetItem(str(row[c]) if c < len(row) else ""))
        self.table.blockSignals(False)


# --------------------------------------------------------------------------- #
# Aufbau                                                                       #
# --------------------------------------------------------------------------- #


def build_field(spec: FieldSpec, repo: ContentRepository, lang: str) -> FieldWidget:
    """Erzeugt das passende Bedienelement zu einer Feldbeschreibung."""
    kind = spec.kind
    if kind is FieldKind.RICH:
        return RichField(spec, repo, lang)
    if kind is FieldKind.PLAIN:
        return PlainField(spec)
    if kind is FieldKind.LONG:
        return LongField(spec)
    if kind is FieldKind.BOOL:
        return BoolField(spec)
    if kind is FieldKind.CHOICE:
        return ChoiceField(spec)
    if kind is FieldKind.INT:
        return IntField(spec)
    if kind is FieldKind.IMAGE:
        return ImageField(spec, repo)
    if kind is FieldKind.TEXT_LIST:
        return TextListField(repo, lang)
    if kind is FieldKind.TERM_LIST:
        return TermListField(repo, lang)
    if kind is FieldKind.FIGURE_LIST:
        return FigureListField(repo, lang)
    if kind is FieldKind.TABLE:
        return TableField()
    if kind is FieldKind.BLOCK_LIST:
        from .nested import NestedBlockField

        return NestedBlockField(repo, lang)
    if kind is FieldKind.CHAPTER_GROUPS:
        from .nested import ChapterGroupsField

        return ChapterGroupsField(repo, lang)
    return PlainField(spec)  # pragma: no cover - unerreichbar
