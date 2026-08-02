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

Aus demselben Grund wird hier auch das Ausgabefenster geprüft: es hatte sich
über die gespeicherte Fenstereinstellung als eigenes Fenster wieder hervorgeholt
und die Eingabemaske verdeckt – etwas, das kein Modelltest sehen kann.
"""

from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QMessageBox,
    QScrollArea,
)

from .model import spec_for
from .model.repository import ContentRepository
from .ui import MainWindow
from .ui.imagepicker import ImagePickerDialog

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


def test_console_dock(app: QApplication, w: MainWindow) -> None:
    print("\nAusgabe der Werkzeuge")
    dock = w.console_dock

    check("Nach dem Start eingeklappt", not dock.isVisible())
    check("Und nicht als eigenes Fenster", not dock.isFloating())
    check(
        "Abkoppeln ist gar nicht vorgesehen",
        not (dock.features() & QDockWidget.DockWidgetFeature.DockWidgetFloatable),
    )
    check(
        "Es kann nur unten stehen",
        dock.allowedAreas() == Qt.DockWidgetArea.BottomDockWidgetArea,
    )
    check("Der Schalter lädt zum Aufklappen ein", "zeigen" in w.console_toggle.toolTip())

    w.console_toggle.click()
    settle(250)
    check("Der Schalter klappt es auf", dock.isVisible())
    check("Der Schalter zeigt jetzt aufs Verbergen", "verbergen" in w.console_toggle.toolTip())
    check("Es steht unten, nicht davor", not dock.isFloating())

    # Die Eingabemaske muss trotz Ausgabefenster bis zum letzten Feld reichen.
    scroll = w.editor.findChild(QScrollArea)
    unten = scroll.mapTo(w, scroll.rect().bottomLeft()).y()
    check(
        "Die Eingabemaske bleibt im Fenster",
        unten <= w.height(),
        f"Unterkante bei y={unten}, Fenster {w.height()} hoch",
    )

    dock.titleBarWidget().collapse.click()
    settle(250)
    check("Der Minus-Knopf klappt es wieder ein", not dock.isVisible())
    check("Der Schalter merkt es", "zeigen" in w.console_toggle.toolTip())

    w.console.begin("Prüfen")
    settle(250)
    check("Eine Ausgabezeile holt es von selbst hervor", dock.isVisible())

    dock.hide()
    settle(150)


def test_delete_image(app: QApplication, w: MainWindow) -> None:
    print("\nBild löschen")
    used = {info.src for info in w.repo.manifest.all()}
    dialog = ImagePickerDialog(w.repo.manifest, "", used, w, root=w.root)
    dialog.show()
    settle(300)

    check("Die Bildauswahl zeigt den ganzen Bestand", dialog.grid.count() == len(w.repo.manifest))

    dialog.grid.setCurrentRow(0)
    settle(200)
    check("Ein verwendetes Bild lässt sich nicht löschen", not dialog.delete_button.isEnabled())
    check("Der Grund steht am Knopf", "verwendet" in dialog.delete_button.toolTip())
    check("Ersetzen bleibt dennoch möglich", dialog.replace_button.isEnabled())

    # Ein Wegwerfbild, damit der „Ja“-Weg wirklich durchlaufen wird. Ihn
    # auszulassen wäre genau der Fehler, der diesen Test hervorgebracht hat.
    source = Path(tempfile.gettempdir()) / "tussetkapelle-uitest.png"
    image = QImage(320, 240, QImage.Format.Format_RGB32)
    image.fill(QColor("#304332"))
    image.save(str(source))
    # Ein eigener Ordner: so lässt sich mitprüfen, dass er nach dem Löschen
    # nicht leer zurückbleibt.
    target = "uitest-wegwerf/wegwerfbild.jpg"

    check("Wegwerfbild aufgenommen", dialog._job.add(source, target))
    w.repo.manifest.reload()
    dialog._fill(target)
    settle(200)
    check("Es steht im Bildverzeichnis", target in w.repo.manifest)
    check("Und ist löschbar, weil unverwendet", dialog.delete_button.isEnabled())

    press(app, QMessageBox.StandardButton.No)
    dialog.delete_image()
    settle(400)
    check("„Nein“ behält das Bild", (w.repo.manifest.images_dir / target).exists())

    press(app, QMessageBox.StandardButton.Yes)
    dialog.delete_image()
    settle(2500)
    check(
        "„Ja“ löscht das Bild wirklich",
        not (w.repo.manifest.images_dir / target).exists(),
    )
    check("Auch aus dem Bildverzeichnis", target not in w.repo.manifest)
    check(
        "Und ohne Reste",
        not list((w.repo.manifest.images_dir / "uitest-wegwerf").glob("wegwerfbild*")),
    )
    check(
        "Der leere Ordner bleibt nicht zurück",
        not (w.repo.manifest.images_dir / "uitest-wegwerf").exists(),
    )
    check(
        "Gefüllte Ordner bleiben unangetastet",
        (w.repo.manifest.images_dir / "kontakt").is_dir(),
    )
    check("Der Eingriff ist vermerkt", dialog.images_changed)

    source.unlink(missing_ok=True)
    dialog.reject()
    settle(150)


def wait_idle(w: MainWindow, seconds: int = 30) -> None:
    """Wartet, bis kein npm-Skript mehr läuft."""
    for _ in range(seconds * 4):
        settle(250)
        if not w.runner.busy:
            return


def test_stale_site(app: QApplication, w: MainWindow) -> None:
    """Die fertigen Seiten dürfen nicht hinter dem Bildbestand herlaufen.

    Der Anlass: ein Bild wurde aufgenommen, eingebaut, die Website erzeugt, der
    Abschnitt wieder entfernt und das Bild gelöscht. „Prüfen“ meldete darauf
    sieben defekte Bildverweise – zu Recht, denn die erzeugte Seite stand noch
    vom Erzeugen davor und nannte ein Bild, das es nicht mehr gab. Gelöscht war
    richtig; erzeugt war nichts.
    """
    print("\nVeraltete Website")
    w.build_site()
    wait_idle(w)
    check("Nach dem Erzeugen gilt die Website als aktuell", not w.repo.site_stale)
    check("Die Statuszeile schweigt dann", w.status_site.text() == "")

    # Jeder Eingriff in den Bildbestand schreibt src/image-manifest.json neu.
    (w.root / "src" / "image-manifest.json").touch()
    check("Ein neuerer Zeitstempel wird beim Start erkannt", ContentRepository(w.root).site_stale)

    w.repo.site_stale = True
    w._update_status()
    check("Die Statuszeile sagt es", "nicht auf dem neuesten Stand" in w.status_site.text())

    w.check_site()
    check("„Prüfen“ erzeugt erst neu", w._after_build == "check")
    wait_idle(w)
    check("Und prüft danach", w.status_result.text().startswith("Prüfen"))
    check("Die Prüfung geht durch", "erfolgreich" in w.status_result.text())
    check("Danach gilt die Website als aktuell", not w.repo.site_stale)
    check("Und die Statuszeile schweigt wieder", w.status_site.text() == "")


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
    test_console_dock(app, w)
    test_delete_image(app, w)
    test_stale_site(app, w)

    print()
    if _failures:
        print(f"FEHLGESCHLAGEN – {len(_failures)}: " + ", ".join(_failures))
        return 1
    print("Alle Bedienungstests bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
