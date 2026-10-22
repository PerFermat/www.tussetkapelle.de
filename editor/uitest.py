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
import socket
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QEventLoop, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDockWidget,
    QMessageBox,
    QScrollArea,
    QWidget,
)

from .model import spec_for
from .model.repository import ContentRepository
from .ui import MainWindow, mainwindow
from .ui.imagepicker import ImagePickerDialog
from .ui.widgets import ComboBox, SpinBox
from .model.search import find as find_in_content

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


def test_wheel_safe_fields(app: QApplication, w: MainWindow) -> None:
    """Das Mausrad darf beim Scrollen keinen Wert verstellen.

    Gemeldet wurde: auf der Startseite nach unten gescrollt, dabei mit dem
    Zeiger über „Schaltfläche führt zu“ geraten – das Feld sprang auf ein
    anderes Ziel. Lautlos, ohne Rückfrage, und erst auf der fertigen Website
    zu bemerken. Qt schickt Rad-Ereignisse an das Widget unter dem Zeiger,
    auch ohne Fokus; Auswahl- und Zahlenfelder verarbeiten sie von sich aus.

    Geprüft wird der Vertrag, auf dem Qts Weiterreichung beruht: Ein Feld, das
    das Ereignis *annimmt*, verschluckt es und der Scrollbereich bekommt nichts
    mehr. Unsere Felder müssen es freigeben und den Wert in Ruhe lassen.
    """
    print("\nMausrad über Eingabefeldern")

    def dreh(widget: QWidget) -> bool:
        """Ein Rad-Ereignis zustellen; True, wenn das Feld es angenommen hat."""
        event = QWheelEvent(
            QPointF(10, 10), QPointF(10, 10), QPoint(0, -120), QPoint(0, -360),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase, False,
        )
        event.setAccepted(False)
        QApplication.sendEvent(widget, event)
        return event.isAccepted()

    # Gegenprobe: Qts eigene Felder zeigen den Fehler – sonst prüfte der Test
    # womöglich gar nichts.
    roh = QComboBox()
    for text in ("eins", "zwei", "drei"):
        roh.addItem(text)
    vorher = roh.currentText()
    check("Qts Auswahlfeld verschluckt das Rad", dreh(roh))
    check("und verstellt dabei den Wert", roh.currentText() != vorher)

    eigen = ComboBox()
    for text in ("eins", "zwei", "drei"):
        eigen.addItem(text)
    vorher = eigen.currentText()
    check("Unser Auswahlfeld reicht das Rad weiter", not dreh(eigen))
    check("und lässt den Wert stehen", eigen.currentText() == vorher)

    zahl = SpinBox()
    zahl.setRange(0, 4000)
    zahl.setValue(350)
    check("Unser Zahlenfeld reicht das Rad weiter", not dreh(zahl))
    check("und lässt den Wert stehen", zahl.value() == 350, f"steht auf {zahl.value()}")

    # Und in der echten Maske: die Startseite hat die meisten Auswahlfelder.
    w.open_page("home")
    settle(400)
    felder = w.home_editor.findChildren(QComboBox)
    check("Die Startseite hat Auswahlfelder", len(felder) > 0, f"{len(felder)} gefunden")
    check(
        "Alle sind die radsichere Fassung",
        all(isinstance(f, ComboBox) for f in felder),
        f"{sum(1 for f in felder if not isinstance(f, ComboBox))} ungeschützt",
    )
    sauber = w.repo.dirty
    ziel = felder[0]
    stand = ziel.currentText()
    for _ in range(5):
        dreh(ziel)
    check("Fünfmal darüber gedreht ändert nichts", ziel.currentText() == stand)
    check("Und die Seite gilt weiter als ungeändert", w.repo.dirty == sauber)


def test_preview(app: QApplication, w: MainWindow) -> None:
    """„Vorschau“ muss den Testserver selbst starten und wieder aufräumen.

    Gemeldet wurde: Vorschau angeklickt, Browser zeigt einen Verbindungsfehler.
    Kein Fehler im Programm – es lief nur kein Testserver. Der Knopf öffnete die
    Adresse blind, und der Hinweis darauf stand in der Statuszeile, wo ihn
    niemand liest. Vor einer Vorführung ist das unangenehm.

    Geprüft wird beides: die Verkettung bei veralteter Website (erst erzeugen,
    dann zeigen) und der Server selbst – startet, liefert aus, wird beim
    Schließen beendet. Der Browseraufruf wird dabei abgefangen; aufspringen
    soll hier nichts.
    """
    print("\nVorschau")

    def port_frei() -> bool:
        with socket.socket() as probe:
            probe.settimeout(0.3)
            return probe.connect_ex(("127.0.0.1", mainwindow.PREVIEW_PORT)) != 0

    geoeffnet: list[str] = []
    echt_qt, echt_web = mainwindow.QDesktopServices, mainwindow.webbrowser
    mainwindow.QDesktopServices = type("Abfang", (), {
        "openUrl": staticmethod(lambda url: (geoeffnet.append(url.toString()), True)[1])
    })
    mainwindow.webbrowser = type("Abfang", (), {
        "open": staticmethod(lambda url: geoeffnet.append(url))
    })
    try:
        check("Vor dem Test läuft kein Server", port_frei())

        # 1. Veraltete Website: erst erzeugen, nicht sofort zeigen.
        w.repo.site_stale = True
        w.open_preview()
        # Ohne settle() geprüft, und das mit Absicht: Das Erzeugen dauert keine
        # halbe Sekunde. Wartet man erst, ist es schon durch, der Folgeschritt
        # abgearbeitet und _after_build wieder leer – der Test prüfte dann
        # nichts mehr. open_preview() kehrt nach dem Anstoßen sofort zurück.
        check("Bei veralteter Website wird erst erzeugt", w._after_build == "preview")
        check("Der Browser bleibt so lange zu", not geoeffnet)

        wait_idle(w)
        settle(600)
        check("Danach gilt die Website als aktuell", not w.repo.site_stale)
        check("Der Testserver antwortet", not port_frei())
        check("Und der Browser wurde geschickt", geoeffnet == [mainwindow.PREVIEW_URL])

        # 2. Ein zweiter Klick startet keinen zweiten Server.
        laufend = w._preview
        w.open_preview()
        settle(200)
        check("Ein zweiter Klick startet keinen zweiten Server", w._preview is laufend)

        # 3. Beim Schließen wird aufgeräumt.
        w._stop_preview_server()
        settle(400)
        check("Nach dem Schließen ist der Port wieder frei", port_frei())
        check("Und der Prozess ist vergessen", w._preview is None)
    finally:
        mainwindow.QDesktopServices, mainwindow.webbrowser = echt_qt, echt_web


def test_search(app: QApplication, w: MainWindow) -> None:
    """Suchen, zum Treffer springen – und dabei im Suchfeld bleiben.

    Gewünscht war: ein Wort eintippen, der Editor springt zur ersten Fundstelle
    *nach der aktuellen Stelle*, Pfeil ab zur nächsten, Pfeil auf zurück.

    Der erste Anlauf suchte bei jedem Tastendruck. Das war unbrauchbar: Der
    Sprung wechselt den Abschnitt, und mit ihm wanderte der Fokus aus dem
    Suchfeld – schon nach dem ersten Buchstaben. Gesucht wird deshalb erst auf
    die Eingabetaste, und der Fokus bleibt beim Blättern im Feld. Beides wird
    hier mit echten Tastendrücken geprüft, nicht mit gesetztem Text.
    """
    print("\nSuche im Inhalt")

    # Die Dialoge der vorangegangenen Tests haben das Fenster unaktiv gemacht,
    # und ohne aktives Fenster vergibt Qt keinen Fokus. Das ist ein Umstand der
    # Testumgebung, kein Verhalten des Editors – im Betrieb ist das Fenster aktiv.
    w.activateWindow()
    settle(200)
    w.switch_language("de")
    settle(300)
    w.open_page("home")
    settle(300)
    feld = w.search_bar.edit

    def tippe(wort: str) -> None:
        feld.clear()
        for zeichen in wort:
            QTest.keyClick(feld, zeichen)
            settle(20)

    def taste(key: Qt.Key, ms: int = 250) -> None:
        QTest.keyClick(feld, key)
        settle(ms)

    w.search_bar.focus()
    settle(120)
    check("Strg+F setzt den Fokus ins Suchfeld", QApplication.focusWidget() is feld)

    # -- Tippen darf nichts auslösen --------------------------------------- #
    tippe("Richtsfeld")
    check("Der Text steht im Feld", feld.text() == "Richtsfeld", feld.text())
    check("Tippen sucht noch nicht", not w._hits, f"{len(w._hits)} Treffer")
    check("Und behauptet nichts", w.search_bar.count.text() == "",
          w.search_bar.count.text())
    check("Der Fokus bleibt beim Tippen im Feld", QApplication.focusWidget() is feld)

    # -- Erst die Eingabetaste sucht --------------------------------------- #
    # Wie viele Treffer es gibt, verrät das Modell – eine eingetippte Zahl
    # veraltet mit dem nächsten Inhaltsstand. Der Test prüft das Verhalten,
    # nicht den Bestand.
    erwartet = find_in_content(w.repo, "Richtsfeld", w.lang)
    check("Der Bestand taugt für diesen Test", len(erwartet) >= 2,
          f"{len(erwartet)} Fundstellen")

    taste(Qt.Key.Key_Return)
    check("Die Eingabetaste sucht", len(w._hits) == len(erwartet),
          f"{len(w._hits)} statt {len(erwartet)}")
    check("Der Zähler sagt es", w.search_bar.count.text() == f"1 von {len(erwartet)}",
          w.search_bar.count.text())
    check("Der Editor ist hingesprungen", w.page.page_id == erwartet[0].page_id,
          f"steht auf {w.page.page_id}, erwartet {erwartet[0].page_id}")
    check("Und zwar auf den Abschnitt", w.block_index == w._hits[0].block_index)
    check("Der Fokus bleibt trotzdem im Feld", QApplication.focusWidget() is feld)

    # -- Blättern ----------------------------------------------------------- #
    seiten = []
    for _ in range(len(erwartet)):
        taste(Qt.Key.Key_Down, 150)
        seiten.append(w.page.page_id)
    # Einmal rundherum: Pfeil ab so oft wie es Treffer gibt führt zurück zum
    # Ausgangspunkt. Welche Seiten dazwischen liegen, sagt das Modell.
    folge = [h.page_id for h in erwartet[1:]] + [erwartet[0].page_id]
    check("Pfeil ab führt der Reihe nach weiter", seiten == folge,
          f"{seiten} statt {folge}")
    check("Und am Ende wieder von vorn", seiten[-1] == erwartet[0].page_id)
    check("Auch nach dem Blättern bleibt der Fokus", QApplication.focusWidget() is feld)

    taste(Qt.Key.Key_Up, 150)
    check("Pfeil auf führt zurück", w.search_bar.count.text() == f"{len(erwartet)} von {len(erwartet)}",
          w.search_bar.count.text())

    # -- Esc gibt den Fokus an die Fundstelle ------------------------------- #
    taste(Qt.Key.Key_Escape, 200)
    check("Esc holt den Fokus aus dem Suchfeld", QApplication.focusWidget() is not feld)

    # -- Markup und Bildpfade sind kein Lesetext ---------------------------- #
    w.search_bar.focus()
    tippe("href")
    taste(Qt.Key.Key_Return)
    check("Auszeichnung wird nicht durchsucht", not w._hits, f"{len(w._hits)} Treffer")
    check("Dann steht da „nichts gefunden“",
          w.search_bar.count.text() == "nichts gefunden", w.search_bar.count.text())

    tippe("neuetk/einleitung")
    taste(Qt.Key.Key_Return)
    check("Bildpfade werden nicht durchsucht", not w._hits, f"{len(w._hits)} Treffer")

    # -- Der Inhalt der Startseite steht neben den Abschnitten -------------- #
    tippe("Erinnerungsort")
    taste(Qt.Key.Key_Return)
    check("Auch der Inhalt der Startseite wird gefunden",
          any(h.page_id == "home" and h.block_index == -1 for h in w._hits),
          f"{len(w._hits)} Treffer")

    # -- Pfeil ab sucht ebenfalls, wenn der Begriff neu ist ----------------- #
    tippe("Richtsfeld")
    taste(Qt.Key.Key_Down)
    check("Pfeil ab sucht einen neuen Begriff von sich aus",
          len(w._hits) == len(erwartet), f"{len(w._hits)} Treffer")

    # -- Beim Sprachwechsel gilt die andere Fassung ------------------------- #
    # Nur prüfbar, solange es mehr als eine Fassung gibt. Englisch und Leichte
    # Sprache wurden auf Wunsch der Gemeinde entfernt; der Mechanismus bleibt
    # im Editor, er hat dann bloß nichts zu tun.
    andere = [l for l in w.repo.languages if l != w.lang]
    if andere:
        vorher = len(w._hits)
        w.switch_language(andere[0])
        settle(500)
        drüben = find_in_content(w.repo, "Richtsfeld", w.lang)
        check("Der Sprachwechsel sucht neu", len(w._hits) == len(drüben),
              f"{w.lang}: {len(w._hits)} statt {len(drüben)} (vorher {vorher})")
        feld.clear()
        settle(150)
        w.switch_language("de")
        settle(400)
    else:
        print("  --    Sprachwechsel: nur eine Fassung vorhanden, übersprungen")
    feld.clear()
    settle(150)


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
    test_wheel_safe_fields(app, w)
    test_preview(app, w)
    test_search(app, w)

    print()
    if _failures:
        print(f"FEHLGESCHLAGEN – {len(_failures)}: " + ", ".join(_failures))
        return 1
    print("Alle Bedienungstests bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
