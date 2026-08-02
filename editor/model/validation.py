"""Prüft die Inhalte, bevor sie auf die Platte gehen.

Der Editor soll niemals einen Zustand speichern, an dem ``node build.js``
scheitert. Die Fehler hier bilden deshalb genau die Stellen ab, an denen der
Build abbricht: fehlender Adresseintrag, unbekanntes Bild, Verweis auf eine
Seite, die es nicht gibt.

Warnungen halten nichts auf, weisen aber auf Nachlässigkeiten hin, die erst
später auffallen – etwa eine fehlende Bildbeschreibung, die tools/check-links.mjs
nach dem Erzeugen bemängelt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from .blockspec import FieldKind, spec_for

if TYPE_CHECKING:  # pragma: no cover
    from .repository import ContentRepository

__all__ = ["Severity", "Problem", "validate"]

_HREF = re.compile(r"\{\{href:([^}]*)\}\}")

#: Länge, ab der Suchmaschinen die Beschreibung abschneiden.
MAX_DESCRIPTION = 160


class Severity(Enum):
    ERROR = "Fehler"
    WARNING = "Hinweis"


@dataclass(frozen=True)
class Problem:
    severity: Severity
    lang: str
    page_id: str
    message: str
    block_index: int | None = None
    field: str = ""

    @property
    def is_error(self) -> bool:
        return self.severity is Severity.ERROR

    def where(self) -> str:
        parts = [self.page_id]
        if self.block_index is not None:
            parts.append(f"Abschnitt {self.block_index + 1}")
        if self.field:
            parts.append(self.field)
        return " · ".join(parts)

    def __str__(self) -> str:
        return f"{self.severity.value}: {self.where()} – {self.message}"


def validate(repo: "ContentRepository") -> list[Problem]:
    """Prüft den gesamten Bestand und liefert alle Beanstandungen."""
    out: list[Problem] = []
    all_ids = {pid for pages in repo.pages.values() for pid in pages}

    for lang, pages in repo.pages.items():
        site = repo.sites[lang]
        known = site.known_ids()

        for page_id, page in sorted(pages.items()):
            def err(msg: str, idx: int | None = None, field: str = "") -> None:
                out.append(Problem(Severity.ERROR, lang, page_id, msg, idx, field))

            def warn(msg: str, idx: int | None = None, field: str = "") -> None:
                out.append(Problem(Severity.WARNING, lang, page_id, msg, idx, field))

            # -- Kopfdaten ------------------------------------------------- #
            if page_id not in known:
                err(
                    "Die Seite hat keine Adresse in der Sprachdatei. "
                    "Ohne Eintrag in „slugs“ bricht das Erzeugen ab."
                )
            for required in ("title", "navLabel", "description"):
                if not str(page.data.get(required, "")).strip():
                    err(f"Das Feld „{required}“ ist leer.", field=required)

            desc = str(page.data.get("description", ""))
            if len(desc) > MAX_DESCRIPTION:
                warn(
                    f"Die Beschreibung für Suchmaschinen ist {len(desc)} Zeichen lang. "
                    f"Ab {MAX_DESCRIPTION} Zeichen wird sie abgeschnitten.",
                    field="description",
                )

            parent = page.parent
            if parent and parent not in pages:
                err(f"Die übergeordnete Seite „{parent}“ gibt es nicht.", field="parent")
            elif parent and _has_cycle(pages, page_id):
                err("Die Seitenhierarchie dreht sich im Kreis.", field="parent")

            for other in repo.languages:
                if other != lang and page_id not in repo.pages.get(other, {}):
                    warn(
                        f"Die Seite fehlt in der Fassung „{repo.sites[other].label}“. "
                        "Der Sprachwechsler führt dort zur Startseite."
                    )

            # -- Bausteine ------------------------------------------------- #
            for idx, block in enumerate(page.blocks):
                out.extend(_check_block(repo, lang, page_id, idx, block, all_ids))

    return out


def _has_cycle(pages: dict[str, Any], start: str) -> bool:
    seen: set[str] = set()
    cur: str | None = start
    while cur:
        if cur in seen:
            return True
        seen.add(cur)
        page = pages.get(cur)
        cur = page.parent if page else None
    return False


def _check_block(
    repo: "ContentRepository",
    lang: str,
    page_id: str,
    idx: int,
    block: dict[str, Any],
    all_ids: set[str],
    prefix: str = "",
) -> list[Problem]:
    out: list[Problem] = []

    def err(msg: str, field: str = "") -> None:
        out.append(Problem(Severity.ERROR, lang, page_id, msg, idx, prefix + field))

    def warn(msg: str, field: str = "") -> None:
        out.append(Problem(Severity.WARNING, lang, page_id, msg, idx, prefix + field))

    t = block.get("t", "")
    spec = spec_for(t)
    if spec is None:
        err(f"Unbekannte Art von Abschnitt: „{t}“.")
        return out

    for fs in spec.fields:
        value = block.get(fs.key)
        if fs.required and not _filled(value):
            err(f"„{fs.label}“ muss ausgefüllt sein.", fs.key)

        if fs.kind is FieldKind.IMAGE and value and value not in repo.manifest:
            err(
                f"Das Bild „{value}“ steht nicht im Bildbestand. "
                "Neue Bilder kommen über das Bilder-Werkzeug dazu.",
                fs.key,
            )
        if fs.kind is FieldKind.FIGURE_LIST and isinstance(value, list):
            for n, item in enumerate(value):
                src = item.get("src", "")
                if src and src not in repo.manifest:
                    err(f"Bild {n + 1}: „{src}“ steht nicht im Bildbestand.", fs.key)
                if not str(item.get("alt", "")).strip():
                    warn(f"Bild {n + 1} hat keine Bildbeschreibung.", fs.key)
        if fs.kind is FieldKind.BLOCK_LIST and isinstance(value, list):
            for n, inner in enumerate(value):
                out.extend(
                    _check_block(
                        repo, lang, page_id, idx, inner, all_ids, f"{fs.key}[{n + 1}]."
                    )
                )

    if t in ("fig", "station") and not str(block.get("alt", "")).strip():
        warn("Ohne Bildbeschreibung ist das Bild für blinde Besucher stumm.", "alt")

    for target in _links_in(block):
        if target not in all_ids:
            err(f"Der Verweis zeigt auf die Seite „{target}“, die es nicht gibt.")

    return out


def _filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _links_in(value: Any) -> set[str]:
    """Alle {{href:…}}-Ziele in einem Baustein, beliebig tief."""
    found: set[str] = set()
    if isinstance(value, str):
        found.update(_HREF.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            found |= _links_in(v)
    elif isinstance(value, list):
        for v in value:
            found |= _links_in(v)
    return found
