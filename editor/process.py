"""Website erzeugen und prüfen.

Die beiden Knöpfe rufen ``npm run build`` und ``npm run check`` auf. Der Aufruf
läuft nebenläufig: die Ausgabe erscheint zeilenweise im Konsolenfenster,
während der Editor bedienbar bleibt. Ein blockierender Aufruf wäre bei
60 Seiten zwar nur eine Sekunde, aber ein eingefrorenes Fenster verunsichert.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

__all__ = ["NpmRunner"]


class NpmRunner(QObject):
    """Startet npm-Skripte und reicht deren Ausgabe weiter."""

    #: Eine Zeile Ausgabe (Text, ist_fehler)
    line = Signal(str, bool)
    #: Vorgang gestartet (Klartextname)
    started = Signal(str)
    #: Vorgang beendet (Klartextname, Erfolg, Rückgabewert)
    finished = Signal(str, bool, int)

    LABELS = {"build": "Website erzeugen", "check": "Prüfen", "images": "Bilder aufbereiten"}

    def __init__(self, root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.root = root
        self._process: QProcess | None = None
        self._script = ""

    @property
    def busy(self) -> bool:
        return self._process is not None

    def run(self, script: str) -> bool:
        """Startet ein npm-Skript. Gibt False zurück, wenn schon eines läuft."""
        if self.busy:
            return False
        self._script = script
        label = self.LABELS.get(script, script)

        process = QProcess(self)
        process.setWorkingDirectory(str(self.root))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process.readyReadStandardOutput.connect(self._read_out)
        process.readyReadStandardError.connect(self._read_err)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_error)
        self._process = process

        self.started.emit(label)
        process.start("npm", ["run", "--silent", script])
        return True

    def stop(self) -> None:
        if self._process is not None:
            self._process.kill()

    # -- Ausgabe ----------------------------------------------------------- #

    def _read_out(self) -> None:
        self._emit(self._process.readAllStandardOutput().data(), False)

    def _read_err(self) -> None:
        # npm schreibt auch Fortschritt nach stderr; als Fehler gilt erst der
        # Rückgabewert. Rot eingefärbt wird nur, was wie ein Fehler aussieht.
        self._emit(self._process.readAllStandardError().data(), None)

    def _emit(self, raw: bytes, is_error: bool | None) -> None:
        text = raw.decode("utf-8", errors="replace")
        for line in text.splitlines():
            flag = is_error
            if flag is None:
                lowered = line.lower()
                flag = any(
                    word in lowered
                    for word in ("error", "fehler", "beanstandung", "failed", "throw")
                )
            self.line.emit(line, bool(flag))

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.line.emit(
                "npm konnte nicht gestartet werden. Ist Node.js installiert "
                "und im Suchpfad?",
                True,
            )

    def _on_finished(self, code: int, status: QProcess.ExitStatus) -> None:
        label = self.LABELS.get(self._script, self._script)
        ok = code == 0 and status == QProcess.ExitStatus.NormalExit
        self._process = None
        self.finished.emit(label, ok, code)
