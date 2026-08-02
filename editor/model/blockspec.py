"""Beschreibung der Inhaltsbausteine in Klartext.

Diese Datei ist die einzige Stelle, an der ein Blocktyp beschrieben wird. Aus
ihr entstehen das Menü „Abschnitt hinzufügen“, die Eingabemaske, die
Zusammenfassung in der Blockliste und die Prüfung. Ein neuer Blocktyp bedeutet
später einen Eintrag hier – keinen neuen Dialog.

Die JSON-Namen (``t``, ``html``, ``src`` …) stehen ausschließlich hier. Weiter
oben in der Oberfläche kommen nur noch deutsche Bezeichnungen vor.
Gegengeprüft mit src/templates/blocks.mjs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

__all__ = ["FieldKind", "FieldSpec", "BlockSpec", "BLOCKS", "PAGE_FIELDS", "spec_for", "summarize"]


class FieldKind(Enum):
    """Art der Eingabe – bestimmt, welches Bedienelement die Maske zeigt."""

    RICH = "rich"  # Fließtext mit Fett, Kursiv, Link
    PLAIN = "plain"  # einzeilig, ohne Auszeichnung
    LONG = "long"  # mehrzeilig, ohne Auszeichnung
    BOOL = "bool"
    IMAGE = "image"
    CHOICE = "choice"
    INT = "int"
    TEXT_LIST = "text_list"  # ["…", "…"]
    TERM_LIST = "term_list"  # [{"term":…, "html":…}]
    FIGURE_LIST = "figure_list"  # [{"src":…, "alt":…, "caption":…}]
    TABLE = "table"  # head[] + rows[][]
    BLOCK_LIST = "block_list"  # verschachtelte Blöcke (Brief)
    CHAPTER_GROUPS = "chapter_groups"


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    kind: FieldKind
    required: bool = False
    help: str = ""
    choices: tuple[tuple[str, str], ...] = ()  # (Wert, Beschriftung)
    default: Any = None


@dataclass(frozen=True)
class BlockSpec:
    t: str
    label: str
    icon: str
    hint: str
    fields: tuple[FieldSpec, ...]
    summary_key: str = ""
    #: Blöcke, die der Benutzer nicht selbst anlegen soll (nur im Bestand gepflegt).
    creatable: bool = True

    def field(self, key: str) -> FieldSpec | None:
        return next((f for f in self.fields if f.key == key), None)

    def new(self) -> dict[str, Any]:
        """Leerer Block dieses Typs, bereit zum Ausfüllen."""
        out: dict[str, Any] = {"t": self.t}
        for f in self.fields:
            if f.default is not None:
                out[f.key] = f.default
            elif f.required:
                out[f.key] = [] if f.kind.name.endswith("LIST") else ""
        return out


# --------------------------------------------------------------------------- #
# Wiederkehrende Felder                                                        #
# --------------------------------------------------------------------------- #

_ANCHOR = FieldSpec(
    "id",
    "Sprungmarke",
    FieldKind.PLAIN,
    help="Optional. Erlaubt einen Link direkt auf diese Überschrift.",
)

_ALIGN = FieldSpec(
    "align",
    "Ausrichtung",
    FieldKind.CHOICE,
    choices=(("center", "zentriert"), ("left", "links"), ("right", "rechts")),
    default="center",
)


# --------------------------------------------------------------------------- #
# Die fünfzehn Blocktypen                                                      #
# --------------------------------------------------------------------------- #

BLOCKS: tuple[BlockSpec, ...] = (
    BlockSpec(
        "p",
        "Absatz",
        "paragraph",
        "Fließtext. Der häufigste Baustein.",
        (
            FieldSpec("html", "Text", FieldKind.RICH, required=True),
            FieldSpec(
                "lede",
                "Einleitungsabsatz",
                FieldKind.BOOL,
                help="Wird größer und in dunklerem Grün gesetzt.",
            ),
            FieldSpec(
                "lang",
                "Sprache des Absatzes",
                FieldKind.PLAIN,
                help="Nur ausfüllen, wenn der Absatz in einer anderen Sprache "
                "steht als die Seite, z. B. „cs“ für Tschechisch.",
            ),
        ),
        summary_key="html",
    ),
    BlockSpec(
        "h2",
        "Überschrift 2",
        "heading2",
        "Gliedert die Seite in Hauptabschnitte.",
        (FieldSpec("text", "Überschrift", FieldKind.RICH, required=True), _ANCHOR),
        summary_key="text",
    ),
    BlockSpec(
        "h3",
        "Überschrift 3",
        "heading3",
        "Untergliederung innerhalb eines Abschnitts.",
        (FieldSpec("text", "Überschrift", FieldKind.RICH, required=True), _ANCHOR),
        summary_key="text",
    ),
    BlockSpec(
        "fig",
        "Bild",
        "image",
        "Ein Bild mit Bildunterschrift.",
        (
            FieldSpec("src", "Bild", FieldKind.IMAGE, required=True),
            FieldSpec(
                "alt",
                "Bildbeschreibung",
                FieldKind.LONG,
                required=True,
                help="Was ist zu sehen? Wird blinden Besuchern vorgelesen und "
                "erscheint, wenn das Bild nicht lädt. Nicht die Bildunterschrift "
                "wiederholen.",
            ),
            FieldSpec("caption", "Bildunterschrift", FieldKind.RICH),
            _ALIGN,
            FieldSpec(
                "max",
                "Höchstbreite in Pixeln",
                FieldKind.INT,
                help="Optional. Zeigt das Bild kleiner als seine echte Breite. "
                "Größer wird es nie – dafür ist die Vorlage zu klein.",
            ),
            FieldSpec(
                "eager",
                "Sofort laden",
                FieldKind.BOOL,
                help="Nur für das erste Bild einer Seite sinnvoll.",
            ),
        ),
        summary_key="caption",
    ),
    BlockSpec(
        "figrow",
        "Bilderreihe",
        "images",
        "Mehrere Bilder nebeneinander.",
        (FieldSpec("items", "Bilder", FieldKind.FIGURE_LIST, required=True),),
    ),
    BlockSpec(
        "list",
        "Liste",
        "list",
        "Aufzählung mit Punkten oder Nummern.",
        (
            FieldSpec("items", "Einträge", FieldKind.TEXT_LIST, required=True),
            FieldSpec("ordered", "Nummeriert", FieldKind.BOOL),
        ),
    ),
    BlockSpec(
        "dl",
        "Begriffsliste",
        "deflist",
        "Begriff und Erläuterung, z. B. „Betreuerin: Frau Therese Friedsam“.",
        (FieldSpec("items", "Einträge", FieldKind.TERM_LIST, required=True),),
    ),
    BlockSpec(
        "table",
        "Tabelle",
        "table",
        "Echte Datentabelle mit Kopfzeile.",
        (
            FieldSpec("caption", "Tabellenüberschrift", FieldKind.PLAIN),
            FieldSpec("head", "Spaltenköpfe", FieldKind.TEXT_LIST, required=True),
            FieldSpec("rows", "Zeilen", FieldKind.TABLE, required=True),
        ),
        summary_key="caption",
    ),
    BlockSpec(
        "quote",
        "Zitat",
        "quote",
        "Hervorgehobener Wortlaut mit Quellenangabe.",
        (
            FieldSpec("html", "Wortlaut", FieldKind.RICH, required=True),
            FieldSpec("cite", "Quelle", FieldKind.PLAIN),
        ),
        summary_key="html",
    ),
    BlockSpec(
        "letter",
        "Brief",
        "letter",
        "Abgesetzter Brief mit Ort, Datum und Grußformel.",
        (
            FieldSpec("meta", "Ort und Datum", FieldKind.PLAIN),
            FieldSpec("blocks", "Brieftext", FieldKind.BLOCK_LIST, required=True),
            FieldSpec("sign", "Grußformel", FieldKind.PLAIN),
        ),
        summary_key="meta",
    ),
    BlockSpec(
        "note",
        "Hinweis",
        "note",
        "Abgesetzter Kasten für Anmerkungen der Redaktion.",
        (
            FieldSpec("title", "Überschrift", FieldKind.PLAIN),
            FieldSpec("html", "Text", FieldKind.RICH, required=True),
        ),
        summary_key="title",
    ),
    BlockSpec(
        "sources",
        "Quellen",
        "sources",
        "Quellenangabe am Ende eines Kapitels, klein gesetzt.",
        (FieldSpec("html", "Angabe", FieldKind.RICH, required=True),),
        summary_key="html",
    ),
    BlockSpec(
        "explain",
        "Erklärung",
        "explain",
        "Schweres Wort erklären. Nur in Leichter Sprache üblich.",
        (
            FieldSpec("word", "Wort", FieldKind.PLAIN, required=True),
            FieldSpec("html", "Erklärung", FieldKind.RICH, required=True),
        ),
        summary_key="word",
    ),
    BlockSpec(
        "chapters",
        "Kapitelübersicht",
        "chapters",
        "Verweist auf andere Seiten, gruppiert nach Themen.",
        (FieldSpec("groups", "Gruppen", FieldKind.CHAPTER_GROUPS, required=True),),
        creatable=False,
    ),
    BlockSpec(
        "station",
        "Kreuzwegstation",
        "station",
        "Bild und Text nebeneinander, für die vierzehn Stationen.",
        (
            FieldSpec("title", "Überschrift", FieldKind.RICH, required=True),
            FieldSpec("src", "Bild", FieldKind.IMAGE, required=True),
            FieldSpec("alt", "Bildbeschreibung", FieldKind.LONG, required=True),
            FieldSpec("html", "Text", FieldKind.RICH, required=True),
            FieldSpec(
                "flip",
                "Bild rechts",
                FieldKind.BOOL,
                help="Ohne Haken steht das Bild links.",
            ),
        ),
        summary_key="title",
    ),
)

_BY_TYPE = {b.t: b for b in BLOCKS}


# --------------------------------------------------------------------------- #
# Seitenkopf                                                                   #
# --------------------------------------------------------------------------- #

PAGE_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "title",
        "Titel der Seite",
        FieldKind.PLAIN,
        required=True,
        help="Erscheint als große Überschrift und im Reiter des Browsers.",
    ),
    FieldSpec("kicker", "Überzeile", FieldKind.PLAIN, help="Kleine Zeile über dem Titel."),
    FieldSpec("subtitle", "Untertitel", FieldKind.PLAIN),
    FieldSpec(
        "navLabel",
        "Beschriftung im Menü",
        FieldKind.PLAIN,
        required=True,
        help="Kurzform des Titels für Navigation und Brotkrumenpfad.",
    ),
    FieldSpec(
        "description",
        "Beschreibung für Suchmaschinen",
        FieldKind.LONG,
        required=True,
        help="Ein bis zwei Sätze, höchstens 160 Zeichen. Erscheint im "
        "Suchergebnis unter dem Titel.",
    ),
)


# --------------------------------------------------------------------------- #
# Hilfen                                                                       #
# --------------------------------------------------------------------------- #


def spec_for(t: str) -> BlockSpec | None:
    return _BY_TYPE.get(t)


_TAGS = re.compile(r"<[^>]+>")
_HREF = re.compile(r"\{\{href:([a-z0-9-]+)\}\}")


def summarize(block: dict[str, Any], limit: int = 90) -> str:
    """Einzeilige Vorschau für die Blockliste – ohne jedes Markup."""
    spec = spec_for(block.get("t", ""))
    raw = ""
    if spec and spec.summary_key:
        raw = str(block.get(spec.summary_key) or "")
    if not raw:
        for key in ("title", "text", "html", "word", "caption", "alt", "meta", "src"):
            if block.get(key):
                raw = str(block[key])
                break
    if not raw:
        items = block.get("items") or block.get("groups") or block.get("head") or []
        if items:
            first = items[0]
            raw = str(first.get("term") or first.get("title") or first.get("alt") or "")  \
                if isinstance(first, dict) else str(first)
            raw = f"{len(items)} Einträge – {raw}" if raw else f"{len(items)} Einträge"

    text = _HREF.sub("", _TAGS.sub("", raw))
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&gt;", ">")
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
