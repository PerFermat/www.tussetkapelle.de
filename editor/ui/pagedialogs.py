"""Dialoge für Seiten: anlegen, umbenennen, löschen.

Alle drei Vorgänge fassen mehrere Dateien gleichzeitig an. Die Dialoge zeigen
deshalb vorher, was geschehen wird – besonders beim Löschen, wo auch Verweise
anderer Seiten betroffen sein können.
"""

from __future__ import annotations

import re
import unicodedata

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..model import ContentRepository, NewPage
from .theme import Color

__all__ = ["NewPageDialog", "RenamePageDialog", "slugify"]


def slugify(text: str) -> str:
    """Macht aus einem Titel eine Kennung: „Die neue Kapelle“ → „die-neue-kapelle“."""
    lowered = text.strip().casefold()
    for source, target in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        lowered = lowered.replace(source, target)
    ascii_text = unicodedata.normalize("NFKD", lowered).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_text)).strip("-")


class NewPageDialog(QDialog):
    """Legt eine Seite in allen drei Sprachen an."""

    def __init__(
        self, repo: ContentRepository, parent_id: str = "home", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Neue Seite")
        self.setMinimumWidth(560)
        self._repo = repo
        self._touched_id = False

        self.titles: dict[str, QLineEdit] = {}
        form = QFormLayout()
        form.setSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        for lang in repo.languages:
            edit = QLineEdit()
            edit.setPlaceholderText("Titel der Seite")
            self.titles[lang] = edit
            form.addRow(repo.sites[lang].label, edit)
        first = repo.languages[0]
        self.titles[first].textChanged.connect(self._suggest_id)

        self.parent_combo = QComboBox()
        pages = repo.pages.get(first, {})
        for page_id in repo.page_ids():
            page = pages.get(page_id)
            if page is not None:
                self.parent_combo.addItem(page.title, page_id)
        index = self.parent_combo.findData(parent_id)
        self.parent_combo.setCurrentIndex(max(index, 0))
        form.addRow("Untergeordnet zu", self.parent_combo)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("wird aus dem Titel gebildet")
        self.id_edit.textEdited.connect(lambda: setattr(self, "_touched_id", True))
        self.id_edit.textChanged.connect(self._update_preview)
        form.addRow("Kennung", self.id_edit)

        self.preview = QLabel()
        self.preview.setProperty("rolle", "hinweis")
        self.preview.setWordWrap(True)

        hint = QLabel(
            "Die Seite entsteht in allen drei Sprachfassungen. Fehlte sie in "
            "einer, führte der Sprachwechsler dort auf die Startseite."
        )
        hint.setProperty("rolle", "hinweis")
        hint.setWordWrap(True)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Seite anlegen")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addWidget(self.preview)
        layout.addWidget(hint)
        layout.addWidget(self.buttons)

        self.parent_combo.currentIndexChanged.connect(self._update_preview)
        self._update_preview()

    def _suggest_id(self, text: str) -> None:
        if not self._touched_id:
            self.id_edit.setText(slugify(text))

    def _update_preview(self) -> None:
        page_id = self.id_edit.text().strip()
        parent_id = self.parent_combo.currentData()
        ok = bool(page_id)
        if ok:
            try:
                self._repo.check_new_id(page_id)
            except Exception as err:  # noqa: BLE001 - Meldung geht in die Anzeige
                self.preview.setText(f"<span style='color:{Color.ERROR}'>{err}</span>")
                ok = False
            else:
                slug = self._repo.sites[self._repo.languages[0]].slugs.get(parent_id, "")
                address = f"/{slug}/{page_id}/" if slug else f"/{page_id}/"
                self.preview.setText(f"Adresse der Seite: <b>{address}</b>")
        else:
            self.preview.setText("Bitte einen Titel eingeben.")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)

    @property
    def spec(self) -> NewPage:
        return NewPage(
            page_id=self.id_edit.text().strip(),
            parent=self.parent_combo.currentData(),
            titles={lang: edit.text().strip() for lang, edit in self.titles.items()},
        )


class RenamePageDialog(QDialog):
    """Ändert die Kennung – und damit die Adresse – einer Seite."""

    def __init__(
        self, repo: ContentRepository, page_id: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Seite umbenennen")
        self.setMinimumWidth(560)
        self._repo = repo
        self._old = page_id

        self.id_edit = QLineEdit(page_id)
        self.id_edit.textChanged.connect(self._update)

        form = QFormLayout()
        form.setSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.addRow("Neue Kennung", self.id_edit)

        referrers = repo.referrers(page_id)
        self.info = QLabel()
        self.info.setProperty("rolle", "hinweis")
        self.info.setWordWrap(True)

        warning = QLabel(
            "Die Adresse der Seite ändert sich. Verweise innerhalb der Website "
            f"werden mitgeführt ({len(referrers)} betroffen). Wer die alte "
            "Adresse als Lesezeichen hat, landet danach auf der Fehlerseite."
        )
        warning.setProperty("rolle", "hinweis")
        warning.setWordWrap(True)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Umbenennen")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addWidget(self.info)
        layout.addWidget(warning)
        layout.addWidget(self.buttons)
        self._update()

    def _update(self) -> None:
        new_id = self.id_edit.text().strip()
        ok = bool(new_id) and new_id != self._old
        if not new_id:
            self.info.setText("Bitte eine Kennung eingeben.")
        elif new_id == self._old:
            self.info.setText("Die Kennung ist unverändert.")
        else:
            try:
                self._repo.check_new_id(new_id)
            except Exception as err:  # noqa: BLE001
                self.info.setText(f"<span style='color:{Color.ERROR}'>{err}</span>")
                ok = False
            else:
                lang = self._repo.languages[0]
                old_slug = self._repo.sites[lang].slugs.get(self._old, "")
                new_slug = "/".join(
                    new_id if part == self._old else part for part in old_slug.split("/")
                )
                self.info.setText(f"Neue Adresse: <b>/{new_slug}/</b>")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)

    @property
    def new_id(self) -> str:
        return self.id_edit.text().strip()
