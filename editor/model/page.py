"""Eine Seite und ihre Bausteine.

Die Klasse hält bewusst das rohe Wörterbuch der JSON-Datei und keine
ausmodellierte Kopie: nur so überleben Schlüssel, die der Editor nicht kennt
(``_quelle``, ``_hinweis``, ``_erzeugt``) und die Sonderformate von
Startseite und Galerie das Speichern unverändert.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path as FsPath
from typing import Any

from .jsonio import Style

__all__ = ["Page", "PageKind"]

#: Seiten, deren Kennung fest in Navigation, Fußzeile oder Vorlagen steht.
FIXED_IDS = frozenset(
    {"home", "geschichte", "galerie", "besuch", "kontakt", "impressum", "datenschutz"}
)


class PageKind:
    ARTICLE = "article"
    HOME = "home"
    HUB = "hub"
    GALLERY = "gallery"


@dataclass
class Page:
    lang: str
    page_id: str
    path: FsPath
    data: dict[str, Any]
    style: Style
    dirty: bool = field(default=False, compare=False)

    # -- Kopfdaten --------------------------------------------------------- #

    @property
    def kind(self) -> str:
        return str(self.data.get("type", PageKind.ARTICLE))

    @property
    def title(self) -> str:
        return str(self.data.get("title") or self.page_id)

    @property
    def nav_label(self) -> str:
        return str(self.data.get("navLabel") or self.title)

    @property
    def parent(self) -> str | None:
        p = self.data.get("parent")
        return str(p) if p else None

    @parent.setter
    def parent(self, value: str | None) -> None:
        if value:
            self.data["parent"] = value
        else:
            self.data.pop("parent", None)

    # -- Bausteine --------------------------------------------------------- #

    @property
    def blocks(self) -> list[dict[str, Any]]:
        """Blockliste. Startseite und Galerie haben keine – dann leer."""
        return self.data.get("blocks") or []

    @property
    def has_blocks(self) -> bool:
        return isinstance(self.data.get("blocks"), list)

    # -- Sperren ----------------------------------------------------------- #

    @property
    def is_generated(self) -> bool:
        """Erzeugte Datei – wird von einem Werkzeug überschrieben.

        Die Galerieseiten entstehen aus tools/make-gallery.mjs. Sie hier zu
        bearbeiten wäre vergebliche Mühe, der nächste Lauf machte es zunichte.
        """
        return "_erzeugt" in self.data

    @property
    def is_renamable(self) -> bool:
        return self.page_id not in FIXED_IDS

    @property
    def read_only(self) -> bool:
        return self.is_generated

    def lock_reason(self) -> str:
        if self.is_generated:
            return (
                "Diese Seite wird automatisch erzeugt. Änderungen hier gingen "
                "beim nächsten Erzeugen der Bildergalerie verloren. Die Bilder "
                "und Bildunterschriften stammen aus dem Bildbestand."
            )
        return ""

    def __repr__(self) -> str:  # pragma: no cover - Diagnose
        return f"<Page {self.lang}/{self.page_id} {len(self.blocks)} Blöcke>"
