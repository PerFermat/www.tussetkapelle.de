"""Bedienungstest mit echten Dialogen.

    QT_QPA_PLATFORM=offscreen .venv/bin/python -m editor.uitest

Warum eigens dafür ein Test: Beim Abnehmen des Editors war die Sicherheitsabfrage
vor dem Löschen durch eine Attrappe ersetzt worden, die einfach „Ja“ zurückgab.
Damit blieb unbemerkt, dass ``QMessageBox.question()`` in PySide6 keinen
Enum-Wert liefert, sondern eine einfache Zahl (16384). Der Vergleich
``antwort is QMessageBox.StandardButton.Yes`` war deshalb immer falsch – das
Löschen geschah nie, und beim Schließen des Fensters wären ungespeicherte
Änderungen ohne Nachfrage verloren gegangen.

Dieser Test drückt stattdessen auf die Schaltflächen der wirklich angezeigten
Dialoge. Er läuft ohne Bildschirm.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from .model import spec_for
from .ui import MainWindow

ROOT = Path(__file__).resolve().parent.parent

_failures: list[str] = []


def check(title: str, condition: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if condition else 'FEHL'}  {title}{'  – ' + detail if detail else ''}")
    if not condition:
        _failures.append(title)


def settle(ms: int = 120) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def press(app: QApplication, button: QMessageBox.StandardButton, delay: int = 120) -> None:
    """Drückt in dem Dialog, der gleich erscheint, die genannte Schaltfläche."""

    def click() -> None:
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMessageBox) and widget.isVisible():
                target = widget.button(button)
                if target is not None:
                    target.click()
                    return
                widget.reject()

    QTimer.singleShot(delay, click)


def close_dialogs(app: QApplication, delay: int = 120) -> None:
    def close() -> None:
        for widget in app.topLevelWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                widget.reject()

    QTimer.singleShot(delay, close)


# --------------------------------------------------------------------------- #


def test_remove_block(app: QApplication, w: MainWindow) -> None:
    print("\nAbschnitt löschen")
    w.open_page("kontakt")
    settle(200)
    before = copy.deepcopy(w.page.blocks)

    w.add_block(spec_for("p"))
    settle(150)
    check("Hinzufügen legt einen Abschnitt an", len(w.page.blocks) == len(before) + 1)

    press(app, QMessageBox.StandardButton.No)
    w.remove_block()
    settle(250)
    check("„Nein“ behält den Abschnitt", len(w.page.blocks) == len(before) + 1)

    press(app, QMessageBox.StandardButton.Yes)
    w.remove_block()
    settle(250)
    check(
        "„Ja“ löscht den Abschnitt wirklich",
        len(w.page.blocks) == len(before),
        f"{len(w.page.blocks)} statt {len(before)}",
    )
    check("Die Liste zeigt es auch an", w.blocks.count() == len(before))
    check("Der übrige Inhalt ist unverändert", w.page.blocks == before)

    while w.undo_stack.canUndo():
        w.undo_stack.undo()
    settle(150)


def test_delete_page(app: QApplication, w: MainWindow) -> None:
    print("\nSeite löschen")
    from .model import NewPage

    w.repo.create_page(NewPage("uitest-seite", "geschichte", {l: "UI-Test" for l in w.repo.languages}))
    w._reload_tree(select="uitest-seite")
    settle(200)
    check("Testseite angelegt", w.repo.page("de", "uitest-seite") is not None)

    press(app, QMessageBox.StandardButton.No)
    w.delete_page("uitest-seite")
    settle(250)
    check("„Nein“ behält die Seite", w.repo.page("de", "uitest-seite") is not None)

    press(app, QMessageBox.StandardButton.Yes)
    w.delete_page("uitest-seite")
    settle(250)
    check("„Ja“ löscht die Seite wirklich", w.repo.page("de", "uitest-seite") is None)
    check(
        "Auch in den anderen Sprachen",
        all(w.repo.page(l, "uitest-seite") is None for l in w.repo.languages),
    )
    check("Und die Adresse ist frei", "uitest-seite" not in w.repo.sites["de"].slugs)


def test_close_with_changes(app: QApplication, w: MainWindow) -> None:
    print("\nSchließen mit ungespeicherten Änderungen")
    w.open_page("kontakt")
    settle(150)
    w.add_block(spec_for("p"))
    settle(150)
    check("Es gibt ungespeicherte Änderungen", w.repo.dirty)

    press(app, QMessageBox.StandardButton.Cancel)
    w.close()
    settle(300)
    check("„Abbrechen“ hält das Fenster offen", w.isVisible())
    check("Und die Änderungen bleiben ungespeichert", w.repo.dirty)

    while w.undo_stack.canUndo():
        w.undo_stack.undo()
    settle(150)
    w.repo.load()


def main() -> int:
    app = QApplication(sys.argv[:1])
    w = MainWindow(ROOT)
    w.autosave.stop()
    w.resize(1500, 940)
    w.show()
    settle(700)

    test_remove_block(app, w)
    test_delete_page(app, w)
    test_close_with_changes(app, w)

    print()
    if _failures:
        print(f"FEHLGESCHLAGEN – {len(_failures)}: " + ", ".join(_failures))
        return 1
    print("Alle Bedienungstests bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
