#!/usr/bin/env bash
# Lokaler Testserver für die Tussetkapelle-Website.
# Fester Port, damit Lesezeichen und Screenshots über Sitzungen hinweg stabil bleiben.
set -euo pipefail
npm run build

PORT="${TK_PORT:-8473}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Tussetkapelle – lokaler Testserver"
echo "  Wurzel : $ROOT"
echo "  Adresse: http://localhost:$PORT/"
echo "  Beenden: Strg+C"
echo

exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT"
