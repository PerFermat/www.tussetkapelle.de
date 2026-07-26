#!/usr/bin/env bash
# Einmalige Wiederherstellung des Quellarchivs bilder/ der Altsite.
#
# Hintergrund: Das Verzeichnis wurde am 26.07.2026 versehentlich gelöscht. Die
# Bild-Pipeline hatte kurz zuvor Kopien ins Zielverzeichnis gelegt; 113 der 114
# Dateien sind dort bitgleich erhalten (mit cp -p kopiert, Original-Zeitstempel
# von 2003 blieben erhalten, Byte-Größen stimmen mit den Aufzeichnungen überein).
#
# Nicht bitgleich wiederherstellbar: bilder/altetk/tusset_alt.jpg
#   Original: 1087x1447, q90, 905.651 Bytes
#   Vorhanden: dieselben Pixelmaße, aber mit q82 neu kodiert (760.186 Bytes).
# Diese Datei wird deshalb NICHT unter dem Originalnamen abgelegt, sondern als
#   tusset_alt.NEUKODIERT-q82.jpg
# damit der Fehlbestand im Archiv sichtbar bleibt.
#
# Alle Pfade absolut – das Missgeschick entstand durch einen relativen Pfad.
set -euo pipefail

SRC=/home/michael/Dokumente/tussent/www.tussetkapelle.de
TGT=/home/michael/git/www.tussetkapelle.de
LIST="$TGT/tools/archive-filelist.txt"

[[ -f $LIST ]] || { echo "FEHLER: Dateiliste fehlt: $LIST" >&2; exit 1; }

ok=0 miss=0 special=0

while IFS= read -r p; do
  [[ -n $p && $p != \#* ]] || continue

  # Pfad, unter dem die Pipeline die Datei im Zielverzeichnis abgelegt hat.
  norm=$(printf '%s' "$p" | tr '[:upper:]' '[:lower:]' | tr '~' '-')

  if [[ ! -f "$TGT/$norm" ]]; then
    echo "FEHLT im Ziel: $p"; miss=$((miss + 1)); continue
  fi

  if [[ $p == bilder/altetk/tusset_alt.jpg ]]; then
    dest="$SRC/bilder/altetk/tusset_alt.NEUKODIERT-q82.jpg"
    mkdir -p "$(dirname "$dest")"
    cp -p "$TGT/$norm" "$dest"
    special=$((special + 1))
    continue
  fi

  mkdir -p "$SRC/$(dirname "$p")"
  cp -p "$TGT/$norm" "$SRC/$p"
  ok=$((ok + 1))
done < "$LIST"

cat > "$SRC/bilder/altetk/FEHLBESTAND.txt" <<'EOF'
Fehlbestand in diesem Verzeichnis
=================================

tusset_alt.jpg  (Original, 1087x1447 px, JPEG-Qualität 90, 905.651 Bytes)
ist am 26.07.2026 verloren gegangen und NICHT im Archiv enthalten.

Stattdessen liegt hier:
  tusset_alt.NEUKODIERT-q82.jpg   1087x1447 px, Qualität 82, 760.186 Bytes

Gleiche Bildmaße und gleicher Bildinhalt, aber einmal neu komprimiert
(Generationsverlust). Falls ein Backup des Originals existiert, sollte es
diese Datei ersetzen; danach kann diese Notiz entfernt werden.

Das Original ist unter Umständen noch über die Live-Website erreichbar:
  https://www.tussetkapelle.de/bilder/altetk/tusset_alt.jpg
EOF

echo
echo "Wiederhergestellt : $ok Dateien bitgleich"
echo "Als Neukodierung  : $special Datei (tusset_alt.NEUKODIERT-q82.jpg)"
echo "Fehlend           : $miss"
echo "Dateien in $SRC/bilder: $(find "$SRC/bilder" -type f | wc -l)"
