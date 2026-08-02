"""Das Hauptfenster.

Aufteilung: links der Seitenbaum, in der Mitte die Abschnitte der Seite, rechts
die Eingabemaske des ausgewählten Abschnitts. Oben die Werkzeugleiste, unten
die Statusleiste, darunter ausklappbar die Ausgabe der Werkzeuge.

Der Fensterinhalt hängt an genau einer Frage: welche Sprache und welche Seite
sind gewählt? Beim Wechsel wird alles neu aufgebaut. Das ist bei zwanzig Seiten
je Sprache schnell genug und erspart eine Menge Zustandsverwaltung, bei der
sonst irgendwann eine Anzeige nicht mehr zum Inhalt passt.
"""

from __future__ import annotations

import copy
import webbrowser
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..commands import AddBlockCommand, EditBlockCommand, MoveBlockCommand, RemoveBlockCommand
from ..model import BLOCKS, ContentRepository, Page, RepositoryError, Severity, spec_for
from ..process import NpmRunner
from .blockeditor import BlockEditor
from .blocklist import BlockList
from .console import ConsolePanel, ConsoleTitleBar
from .homeeditor import HomeEditor
from .pagedialogs import NewPageDialog, RenamePageDialog
from .pagetree import PageTree
from .theme import STYLESHEET, Color, icon

__all__ = ["MainWindow"]

AUTOSAVE_MS = 60_000
PREVIEW_URL = "http://localhost:8473/"


class MainWindow(QMainWindow):
    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self.repo = ContentRepository(root)
        self.settings = QSettings("Tussetkapelle", "Inhaltseditor")
        self.undo_stack = QUndoStack(self)
        self.runner = NpmRunner(root, self)

        self.lang = "de"
        self.page: Page | None = None
        self.block_index = 0
        self._before_edit: dict[str, Any] | None = None
        self._rebuilding = False
        #: Anschließend auszuführendes Skript – „Prüfen“ lässt die Website erst
        #: neu erzeugen, wenn sie veraltet ist.
        self._after_build = ""

        self.setWindowTitle("Tussetkapelle – Inhalte bearbeiten")
        self.resize(1500, 940)
        self.setStyleSheet(STYLESHEET)

        self._build_widgets()
        self._build_toolbar()
        self._build_statusbar()
        self._build_console()
        self._connect()

        self.autosave = QTimer(self)
        self.autosave.setInterval(AUTOSAVE_MS)
        self.autosave.timeout.connect(self._autosave)
        if self.settings.value("autosave", True, type=bool):
            self.autosave.start()

        self._restore_geometry()
        # Der Zustand des Ausgabefensters wird bewusst NICHT aus den
        # Einstellungen übernommen: es ist eine Antwort auf einen Knopfdruck,
        # kein Arbeitsbereich. Das setzt zugleich alte Einstellungsdateien
        # zurück, in denen es abgekoppelt und sichtbar gespeichert ist.
        self.console_dock.setFloating(False)
        self.console_dock.hide()

        self._reload_tree(select=self.settings.value("lastPage", "home", type=str))

    # ------------------------------------------------------------------ #
    # Aufbau                                                             #
    # ------------------------------------------------------------------ #

    def _build_widgets(self) -> None:
        self.tree = PageTree()
        self.blocks = BlockList()

        # Die Sprachwahl steht über dem Seitenbaum, nicht in der Werkzeugleiste:
        # sie bestimmt, welche Fassung der Baum zeigt, und gehört deshalb daneben.
        # In der Leiste passte sie bei 1560 Pixeln Fensterbreite ohnehin nicht mehr.
        self.lang_combo = QComboBox()
        for lang in self.repo.languages:
            self.lang_combo.addItem(self.repo.sites[lang].label, lang)
        self.lang_combo.setCurrentIndex(self.lang_combo.findData(self.lang))
        self.lang_combo.currentIndexChanged.connect(
            lambda _: self.switch_language(self.lang_combo.currentData())
        )

        lang_caption = QLabel("Sprachfassung")
        lang_caption.setProperty("rolle", "feld")

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 6, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(lang_caption)
        left_layout.addWidget(self.lang_combo)
        left_layout.addSpacing(4)
        left_layout.addWidget(self.tree, 1)
        self.editor = BlockEditor(self.repo, self.lang)
        self.home_editor = HomeEditor(self.repo, self.lang)

        self.page_banner = QLabel()
        self.page_banner.setWordWrap(True)
        self.page_banner.setProperty("rolle", "warnung")
        self.page_banner.setContentsMargins(14, 8, 14, 8)
        self.page_banner.hide()

        middle = QWidget()
        middle_layout = QVBoxLayout(middle)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        middle_layout.addWidget(self.blocks)

        # Zwei Reiter, weil die Startseite beides hat: den festen Aufbau mit
        # Hero, Kacheln und Zeitleiste – und daneben sieben ganz normale
        # Abschnitte („Willkommen …“). Bei allen anderen Seiten bleibt der
        # zweite Reiter verborgen.
        self.tabs = QTabWidget()
        self.tabs.addTab(self.editor, "Abschnitt")
        self.tabs.addTab(self.home_editor, "Aufbau der Startseite")

        right = QWidget()
        self.right_layout = QVBoxLayout(right)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        self.right_layout.addWidget(self.page_banner)
        self.right_layout.addWidget(self.tabs, 1)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(left)
        self.splitter.addWidget(middle)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(2, 1)
        self.splitter.setSizes([270, 330, 900])
        self.setCentralWidget(self.splitter)

    def _build_toolbar(self) -> None:
        bar = QToolBar("Werkzeuge")
        bar.setObjectName("werkzeugleiste")  # nötig, damit saveState() greift
        bar.setMovable(False)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        bar.setIconSize(bar.iconSize() * 0.9)
        self.addToolBar(bar)

        self.action_save = self._action(
            bar, "save", "Speichern", "Strg+S", self.save, Color.CREAM
        )
        self.action_undo = self._action(bar, "undo", "Rückgängig", "Strg+Z", self.undo_stack.undo, Color.CREAM)
        self.action_redo = self._action(
            bar, "redo", "Wiederholen", "Strg+Umschalt+Z", self.undo_stack.redo, Color.CREAM
        )
        bar.addSeparator()

        self.action_new_page = self._action(bar, "add", "Neue Seite", "Strg+N", self.new_page, Color.CREAM)
        self.action_add_block = self._action(
            bar, "paragraph", "Abschnitt hinzufügen", "Strg+Umschalt+N", self.add_block_menu, Color.CREAM
        )
        self.action_remove_block = self._action(
            bar, "remove", "Abschnitt löschen", "", self.remove_block, Color.CREAM
        )
        bar.addSeparator()

        self.action_build = self._action(bar, "build", "Website erzeugen", "F5", self.build_site, Color.CREAM)
        self.action_check = self._action(bar, "check", "Prüfen", "F6", self.check_site, Color.CREAM)
        self.action_preview = self._action(bar, "preview", "Vorschau", "", self.open_preview, Color.CREAM)

        self._build_menu()

    def _action(self, bar, name, text, shortcut, slot, color=Color.GREEN) -> QAction:
        action = QAction(icon(name, color), text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut.replace("Strg", "Ctrl").replace("Umschalt", "Shift")))
            action.setToolTip(f"{text}  ({shortcut})")
        action.triggered.connect(slot)
        bar.addAction(action)
        return action

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&Datei")
        file_menu.addAction(self.action_save)
        file_menu.addAction(self.action_new_page)
        file_menu.addSeparator()

        self.action_autosave = QAction("Automatisch speichern", self)
        self.action_autosave.setCheckable(True)
        self.action_autosave.setChecked(self.settings.value("autosave", True, type=bool))
        self.action_autosave.toggled.connect(self._toggle_autosave)
        file_menu.addAction(self.action_autosave)
        file_menu.addSeparator()
        file_menu.addAction(QAction("Beenden", self, shortcut="Ctrl+Q", triggered=self.close))

        edit_menu = self.menuBar().addMenu("&Bearbeiten")
        edit_menu.addAction(self.action_undo)
        edit_menu.addAction(self.action_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_add_block)
        edit_menu.addAction(self.action_remove_block)

        site_menu = self.menuBar().addMenu("&Website")
        site_menu.addAction(self.action_build)
        site_menu.addAction(self.action_check)
        site_menu.addAction(self.action_preview)
        site_menu.addSeparator()
        # Für den Fall, dass Bilder von Hand nach bilder/ gelegt wurden. Beim
        # Aufnehmen über die Bildauswahl läuft das ohnehin von selbst.
        self.action_images = QAction("Bilder auffrischen", self, triggered=self.refresh_images)
        site_menu.addAction(self.action_images)

        help_menu = self.menuBar().addMenu("&Hilfe")
        help_menu.addAction(QAction("Über diesen Editor", self, triggered=self._about))

    def _build_statusbar(self) -> None:
        self.status_page = QLabel()
        self.status_dirty = QLabel()
        self.status_site = QLabel()
        self.status_site.setProperty("rolle", "warnung")
        self.status_site.setToolTip(
            "Die hochgeladenen Seiten liegen fertig im Projektordner. Solange "
            "sie nicht neu erzeugt sind, zeigen sie den Stand von vorher – nach "
            "dem Löschen eines Bildes sogar Verweise auf eine Datei, die es "
            "nicht mehr gibt. „Website erzeugen“ (F5) bringt sie auf den Stand."
        )
        self.status_result = QLabel()

        # Ganz rechts der Schalter für das Ausgabefenster. Eingeklappt ist die
        # Statuszeile alles, was unten steht – ein Pluszeichen holt die Ausgabe
        # zurück.
        self.console_toggle = QToolButton()
        self.console_toggle.setObjectName("ausgabeSchalter")
        self.console_toggle.setAutoRaise(True)
        self.console_toggle.clicked.connect(self._toggle_console)

        bar = self.statusBar()
        bar.addWidget(self.status_page, 1)
        bar.addPermanentWidget(self.status_dirty)
        bar.addPermanentWidget(self.status_site)
        bar.addPermanentWidget(self.status_result)
        bar.addPermanentWidget(self.console_toggle)

    def _toggle_console(self) -> None:
        self.console_dock.setVisible(not self.console_dock.isVisible())

    def _console_visibility_changed(self, visible: bool) -> None:
        """Hält den Schalter im Gleichklang mit dem Fenster.

        Der Schalter ändert sein Aussehen nicht selbst, sondern erst auf diese
        Meldung hin. So stimmt er auch, wenn das Fenster von anderer Stelle
        geöffnet wird – etwa durch eine eintreffende Ausgabezeile.
        """
        self.console_toggle.setIcon(icon("minus" if visible else "add", Color.CREAM))
        self.console_toggle.setToolTip(
            "Ausgabe der Werkzeuge verbergen" if visible else "Ausgabe der Werkzeuge zeigen"
        )

    def _show_console(self) -> None:
        self.console_dock.show()
        # Eine feste, bescheidene Höhe: die Ausgabe ist ein Blick, kein
        # Arbeitsbereich. Ohne das nimmt sie sich beim ersten Öffnen die halbe
        # Fensterhöhe und die Eingabemaske wird eng.
        self.resizeDocks([self.console_dock], [280], Qt.Orientation.Vertical)

    def _build_console(self) -> None:
        """Das Ausgabefenster – fest unten, einklappbar, nie ein eigenes Fenster.

        Abkoppeln war die Voreinstellung und hat sich als Fehler erwiesen: als
        frei schwebendes Fenster legt sich die Ausgabe über die Eingabemaske,
        und ``restoreState()`` holte diesen Zustand bei jedem Start zurück.
        Deshalb bleibt allein ``DockWidgetClosable`` übrig, der erlaubte Bereich
        ist auf „unten“ beschränkt, und die Titelzeile ist eine eigene – die
        voreingestellte reißt das Fenster schon beim Doppelklick los.
        """
        self.console = ConsolePanel()
        self.console_dock = QDockWidget("Ausgabe der Werkzeuge", self)
        self.console_dock.setObjectName("ausgabe")
        self.console_dock.setWidget(self.console)
        self.console_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.console_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)

        title = ConsoleTitleBar(self.console_dock)
        title.collapse_requested.connect(self.console_dock.hide)
        self.console_dock.setTitleBarWidget(title)

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock)
        self.console_dock.hide()

    def _connect(self) -> None:
        self.tree.page_selected.connect(self.open_page)
        self.tree.page_moved.connect(self.move_page)
        self.tree.customContextMenuRequested.connect(self._page_menu)

        self.blocks.block_selected.connect(self.open_block)
        self.blocks.order_changed.connect(self.move_block)

        self.editor.changed.connect(self._on_block_edited)
        self.home_editor.changed.connect(self._on_page_edited)
        self.editor.stock_changed.connect(self._update_status)
        self.home_editor.stock_changed.connect(self._update_status)

        self.undo_stack.canUndoChanged.connect(self.action_undo.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.action_redo.setEnabled)
        self.undo_stack.cleanChanged.connect(lambda _: self._update_status())
        self.action_undo.setEnabled(False)
        self.action_redo.setEnabled(False)

        self.console.output_arrived.connect(self._show_console)
        self.console_dock.visibilityChanged.connect(self._console_visibility_changed)
        self._console_visibility_changed(False)

        self.runner.started.connect(self._run_started)
        self.runner.line.connect(self.console.append)
        self.runner.finished.connect(self._run_finished)

    # ------------------------------------------------------------------ #
    # Anzeige                                                            #
    # ------------------------------------------------------------------ #

    def _reload_tree(self, select: str | None = None) -> None:
        self._rebuilding = True
        keep = select or (self.page.page_id if self.page else "home")
        self.tree.show_pages(self.repo, self.lang, keep)
        self._rebuilding = False
        self.open_page(self.tree.current_page_id() or "home")

    def open_page(self, page_id: str) -> None:
        page = self.repo.page(self.lang, page_id)
        if page is None:
            return
        self.page = page
        self.settings.setValue("lastPage", page_id)
        if self.tree.current_page_id() != page_id:
            self.tree.select_page(page_id)

        is_home = page.kind == "home"
        self.tabs.setTabVisible(1, is_home)
        if is_home:
            self.home_editor.show_page(page)
        self.tabs.setCurrentIndex(0)

        self.blocks.show_blocks(page.blocks, 0)
        if not page.blocks:
            self.editor.clear()

        self.editor.set_read_only(page.read_only)
        self.home_editor.setEnabled(not page.read_only)
        reason = page.lock_reason()
        self.page_banner.setVisible(bool(reason))
        self.page_banner.setText(reason)

        self.action_add_block.setEnabled(page.has_blocks and not page.read_only)
        self.action_remove_block.setEnabled(page.has_blocks and not page.read_only)
        self._update_status()

    def open_block(self, index: int) -> None:
        if self.page is None or not (0 <= index < len(self.page.blocks)):
            return
        self.block_index = index
        block = self.page.blocks[index]
        self._before_edit = copy.deepcopy(block)
        self.editor.show_block(block)

    def _refresh_after_command(self, select: int) -> None:
        """Rückruf der Befehle: Anzeige an das geänderte Modell angleichen."""
        if self.page is None:
            return
        self.blocks.show_blocks(self.page.blocks, select)
        if self.page.blocks:
            self.open_block(min(select, len(self.page.blocks) - 1))
        else:
            self.editor.clear()
        self._update_status()

    def _update_status(self) -> None:
        if self.page is not None:
            kind = {"home": "Startseite", "hub": "Übersicht", "gallery": "Galerie"}.get(
                self.page.kind, "Seite"
            )
            count = len(self.page.blocks)
            self.status_page.setText(
                f"{kind}: {self.page.title}   ·   {self.repo.sites[self.lang].label}"
                + (f"   ·   {count} Abschnitte" if self.page.has_blocks else "")
            )
        n = self.repo.dirty_count()
        self.status_dirty.setText("Alles gespeichert" if n == 0 else f"{n} Dateien geändert")
        self.action_save.setEnabled(n > 0)
        self.status_site.setText(
            "Website nicht auf dem neuesten Stand" if self.repo.site_stale else ""
        )

    # ------------------------------------------------------------------ #
    # Bearbeiten                                                         #
    # ------------------------------------------------------------------ #

    def _on_block_edited(self) -> None:
        if self.page is None or self._before_edit is None or self._rebuilding:
            return
        current = self.page.blocks[self.block_index]
        if current == self._before_edit:
            return
        command = EditBlockCommand(
            self.page,
            self.block_index,
            self._before_edit,
            current,
            self._refresh_after_command,
            already_applied=True,
        )
        self._before_edit = copy.deepcopy(current)
        self.undo_stack.push(command)
        self.blocks.refresh_current(current)
        self._update_status()

    def _on_page_edited(self) -> None:
        self._update_status()

    def add_block_menu(self) -> None:
        if self.page is None or not self.page.has_blocks or self.page.read_only:
            return
        menu = QMenu(self)
        for spec in BLOCKS:
            if not spec.creatable:
                continue
            action = menu.addAction(icon(spec.icon, Color.GREEN), spec.label)
            action.setToolTip(spec.hint)
            action.triggered.connect(lambda _=False, s=spec: self.add_block(s))
        menu.exec(self.mapToGlobal(self.rect().center()))

    def add_block(self, spec) -> None:
        if self.page is None:
            return
        index = min(self.block_index + 1, len(self.page.blocks))
        self.undo_stack.push(
            AddBlockCommand(self.page, index, spec.new(), self._refresh_after_command, spec.label)
        )

    def remove_block(self) -> None:
        if self.page is None or not self.page.blocks or self.page.read_only:
            return
        block = self.page.blocks[self.block_index]
        spec = spec_for(block.get("t", ""))
        label = spec.label if spec else "Abschnitt"
        answer = QMessageBox.question(
            self,
            "Abschnitt löschen",
            f"Den Abschnitt „{label}“ wirklich löschen?\n\n"
            "Mit Strg+Z lässt sich das rückgängig machen, solange der Editor "
            "geöffnet bleibt.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.undo_stack.push(
                RemoveBlockCommand(self.page, self.block_index, self._refresh_after_command, label)
            )

    def move_block(self, source: int, target: int) -> None:
        if self.page is None or self.page.read_only:
            return
        self.undo_stack.push(
            MoveBlockCommand(self.page, source, target, self._refresh_after_command)
        )

    # ------------------------------------------------------------------ #
    # Seiten                                                             #
    # ------------------------------------------------------------------ #

    def switch_language(self, lang: str) -> None:
        if lang == self.lang:
            return
        current = self.page.page_id if self.page else "home"
        self.lang = lang
        # Die Eingabemasken merken sich die Sprache für den Verweisdialog und
        # werden deshalb ausgetauscht, nicht bloß neu befüllt.
        while self.tabs.count():
            self.tabs.removeTab(0)
        self.editor.deleteLater()
        self.home_editor.deleteLater()
        self.editor = BlockEditor(self.repo, lang)
        self.home_editor = HomeEditor(self.repo, lang)
        self.editor.changed.connect(self._on_block_edited)
        self.home_editor.changed.connect(self._on_page_edited)
        self.editor.stock_changed.connect(self._update_status)
        self.home_editor.stock_changed.connect(self._update_status)
        self.tabs.insertTab(0, self.editor, "Abschnitt")
        self.tabs.insertTab(1, self.home_editor, "Aufbau der Startseite")
        self.undo_stack.clear()
        self._reload_tree(select=current)

    def new_page(self) -> None:
        parent_id = self.page.page_id if self.page else "home"
        dialog = NewPageDialog(self.repo, parent_id, self)
        if dialog.exec() != NewPageDialog.DialogCode.Accepted:
            return
        try:
            self.repo.create_page(dialog.spec)
        except RepositoryError as err:
            self._error("Seite konnte nicht angelegt werden", str(err))
            return
        self.undo_stack.clear()
        self._reload_tree(select=dialog.spec.page_id)
        self._info(
            "Seite angelegt",
            f"„{dialog.spec.titles.get(self.lang) or dialog.spec.page_id}“ wurde in "
            f"allen {len(self.repo.languages)} Sprachfassungen angelegt.\n\n"
            "Die Seite ist noch leer. Fügen Sie Abschnitte hinzu und speichern Sie.",
        )

    def rename_page(self, page_id: str) -> None:
        dialog = RenamePageDialog(self.repo, page_id, self)
        if dialog.exec() != RenamePageDialog.DialogCode.Accepted:
            return
        try:
            removed = self.repo.rename_page(page_id, dialog.new_id)
        except RepositoryError as err:
            self._error("Umbenennen nicht möglich", str(err))
            return
        self.undo_stack.clear()
        self._reload_tree(select=dialog.new_id)
        note = (
            f"\n\n{len(removed)} alte Ausgabeverzeichnisse wurden entfernt."
            if removed
            else ""
        )
        self._info(
            "Seite umbenannt",
            f"Die Seite heißt jetzt „{dialog.new_id}“. Alle Verweise wurden "
            f"mitgeführt.{note}\n\nBitte speichern und die Website neu erzeugen.",
        )

    def delete_page(self, page_id: str) -> None:
        page = self.repo.page(self.lang, page_id)
        if page is None:
            return
        referrers = self.repo.referrers(page_id)
        detail = ""
        if referrers:
            names = sorted({self.repo.page(l, p).title for l, p in referrers if self.repo.page(l, p)})
            detail = "\n\nAuf diese Seite verweisen noch:\n• " + "\n• ".join(names[:8])

        answer = QMessageBox.warning(
            self,
            "Seite löschen",
            f"„{page.title}“ in allen {len(self.repo.languages)} Sprachfassungen "
            f"löschen?{detail}\n\nDas lässt sich nicht rückgängig machen.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.repo.delete_page(page_id)
        except RepositoryError as err:
            self._error("Löschen nicht möglich", str(err))
            return
        self.undo_stack.clear()
        self._reload_tree(select="home")

    def duplicate_page(self, page_id: str) -> None:
        from PySide6.QtWidgets import QInputDialog

        new_id, ok = QInputDialog.getText(
            self, "Seite duplizieren", "Kennung der neuen Seite", text=f"{page_id}-kopie"
        )
        if not ok or not new_id.strip():
            return
        try:
            self.repo.duplicate_page(page_id, new_id.strip())
        except RepositoryError as err:
            self._error("Duplizieren nicht möglich", str(err))
            return
        self.undo_stack.clear()
        self._reload_tree(select=new_id.strip())

    def move_page(self, page_id: str, new_parent: str) -> None:
        try:
            removed = self.repo.reparent(page_id, new_parent)
        except RepositoryError as err:
            self._error("Verschieben nicht möglich", str(err))
            return
        self._reload_tree(select=page_id)
        if removed:
            self.status_result.setText(
                f"Verschoben – {len(removed)} alte Ausgabeverzeichnisse entfernt."
            )

    def _page_menu(self, position) -> None:
        item = self.tree.itemAt(position)
        if item is None:
            return
        page_id = item.data(0, Qt.ItemDataRole.UserRole)
        page = self.repo.page(self.lang, page_id)
        if page is None:
            return

        menu = QMenu(self)
        menu.addAction(icon("add", Color.GREEN), "Neue Unterseite …", lambda: self._new_child(page_id))
        menu.addSeparator()
        rename = menu.addAction(icon("page", Color.GREEN), "Umbenennen …", lambda: self.rename_page(page_id))
        duplicate = menu.addAction(icon("pages", Color.GREEN), "Duplizieren …", lambda: self.duplicate_page(page_id))
        menu.addSeparator()
        delete = menu.addAction(icon("remove", Color.ERROR), "Löschen …", lambda: self.delete_page(page_id))

        for action in (rename, duplicate, delete):
            action.setEnabled(page.is_renamable)
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _new_child(self, parent_id: str) -> None:
        dialog = NewPageDialog(self.repo, parent_id, self)
        if dialog.exec() == NewPageDialog.DialogCode.Accepted:
            try:
                self.repo.create_page(dialog.spec)
            except RepositoryError as err:
                self._error("Seite konnte nicht angelegt werden", str(err))
                return
            self.undo_stack.clear()
            self._reload_tree(select=dialog.spec.page_id)

    # ------------------------------------------------------------------ #
    # Speichern und Werkzeuge                                            #
    # ------------------------------------------------------------------ #

    def save(self) -> bool:
        try:
            written = self.repo.save_all()
        except RepositoryError as err:
            self._error("Nicht gespeichert", str(err))
            return False
        self.undo_stack.setClean()
        self._update_status()
        warnings = [p for p in self.repo.problems() if p.severity is Severity.WARNING]
        self.status_result.setText(
            f"{len(written)} Dateien gespeichert"
            + (f"  ·  {len(warnings)} Hinweise" if warnings else "")
        )
        return True

    def _autosave(self) -> None:
        if not self.repo.dirty:
            return
        if any(p.is_error for p in self.repo.problems()):
            self.status_result.setText("Automatisches Speichern verschoben – bitte Fehler beheben.")
            return
        written = self.repo.save_all(force=False)
        self._update_status()
        self.status_result.setText(f"Automatisch gespeichert ({len(written)} Dateien)")

    def _toggle_autosave(self, on: bool) -> None:
        self.settings.setValue("autosave", on)
        self.autosave.start() if on else self.autosave.stop()

    # Das Ausgabefenster wird hier nicht geöffnet: es meldet sich selbst, sobald
    # die erste Zeile eintrifft (ConsolePanel.output_arrived). Wer es während
    # eines Laufs zuklappt, soll es zugeklappt behalten.

    def build_site(self) -> None:
        if self.repo.dirty and not self.save():
            return
        self.runner.run("build")

    def check_site(self) -> None:
        """Prüft die erzeugten Seiten – nachdem sie auf den Stand gebracht sind.

        Geprüft wird nicht der Inhalt im Editor, sondern was auf der Platte
        liegt. Eine veraltete Seite zu prüfen sagt über den heutigen Stand
        nichts aus und führt in die Irre: nach dem Löschen eines Bildes meldet
        die Prüfung „defekte Bildverweise“ auf Seiten, die längst neu erzeugt
        gehören. Deshalb wird erst erzeugt, dann geprüft.
        """
        if self.repo.dirty and not self.save():
            return
        if self.repo.site_stale:
            self._after_build = "check"
            self.runner.run("build")
            return
        self.runner.run("check")

    def refresh_images(self) -> None:
        """Ableitungen und Bildverzeichnis aus bilder/ neu erzeugen."""
        self.runner.run("images")

    def open_preview(self) -> None:
        QDesktopServices.openUrl(QUrl(PREVIEW_URL)) or webbrowser.open(PREVIEW_URL)
        self.status_result.setText(
            "Vorschau geöffnet. Läuft der Testserver nicht, hilft „npm run serve“."
        )

    def _set_tools_enabled(self, on: bool) -> None:
        for action in (self.action_build, self.action_check, self.action_images):
            action.setEnabled(on)

    def _run_started(self, label: str) -> None:
        self.console.begin(label)
        self._set_tools_enabled(False)
        self.status_result.setText(f"{label} läuft …")

    def _run_finished(self, label: str, ok: bool, code: int) -> None:
        follow, self._after_build = self._after_build, ""
        self.console.end(label, ok, code)
        self._set_tools_enabled(True)
        self.status_result.setText(f"{label}: {'erfolgreich' if ok else 'fehlgeschlagen'}")
        if ok and label == NpmRunner.LABELS["build"]:
            self.repo.site_stale = False
        if ok and label == NpmRunner.LABELS["images"]:
            # Das Skript hat src/image-manifest.json neu geschrieben – Maße und
            # Größenstufen in den erzeugten Seiten stimmen damit womöglich nicht
            # mehr.
            self.repo.manifest.reload()
            self.repo.site_stale = True
        self._update_status()
        if ok and follow:
            self.runner.run(follow)
            return
        if not ok:
            self._error(
                f"{label} fehlgeschlagen",
                "Die Einzelheiten stehen unten im Fenster „Ausgabe der Werkzeuge“.",
            )

    # ------------------------------------------------------------------ #
    # Fenster                                                            #
    # ------------------------------------------------------------------ #

    def _restore_geometry(self) -> None:
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.repo.dirty:
            answer = QMessageBox.question(
                self,
                "Änderungen speichern?",
                f"{self.repo.dirty_count()} Dateien wurden geändert und noch nicht "
                "gespeichert.",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Save and not self.save():
                event.ignore()
                return
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        super().closeEvent(event)

    # -- Meldungen --------------------------------------------------------- #

    def _error(self, title: str, text: str) -> None:
        box = QMessageBox(QMessageBox.Icon.Warning, title, text, parent=self)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.exec()

    def _info(self, title: str, text: str) -> None:
        box = QMessageBox(QMessageBox.Icon.Information, title, text, parent=self)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.exec()

    def _about(self) -> None:
        self._info(
            "Über diesen Editor",
            "Inhaltseditor für www.tussetkapelle.de\n\n"
            f"Bestand: {sum(len(p) for p in self.repo.pages.values())} Seiten in "
            f"{len(self.repo.languages)} Sprachen, {len(self.repo.manifest)} Bilder.\n\n"
            "Die Texte und Bilder stammen von der Familie Weber.\n"
            "Bearbeitet werden ausschließlich die Dateien unter src/content/ – "
            "die fertige Website entsteht daraus über „Website erzeugen“.",
        )
