#!/usr/bin/env bash
# Bild-Pipeline für die Tussetkapelle-Website.
#
# bilder/ ist die Bildquelle des Projekts – alle Dateien liegen in der
# Versionsverwaltung. Dieses Skript erzeugt daraus den ausgelieferten Satz:
#
#   1. eine .webp-Variante je Bild, aber nur wenn sie kleiner ist als das JPEG.
#   2. eine Größenleiter (700/1000/1400 px) für die wenigen großen Bilder.
#   3. Thumbnails "-400" für das Galerie-Grid.
#   4. src/image-manifest.json über tools/make-manifest.mjs.
#
# Grundsatz: nie vergrößern. 55 der 116 Bilder des Bestands sind von sich aus
# kleiner als 400 px und werden unverändert in Nativgröße ausgeliefert.
#
# Bis Juli 2026 las Schritt 1 die Originale aus dem Archiv der Altsite von 2003,
# über einen fest verdrahteten Pfad außerhalb des Projekts. Das ist entfallen:
# der Bestand ist übernommen, und auf keinem anderen Rechner wäre es lauffähig
# gewesen. Neue Bilder kommen über den Inhaltseditor herein, der die drei
# Betriebsarten unten aufruft.
#
# Idempotent. Aufruf:
#   npm run images                                 alles auffrischen  [FORCE=1]
#   tools/build-images.sh --add     <datei> <ziel> Bild aufnehmen
#   tools/build-images.sh --replace <datei> <ziel> Bild ersetzen
#   tools/build-images.sh --remove           <ziel> Bild entfernen
#
# <ziel> ist ein Pfad relativ zu bilder/, etwa neuetk/anfahrt/wegweiser.jpg.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/bilder"
FORCE="${FORCE:-0}"

JPEG_Q=82
WEBP_Q=82
THUMB_MAX=400
LARGE_MIN=800          # ab dieser Breite gibt es eine Größenleiter
LADDER=(700 1000 1400) # Zwischenstufen; die Nativbreite kommt automatisch dazu

for bin in convert identify; do
  command -v $bin >/dev/null || { echo "FEHLER: ImageMagick ($bin) fehlt." >&2; exit 1; }
done
command -v node >/dev/null || { echo "FEHLER: Node.js fehlt (für das Bildverzeichnis)." >&2; exit 1; }

n_webp=0 n_webp_skip=0 n_thumb=0 n_native=0 n_ladder=0

width_of()   { identify -format '%w' "$1[0]" 2>/dev/null || echo 0; }
longest_of() { identify -format '%[fx:int(max(w,h))]' "$1[0]" 2>/dev/null || echo 0; }

# Abgeleitete Dateien (…-400.jpg, …-1000.jpg) beim Durchlauf überspringen.
is_derived() { [[ $(basename "$1") =~ -[0-9]{3,4}\.(jpg|webp)$ ]]; }

# $1 = Quelldatei (absolut), $2 = Zielpfad relativ zu bilder/
#
# Kleine JPEGs werden unverändert übernommen. Alles andere geht durch convert:
# große Bilder, weil q90 für die Auslieferung unnötig schwer ist – und PNG, GIF,
# WebP oder TIFF, weil die Schritte danach ausschließlich auf .jpg arbeiten.
ingest() {
  local src=$1 dst="$DEST/$2"
  mkdir -p "$(dirname "$dst")"
  if [[ ${src,,} == *.jpg || ${src,,} == *.jpeg ]] && (( $(width_of "$src") <= LARGE_MIN )); then
    cp -p "$src" "$dst"
  else
    # -alpha remove: eine durchsichtige Fläche würde im JPEG sonst schwarz.
    convert "$src" -background white -alpha remove -alpha off \
            -quality "$JPEG_Q" -sampling-factor 4:2:0 -interlace Plane -strip "$dst"
  fi
}

# <name>.webp neben <name>.jpg – nur behalten, wenn kleiner.
make_webp() {
  local jpg=$1 webp="${1%.*}.webp"
  [[ $FORCE == 1 || ! -f $webp || $jpg -nt $webp ]] || return 0
  convert "$jpg" -quality "$WEBP_Q" -define webp:method=6 -strip "$webp"
  if (( $(stat -c%s "$webp") >= $(stat -c%s "$jpg") )); then
    # WebP bringt bei diesem Bild nichts – entfernen, damit kein toter
    # <source> ausgeliefert wird und der Bestand nicht grundlos wächst.
    rm -f "$webp"; n_webp_skip=$((n_webp_skip + 1))
  else
    n_webp=$((n_webp + 1))
  fi
}

# Größenleiter für Bilder oberhalb LARGE_MIN.
make_ladder() {
  local jpg=$1 base="${1%.*}" w native
  native=$(width_of "$jpg")
  (( native > LARGE_MIN )) || return 0
  for w in "${LADDER[@]}"; do
    # Nur Stufen, die spürbar kleiner sind als das Original. Eine 1000-px-Stufe
    # eines 1087-px-Bildes wäre 8 % schmaler und praktisch ein Duplikat.
    (( w * 100 <= native * 80 )) || continue
    local ow="$base-$w.webp" oj="$base-$w.jpg"
    [[ $FORCE == 1 || ! -f $ow || $jpg -nt $ow ]] || continue
    convert "$jpg" -resize "${w}x>" -quality "$WEBP_Q" -define webp:method=6 -strip "$ow"
    convert "$jpg" -resize "${w}x>" -quality "$JPEG_Q" -sampling-factor 4:2:0 -interlace Plane -strip "$oj"
    n_ladder=$((n_ladder + 1))
  done
}

# Thumbnail für das Galerie-Grid. Bilder, die von sich aus unter THUMB_MAX
# liegen, bekommen keines – das Thumbnail wäre eine bitgleiche Kopie.
make_thumb() {
  local jpg=$1 base="${1%.*}"
  local tw="$base-$THUMB_MAX.webp" tj="$base-$THUMB_MAX.jpg"
  if (( $(longest_of "$jpg") <= THUMB_MAX )); then
    n_native=$((n_native + 1)); return 0
  fi
  [[ $FORCE == 1 || ! -f $tw || $jpg -nt $tw ]] || return 0
  convert "$jpg" -resize "${THUMB_MAX}x${THUMB_MAX}>" -quality "$WEBP_Q" \
          -define webp:method=6 -strip "$tw"
  convert "$jpg" -resize "${THUMB_MAX}x${THUMB_MAX}>" -quality "$JPEG_Q" \
          -interlace Plane -strip "$tj"
  n_thumb=$((n_thumb + 1))
}

# Alle Ableitungen eines Bildes entfernen: die WebP-Variante der Nativgröße und
# jede Größenstufe. Nötig vor jedem Ersetzen, weil eine neue Fassung auch
# kleiner sein kann – eine 1400-px-Stufe eines 900-px-Bildes bliebe sonst als
# tote Datei liegen.
drop_derived() {
  local jpg=$1 stem="${1%.*}" f
  rm -f "$stem.webp"
  for f in "$stem"-*; do
    [[ -f $f ]] || continue
    is_derived "$f" && rm -f "$f"
  done
}

# Ordner aufräumen, die nur wegen des gelöschten Bildes bestanden. Ohne das
# bleibt nach dem letzten Bild ein leeres Verzeichnis zurück, das niemand mehr
# anfasst. Aufgeräumt wird ausschließlich unterhalb von bilder/ und nur, solange
# rmdir zustimmt – ein Ordner mit Inhalt bleibt unangetastet.
prune_dirs() {
  local dir=$1
  while [[ $dir == "$DEST"/* ]] && rmdir "$dir" 2>/dev/null; do
    dir=$(dirname "$dir")
  done
}

# Ableitungen für genau eine Datei, danach das Bildverzeichnis.
derive_one() {
  local jpg=$1
  make_webp "$jpg"
  make_ladder "$jpg"
  make_thumb "$jpg"
}

manifest() { node "$ROOT/tools/make-manifest.mjs"; }

# Zielpfad prüfen: relativ, ohne Ausbruch aus bilder/, mit erlaubter Endung.
check_target() {
  local target=$1 pattern=$2
  [[ $target != /* && $target != *..* ]] \
    || { echo "FEHLER: Ungültiger Zielpfad: $target" >&2; exit 1; }
  [[ ${target,,} =~ $pattern ]] \
    || { echo "FEHLER: Zielpfad passt nicht: $target" >&2; exit 1; }
}

# --------------------------------------------------------------------------- #
# Betriebsarten                                                               #
# --------------------------------------------------------------------------- #

case "${1:-}" in
  --add|--replace)
    mode=$1; source=${2:-}; target=${3:-}
    [[ -n $source && -n $target ]] || { echo "Aufruf: $0 $mode <datei> <ziel>" >&2; exit 2; }
    [[ -f $source ]] || { echo "FEHLER: Datei nicht gefunden: $source" >&2; exit 1; }
    check_target "$target" '\.jpg$'
    dst="$DEST/$target"

    if [[ $mode == --add ]]; then
      [[ -e $dst ]] && { echo "FEHLER: Es gibt dort schon ein Bild: $target" >&2; exit 1; }
    else
      [[ -f $dst ]] || { echo "FEHLER: Kein Bild zum Ersetzen: $target" >&2; exit 1; }
      drop_derived "$dst"
    fi

    FORCE=1 ingest "$source" "$target"
    derive_one "$dst"
    manifest
    printf '%s: %s (%s)\n' \
      "$([[ $mode == --add ]] && echo Aufgenommen || echo Ersetzt)" \
      "$target" "$(identify -format '%wx%h' "$dst[0]")"
    exit 0
    ;;

  --remove)
    target=${2:-}
    [[ -n $target ]] || { echo "Aufruf: $0 --remove <ziel>" >&2; exit 2; }
    check_target "$target" '\.(jpg|gif|png)$'
    dst="$DEST/$target"
    [[ -f $dst ]] || { echo "FEHLER: Kein Bild zum Löschen: $target" >&2; exit 1; }

    # Ob das Bild noch irgendwo verwendet wird, weiß dieses Skript nicht. Diese
    # Prüfung gehört in den Editor, der als einziger den Inhalt kennt.
    drop_derived "$dst"
    rm -f "$dst"
    prune_dirs "$(dirname "$dst")"
    manifest
    echo "Gelöscht: $target"
    exit 0
    ;;

  "")
    ;;

  *)
    echo "Unbekannte Betriebsart: $1" >&2
    echo "Aufruf: $0 [--add <datei> <ziel> | --replace <datei> <ziel> | --remove <ziel>]" >&2
    exit 2
    ;;
esac

# --------------------------------------------------------------------------- #
# Sammellauf über den gesamten Bestand                                        #
# --------------------------------------------------------------------------- #

echo "== 1/4  WebP-Varianten (q$WEBP_Q)"
while IFS= read -r -d '' f; do is_derived "$f" || make_webp "$f"; done \
  < <(find "$DEST" -type f -name '*.jpg' -print0)
echo "   $n_webp erzeugt, $n_webp_skip verworfen (WebP war nicht kleiner)"

echo "== 2/4  Größenleiter für große Bilder (${LADDER[*]} px)"
while IFS= read -r -d '' f; do is_derived "$f" || make_ladder "$f"; done \
  < <(find "$DEST" -type f -name '*.jpg' -print0)
echo "   $n_ladder Stufe(n) erzeugt"

echo "== 3/4  Galerie-Thumbnails (max $THUMB_MAX px)"
while IFS= read -r -d '' f; do is_derived "$f" || make_thumb "$f"; done \
  < <(find "$DEST" -type f -name '*.jpg' -print0)
echo "   $n_thumb erzeugt, $n_native bereits klein genug"

echo "== 4/4  Bildverzeichnis"
printf '   '
manifest

echo
printf 'Fertig: %s Dateien, %s in %s\n' \
  "$(find "$DEST" -type f | wc -l)" "$(du -sh "$DEST" | cut -f1)" "${DEST#"$ROOT"/}"
