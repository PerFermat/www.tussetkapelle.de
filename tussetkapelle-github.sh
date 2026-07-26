#!/bin/bash

# Upload-Skript für Tussetkapelle Webseite nach GitHub

REPO="/home/michael/git/www.tussetkapelle.de"

cd "$REPO" || {
    echo "Fehler: Repository nicht gefunden: $REPO"
    exit 1
}

echo "=== Git Status ==="
git status

echo
read -p "Änderungen nach GitHub übertragen? (j/n): " ANTWORT

if [[ "$ANTWORT" != "j" && "$ANTWORT" != "J" ]]; then
    echo "Abgebrochen."
    exit 0
fi

echo
echo "=== Dateien hinzufügen ==="
git add .

echo
echo "=== Commit erstellen ==="
DATUM=$(date "+%Y-%m-%d %H:%M:%S")
git commit -m "Website Update $DATUM"

if [ $? -ne 0 ]; then
    echo "Kein Commit notwendig oder Fehler."
fi

echo
echo "=== Push nach GitHub ==="
git push

if [ $? -eq 0 ]; then
    echo
    echo "================================="
    echo "Upload erfolgreich abgeschlossen."
    echo "================================="
else
    echo
    echo "Fehler beim Push nach GitHub!"
    exit 1
fi
