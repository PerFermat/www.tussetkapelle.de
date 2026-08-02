#!/usr/bin/env bash
#
# Startet den Inhaltseditor.
#
#   ./editor.sh        oder      npm run editor
#
# Beim ersten Aufruf wird eine eigene Python-Umgebung unter .venv/ angelegt und
# PySide6 hineininstalliert (rund 300 MB, dauert ein bis zwei Minuten). Jeder
# weitere Start geht sofort.
#
# Eine eigene Umgebung ist nötig, weil aktuelle Linux-Systeme das
# systemweite Python schützen (PEP 668) und eine Installation dorthin ablehnen.

set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
PYTHON="${VENV}/bin/python"

if [ ! -x "${PYTHON}" ]; then
  echo "Richte die Python-Umgebung ein – das dauert beim ersten Mal etwas."
  python3 -m venv "${VENV}"
  "${VENV}/bin/pip" install --quiet --upgrade pip
  "${VENV}/bin/pip" install --quiet -r requirements.txt
  echo "Fertig."
fi

if ! "${PYTHON}" -c "import PySide6" >/dev/null 2>&1; then
  echo "PySide6 fehlt – installiere nach."
  "${VENV}/bin/pip" install --quiet -r requirements.txt
fi

exec "${PYTHON}" -m editor "$@"
