"""Lesen und Schreiben der Inhaltsdateien ohne Formatierungsschaden.

Die 60 Dateien unter src/content/ sind von Hand gesetzt und dabei bewusst
uneinheitlich: 140 der 185 Überschriftenblöcke stehen einzeilig
(``{ "t": "h2", "text": "Sommer 1981" }``), 45 nicht; vor Überschriften und vor
``"blocks"`` steht meist, aber nicht immer eine Leerzeile.

Ein regelbasierter Formatierer trifft das nie. Würde der Editor stattdessen mit
``json.dumps`` schreiben, wälzte schon die kleinste Textänderung die ganze Datei
um – nur 15 der 60 Dateien sind mit dem Standardformat byte-identisch. Der
Betreiber sähe im Git-Diff nicht mehr, was er eigentlich geändert hat.

Deshalb liest der Parser hier die Formatierungsentscheidungen mit: für jeden
Knoten wird vermerkt, ob er einzeilig steht und ob eine Leerzeile davor liegt.
Beim Schreiben werden genau diese Entscheidungen wieder eingesetzt. Ergebnis:
Laden und Speichern einer unveränderten Datei liefert Byte für Byte dasselbe,
und eine geänderte Zeile erscheint im Diff als genau eine geänderte Zeile.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path as FsPath
from typing import Any

__all__ = [
    "JsonSyntaxError",
    "Style",
    "parse",
    "dump",
    "load_file",
    "save_file",
]

#: Pfad zu einem Knoten, z. B. ``("blocks", 3, "html")``.
NodePath = tuple[str | int, ...]

_WHITESPACE = " \t\n\r"


class JsonSyntaxError(ValueError):
    """Syntaxfehler mit Zeile, Spalte und Ort im Dokument.

    Die Angaben landen unverändert im Fehlerdialog, damit der Benutzer die
    Stelle findet, ohne JSON lesen zu müssen.
    """

    def __init__(self, message: str, text: str, pos: int, path: NodePath) -> None:
        self.line = text.count("\n", 0, pos) + 1
        self.column = pos - (text.rfind("\n", 0, pos) + 1) + 1
        self.path = path
        where = ".".join(str(p) for p in path) or "Dokumentanfang"
        super().__init__(f"Zeile {self.line}, Spalte {self.column} ({where}): {message}")


@dataclass
class Style:
    """Formatierung einer Datei, an Knotenpfaden festgemacht.

    ``inline``       Container, die im Quelltext auf einer Zeile stehen.
    ``blank_before`` Knoten, vor denen eine Leerzeile steht.
    ``indent``       Einrücktiefe der Datei. Die Inhaltsdateien rücken um zwei
                     Leerzeichen ein, src/image-manifest.json um eines – das
                     erzeugt tools/make-manifest.mjs mit ``JSON.stringify(…, 1)``.
    """

    inline: set[NodePath] = field(default_factory=set)
    blank_before: set[NodePath] = field(default_factory=set)
    indent: int = 2

    def child(self, path: NodePath) -> "Style":
        """Teilstil für einen Unterbaum – gebraucht beim Verschieben von Blöcken."""
        n = len(path)
        return Style(
            inline={p[n:] for p in self.inline if p[:n] == path},
            blank_before={p[n:] for p in self.blank_before if p[:n] == path},
            indent=self.indent,
        )

    def rebase(self, old: NodePath, new: NodePath) -> None:
        """Hängt einen Teilbaum um – nötig, wenn Blöcke verschoben werden."""
        for bucket in (self.inline, self.blank_before):
            n = len(old)
            moved = {p for p in bucket if p[:n] == old}
            bucket -= moved
            bucket |= {new + p[n:] for p in moved}


# --------------------------------------------------------------------------- #
# Lesen                                                                        #
# --------------------------------------------------------------------------- #


class _Parser:
    """Rekursiver Abstieg, der nebenbei die Formatierung protokolliert.

    Der eingebaute json-Parser liefert keine Quellpositionen; ohne die lässt
    sich nicht feststellen, welcher Block einzeilig geschrieben war.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.i = 0
        self.style = Style()

    # -- Hilfen ------------------------------------------------------------ #

    def _fail(self, message: str, path: NodePath) -> None:
        raise JsonSyntaxError(message, self.text, min(self.i, len(self.text) - 1), path)

    def _skip_ws(self) -> str:
        """Überspringt Weißraum und gibt ihn zurück (für die Leerzeilenerkennung)."""
        start = self.i
        while self.i < len(self.text) and self.text[self.i] in _WHITESPACE:
            self.i += 1
        return self.text[start : self.i]

    def _expect(self, ch: str, path: NodePath) -> None:
        if self.i >= len(self.text) or self.text[self.i] != ch:
            got = "Dateiende" if self.i >= len(self.text) else repr(self.text[self.i])
            self._fail(f"„{ch}“ erwartet, gefunden {got}", path)
        self.i += 1

    def _note_blank(self, ws: str, path: NodePath) -> None:
        # Zwei Zeilenumbrüche im Weißraum bedeuten: dazwischen lag eine Leerzeile.
        if ws.count("\n") >= 2:
            self.style.blank_before.add(path)

    # -- Werte ------------------------------------------------------------- #

    def parse_document(self) -> Any:
        self._skip_ws()
        value = self.parse_value(())
        self._skip_ws()
        if self.i != len(self.text):
            self._fail("überzähliger Text nach dem Ende des Dokuments", ())
        return value

    def parse_value(self, path: NodePath) -> Any:
        if self.i >= len(self.text):
            self._fail("Wert erwartet, Datei endet", path)
        ch = self.text[self.i]
        if ch == "{":
            return self._parse_object(path)
        if ch == "[":
            return self._parse_array(path)
        if ch == '"':
            return self._parse_string(path)
        return self._parse_literal(path)

    def _parse_object(self, path: NodePath) -> dict[str, Any]:
        start = self.i
        self._expect("{", path)
        out: dict[str, Any] = {}
        ws = self._skip_ws()
        if self.i < len(self.text) and self.text[self.i] == "}":
            self.i += 1
            self._mark_inline(path, start)
            return out
        while True:
            if self.i >= len(self.text) or self.text[self.i] != '"':
                self._fail("Feldname in Anführungszeichen erwartet", path)
            key = self._parse_string(path)
            key_path = path + (key,)
            self._note_blank(ws, key_path)
            self._skip_ws()
            self._expect(":", key_path)
            self._skip_ws()
            out[key] = self.parse_value(key_path)
            ws = self._skip_ws()
            if self.i < len(self.text) and self.text[self.i] == ",":
                self.i += 1
                ws = self._skip_ws()
                continue
            self._expect("}", path)
            break
        self._mark_inline(path, start)
        return out

    def _parse_array(self, path: NodePath) -> list[Any]:
        start = self.i
        self._expect("[", path)
        out: list[Any] = []
        ws = self._skip_ws()
        if self.i < len(self.text) and self.text[self.i] == "]":
            self.i += 1
            self._mark_inline(path, start)
            return out
        while True:
            item_path = path + (len(out),)
            self._note_blank(ws, item_path)
            out.append(self.parse_value(item_path))
            ws = self._skip_ws()
            if self.i < len(self.text) and self.text[self.i] == ",":
                self.i += 1
                ws = self._skip_ws()
                continue
            self._expect("]", path)
            break
        self._mark_inline(path, start)
        return out

    def _mark_inline(self, path: NodePath, start: int) -> None:
        if "\n" not in self.text[start : self.i]:
            self.style.inline.add(path)

    def _parse_string(self, path: NodePath) -> str:
        start = self.i
        self.i += 1  # öffnendes "
        while True:
            if self.i >= len(self.text):
                self._fail("Zeichenkette wird nicht geschlossen", path)
            ch = self.text[self.i]
            if ch == "\\":
                self.i += 2
                continue
            if ch == '"':
                self.i += 1
                break
            if ch == "\n":
                # Häufigster Erfassungsfehler: ein gerades " statt „ oder “
                # beendet die Zeichenkette und der Rest der Zeile kippt.
                self._fail(
                    "Zeilenumbruch in einer Zeichenkette – vermutlich ein "
                    'überzähliges Anführungszeichen (" statt „ oder “)',
                    path,
                )
            self.i += 1
        raw = self.text[start : self.i]
        try:
            return json.loads(raw)
        except ValueError as err:  # pragma: no cover - nur bei kaputten Escapes
            self.i = start
            self._fail(f"ungültige Zeichenkette: {err}", path)
            raise  # unerreichbar, beruhigt aber die Typprüfung

    def _parse_literal(self, path: NodePath) -> Any:
        start = self.i
        while self.i < len(self.text) and self.text[self.i] not in ",]}" + _WHITESPACE:
            self.i += 1
        raw = self.text[start : self.i]
        if not raw:
            self._fail("Wert erwartet", path)
        try:
            return json.loads(raw)
        except ValueError:
            self.i = start
            self._fail(f"unbekannter Wert „{raw}“", path)
            raise  # unerreichbar


def _detect_indent(text: str) -> int:
    """Einrücktiefe aus der ersten eingerückten Zeile ablesen."""
    for line in text.split("\n")[1:]:
        stripped = line.lstrip(" ")
        if stripped and stripped != line:
            return len(line) - len(stripped)
    return 2


def parse(text: str) -> tuple[Any, Style]:
    """Liest JSON und gibt Daten samt Formatierung zurück."""
    p = _Parser(text)
    data = p.parse_document()
    p.style.indent = _detect_indent(text)
    return data, p.style


# --------------------------------------------------------------------------- #
# Schreiben                                                                    #
# --------------------------------------------------------------------------- #


def _scalar(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def dump(data: Any, style: Style | None = None, *, indent: int | None = None) -> str:
    """Erzeugt JSON-Text in der Formatierung der Vorlage.

    Knoten ohne Eintrag in ``style`` werden mehrzeilig und ohne Leerzeile
    gesetzt – das ist die Form, die neu angelegte Blöcke bekommen.
    """
    style = style or Style()
    out: list[str] = []
    _write(out, data, style, (), 0, style.indent if indent is None else indent)
    return "".join(out) + "\n"


def _write(
    out: list[str],
    value: Any,
    style: Style,
    path: NodePath,
    depth: int,
    indent: int,
) -> None:
    if isinstance(value, dict):
        _write_container(out, list(value.items()), style, path, depth, indent, "{}", True)
    elif isinstance(value, list):
        _write_container(out, list(enumerate(value)), style, path, depth, indent, "[]", False)
    else:
        out.append(_scalar(value))


def _write_container(
    out: list[str],
    items: list[tuple[Any, Any]],
    style: Style,
    path: NodePath,
    depth: int,
    indent: int,
    braces: str,
    is_object: bool,
) -> None:
    open_b, close_b = braces
    if not items:
        out.append(open_b + close_b)
        return

    if path in style.inline:
        # Objekte werden innen ausgepolstert (`{ "t": "h2" }`), Arrays nicht
        # (`["impressum", "datenschutz"]`) – so steht es im Bestand.
        gap = " " if is_object else ""
        out.append(open_b + gap)
        for n, (key, val) in enumerate(items):
            if n:
                out.append(", ")
            if is_object:
                out.append(_scalar(key) + ": ")
            _write(out, val, style, path + (key,), depth, indent)
        out.append(gap + close_b)
        return

    pad = " " * (indent * (depth + 1))
    out.append(open_b + "\n")
    for n, (key, val) in enumerate(items):
        child = path + (key,)
        if n and child in style.blank_before:
            out.append("\n")
        out.append(pad)
        if is_object:
            out.append(_scalar(key) + ": ")
        _write(out, val, style, child, depth + 1, indent)
        out.append(",\n" if n < len(items) - 1 else "\n")
    out.append(" " * (indent * depth) + close_b)


# --------------------------------------------------------------------------- #
# Dateien                                                                      #
# --------------------------------------------------------------------------- #


def load_file(path: FsPath) -> tuple[Any, Style, str]:
    """Liest eine Datei und gibt Daten, Formatierung und Rohtext zurück."""
    text = path.read_text(encoding="utf-8")
    data, style = parse(text)
    return data, style, text


def save_file(path: FsPath, data: Any, style: Style | None = None) -> bool:
    """Schreibt nur, wenn sich der Inhalt wirklich ändert.

    Geschrieben wird atomar über eine Nachbardatei; ein Absturz mitten im
    Speichern kann so keine halbe Datei hinterlassen. Rückgabe: wurde
    geschrieben?
    """
    new_text = dump(data, style)
    if path.exists() and path.read_text(encoding="utf-8") == new_text:
        return False
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, path)
    return True
