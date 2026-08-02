"""Fließtextfeld mit Fett, Kursiv und Verweis – ohne sichtbares HTML.

Eingefügter Text wird bewusst als reiner Text übernommen. Wer aus einem
Textverarbeitungsprogramm oder aus dem Browser kopiert, brächte sonst
Schriftarten, Farben und Tabellen mit, die die Website nicht kennt und die
build.js unverändert in die Seite schriebe.
"""

from __future__ import annotations

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QKeySequence, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..model import ContentRepository
from ..richtext import (
    LINE_SEPARATOR,
    NBSP,
    PROP_ANCHOR,
    LINK_COLOR,
    document_to_html,
    html_to_document,
    make_anchor_attrs,
)
from .linkdialog import LinkDialog
from .theme import Color, icon

__all__ = ["RichTextEdit"]


class _TextArea(QTextEdit):
    """Eingabefeld, das nur reinen Text annimmt."""

    def insertFromMimeData(self, source: QMimeData) -> None:  # noqa: N802
        text = source.text().replace("\r\n", "\n").replace("\r", "\n")
        # Zeilenumbrüche aus der Zwischenablage werden zu <br>, nicht zu neuen
        # Absätzen – ein Absatz ist im Editor ein eigener Baustein.
        self.textCursor().insertText(text.replace("\n", LINE_SEPARATOR))


class RichTextEdit(QWidget):
    """Fließtextfeld mit kleiner Leiste darüber."""

    changed = Signal()

    def __init__(
        self,
        repo: ContentRepository,
        lang: str,
        *,
        single_line: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._lang = lang
        self._loading = False

        self.edit = _TextArea()
        self.edit.setAcceptRichText(False)
        self.edit.setTabChangesFocus(True)
        self.edit.document().setDocumentMargin(8)
        self.edit.setMinimumHeight(56 if single_line else 120)
        if single_line:
            self.edit.setMaximumHeight(72)
        self.edit.textChanged.connect(self._on_changed)
        self.edit.cursorPositionChanged.connect(self._update_buttons)

        self.bold_button = self._tool("bold", "Fett", "Strg+B", self._toggle_bold)
        self.italic_button = self._tool("italic", "Kursiv", "Strg+I", self._toggle_italic)
        self.link_button = self._tool("link", "Verweis …", "Strg+K", self.edit_link)
        self.break_button = self._tool(
            "down", "Zeilenumbruch", "Umschalt+Eingabe", self._insert_break
        )
        self.nbsp_button = self._tool(
            "nbsp",
            "Geschütztes Leerzeichen",
            "Strg+Umschalt+Leertaste",
            self._insert_nbsp,
            tip="Hält zwei Wörter zusammen, etwa „27. Juli 1985“ oder "
            "„Tel. 08550/763“. Sie werden nie getrennt umbrochen.",
        )

        self.status = QLabel()
        self.status.setProperty("rolle", "hinweis")

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(2)
        for button in (
            self.bold_button,
            self.italic_button,
            self.link_button,
            self.break_button,
            self.nbsp_button,
        ):
            bar.addWidget(button)
        bar.addWidget(self.status, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(bar)
        layout.addWidget(self.edit)

        self._update_buttons()

    # -- Leiste ------------------------------------------------------------ #

    def _tool(self, name: str, label: str, shortcut: str, slot, tip: str = "") -> QToolButton:
        button = QToolButton()
        button.setIcon(icon(name, Color.GREEN))
        button.setToolTip(f"{tip or label}  ({shortcut})")
        button.setAutoRaise(True)
        button.setCheckable(name in ("bold", "italic"))
        button.clicked.connect(slot)
        button.setShortcut(QKeySequence(shortcut.replace("Strg", "Ctrl").replace("Umschalt", "Shift").replace("Eingabe", "Return").replace("Leertaste", "Space")))
        return button

    def _update_buttons(self) -> None:
        fmt = self.edit.currentCharFormat()
        self.bold_button.setChecked(fmt.fontWeight() >= 700)
        self.italic_button.setChecked(fmt.fontItalic())
        anchor = fmt.property(PROP_ANCHOR)
        self.link_button.setDown(isinstance(anchor, str))
        self.status.setText("Verweis an dieser Stelle" if isinstance(anchor, str) else "")

    # -- Inhalt ------------------------------------------------------------ #

    def set_html(self, html: str) -> None:
        self._loading = True
        html_to_document(html or "", self.edit.document())
        self.edit.moveCursor(QTextCursor.MoveOperation.Start)
        self._loading = False
        self._update_buttons()

    def html(self) -> str:
        return document_to_html(self.edit.document())

    def _on_changed(self) -> None:
        if not self._loading:
            self.changed.emit()

    # -- Auszeichnung ------------------------------------------------------ #

    def _apply(self, fmt: QTextCharFormat) -> None:
        cursor = self.edit.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.edit.mergeCurrentCharFormat(fmt)
        self._update_buttons()

    def _toggle_bold(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontWeight(400 if self.edit.currentCharFormat().fontWeight() >= 700 else 700)
        self._apply(fmt)

    def _toggle_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.edit.currentCharFormat().fontItalic())
        self._apply(fmt)

    def _insert_break(self) -> None:
        self.edit.textCursor().insertText(LINE_SEPARATOR)

    def _insert_nbsp(self) -> None:
        self.edit.textCursor().insertText(NBSP)

    # -- Verweise ---------------------------------------------------------- #

    def edit_link(self) -> None:
        cursor = self.edit.textCursor()
        existing = cursor.charFormat().property(PROP_ANCHOR)
        existing = existing if isinstance(existing, str) else ""

        if not cursor.hasSelection():
            if existing:
                cursor = self._select_anchor(cursor, existing)
            else:
                cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        if not cursor.hasSelection():
            self.status.setText("Bitte zuerst den Text auswählen, der verweisen soll.")
            return

        dialog = LinkDialog(self._repo, self._lang, existing, self)
        if dialog.exec() != LinkDialog.DialogCode.Accepted:
            return

        fmt = QTextCharFormat()
        if dialog.href:
            fmt.setProperty(PROP_ANCHOR, make_anchor_attrs(dialog.href, keep=existing))
            fmt.setForeground(LINK_COLOR)
            fmt.setFontUnderline(True)
        else:
            # Eigenschaft löschen und die Verweisoptik zurücknehmen.
            fmt.setProperty(PROP_ANCHOR, None)
            fmt.setForeground(self.edit.palette().text())
            fmt.setFontUnderline(False)
        cursor.mergeCharFormat(fmt)
        self.edit.setTextCursor(cursor)
        self._update_buttons()
        self.changed.emit()

    @staticmethod
    def _select_anchor(cursor: QTextCursor, attrs: str) -> QTextCursor:
        """Weitet die Auswahl auf den gesamten Verweis aus."""
        block = cursor.block()
        start, end = cursor.position(), cursor.position()
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid() and fragment.charFormat().property(PROP_ANCHOR) == attrs:
                first = fragment.position()
                last = first + fragment.length()
                if first <= cursor.position() <= last:
                    start, end = min(start, first), max(end, last)
            it += 1
        out = QTextCursor(cursor)
        out.setPosition(start)
        out.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        return out

    # -- Tastatur ---------------------------------------------------------- #

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._insert_break()
            return
        super().keyPressEvent(event)
