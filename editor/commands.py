"""Rückgängig und Wiederholen.

Jede Änderung an einer Seite läuft über einen Befehl. Das kostet etwas
Umstand, ist aber der einzige Weg, dem Benutzer ein verlässliches „Strg+Z“ zu
geben – und das braucht er, denn er arbeitet an unersetzlichen Texten.

Die Bausteine werden beim Rückgängigmachen als tiefe Kopie zurückgeschrieben.
Eine flache Kopie genügte nicht: Listen und verschachtelte Bausteine wären
sonst weiterhin dasselbe Objekt wie im Editor.
"""

from __future__ import annotations

import copy
from typing import Any, Callable

from PySide6.QtGui import QUndoCommand

from .model import Page

__all__ = ["EditBlockCommand", "AddBlockCommand", "RemoveBlockCommand", "MoveBlockCommand"]


class _PageCommand(QUndoCommand):
    """Grundlage: merkt sich Seite und Rückruf zum Auffrischen der Anzeige."""

    def __init__(self, page: Page, refresh: Callable[[int], None], text: str) -> None:
        super().__init__(text)
        self.page = page
        self.refresh = refresh

    def _blocks(self) -> list[dict[str, Any]]:
        return self.page.data.setdefault("blocks", [])

    def _done(self, select: int) -> None:
        self.page.dirty = True
        self.refresh(select)


class EditBlockCommand(_PageCommand):
    """Ein Baustein wurde bearbeitet.

    Aufeinanderfolgende Änderungen am selben Baustein werden zusammengefasst,
    damit „Rückgängig“ nicht Buchstabe für Buchstabe zurückgeht.

    ``already_applied`` gilt beim Tippen: der Baustein trägt die Änderung dann
    bereits. Das erste ``redo()`` darf sie nicht noch einmal anwenden und die
    Blockliste nicht mitten in der Eingabe neu aufbauen – der Schreibfokus
    ginge verloren. Vermerkt wird die Änderung trotzdem sofort, sonst hielte
    der Editor die Datei fälschlich für gespeichert.
    """

    ID = 1001

    def __init__(
        self,
        page: Page,
        index: int,
        before: dict[str, Any],
        after: dict[str, Any],
        refresh: Callable[[int], None],
        *,
        already_applied: bool = False,
    ) -> None:
        super().__init__(page, refresh, "Abschnitt bearbeiten")
        self.index = index
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)
        self._skip_redo = already_applied

    def id(self) -> int:  # noqa: A003
        return self.ID

    def mergeWith(self, other: QUndoCommand) -> bool:  # noqa: N802
        if not isinstance(other, EditBlockCommand) or other.index != self.index:
            return False
        if other.page is not self.page:
            return False
        self.after = other.after
        return True

    def redo(self) -> None:
        if self._skip_redo:
            self._skip_redo = False
            self.page.dirty = True
            return
        blocks = self._blocks()
        if 0 <= self.index < len(blocks):
            blocks[self.index] = copy.deepcopy(self.after)
            self._done(self.index)

    def undo(self) -> None:
        blocks = self._blocks()
        if 0 <= self.index < len(blocks):
            blocks[self.index] = copy.deepcopy(self.before)
            self._done(self.index)


class AddBlockCommand(_PageCommand):
    def __init__(
        self, page: Page, index: int, block: dict[str, Any], refresh: Callable[[int], None], label: str
    ) -> None:
        super().__init__(page, refresh, f"{label} hinzufügen")
        self.index = index
        self.block = copy.deepcopy(block)

    def redo(self) -> None:
        blocks = self._blocks()
        blocks.insert(self.index, copy.deepcopy(self.block))
        self._shift_style(self.index, +1)
        self._done(self.index)

    def undo(self) -> None:
        blocks = self._blocks()
        if 0 <= self.index < len(blocks):
            del blocks[self.index]
            self._shift_style(self.index, -1)
            self._done(max(0, self.index - 1))

    def _shift_style(self, at: int, delta: int) -> None:
        _shift_block_style(self.page, at, delta)


class RemoveBlockCommand(_PageCommand):
    def __init__(self, page: Page, index: int, refresh: Callable[[int], None], label: str) -> None:
        super().__init__(page, refresh, f"{label} löschen")
        self.index = index
        self.block = copy.deepcopy(page.blocks[index])

    def redo(self) -> None:
        blocks = self._blocks()
        if 0 <= self.index < len(blocks):
            del blocks[self.index]
            _shift_block_style(self.page, self.index, -1)
            self._done(max(0, self.index - 1))

    def undo(self) -> None:
        blocks = self._blocks()
        blocks.insert(self.index, copy.deepcopy(self.block))
        _shift_block_style(self.page, self.index, +1)
        self._done(self.index)


class MoveBlockCommand(_PageCommand):
    def __init__(self, page: Page, source: int, target: int, refresh: Callable[[int], None]) -> None:
        super().__init__(page, refresh, "Abschnitt verschieben")
        self.source = source
        self.target = target

    def redo(self) -> None:
        self._move(self.source, self.target)

    def undo(self) -> None:
        self._move(self.target, self.source)

    def _move(self, source: int, target: int) -> None:
        blocks = self._blocks()
        if not (0 <= source < len(blocks) and 0 <= target < len(blocks)):
            return
        blocks.insert(target, blocks.pop(source))
        _move_block_style(self.page, source, target)
        self._done(target)


# --------------------------------------------------------------------------- #
# Formatierungsvermerke mitführen                                              #
# --------------------------------------------------------------------------- #


def _shift_block_style(page: Page, at: int, delta: int) -> None:
    """Verschiebt die Formatierungsvermerke hinter der Einfügestelle.

    Die Vermerke hängen an Pfaden wie ``("blocks", 7)``. Wird vor Position 7
    etwas eingefügt, gehören sie danach zu Position 8 – sonst bekäme der neue
    Baustein die einzeilige Schreibweise seines Nachfolgers.
    """
    style = page.style
    for bucket in (style.inline, style.blank_before):
        moved = []
        for path in list(bucket):
            if len(path) >= 2 and path[0] == "blocks" and isinstance(path[1], int):
                if path[1] >= at:
                    bucket.discard(path)
                    if delta > 0 or path[1] > at:
                        moved.append(("blocks", path[1] + delta, *path[2:]))
        bucket.update(moved)


def _move_block_style(page: Page, source: int, target: int) -> None:
    """Zieht die Formatierung eines Bausteins an seine neue Position mit."""
    style = page.style
    for bucket in (style.inline, style.blank_before):
        entries = [p for p in bucket if len(p) >= 2 and p[0] == "blocks" and isinstance(p[1], int)]
        bucket.difference_update(entries)
        rebuilt = set()
        for path in entries:
            index = path[1]
            if index == source:
                new_index = target
            elif source < index <= target:
                new_index = index - 1
            elif target <= index < source:
                new_index = index + 1
            else:
                new_index = index
            rebuilt.add(("blocks", new_index, *path[2:]))
        bucket.update(rebuilt)
