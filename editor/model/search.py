"""Volltextsuche über eine Sprachfassung des Inhalts.

Gesucht wird im **Lesetext**, nicht im Markup: Auszeichnung wird vor dem
Vergleich entfernt, Entities werden aufgelöst. Wer „Kapelle“ eingibt, soll nicht
auf ``class="kapelle"`` stoßen, und wer „href“ eingibt, soll gar nichts finden.

Die Reihenfolge der Treffer ist die Lesereihenfolge: Seiten in der Folge von
``page_ids()``, darin die Abschnitte von oben nach unten, darin die Felder in
der Reihenfolge der Inhaltsdatei. Nur so ergibt „zum nächsten Treffer“ einen
Sinn, der sich mit dem deckt, was der Benutzer auf dem Schirm sieht.

Je Feld wird höchstens **ein** Treffer gemeldet. Käme ein Wort in einem Absatz
dreimal vor, spränge der Editor sonst dreimal an dieselbe Stelle und wirkte
kaputt.

Dieses Modul kennt keine Oberfläche und lässt sich ohne Qt prüfen.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any

__all__ = ["Hit", "find", "plain"]

#: Schlüssel, deren Werte kein Lesetext sind: Art des Abschnitts, Bildpfad,
#: Ausrichtung, Symbolname, Sprungziel, Maße. Sie stünden sonst als Treffer in
#: der Liste, ohne dass jemand sie lesen könnte.
_NOT_TEXT = frozenset(
    {"t", "src", "img", "align", "icon", "to", "max", "type", "kind", "id",
     "w", "h", "parent", "slug", "match"}
)

#: Schlüssel auf Seitenebene, die zur Verwaltung gehören und nicht zum Inhalt.
#: Alles Übrige – auch ``hero``, ``tiles``, ``visit`` und ``timeline`` der
#: Startseite – ist Text, der gefunden werden soll.
_PAGE_PLUMBING = frozenset({"id", "type", "parent", "blocks", "slug", "_quelle"})

_TAG = re.compile(r"<[^>]+>")


def plain(value: str) -> str:
    """Auszeichnung entfernen, Entities auflösen, geschütztes Leerzeichen glätten."""
    return html.unescape(_TAG.sub(" ", value)).replace(" ", " ")


@dataclass(frozen=True)
class Hit:
    """Eine Fundstelle – genug, um im Editor dorthin zu springen."""

    page_id: str
    page_title: str
    #: Nummer des Abschnitts; -1 für Seiten ohne Abschnitte (Startseite, Galerie).
    block_index: int
    #: Feldname innerhalb des Abschnitts, für den Sprung in die Eingabemaske.
    field: str
    #: Textauszug rund um die Fundstelle, für die Anzeige.
    excerpt: str


def _texts(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Alle durchsuchbaren Stücke als (Feldname, Klartext).

    Verschachteltes wird mitgenommen – die Begriffe einer Definitionsliste, die
    Punkte einer Aufzählung, die Stationen eines Kreuzwegs. Als Feldname gilt
    dabei immer der **oberste** Schlüssel: nur den kennt die Eingabemaske, und
    nur dorthin lässt sich springen.
    """
    out: list[tuple[str, str]] = []

    def walk(top: str, key: str, value: Any) -> None:
        if isinstance(value, str):
            if key not in _NOT_TEXT:
                text = plain(value).strip()
                if text:
                    out.append((top, text))
        elif isinstance(value, dict):
            for k, v in value.items():
                walk(top, k, v)
        elif isinstance(value, list):
            for v in value:
                walk(top, key, v)

    for k, v in data.items():
        walk(k, k, v)
    return out


def _excerpt(text: str, pos: int, length: int, width: int = 60) -> str:
    """Textauszug um die Fundstelle, an den Rändern mit Auslassung."""
    start = max(0, pos - width // 2)
    end = min(len(text), pos + length + width // 2)
    stueck = " ".join(text[start:end].split())
    return ("… " if start else "") + stueck + (" …" if end < len(text) else "")


def find(repo: Any, needle: str, lang: str) -> list[Hit]:
    """Alle Fundstellen einer Sprachfassung, in Lesereihenfolge."""
    gesucht = needle.strip()
    if not gesucht:
        return []
    key = gesucht.casefold()

    hits: list[Hit] = []
    pages = repo.pages.get(lang, {})
    for page_id in repo.page_ids():
        page = pages.get(page_id)
        if page is None:
            continue

        titel = page.title

        # Zuerst die Seitenebene: Titel, Suchmaschinentext und – auf der
        # Startseite – das große Bild, die Kacheln, die Besuchskarte und die
        # Zeitleiste. Die stehen neben ``blocks`` und wären sonst unauffindbar,
        # obwohl der Editor sie bearbeitet.
        oben = {k: v for k, v in page.data.items() if k not in _PAGE_PLUMBING}
        quellen: list[tuple[int, dict[str, Any]]] = [(-1, oben)]
        quellen += list(enumerate(page.blocks))

        for index, data in quellen:
            for feld, text in _texts(data):
                pos = text.casefold().find(key)
                if pos >= 0:
                    hits.append(
                        Hit(page_id, titel, index, feld, _excerpt(text, pos, len(key)))
                    )
    return hits
