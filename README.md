# Tussetkapelle Philippsreut – Website

Statische Website über die neue Tussetkapelle in Philippsreut, den originalgetreuen
Wiederaufbau der Gnadenkapelle auf dem Tussetberg im Böhmerwald.

Texte und Bilder stammen von der Familie Weber und sind inhaltlich unverändert
übernommen. Die Fassungen: **Deutsch** (Wurzelverzeichnis), **Englisch**
(`/en/`) und **Leichte Sprache** (`/ls/`).

---

## Schnellstart

```bash
npm run images    # Bilder aus dem Archiv aufbereiten (nur bei Bedarf)
npm run build     # HTML-Dateien erzeugen
npm run serve     # Testserver auf http://localhost:8473
npm run check     # Vollständigkeit und Struktur prüfen
```

Es gibt keine npm-Abhängigkeiten. Vorausgesetzt werden Node ab Version 18,
Python 3 (nur für den Testserver) und ImageMagick (nur für `npm run images`).

## Wie man Inhalte ändert

Die HTML-Dateien werden **erzeugt** – niemals direkt bearbeiten, Änderungen wären
beim nächsten `npm run build` verloren. Bearbeitet wird stattdessen:

| Was | Wo |
|---|---|
| Text einer Seite | `src/content/<sprache>/<seite>.json` |
| Navigation, Adressen, Oberflächentexte | `src/content/site.<sprache>.json` |
| Gestaltung | `src/assets/site.css` |
| Verhalten (Menü, Lightbox) | `src/assets/site.js` |
| Galerie-Zuordnung und Bildunterschriften | `tools/make-gallery.mjs` |

Danach `npm run build`. Die erzeugten Dateien sind eingecheckt und lassen sich
unverändert per FTP hochladen.

### Aufbau einer Inhaltsdatei

```json
{
  "id": "gnadenbilder",
  "type": "article",
  "parent": "alte-tussetkapelle",
  "navLabel": "Die Gnadenbilder",
  "title": "2. Die Gnadenbilder",
  "description": "… für Suchmaschinen, 40–160 Zeichen …",
  "blocks": [
    { "t": "p", "html": "Ein Absatz. <strong>Auszeichnung</strong> ist erlaubt." },
    { "t": "h2", "text": "Eine Zwischenüberschrift" },
    { "t": "fig", "src": "altetk/gnadenbilder/rindenmadonna.jpg",
      "align": "right", "alt": "…", "caption": "…" }
  ]
}
```

Blocktypen: `p` · `h2` · `h3` · `fig` · `figrow` · `list` · `dl` · `table` ·
`quote` · `letter` · `note` · `sources` · `explain` · `chapters`.

Bei `fig` genügt der Pfad ab `bilder/`. Maße, WebP-Varianten und `srcset` holt
der Builder aus `src/image-manifest.json` – deshalb sind `width` und `height`
immer gesetzt und kein Bild wird über seine echte Auflösung hinaus vergrößert.

Interne Verweise im Text als `{{href:seiten-id}}` schreiben, nicht als Pfad.
So bleibt ein Verweis gültig, auch wenn sich eine Adresse ändert.

Seiten sind **zwei Seiten** hinzuzufügen: die Inhaltsdatei **und** ein Eintrag
unter `slugs` in `site.<sprache>.json`.

## Prüfungen

`npm run check` führt drei Skripte aus. Alle drei müssen ohne Beanstandung
durchlaufen.

**`tools/check-content.mjs` – Textvollständigkeit.**
Zerlegt jede Seite der Vorlage in überlappende Wortfolgen von acht Wörtern und
prüft, ob jede davon in der deutschen Fassung wiederzufinden ist. Die Zerlegung
erfolgt blockweise, damit die Tabellenstruktur der Vorlage keine falschen
Treffer erzeugt. Stand: **10.025 Wortfolgen geprüft, 0 unerklärt fehlend.**

Die bewussten Abweichungen sind im Skript einzeln mit Begründung deklariert
und ausschließlich typografischer Art – zum Beispiel:

* `Brottasche ?` → `Brottasche –` (Kodierungsartefakt der Vorlage)
* `E rst wenn` → `Erst wenn`, `I m Sommer` → `Im Sommer` (Leerzeichen im Wort)
* `den richtigen Patz` → `Platz`, `HI. Bruder Konrad` → `Hl.` (Tippfehler)
* `auf,aber` → `auf, aber`, `Mädchenauf` → `Mädchen auf` (fehlende Leerzeichen)
* `Tusset-` + `kapelle` → `Tussetkapelle` (Trennung durch Zeilenumbruch)

Grundsatz: Kodierungsfehler, Trennungen aus dem Zeilenumbruch, fehlende oder
überzählige Leerzeichen und offensichtliche Buchstabendreher werden berichtigt.
**Nicht** angetastet werden historische Rechtschreibung (`daß`, `mußte`),
sprachliche Eigenheiten und inhaltliche Angaben. Wo eine Angabe
einer anderen widerspricht, bleibt der Wortlaut stehen und ein gekennzeichneter
Hinweis nennt den Widerspruch – so beim Einweihungsdatum auf der Seite über
Emil Weber, das dort mit 1987 statt 1985 angegeben ist.

**`tools/check-images.mjs` – Bildvollständigkeit.**
Jedes Bild des Bestandes muss auf mindestens einer Seite eingebunden sein und
jeder Bildverweis auf eine vorhandene Datei zeigen.
Stand: **116 von 117 eingebunden, 0 defekte Verweise.**

Nicht eingebunden ist allein `bilder/neuetk/anfahrt/karte.gif`. Der
Kartenausschnitt trägt den Aufdruck „©2002 Microsoft Corp ©2002 Navteq“; eine
Weiterveröffentlichung ist urheberrechtlich ungeklärt. Die Anfahrtsbeschreibung
steht als Text auf der Besuchsseite.

**`tools/check-links.mjs` – Struktur und Barrierefreiheit.**
Prüft interne Verweise, `alt`/`width`/`height` an jedem Bild, genau ein `<h1>`
je Seite, lückenlose Überschriftenordnung, `lang`, `title`, `description`,
`canonical`, `rel="noopener noreferrer"` an Außenlinks und – als Nachweis der
DSGVO-Konformität – dass **keine Ressource von einem fremden Server** geladen
wird.

## Bilder

`npm run images` liest das Archiv (`TK_SRC`, voreingestellt
`~/Dokumente/tussent/www.tussetkapelle.de`) und erzeugt `bilder/`:

* Dateinamen normalisiert: Kleinschreibung, `.JPG` → `.jpg`, `~` → `-`.
  Das behebt `SM~neubauer~und~emil.jpg` und `lr~schumertl~und~emil.jpg`, die in
  der Vorlage deshalb über absolute `http://`-Adressen mit `%7E` eingebunden
  werden mussten.
* WebP je Bild, aber nur wenn es kleiner ist als das JPEG. Bei 52 der kleinen
  Aufnahmen ist es das nicht – dort wird bewusst keine WebP-Variante angelegt.
* Größenleiter 700/1000/1400 px nur für die drei Bilder über 800 px Breite, und
  auch dort nur Stufen, die höchstens 80 % der Nativbreite haben.
* Thumbnails `-400` nur für Bilder, die tatsächlich größer sind. 55 der 116
  Aufnahmen liegen von sich aus darunter und werden in Nativgröße ausgeliefert.

**Der Bildbestand ist der harte Constraint dieses Projekts.** Nur drei Dateien
sind groß: `ntkaltar.jpg` (1994×789), `ntkwinterbild.jpg` (1448×1086) und
`altetk/tusset_alt.jpg` (1087×1447). Die übrigen 114 sind 125–581 px breit.
Deshalb ist allein das Hero-Bild formatfüllend; alles andere erscheint in
Nativgröße in der Textspalte. Nach `npm run images` immer
`node tools/make-manifest.mjs` laufen lassen.

### Zu den vorbereiteten WebP-Dateien

Im Archiv liegen `ntkaltar.webp` und `ntkwinterbild.webp` mit Qualität 92. Eine
Neukodierung mit Qualität 82 liefert bei gleichen Abmessungen 197 KB gegenüber
209 KB bzw. 111 KB gegenüber 164 KB. Die Pipeline erzeugt daher eigene
Varianten; die Dateien im Archiv bleiben unberührt.

## Gestaltung

Farben nach Vorgabe: Dunkelgrün `#304332`, Cremeweiß `#F7F4ED`, Gold `#B79A5C`.

**Zum Gold ein wichtiger Hinweis.** Das helle Gold erreicht als Textfarbe die
WCAG-AA-Schwelle nicht: gegen Creme nur 2,33:1, gegen Dunkelgrün 3,88:1, weiße
Schrift auf Gold 2,64:1. Es gibt deshalb zwei Werte:

* `--tk-gold` `#B79A5C` – ausschließlich dekorativ: Linien, Rahmen, Symbole auf
  dunkelgrünem Grund.
* `--tk-gold-text` `#8A6F32` – für Text, Verweise und Buttonflächen. Gegen Creme
  4,76:1, mit cremefarbener Schrift ebenfalls über 4,5:1.

Es werden **keine Webfonts** geladen, nur Systemschriften. Das erspart einen
externen Request (DSGVO) und jede Verzögerung beim Rendern. Alle Symbole und die
Sprachkennzeichen sind Inline-SVG.

Das Kennzeichen für Leichte Sprache ist ein **eigenes, neutrales Zeichen**. Das
offizielle Logo (Inclusion Europe / Netzwerk Leichte Sprache) ist geschützt und
wird nicht verwendet.

## Verzeichnisse

```
build.js                 Erzeugt die Seiten. Node 18, ohne Abhängigkeiten.
serve.sh                 Testserver, fester Port 8473.
src/templates/           layout · blocks · pages · icons
src/content/             site.<lang>.json und je Seite eine JSON-Datei
src/assets/              site.css · site.js · favicon.svg
src/image-manifest.json  Maße und Größenstufen, erzeugt
tools/                   Bild-Pipeline, Manifest, Galerie, Prüfungen
bilder/                  Ausgelieferte Bilder, erzeugt
index.html geschichte/ … Erzeugte Seiten
```

Hilfreich beim Erfassen von Inhalten:
`node tools/dump-source.mjs inhalte/…/seite.htm` gibt eine Seite der Vorlage als
lesbaren Klartext aus, mit Markierungen an den Stellen der Bilder und Verweise.

## Offene Punkte und interne Hinweise

Alles, was noch von Hand zu erledigen ist – Impressumsangaben, Daten des
Hosting-Anbieters, die veralteten Telefonnummern – steht in **`ToDo.md`**.
Dort sind auch die Entscheidungen dokumentiert, die bewusst nicht auf der
Website erwähnt werden.

## Sprachwahl und Fußzeile

* **Kopfzeile**: Sprachwahl immer sichtbar, nie im Menü versteckt. Auf breiten
  Schirmen mit Beschriftung, auf schmalen nur die Symbole. Der Text bleibt für
  Screenreader im Markup und steht zusätzlich im `title` des Verweises.
* **Fußzeile**: links die Wortmarke zweizeilig neben dem Symbol, mittig nur
  Impressum und Datenschutz, rechts die Sprachwahl – auf breiten Schirmen nur
  als Symbole, auf schmalen mit Beschriftung auf eigener Zeile.
* Zwischen den Sprachen stehen **keine Trennstriche**.

Die Menüschaltfläche trägt `flex: none`. Ohne das drücken Wortmarke und
Sprachwahl sie auf schmalen Schirmen auf 0 px zusammen und das Menü ist nicht
mehr erreichbar.

## Die 14 Kreuzwegstationen

Die Stationen benutzen den eigenen Blocktyp `station`. Jede Station ist ein
abgeschlossenes Raster aus Überschrift, Bild und Text. Mit umflossenen Bildern
verschieben sich Bild und Text gegeneinander, sobald ein Absatz länger ist als
das Bild hoch – dann steht Bild 5 neben Text 6.

Zwei Fallstricke sind im Stylesheet vermerkt:

* Die Regel `.prose h3 + *` setzt 1 rem Abstand und hat mit (0,1,1) eine höhere
  Spezifität als `.station__media`. Die Stationsregeln sind deshalb als
  `.station > .station__media` geschrieben.
* Bei den gespiegelten Stationen muss auch `grid-template-columns` kippen,
  sonst steht das schmale Bild in der breiten Spalte.

Die Stationen bleiben in der Lesespalte und sind damit genauso breit wie
Absätze und Überschriften der übrigen Seite. Die Textspalte neben dem Bild
fällt dadurch schmal aus – das ist der Preis für eine durchgehende Satzkante.
