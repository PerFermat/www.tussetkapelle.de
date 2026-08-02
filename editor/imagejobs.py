"""Bilder aufnehmen, ersetzen, löschen.

Die eigentliche Arbeit macht ``tools/build-images.sh``. Dieses Modul ruft es auf
und wartet, bis die Größenstufen wirklich auf der Platte liegen – erst danach
darf die Oberfläche das Bildverzeichnis neu lesen.

Die Aufteilung ist bewusst: **jede Angabe zur Bildqualität steht allein im
Skript** (Qualität 82, Größenleiter 700/1000/1400, Thumbnails bis 400 px, WebP
nur wenn kleiner). Würde der Editor die Stufen selbst erzeugen, gäbe es zwei
Stellen, die dasselbe festlegen – und irgendwann liefen sie auseinander.

Umgekehrt steht die Namensbildung hier und nicht im Skript: sie ist eine Frage
der Adressbildung. Ein Bild wird Teil einer URL, und dort haben Umlaute,
Leerzeichen und Großbuchstaben nichts verloren.
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog, QWidget

__all__ = ["ImageJob", "derived_files", "normalize_name", "split_target"]

#: Was der Dateidialog annimmt. Alles landet am Ende als JPEG in bilder/.
IMAGE_FILTER = (
    "Bilder (*.jpg *.jpeg *.png *.gif *.webp *.tif *.tiff "
    "*.JPG *.JPEG *.PNG *.GIF *.WEBP *.TIF *.TIFF)"
)

_UMLAUTS = {
    "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    "á": "a", "à": "a", "â": "a", "é": "e", "è": "e", "ê": "e",
    "í": "i", "ì": "i", "ó": "o", "ò": "o", "ô": "o", "ú": "u", "ù": "u",
    "ç": "c", "ñ": "n",
}

#: Muster einer abgeleiteten Datei – ``foo-400.jpg``, ``foo-1400.webp``.
_DERIVED = re.compile(r"-\d{3,4}\.(jpg|webp)$")


def _fold(text: str) -> str:
    out = []
    for char in text.lower():
        out.append(_UMLAUTS.get(char, char))
    return "".join(out)


def normalize_name(filename: str) -> str:
    """Macht aus einem beliebigen Dateinamen einen tauglichen Bildnamen.

    ``Prüf Bild~1.JPG`` wird zu ``pruef-bild-1.jpg``. Die Endung ist immer
    ``.jpg``: die Größenleiter und die WebP-Varianten entstehen ausschließlich
    aus JPEG-Dateien, ein PNG bliebe im Bestand ohne jede Stufe liegen.
    """
    stem = _fold(Path(filename).stem)
    stem = re.sub(r"[~_\s]+", "-", stem)
    stem = re.sub(r"[^a-z0-9.-]", "", stem)
    stem = re.sub(r"-{2,}", "-", stem).strip("-.")
    return f"{stem or 'bild'}.jpg"


def split_target(target: str) -> tuple[str, str]:
    """Zerlegt ``neuetk/anfahrt/wegweiser.jpg`` in Ordner und Dateiname."""
    return (target.rsplit("/", 1)[0], target.rsplit("/", 1)[-1]) if "/" in target else ("", target)


def derived_files(images_dir: Path, src: str) -> list[Path]:
    """Alle Dateien, die zu einem Bild gehören – Nativfassung eingeschlossen.

    Wird gebraucht, um vor dem Löschen zu sagen, was genau verschwindet.
    Gelöscht wird trotzdem im Skript: es soll nur eine Stelle geben, die im
    Bildbestand aufräumt.
    """
    native = images_dir / src
    stem = native.with_suffix("")
    found = [native] if native.exists() else []
    webp = stem.with_suffix(".webp")
    if webp.exists():
        found.append(webp)
    if native.parent.is_dir():
        for path in sorted(native.parent.glob(stem.name + "-*")):
            if path.is_file() and _DERIVED.search(path.name):
                found.append(path)
    return found


def human_size(total: int) -> str:
    kb = total / 1024
    return f"{kb:.0f} kB" if kb < 1024 else f"{kb / 1024:.1f} MB"


class ImageJob:
    """Ein Aufruf von ``tools/build-images.sh``, mit Fortschrittsanzeige.

    Der Aufruf blockiert bewusst: der Bildauswahl-Dialog darf erst weitermachen,
    wenn das Bildverzeichnis geschrieben ist. Damit das Fenster dabei nicht
    einfriert, läuft eine eigene Ereignisschleife in der ``QProgressDialog``.
    """

    def __init__(self, root: Path, parent: QWidget | None = None) -> None:
        self.root = root
        self.parent = parent
        self.output: list[str] = []

    # -- Betriebsarten ----------------------------------------------------- #

    def add(self, source: Path, target: str) -> bool:
        return self._run(
            ["--add", str(source), target],
            "Bild wird aufgenommen",
            f"„{target}“ wird aufbereitet:\nGrößenstufen, WebP und Bildverzeichnis.",
        )

    def replace(self, source: Path, target: str) -> bool:
        return self._run(
            ["--replace", str(source), target],
            "Bild wird ersetzt",
            f"„{target}“ wird neu aufbereitet:\nGrößenstufen, WebP und Bildverzeichnis.",
        )

    def remove(self, target: str) -> bool:
        return self._run(
            ["--remove", target],
            "Bild wird gelöscht",
            f"„{target}“ wird mit allen Größenstufen entfernt.",
        )

    # -- Durchführung ------------------------------------------------------- #

    def _run(self, args: list[str], title: str, text: str) -> bool:
        script = self.root / "tools" / "build-images.sh"
        if not script.exists():
            self._error(title, f"Das Skript fehlt:\n{script}")
            return False

        self.output = []
        process = QProcess()
        process.setWorkingDirectory(str(self.root))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(
            lambda: self.output.extend(
                process.readAllStandardOutput().data().decode("utf-8", "replace").splitlines()
            )
        )

        # Ohne Abbruchknopf: ein halb erzeugter Bildsatz wäre schlimmer als
        # ein paar Sekunden Warten.
        dialog = QProgressDialog(text, "", 0, 0, self.parent)
        dialog.setWindowTitle(title)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.show()
        QApplication.processEvents()

        process.start("bash", [str(script), *args])
        if not process.waitForStarted(5000):
            dialog.close()
            self._error(title, "Das Bildskript ließ sich nicht starten. Ist bash vorhanden?")
            return False

        while process.state() != QProcess.ProcessState.NotRunning:
            process.waitForFinished(50)
            QApplication.processEvents()
        dialog.close()

        ok = (
            process.exitStatus() == QProcess.ExitStatus.NormalExit
            and process.exitCode() == 0
        )
        if not ok:
            self._error(title, self._explain(process.exitCode()))
        return ok

    def _explain(self, code: int) -> str:
        tail = [line for line in self.output if line.strip()][-6:]
        detail = "\n".join(tail) if tail else "(keine Ausgabe)"
        hint = ""
        if any("ImageMagick" in line for line in self.output):
            hint = (
                "\n\nImageMagick fehlt. Unter Debian und Ubuntu hilft:\n"
                "    sudo apt install imagemagick"
            )
        elif any("Node.js" in line for line in self.output):
            hint = "\n\nNode.js fehlt – es wird für das Bildverzeichnis gebraucht."
        return f"Das Bildskript brach mit dem Rückgabewert {code} ab.\n\n{detail}{hint}"

    def _error(self, title: str, text: str) -> None:
        box = QMessageBox(QMessageBox.Icon.Warning, title, text, parent=self.parent)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.exec()
