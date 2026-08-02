"""Der Seitenbaum links.

Die Hierarchie steht in den Seitendateien als ``parent``; die Reihenfolge unter
einer Elternseite kommt aus ``sequence`` der Sprachdatei. Beides zusammen ergibt
den Baum – und beides muss beim Verschieben mitgeführt werden, sonst stimmt
hinterher der Brotkrumenpfad oder das Blättern zwischen den Kapiteln nicht mehr.

Seiten, deren Kennung fest in Navigation und Vorlagen steht, tragen ein Schloss
und lassen sich nicht verschieben.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem, QWidget

from ..model import ContentRepository, Page
from .theme import Color, icon

__all__ = ["PageTree"]

_ROLE_ID = Qt.ItemDataRole.UserRole


class PageTree(QTreeWidget):
    page_selected = Signal(str)
    #: Seite wurde per Maus unter eine andere gehängt (Seite, neue Elternseite).
    page_moved = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setMinimumWidth(250)
        self.setIndentation(16)
        self.currentItemChanged.connect(self._on_current)
        self._repo: ContentRepository | None = None
        self._lang = "de"
        self._loading = False

    # -- Aufbau ------------------------------------------------------------ #

    def show_pages(self, repo: ContentRepository, lang: str, select: str | None = None) -> None:
        self._repo, self._lang = repo, lang
        self._loading = True
        self.clear()

        home = repo.page(lang, "home")
        root = self._make_item(home) if home else QTreeWidgetItem(["Startseite"])
        self.addTopLevelItem(root)
        self._add_children(root, "home")
        self.expandAll()
        self._loading = False

        if select:
            self.select_page(select)
        elif self.topLevelItemCount():
            self.setCurrentItem(root)

    def _add_children(self, parent_item: QTreeWidgetItem, parent_id: str) -> None:
        assert self._repo is not None
        for page in self._repo.children_of(self._lang, parent_id):
            item = self._make_item(page)
            parent_item.addChild(item)
            self._add_children(item, page.page_id)

    def _make_item(self, page: Page) -> QTreeWidgetItem:
        item = QTreeWidgetItem([page.nav_label])
        item.setData(0, _ROLE_ID, page.page_id)
        item.setIcon(0, icon(self._icon_for(page), Color.GREEN))

        flags = item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        if not page.is_renamable:
            flags &= ~Qt.ItemFlag.ItemIsDragEnabled
        item.setFlags(flags)

        tip = [page.title, f"Kennung: {page.page_id}", f"{len(page.blocks)} Abschnitte"]
        if page.is_generated:
            tip.append("Wird automatisch erzeugt – nur lesbar.")
            item.setForeground(0, QColor(Color.INK_SOFT))
            font = QFont()
            font.setItalic(True)
            item.setFont(0, font)
        elif not page.is_renamable:
            tip.append("Feste Seite: Kennung steht in Navigation und Vorlagen.")
        item.setToolTip(0, "\n".join(tip))
        return item

    @staticmethod
    def _icon_for(page: Page) -> str:
        if page.is_generated:
            return "lock"
        return {"home": "home", "hub": "pages", "gallery": "images"}.get(page.kind, "page")

    # -- Auswahl ----------------------------------------------------------- #

    def current_page_id(self) -> str | None:
        item = self.currentItem()
        return item.data(0, _ROLE_ID) if item else None

    def select_page(self, page_id: str) -> None:
        item = self._find(page_id)
        if item is not None:
            self.setCurrentItem(item)

    def _find(self, page_id: str) -> QTreeWidgetItem | None:
        stack = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        while stack:
            item = stack.pop()
            if item is None:
                continue
            if item.data(0, _ROLE_ID) == page_id:
                return item
            stack += [item.child(i) for i in range(item.childCount())]
        return None

    def _on_current(self, item: QTreeWidgetItem | None, _previous) -> None:
        if not self._loading and item is not None:
            page_id = item.data(0, _ROLE_ID)
            if page_id:
                self.page_selected.emit(page_id)

    # -- Verschieben ------------------------------------------------------- #

    def dropEvent(self, event) -> None:  # noqa: N802
        source = self.currentItem()
        target = self.itemAt(event.position().toPoint())
        if source is None or target is None or source is target:
            event.ignore()
            return
        page_id = source.data(0, _ROLE_ID)
        parent_id = target.data(0, _ROLE_ID)
        if not page_id or not parent_id:
            event.ignore()
            return
        # Der Baum wird nach der Änderung ohnehin neu aufgebaut; Qt soll die
        # Einträge nicht zusätzlich selbst umhängen.
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()
        self.page_moved.emit(page_id, parent_id)
