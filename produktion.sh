#!/bin/bash
#
# Überträgt die *erzeugte* Website auf den Server der Gemeinde Philippsreut.
#
#   ./produktion.sh            überträgt
#   ./produktion.sh --probe    zeigt nur, was übertragen würde (rsync --dry-run)
#
# Hochgeladen wird ausschließlich das Auslieferungsgut: die von `node build.js`
# erzeugten HTML-Seiten, assets/, bilder/, sitemap.xml, robots.txt, 404.html.
#
# Alles, was nur zur Pflege gehört, bleibt hier und auf GitHub: die Quellen in
# src/, die Bild- und Prüfwerkzeuge in tools/, der Inhaltseditor, die Skripte,
# README/ToDo, das alte Archiv in alt/ und sämtliche versteckten Verzeichnisse
# (.git, .venv, .claude). Auf dem Server hat davon nichts etwas zu suchen –
# es wäre über die Adresse abrufbar, ohne je gebraucht zu werden.
#
# Der Server hält danach nichts als das Auslieferungsgut: --delete-excluded
# löscht dort nicht nur, was hier verschwunden ist, sondern auch alles
# Ausgeschlossene. Ein bloßes --delete genügt dafür nicht – es schützt die
# ausgeschlossenen Dateien auf der Gegenseite, ein einmal hochgeladenes src/
# bliebe also für immer liegen.
#
# Damit ist der Webroot allein aus diesem Verzeichnis bestimmt. Was dort von
# Hand abgelegt wurde, ist nach dem nächsten Lauf fort – es steht nur noch im
# Backup, das vorher erstellt wird.

set -euo pipefail

# Lokales Verzeichnis mit der neuen Version
LOKAL="/home/michael/git/www.tussetkapelle.de"

# Serverdaten
SERVER="root@87.106.133.140"

# Verzeichnisse auf dem Server
WEBROOT="/var/www/tussetkapelle.de"
BACKUPDIR="/home/michael/backups"

# Nicht auszuliefern – Reihenfolge wie im Projektverzeichnis.
AUSNAHMEN=(
    "/.*"                 # .git .venv .claude .gitignore – alles Versteckte
    "/src/"               # Inhalte und Vorlagen, aus denen erzeugt wird
    "/tools/"             # Bild-Pipeline, Manifest, Galerie, Prüfungen
    "/editor/"            # Inhaltseditor
    "/editor.py"
    "/editor.sh"
    "/alt/"               # Archiv der alten Webseite
    "/build.js"
    "/serve.sh"
    "/produktion.sh"
    "/tussetkapelle-github.sh"
    "/package.json"
    "/package-lock.json"
    "/node_modules/"
    "/requirements.txt"
    "/README.md"
    "/ToDo.md"
    "__pycache__/"
    "*.pyc"
    "*.json.tmp"          # Zwischendateien des atomaren Speicherns
)

TROCKEN=""
if [ "${1:-}" = "--probe" ]; then
    TROCKEN="--dry-run"
fi

# rsync-Argumente aus der Liste bauen
RSYNC_AUSNAHMEN=()
for muster in "${AUSNAHMEN[@]}"; do
    RSYNC_AUSNAHMEN+=(--exclude "$muster")
done

# Ohne erzeugte Seiten wäre --delete auf dem Server verheerend.
if [ ! -f "$LOKAL/index.html" ]; then
    echo "Fehler: $LOKAL/index.html fehlt – erst 'npm run build' laufen lassen." >&2
    exit 1
fi

if [ -n "$TROCKEN" ]; then
    echo "Probelauf – es wird nichts verändert."
    rsync -avz --delete --delete-excluded "${RSYNC_AUSNAHMEN[@]}" \
        "$TROCKEN" \
        "$LOKAL/" \
        "$SERVER:$WEBROOT/"
    exit 0
fi

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUPFILE="$BACKUPDIR/backup-$TIMESTAMP.zip"

echo "Erstelle Backup auf dem Server..."

ssh "$SERVER" "
    mkdir -p '$BACKUPDIR' &&
    cd '$WEBROOT' &&
    zip -rq '$BACKUPFILE' .
"

echo "Backup erstellt: $BACKUPFILE"

echo "Kopiere neue Version auf den Server..."

rsync -avz --delete --delete-excluded "${RSYNC_AUSNAHMEN[@]}" \
    "$LOKAL/" \
    "$SERVER:$WEBROOT/"

echo "Upload abgeschlossen."
