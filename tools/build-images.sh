#!/usr/bin/env bash
# Bild-Pipeline für die Tussetkapelle-Website.
#
# Die Altsite bleibt der unangetastete Archivbestand (nur lesend). In bilder/
# entsteht daraus ein für die Auslieferung optimierter Satz:
#
#   1. Kopien der Originale mit normalisierten Dateinamen
#      (Kleinschreibung, ~ -> -, .JPG -> .jpg).
#      Bilder breiter als LARGE_MIN werden dabei mit q82 neu kodiert – die
#      Originale liegen mit q90 vor und sind für Webauslieferung unnötig schwer.
#   2. eine .webp-Variante je Bild, aber nur wenn sie kleiner ist als das JPEG.
#   3. eine Größenleiter (700/1000/1400 px) für die wenigen großen Bilder.
#   4. Thumbnails "-400" für das Galerie-Grid.
#
# Grundsatz: nie vergrößern. 55 der 116 Bilder des Bestands sind von sich aus
# kleiner als 400 px und werden unverändert in Nativgröße ausgeliefert.
#
# Idempotent. Aufruf: npm run images   [TK_SRC=<pfad>]  [FORCE=1]
set -euo pipefail

SRC="${TK_SRC:-/home/michael/Dokumente/tussent/www.tussetkapelle.de}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/bilder"
FORCE="${FORCE:-0}"

JPEG_Q=82
WEBP_Q=82
THUMB_MAX=400
LARGE_MIN=800          # ab dieser Breite gibt es eine Größenleiter
LADDER=(700 1000 1400) # Zwischenstufen; die Nativbreite kommt automatisch dazu

[[ -d $SRC ]] || { echo "FEHLER: Quellverzeichnis nicht gefunden: $SRC" >&2; exit 1; }
for bin in convert identify; do
  command -v $bin >/dev/null || { echo "FEHLER: ImageMagick ($bin) fehlt." >&2; exit 1; }
done

# Frameset-Chrome der Altsite – kein Inhalt, wird nicht übernommen.
# tusset_alt.NEUKODIERT-q82.jpg wird von der Ersatzregel weiter unten unter dem
# kanonischen Namen übernommen und darf hier nicht zusätzlich einlaufen.
SKIP_NAMES=("back.gif" "Image6_.gif" "tusset_alt.NEUKODIERT-q82.jpg")

n_copy=0 n_reenc=0 n_webp=0 n_webp_skip=0 n_thumb=0 n_native=0 n_ladder=0

# Behebt u. a. SM~neubauer~und~emil.jpg / lr~schumertl~und~emil.jpg, die im
# Original deshalb über absolute http://-URLs mit %7E eingebunden werden mussten.
normalize() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr '~' '-'; }

width_of()   { identify -format '%w' "$1[0]" 2>/dev/null || echo 0; }
longest_of() { identify -format '%[fx:int(max(w,h))]' "$1[0]" 2>/dev/null || echo 0; }

# $1 = Quelldatei (absolut), $2 = Zielpfad relativ zu bilder/
ingest() {
  local src=$1 dst="$DEST/$2"
  mkdir -p "$(dirname "$dst")"
  [[ $FORCE == 1 || ! -f $dst || $src -nt $dst ]] || return 0

  if [[ ${src,,} == *.jpg || ${src,,} == *.jpeg ]] && (( $(width_of "$src") > LARGE_MIN )); then
    # Großes Bild: neu kodieren statt kopieren.
    convert "$src" -quality "$JPEG_Q" -sampling-factor 4:2:0 -interlace Plane -strip "$dst"
    n_reenc=$((n_reenc + 1))
  else
    cp -p "$src" "$dst"
    n_copy=$((n_copy + 1))
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

# Abgeleitete Dateien (…-400.jpg, …-1000.jpg) beim Durchlauf überspringen.
is_derived() { [[ $(basename "$1") =~ -[0-9]{3,4}\.(jpg|webp)$ ]]; }

echo "== 1/4  Originale übernehmen, Dateinamen normalisieren"
while IFS= read -r -d '' f; do
  base=$(basename "$f"); skip=0
  for s in "${SKIP_NAMES[@]}"; do [[ $base == "$s" ]] && skip=1; done
  (( skip )) && continue
  ingest "$f" "$(normalize "${f#"$SRC"/bilder/}")"
done < <(find "$SRC/bilder" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.gif' -o -iname '*.png' \) -print0)

# Bilder aus dem Wurzelverzeichnis der Altsite -> bilder/ (oberste Ebene).
for base in ntkaltar.JPG ntkwinterbild.JPG zeichnungntkumkehr.JPG; do
  [[ -f "$SRC/$base" ]] && ingest "$SRC/$base" "$(normalize "$base")"
done

# Ersatzquellen: Für tusset_alt.jpg existiert im Archiv nur noch eine
# Neukodierung (siehe bilder/altetk/FEHLBESTAND.txt im Archiv). Sie wird unter
# dem kanonischen Namen übernommen, damit der Build reproduzierbar bleibt.
# Sobald das Original wieder im Archiv liegt, greift automatisch die Schleife
# oben und diese Ersatzregel läuft ins Leere.
if [[ ! -f "$SRC/bilder/altetk/tusset_alt.jpg" \
   && -f "$SRC/bilder/altetk/tusset_alt.NEUKODIERT-q82.jpg" ]]; then
  ingest "$SRC/bilder/altetk/tusset_alt.NEUKODIERT-q82.jpg" "altetk/tusset_alt.jpg"
fi
echo "   $n_copy unverändert kopiert, $n_reenc neu kodiert (breiter als $LARGE_MIN px)"

echo "== 2/4  WebP-Varianten (q$WEBP_Q)"
while IFS= read -r -d '' f; do is_derived "$f" || make_webp "$f"; done \
  < <(find "$DEST" -type f -name '*.jpg' -print0)
echo "   $n_webp erzeugt, $n_webp_skip verworfen (WebP war nicht kleiner)"

echo "== 3/4  Größenleiter für große Bilder (${LADDER[*]} px)"
while IFS= read -r -d '' f; do is_derived "$f" || make_ladder "$f"; done \
  < <(find "$DEST" -type f -name '*.jpg' -print0)
echo "   $n_ladder Stufe(n) erzeugt"

echo "== 4/4  Galerie-Thumbnails (max $THUMB_MAX px)"
while IFS= read -r -d '' f; do is_derived "$f" || make_thumb "$f"; done \
  < <(find "$DEST" -type f -name '*.jpg' -print0)
echo "   $n_thumb erzeugt, $n_native bereits klein genug"

echo
printf 'Fertig: %s Dateien, %s in %s\n' \
  "$(find "$DEST" -type f | wc -l)" "$(du -sh "$DEST" | cut -f1)" "${DEST#"$ROOT"/}"
