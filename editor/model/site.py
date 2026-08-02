"""Navigation, Adressen und Oberflächentexte einer Sprachfassung.

Entspricht src/content/site.<lang>.json. Wichtig ist vor allem, dass jede
Seitenkennung in ``slugs`` steht – ohne Eintrag bricht build.js ab
(„Kein Slug für … in site.de.json“).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path as FsPath
from typing import Any

from .jsonio import Style

__all__ = ["SiteConfig"]


@dataclass
class SiteConfig:
    lang: str
    path: FsPath
    data: dict[str, Any]
    style: Style
    dirty: bool = field(default=False, compare=False)

    # -- Stammdaten -------------------------------------------------------- #

    @property
    def label(self) -> str:
        return str(self.data.get("label", self.lang))

    @property
    def slugs(self) -> dict[str, str]:
        return self.data.setdefault("slugs", {})

    @property
    def nav(self) -> list[dict[str, Any]]:
        return self.data.setdefault("nav", [])

    @property
    def sequence(self) -> list[str]:
        return self.data.setdefault("sequence", [])

    @property
    def footer_links(self) -> list[str]:
        return self.data.setdefault("footerLinks", [])

    @property
    def ui(self) -> dict[str, str]:
        return self.data.setdefault("ui", {})

    # -- Kennungen pflegen -------------------------------------------------- #

    def known_ids(self) -> set[str]:
        return set(self.slugs)

    def add_slug(self, page_id: str, slug: str) -> None:
        self.slugs[page_id] = slug
        self.dirty = True

    def rename_id(self, old: str, new: str) -> None:
        """Kennung an allen Stellen dieser Sprachdatei ersetzen.

        Betroffen sind slugs (samt dem Adressbestandteil selbst), die
        Navigationsgruppen, die Kapitelfolge und die Fußzeile. Wird eine davon
        vergessen, verschwindet die Seite aus dem Menü oder der Build bricht ab.
        """
        if old not in self.slugs:
            return
        # Reihenfolge der Adressen erhalten – sie bestimmt nichts, liest sich
        # aber wie die Seitenkarte des Projekts.
        rebuilt: dict[str, str] = {}
        for key, slug in self.slugs.items():
            if key == old:
                rebuilt[new] = self._slug_renamed(slug, old, new)
            else:
                rebuilt[key] = self._slug_reparented(slug, old, new)
        self.data["slugs"] = rebuilt

        for group in self.nav:
            if group.get("id") == old:
                group["id"] = new
            for panel in group.get("panel", []):
                panel["items"] = [new if i == old else i for i in panel.get("items", [])]

        self.data["sequence"] = [new if i == old else i for i in self.sequence]
        self.data["footerLinks"] = [new if i == old else i for i in self.footer_links]
        self.dirty = True

    @staticmethod
    def _slug_renamed(slug: str, old: str, new: str) -> str:
        parts = slug.split("/")
        if parts and parts[-1] == old:
            parts[-1] = new
        return "/".join(parts)

    @staticmethod
    def _slug_reparented(slug: str, old: str, new: str) -> str:
        """Adressen von Unterseiten folgen der umbenannten Elternseite."""
        parts = slug.split("/")
        return "/".join(new if p == old else p for p in parts)

    def remove_id(self, page_id: str) -> None:
        self.slugs.pop(page_id, None)
        for group in list(self.nav):
            for panel in group.get("panel", []):
                panel["items"] = [i for i in panel.get("items", []) if i != page_id]
            if group.get("id") == page_id:
                self.nav.remove(group)
        self.data["sequence"] = [i for i in self.sequence if i != page_id]
        self.data["footerLinks"] = [i for i in self.footer_links if i != page_id]
        self.dirty = True

    def insert_into_sequence(self, page_id: str, after: str | None) -> None:
        seq = self.sequence
        if page_id in seq:
            seq.remove(page_id)
        if after and after in seq:
            seq.insert(seq.index(after) + 1, page_id)
        else:
            seq.append(page_id)
        self.dirty = True

    def nav_group_containing(self, page_id: str) -> dict[str, Any] | None:
        for group in self.nav:
            for panel in group.get("panel", []):
                if page_id in panel.get("items", []):
                    return panel
        return None
