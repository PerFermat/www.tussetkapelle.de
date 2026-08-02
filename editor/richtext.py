"""Fließtext bearbeiten, ohne HTML zu sehen.

Die Inhaltsdateien enthalten an einigen Stellen Auszeichnung – aber nur eine
sehr kleine, geschlossene Menge. Gezählt über den gesamten Bestand:
80 Verweise, 38 Fettungen, 34 Zeilenumbrüche, 8 Kursivsetzungen, 2 fremdsprachige
Einschübe, dazu 207 geschützte Leerzeichen. Verschachtelt wird nur ``a > strong``
und ``a > em``.

Deshalb genügt hier ein sehr kleiner, exakter Umsetzer statt eines allgemeinen
HTML-Editors. Er hat eine Bedingung zu erfüllen, an der alles hängt: Text, der
unverändert bleibt, muss auch als Zeichenkette unverändert wieder herauskommen.
Sonst zeigte das Git-Diff nach jeder Bearbeitung Dutzende Zeilen, die niemand
angefasst hat.

Erreicht wird das dadurch, dass die **rohen Attributtexte** der Tags mitgeführt
werden, nicht bloß deren ausgewertete Bedeutung: ``rel="noopener noreferrer"``
bleibt so erhalten, obwohl build.js es ohnehin selbst ergänzt.

Interne Verweise stehen in den Dateien als ``{{href:emil-weber}}``. In der
Oberfläche sieht der Benutzer davon nichts – nur den Verweistext und im
Verweisdialog den Seitentitel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

from PySide6.QtGui import (
    QColor,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)

__all__ = [
    "PROP_ANCHOR",
    "PROP_SPAN",
    "LINE_SEPARATOR",
    "NBSP",
    "html_to_document",
    "document_to_html",
    "plain_text",
    "make_anchor_attrs",
    "href_of",
    "LINK_COLOR",
]

#: Roher Attributtext des umgebenden ``<a>``, z. B. ``' href="{{href:kontakt}}"'``.
PROP_ANCHOR = QTextFormat.Property.UserProperty + 1
#: Roher Attributtext eines ``<span>``, z. B. ``' lang="en"'``.
PROP_SPAN = QTextFormat.Property.UserProperty + 2

#: Zeilenumbruch innerhalb eines Absatzes – entspricht ``<br>``.
LINE_SEPARATOR = " "
NBSP = " "

#: Dasselbe Gold wie auf der Website (--tk-gold-text).
LINK_COLOR = QColor("#8A6F32")

_HREF_ATTR = re.compile(r'href="([^"]*)"')
_INTERNAL = re.compile(r"^\{\{href:([a-z0-9-]+)\}\}$")


# --------------------------------------------------------------------------- #
# HTML → Dokument                                                              #
# --------------------------------------------------------------------------- #


class _Reader(HTMLParser):
    """Baut aus der HTML-Teilmenge ein Textdokument auf.

    ``convert_charrefs=False``: die Entities werden selbst behandelt, damit
    ``&nbsp;`` als geschütztes Leerzeichen und nicht als gewöhnliches ankommt.
    """

    def __init__(self, cursor: QTextCursor) -> None:
        super().__init__(convert_charrefs=False)
        self.cursor = cursor
        self.bold = 0
        self.italic = 0
        self.anchor: str | None = None
        self.span: str | None = None

    # -- Format ------------------------------------------------------------ #

    def _format(self) -> QTextCharFormat:
        fmt = QTextCharFormat()
        if self.bold:
            fmt.setFontWeight(700)
        if self.italic:
            fmt.setFontItalic(True)
        if self.anchor is not None:
            fmt.setProperty(PROP_ANCHOR, self.anchor)
            fmt.setForeground(LINK_COLOR)
            fmt.setFontUnderline(True)
        if self.span is not None:
            fmt.setProperty(PROP_SPAN, self.span)
            fmt.setFontItalic(True)
        return fmt

    def _insert(self, text: str) -> None:
        if text:
            self.cursor.insertText(text, self._format())

    # -- Ereignisse -------------------------------------------------------- #

    def handle_starttag(self, tag: str, attrs: list) -> None:  # noqa: ARG002
        raw = self._raw_attrs()
        if tag == "strong":
            self.bold += 1
        elif tag == "em":
            self.italic += 1
        elif tag == "a":
            self.anchor = raw
        elif tag == "span":
            self.span = raw
        elif tag == "br":
            self._insert(LINE_SEPARATOR)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        if tag == "br":
            self._insert(LINE_SEPARATOR)
        else:  # pragma: no cover - im Bestand nicht vorhanden
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "strong":
            self.bold = max(0, self.bold - 1)
        elif tag == "em":
            self.italic = max(0, self.italic - 1)
        elif tag == "a":
            self.anchor = None
        elif tag == "span":
            self.span = None

    def handle_data(self, data: str) -> None:
        self._insert(data)

    def handle_entityref(self, name: str) -> None:
        self._insert({"nbsp": NBSP, "amp": "&", "gt": ">", "lt": "<", "quot": '"'}.get(name, f"&{name};"))

    def handle_charref(self, name: str) -> None:  # pragma: no cover - nicht im Bestand
        try:
            self._insert(chr(int(name[1:], 16) if name[:1].lower() == "x" else int(name)))
        except ValueError:
            self._insert(f"&#{name};")

    def _raw_attrs(self) -> str:
        """Attributtext, genau so wie er in der Datei steht."""
        text = self.get_starttag_text() or ""
        inner = text[1:-1].rstrip("/")  # ohne < und >
        return inner[len(inner.split(" ", 1)[0]) :] if " " in inner else ""


def html_to_document(html: str, doc: QTextDocument | None = None) -> QTextDocument:
    """Wandelt gespeicherten Text in ein bearbeitbares Dokument."""
    doc = doc or QTextDocument()
    doc.clear()
    cursor = QTextCursor(doc)
    reader = _Reader(cursor)
    reader.feed(html or "")
    reader.close()
    return doc


# --------------------------------------------------------------------------- #
# Dokument → HTML                                                              #
# --------------------------------------------------------------------------- #


def _escape(text: str) -> str:
    """Text absichern und Sonderzeichen zurückschreiben.

    Nur ``&``, ``<``, ``>`` und das geschützte Leerzeichen werden umgesetzt –
    genau die Zeichen, die im Bestand als Entity stehen. Umlaute bleiben
    Umlaute; die Dateien sind UTF-8.
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace(NBSP, "&nbsp;")
        .replace(LINE_SEPARATOR, "<br>")
    )


@dataclass
class _State:
    anchor: str | None = None
    span: str | None = None
    bold: bool = False
    italic: bool = False

    @classmethod
    def of(cls, fmt: QTextCharFormat) -> "_State":
        anchor = fmt.property(PROP_ANCHOR)
        span = fmt.property(PROP_SPAN)
        return cls(
            anchor=anchor if isinstance(anchor, str) else None,
            span=span if isinstance(span, str) else None,
            bold=fmt.fontWeight() >= 700,
            # Der fremdsprachige Einschub wird kursiv dargestellt, ist aber
            # keine Kursivsetzung im Text – sonst entstünde ein <em> zu viel.
            italic=fmt.fontItalic() and not isinstance(span, str),
        )


def document_to_html(doc: QTextDocument) -> str:
    """Erzeugt wieder genau die HTML-Teilmenge, aus der das Dokument entstand.

    Die Reihenfolge der Tags ist festgelegt: ``a`` außen, darin ``span``, darin
    ``strong``, darin ``em``. So steht es auch im Bestand – dort kommen nur
    ``a > strong`` und ``a > em`` vor.
    """
    out: list[str] = []
    state = _State()

    def close_to(new: _State) -> None:
        if state.italic and not new.italic:
            out.append("</em>")
        if state.bold and not new.bold:
            out.append("</strong>")
        if state.span is not None and state.span != new.span:
            out.append("</span>")
        if state.anchor is not None and state.anchor != new.anchor:
            out.append("</a>")

    def open_from(new: _State) -> None:
        if new.anchor is not None and new.anchor != state.anchor:
            out.append(f"<a{new.anchor}>")
        if new.span is not None and new.span != state.span:
            out.append(f"<span{new.span}>")
        if new.bold and not state.bold:
            out.append("<strong>")
        if new.italic and not state.italic:
            out.append("<em>")

    block = doc.begin()
    first_block = True
    while block.isValid():
        if not first_block:
            # Ein neuer Absatz im Editor ist innerhalb eines Bausteins ein
            # Zeilenumbruch – eigene Absätze legt der Benutzer als eigene
            # Bausteine an.
            close_to(_State())
            state = _State()
            out.append("<br>")
        first_block = False

        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid():
                new = _State.of(fragment.charFormat())
                # Beim Wechsel des Verweises müssen auch die inneren Tags zu,
                # sonst entstünde </a> vor </strong>.
                if new.anchor != state.anchor or new.span != state.span:
                    close_to(_State())
                    state = _State()
                close_to(new)
                open_from(new)
                state = new
                out.append(_escape(fragment.text()))
            it += 1
        block = block.next()

    close_to(_State())
    return "".join(out)


def plain_text(html: str) -> str:
    """Reiner Text ohne Auszeichnung – für Vorschauen und Suche."""
    text = re.sub(r"<[^>]+>", "", html or "")
    for entity, char in (("&nbsp;", " "), ("&amp;", "&"), ("&gt;", ">"), ("&lt;", "<")):
        text = text.replace(entity, char)
    return " ".join(text.split())


# --------------------------------------------------------------------------- #
# Verweise                                                                     #
# --------------------------------------------------------------------------- #


def href_of(attrs: str) -> str:
    """Zieladresse aus einem rohen Attributtext."""
    m = _HREF_ATTR.search(attrs or "")
    return m.group(1) if m else ""


def internal_target(attrs: str) -> str | None:
    """Seitenkennung, falls der Verweis auf eine eigene Seite zeigt."""
    m = _INTERNAL.match(href_of(attrs))
    return m.group(1) if m else None


def make_anchor_attrs(href: str, *, keep: str = "") -> str:
    """Baut den Attributtext eines Verweises.

    Ein vorhandener Attributtext wird nur an der Adresse geändert; alles
    andere – etwa ein ``rel`` aus dem Bestand – bleibt stehen. ``target`` und
    ``rel`` setzt build.js bei Außenlinks ohnehin selbst.
    """
    if keep and _HREF_ATTR.search(keep):
        return _HREF_ATTR.sub(lambda _: f'href="{href}"', keep, count=1)
    return f' href="{href}"'
