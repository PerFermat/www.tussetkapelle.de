"""Verweise setzen, ohne eine Adresse zu tippen.

Interne Verweise laufen auf der Website über Seitenkennungen
(``{{href:emil-weber}}``), nicht über Pfade. Das ist absichtlich so: eine Seite
kann umziehen, ohne dass ein Verweis bricht. Der Benutzer sieht davon nichts –
er wählt hier eine Seite aus einer Liste.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..model import ContentRepository
from ..richtext import href_of
from .theme import Color, icon

__all__ = ["LinkDialog"]


class LinkDialog(QDialog):
    """Liefert die neue Zieladresse eines Verweises."""

    def __init__(
        self,
        repo: ContentRepository,
        lang: str,
        current_attrs: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Verweis")
        self.setMinimumSize(560, 480)
        self._repo = repo
        self._lang = lang
        self._result = ""

        current = href_of(current_attrs)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_pages(current), "Seite dieser Website")
        self.tabs.addTab(self._build_external(current), "Adresse im Internet")
        self.tabs.addTab(self._build_mail(current), "E-Mail")

        if current.startswith("mailto:"):
            self.tabs.setCurrentIndex(2)
        elif current.startswith(("http://", "https://")):
            self.tabs.setCurrentIndex(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Übernehmen")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self.remove_button = QPushButton("Verweis entfernen")
        self.remove_button.setIcon(icon("remove", Color.ERROR))
        self.remove_button.clicked.connect(self._remove)
        self.remove_button.setEnabled(bool(current))
        buttons.addButton(self.remove_button, QDialogButtonBox.ButtonRole.ResetRole)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)

    # -- Reiter ------------------------------------------------------------ #

    def _build_pages(self, current: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)

        hint = QLabel(
            "Der Verweis folgt der Seite auch dann, wenn ihre Adresse sich "
            "später ändert."
        )
        hint.setProperty("rolle", "hinweis")
        hint.setWordWrap(True)

        self.page_filter = QLineEdit()
        self.page_filter.setPlaceholderText("Seite suchen …")
        self.page_filter.setClearButtonEnabled(True)
        self.page_filter.textChanged.connect(self._filter_pages)

        self.page_list = QListWidget()
        self.page_list.itemDoubleClicked.connect(lambda _: self.accept())

        target = current[7:-2] if current.startswith("{{href:") else ""
        pages = self._repo.pages.get(self._lang, {})
        for page_id in self._repo.page_ids():
            entry = pages.get(page_id)
            if entry is None:
                continue
            item = QListWidgetItem(icon("page", Color.GREEN), entry.title)
            item.setData(Qt.ItemDataRole.UserRole, page_id)
            item.setToolTip(f"Kennung: {page_id}")
            self.page_list.addItem(item)
            if page_id == target:
                self.page_list.setCurrentItem(item)

        layout.addWidget(hint)
        layout.addWidget(self.page_filter)
        layout.addWidget(self.page_list, 1)
        return page

    def _filter_pages(self, text: str) -> None:
        needle = text.strip().casefold()
        for row in range(self.page_list.count()):
            item = self.page_list.item(row)
            haystack = f"{item.text()} {item.data(Qt.ItemDataRole.UserRole)}".casefold()
            item.setHidden(bool(needle) and needle not in haystack)

    def _build_external(self, current: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.url_edit = QLineEdit(current if current.startswith("http") else "")
        self.url_edit.setPlaceholderText("https://…")

        hint = QLabel(
            "Fremde Adressen öffnen sich beim Besucher automatisch in einem "
            "neuen Tab. Ein Zusatz ist nicht nötig."
        )
        hint.setProperty("rolle", "hinweis")
        hint.setWordWrap(True)

        layout.addWidget(QLabel("Vollständige Adresse"))
        layout.addWidget(self.url_edit)
        layout.addWidget(hint)
        layout.addStretch(1)
        return page

    def _build_mail(self, current: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.mail_edit = QLineEdit(current[7:] if current.startswith("mailto:") else "")
        self.mail_edit.setPlaceholderText("name@beispiel.de")

        row = QHBoxLayout()
        row.addWidget(QLabel("E-Mail-Adresse"))
        row.addStretch(1)

        layout.addLayout(row)
        layout.addWidget(self.mail_edit)
        layout.addStretch(1)
        return page

    # -- Ergebnis ---------------------------------------------------------- #

    def _remove(self) -> None:
        self._result = ""
        self.done(QDialog.DialogCode.Accepted)

    def accept(self) -> None:
        index = self.tabs.currentIndex()
        if index == 0:
            item = self.page_list.currentItem()
            self._result = f"{{{{href:{item.data(Qt.ItemDataRole.UserRole)}}}}}" if item else ""
        elif index == 1:
            url = self.url_edit.text().strip()
            if url and not url.startswith(("http://", "https://")):
                url = "https://" + url
            self._result = url
        else:
            mail = self.mail_edit.text().strip()
            self._result = f"mailto:{mail}" if mail else ""
        super().accept()

    @property
    def href(self) -> str:
        """Neue Adresse. Leer bedeutet: Verweis entfernen."""
        return self._result
