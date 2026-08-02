"""Einstiegspunkt.

    python -m editor            im Projektverzeichnis
    python -m editor <Pfad>     für ein anderes Arbeitsverzeichnis
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox


def _project_root(argv: list[str]) -> Path:
    if len(argv) > 1:
        return Path(argv[1]).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    root = _project_root(argv)

    app = QApplication(argv[:1])
    app.setApplicationName("Tussetkapelle-Editor")
    app.setOrganizationName("Tussetkapelle")

    missing = [
        name
        for name in ("src/content", "src/image-manifest.json", "package.json")
        if not (root / name).exists()
    ]
    if missing:
        QMessageBox.critical(
            None,
            "Projekt nicht gefunden",
            f"In „{root}“ fehlen:\n\n• " + "\n• ".join(missing) + "\n\n"
            "Bitte den Editor im Projektverzeichnis von www.tussetkapelle.de "
            "starten oder den Pfad als Argument angeben.",
        )
        return 1

    from .model import JsonSyntaxError
    from .ui import MainWindow

    try:
        window = MainWindow(root)
    except JsonSyntaxError as err:
        QMessageBox.critical(
            None,
            "Eine Inhaltsdatei ist beschädigt",
            f"{err}\n\nBitte die Datei in einem Texteditor berichtigen oder aus "
            "der Versionsverwaltung zurückholen.",
        )
        return 1

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
