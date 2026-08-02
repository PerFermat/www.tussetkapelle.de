"""Verschachtelte Inhalte: Brieftext und Kapitelübersicht.

Zwei Bausteine enthalten selbst wieder Bausteine. Der Brief besteht aus
Absätzen, die Kapitelübersicht aus Gruppen mit Verweisen auf andere Seiten.
Beide kommen im Bestand selten vor (zweimal beziehungsweise dreimal), brauchen
aber ein Bedienelement, sonst wären die betroffenen Seiten nicht pflegbar.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..model import ContentRepository, FieldKind, FieldSpec, summarize
from .fields import FieldWidget, RichField
from .theme import Color, icon

__all__ = ["NestedBlockField", "ChapterGroupsField"]


# --------------------------------------------------------------------------- #
# Brieftext                                                                    #
# --------------------------------------------------------------------------- #


class _ParagraphDialog(QDialog):
    def __init__(
        self, repo: ContentRepository, lang: str, html: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Absatz des Briefes")
        self.setMinimumWidth(640)
        self.field = RichField(FieldSpec("html", "Text", FieldKind.RICH), repo, lang)
        self.field.set_value(html)

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
        layout.addWidget(self.field)
        layout.addWidget(buttons)

    @property
    def html(self) -> str:
        return self.field.value()


class NestedBlockField(FieldWidget):
    """Die Absätze innerhalb eines Briefes."""

    def __init__(self, repo: ContentRepository, lang: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo, self._lang = repo, lang
        self._blocks: list[dict[str, Any]] = []

        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setMinimumHeight(150)
        self.list.itemDoubleClicked.connect(lambda _: self._edit())
        self.list.model().rowsMoved.connect(self._reorder)

        add = QPushButton("Absatz hinzufügen")
        add.setIcon(icon("add", Color.GREEN))
        add.clicked.connect(self._add)

        edit = QToolButton()
        edit.setIcon(icon("paragraph", Color.GREEN))
        edit.setToolTip("Absatz bearbeiten")
        edit.clicked.connect(self._edit)

        remove = QToolButton()
        remove.setIcon(icon("remove", Color.ERROR))
        remove.setToolTip("Absatz löschen")
        remove.clicked.connect(self._remove)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addWidget(add)
        bar.addStretch(1)
        bar.addWidget(edit)
        bar.addWidget(remove)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.list)
        layout.addLayout(bar)

    def _refresh(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for block in self._blocks:
            self.list.addItem(QListWidgetItem(summarize(block) or "(leerer Absatz)"))
        self.list.blockSignals(False)

    def _reorder(self, _parent, start: int, end: int, _dest, row: int) -> None:  # noqa: ANN001
        moved = self._blocks.pop(start)
        self._blocks.insert(row if row < start else row - 1, moved)
        self._refresh()
        self.changed.emit()

    def _add(self) -> None:
        dialog = _ParagraphDialog(self._repo, self._lang, "", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._blocks.append({"t": "p", "html": dialog.html})
            self._refresh()
            self.changed.emit()

    def _edit(self) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        dialog = _ParagraphDialog(self._repo, self._lang, self._blocks[row].get("html", ""), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._blocks[row]["html"] = dialog.html
            self._refresh()
            self.changed.emit()

    def _remove(self) -> None:
        row = self.list.currentRow()
        if row >= 0:
            del self._blocks[row]
            self._refresh()
            self.changed.emit()

    def value(self) -> list[dict[str, Any]]:
        return self._blocks

    def set_value(self, value: Any) -> None:
        self._blocks = [dict(b) for b in (value or [])]
        self._refresh()


# --------------------------------------------------------------------------- #
# Kapitelübersicht                                                             #
# --------------------------------------------------------------------------- #


class _ChapterEntryDialog(QDialog):
    def __init__(
        self, repo: ContentRepository, lang: str, entry: dict[str, str], parent: QWidget | None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Eintrag der Kapitelübersicht")
        self.setMinimumWidth(560)
        self._repo, self._lang = repo, lang

        self.page = QComboBox()
        pages = repo.pages.get(lang, {})
        for page_id in repo.page_ids():
            page = pages.get(page_id)
            if page is not None:
                self.page.addItem(page.title, page_id)
        index = self.page.findData(entry.get("id", ""))
        if index >= 0:
            self.page.setCurrentIndex(index)
        self.page.currentIndexChanged.connect(self._fill_title)

        self.title = QLineEdit(entry.get("title", ""))
        self.sub = QLineEdit(entry.get("sub", ""))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Übernehmen")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        for label, widget, hint in (
            ("Seite", self.page, "Auf welche Seite führt der Eintrag?"),
            ("Beschriftung", self.title, "Darf vom Seitentitel abweichen."),
            ("Zusatz", self.sub, "Zweite Zeile, zum Beispiel „Ein Bericht von Otto Veith“."),
        ):
            caption = QLabel(label)
            caption.setProperty("rolle", "feld")
            note = QLabel(hint)
            note.setProperty("rolle", "hinweis")
            layout.addWidget(caption)
            layout.addWidget(widget)
            layout.addWidget(note)
        layout.addWidget(buttons)

        if not self.title.text():
            self._fill_title()

    def _fill_title(self) -> None:
        page = self._repo.page(self._lang, self.page.currentData())
        if page is not None and not self.title.text().strip():
            self.title.setText(page.title)

    @property
    def entry(self) -> dict[str, str]:
        out = {"id": self.page.currentData(), "title": self.title.text().strip()}
        if self.sub.text().strip():
            out["sub"] = self.sub.text().strip()
        return out


class ChapterGroupsField(FieldWidget):
    """Gruppen mit Verweisen auf andere Seiten."""

    def __init__(self, repo: ContentRepository, lang: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo, self._lang = repo, lang
        self._groups: list[dict[str, Any]] = []

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Gruppe und Einträge", "Zusatz"])
        self.tree.setColumnWidth(0, 330)
        self.tree.setMinimumHeight(230)
        self.tree.itemDoubleClicked.connect(lambda *_: self._edit())

        add_group = QPushButton("Gruppe")
        add_group.setIcon(icon("add", Color.GREEN))
        add_group.clicked.connect(self._add_group)

        add_entry = QPushButton("Eintrag")
        add_entry.setIcon(icon("add", Color.GREEN))
        add_entry.clicked.connect(self._add_entry)

        edit = QToolButton()
        edit.setIcon(icon("paragraph", Color.GREEN))
        edit.setToolTip("Bearbeiten")
        edit.clicked.connect(self._edit)

        remove = QToolButton()
        remove.setIcon(icon("remove", Color.ERROR))
        remove.setToolTip("Löschen")
        remove.clicked.connect(self._remove)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addWidget(add_group)
        bar.addWidget(add_entry)
        bar.addStretch(1)
        bar.addWidget(edit)
        bar.addWidget(remove)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.tree)
        layout.addLayout(bar)

    # -- Anzeige ----------------------------------------------------------- #

    def _refresh(self) -> None:
        self.tree.clear()
        for g, group in enumerate(self._groups):
            node = QTreeWidgetItem([group.get("title", ""), ""])
            node.setIcon(0, icon("chapters", Color.GREEN))
            node.setData(0, Qt.ItemDataRole.UserRole, ("group", g))
            for e, entry in enumerate(group.get("items", [])):
                child = QTreeWidgetItem([entry.get("title", entry.get("id", "")), entry.get("sub", "")])
                child.setIcon(0, icon("page", Color.INK_SOFT))
                child.setData(0, Qt.ItemDataRole.UserRole, ("entry", g, e))
                node.addChild(child)
            self.tree.addTopLevelItem(node)
        self.tree.expandAll()

    def _selection(self) -> tuple | None:
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    # -- Bedienung --------------------------------------------------------- #

    def _add_group(self) -> None:
        self._groups.append({"title": "Neue Gruppe", "items": []})
        self._refresh()
        self.changed.emit()

    def _add_entry(self) -> None:
        selection = self._selection()
        if selection is None:
            if not self._groups:
                self._add_group()
            group_index = len(self._groups) - 1
        else:
            group_index = selection[1]
        dialog = _ChapterEntryDialog(self._repo, self._lang, {}, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._groups[group_index].setdefault("items", []).append(dialog.entry)
            self._refresh()
            self.changed.emit()

    def _edit(self) -> None:
        selection = self._selection()
        if selection is None:
            return
        if selection[0] == "group":
            group = self._groups[selection[1]]
            text, ok = _ask_text(self, "Gruppe", "Überschrift der Gruppe", group.get("title", ""))
            if ok:
                group["title"] = text
                self._refresh()
                self.changed.emit()
            return
        _, g, e = selection
        dialog = _ChapterEntryDialog(self._repo, self._lang, self._groups[g]["items"][e], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._groups[g]["items"][e] = dialog.entry
            self._refresh()
            self.changed.emit()

    def _remove(self) -> None:
        selection = self._selection()
        if selection is None:
            return
        if selection[0] == "group":
            del self._groups[selection[1]]
        else:
            _, g, e = selection
            del self._groups[g]["items"][e]
        self._refresh()
        self.changed.emit()

    def value(self) -> list[dict[str, Any]]:
        return self._groups

    def set_value(self, value: Any) -> None:
        self._groups = [
            {"title": g.get("title", ""), "items": [dict(i) for i in g.get("items", [])]}
            for g in (value or [])
        ]
        self._refresh()


def _ask_text(parent: QWidget, title: str, label: str, value: str) -> tuple[str, bool]:
    from PySide6.QtWidgets import QInputDialog

    text, ok = QInputDialog.getText(parent, title, label, text=value)
    return text.strip(), ok
