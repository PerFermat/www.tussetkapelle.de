"""Die Abschnitte einer Seite als verschiebbare Liste.

Verschieben geschieht mit der Maus. Damit das Ergebnis nicht nur auf dem
Bildschirm, sondern auch in der Datei stimmt, wird die Blockliste der Seite
beim Ablegen komplett neu aus der Anzeige aufgebaut – und mit ihr die
Formatierungsvermerke, die an den Positionen der Bausteine hängen. Ohne das
behielte ein einzeilig geschriebener Überschriftenblock nach dem Verschieben
die Formatierung seines Vorgängers.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)
from PySide6.QtGui import QColor, QFont, QIcon, QPainter

from ..model import spec_for, summarize
from .theme import Color, icon

__all__ = ["BlockList"]

_ROLE_INDEX = Qt.ItemDataRole.UserRole
_ROLE_LABEL = Qt.ItemDataRole.UserRole + 1
_ROLE_TEXT = Qt.ItemDataRole.UserRole + 2


class _Delegate(QStyledItemDelegate):
    """Zwei Zeilen je Eintrag: Art des Abschnitts und Textanfang."""

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:  # noqa: N802
        return QSize(240, 50)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        rect = option.rect.adjusted(4, 3, -4, -3)

        if selected or option.state & QStyle.StateFlag.State_MouseOver:
            painter.setBrush(QColor(Color.GREEN if selected else Color.CREAM))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 6, 6)

        item_icon = index.data(Qt.ItemDataRole.DecorationRole)
        if isinstance(item_icon, QIcon):
            size = 18
            item_icon.paint(
                painter,
                rect.left() + 8,
                rect.top() + (rect.height() - size) // 2,
                size,
                size,
                Qt.AlignmentFlag.AlignCenter,
                QIcon.Mode.Selected if selected else QIcon.Mode.Normal,
            )

        text_left = rect.left() + 34
        # Die Schriftgröße kommt aus dem Stylesheet in Pixeln; dann liefert
        # pointSizeF() -1 und ein Rechnen damit ergäbe eine ungültige Größe.
        label_font = QFont(option.font)
        if option.font.pointSizeF() > 0:
            label_font.setPointSizeF(option.font.pointSizeF() - 1.2)
        else:
            label_font.setPixelSize(max(9, option.font.pixelSize() - 2))
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(QColor(Color.GOLD if selected else Color.GOLD_TEXT))
        painter.drawText(
            text_left,
            rect.top() + 6,
            rect.width() - 40,
            16,
            Qt.AlignmentFlag.AlignVCenter,
            index.data(_ROLE_LABEL) or "",
        )

        body_font = QFont(option.font)
        painter.setFont(body_font)
        painter.setPen(QColor(Color.CREAM if selected else Color.INK))
        metrics = painter.fontMetrics()
        text = metrics.elidedText(
            index.data(_ROLE_TEXT) or "", Qt.TextElideMode.ElideRight, rect.width() - 44
        )
        painter.drawText(
            text_left, rect.top() + 24, rect.width() - 40, 18, Qt.AlignmentFlag.AlignVCenter, text
        )
        painter.restore()


class BlockList(QListWidget):
    """Liste der Abschnitte einer Seite."""

    #: Ein Abschnitt wurde ausgewählt (Index in der Blockliste).
    block_selected = Signal(int)
    #: Die Reihenfolge hat sich geändert (alter Index, neuer Index).
    order_changed = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setItemDelegate(_Delegate(self))
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setMouseTracking(True)
        self.setUniformItemSizes(True)
        self.setMinimumWidth(280)
        self.currentRowChanged.connect(self._on_row)
        self.model().rowsMoved.connect(self._on_moved)
        self._loading = False

    # -- Füllen ------------------------------------------------------------ #

    def show_blocks(self, blocks: list[dict[str, Any]], current: int = 0) -> None:
        self._loading = True
        self.clear()
        for block in blocks:
            self.addItem(self._make_item(block))
        self._loading = False
        if self.count():
            self.setCurrentRow(min(max(current, 0), self.count() - 1))

    @staticmethod
    def _make_item(block: dict[str, Any]) -> QListWidgetItem:
        spec = spec_for(block.get("t", ""))
        item = QListWidgetItem()
        item.setData(_ROLE_LABEL, spec.label if spec else f"Unbekannt ({block.get('t')})")
        item.setData(_ROLE_TEXT, summarize(block) or "—")
        item.setIcon(icon(spec.icon if spec else "warning", Color.GREEN))
        return item

    def refresh_current(self, block: dict[str, Any]) -> None:
        """Aktualisiert die Vorschauzeile des gerade bearbeiteten Abschnitts."""
        item = self.currentItem()
        if item is None:
            return
        item.setData(_ROLE_TEXT, summarize(block) or "—")
        self.viewport().update()

    # -- Ereignisse -------------------------------------------------------- #

    def _on_row(self, row: int) -> None:
        if not self._loading and row >= 0:
            self.block_selected.emit(row)

    def _on_moved(self, _parent, start: int, _end: int, _dest, row: int) -> None:  # noqa: ANN001
        if self._loading:
            return
        target = row if row < start else row - 1
        if target != start:
            self.order_changed.emit(start, target)
