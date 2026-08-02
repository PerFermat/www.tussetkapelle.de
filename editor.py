#!/usr/bin/env python3
"""
Startet den Inhaltseditor.

Beim ersten Start wird automatisch eine virtuelle Python-Umgebung
unter .venv angelegt und die Abhängigkeiten aus requirements.txt
installiert.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / ".venv"


def get_venv_python() -> Path:
    """Liefert den Python-Pfad innerhalb der virtuellen Umgebung."""
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def get_venv_pip() -> Path:
    """Liefert den Pip-Pfad innerhalb der virtuellen Umgebung."""
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def run(cmd):
    subprocess.check_call(cmd, cwd=BASE_DIR)


def ensure_venv():
    python = get_venv_python()

    if python.exists():
        return

    print("Richte die Python-Umgebung ein – das dauert beim ersten Mal etwas.")

    run([sys.executable, "-m", "venv", str(VENV_DIR)])

    pip = get_venv_pip()

    run([str(pip), "install", "--quiet", "--upgrade", "pip"])
    run([str(pip), "install", "--quiet", "-r", "requirements.txt"])

    print("Fertig.")


def ensure_requirements():
    python = get_venv_python()

    result = subprocess.run(
        [str(python), "-c", "import PySide6"],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if result.returncode == 0:
        return

    print("PySide6 fehlt – installiere nach.")

    pip = get_venv_pip()
    run([str(pip), "install", "--quiet", "-r", "requirements.txt"])


def main():
    os.chdir(BASE_DIR)

    ensure_venv()
    ensure_requirements()

    python = get_venv_python()

    os.execv(
        str(python),
        [str(python), "-m", "editor", *sys.argv[1:]],
    )


if __name__ == "__main__":
    main()
