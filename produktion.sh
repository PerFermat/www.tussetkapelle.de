#!/bin/bash

set -e

# Lokales Verzeichnis mit der neuen Version
LOKAL="/home/michael/git/www.tussetkapelle.de/"

# Serverdaten
SERVER="root@87.106.133.140"

# Verzeichnisse auf dem Server
WEBROOT="/var/www/tussetkapelle.de"
BACKUPDIR="/home/michael/backups"

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

rsync -avz --delete \
    "$LOKAL/" \
    "$SERVER:$WEBROOT/"

echo "Upload abgeschlossen."
