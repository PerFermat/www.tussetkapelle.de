# Tussetkapelle Philippsreut – Website

Statische Website über die neue Tussetkapelle in Philippsreut, den originalgetreuen
Wiederaufbau der Gnadenkapelle auf dem Tussetberg im Böhmerwald.

Texte und Bilder stammen von der Familie Weber und sind inhaltlich unverändert
übernommen. Die Fassungen: **Deutsch** (Wurzelverzeichnis), **Englisch**
(`/en/`) und **Leichte Sprache** (`/ls/`).

---

## Schnellstart

```bash
npm run editor    # grafischer Inhaltseditor – der übliche Weg
npm run images    # Größenstufen und Bildverzeichnis auffrischen (bei Bedarf)
npm run build     # HTML-Dateien erzeugen
npm run serve     # Testserver auf http://localhost:8473
npm run check     # Vollständigkeit und Struktur prüfen (setzt build voraus)
```

Es gibt keine npm-Abhängigkeiten. Vorausgesetzt werden Node ab Version 18,
Python 3 (für den Testserver und den Editor) und ImageMagick (für alles, was mit
Bildern zu tun hat – auch für das Aufnehmen im Editor).

## Inhalte pflegen – mit dem Editor

```bash
npm run editor      # oder  ./editor.sh
```

Der Editor unter `editor/` zeigt Seiten, Abschnitte und Bilder in Klartext.
JSON und HTML kommen darin nirgends vor. Er kann Seiten anlegen, umbenennen,
verschieben und löschen, Abschnitte per Maus umsortieren, Bilder mit Vorschau
auswählen, aufnehmen, ersetzen und löschen und am Ende **Website erzeugen** und
**Prüfen** anstoßen.

Die Ausgabe der Werkzeuge steht unten. Sie ist eingeklappt und meldet sich von
selbst, sobald ein Lauf etwas zu sagen hat; das **+** rechts in der Statuszeile
holt sie jederzeit hervor, das **−** in ihrer Titelzeile klappt sie wieder ein.
Als eigenes Fenster lässt sie sich nicht abkoppeln – das verdeckte die
Eingabemaske.

Beim ersten Start legt `editor.sh` eine Python-Umgebung unter `.venv/` an und
installiert PySide6 hinein (rund 300 MB, ein bis zwei Minuten). Danach startet
er sofort. Voraussetzung ist Python 3.12 oder neuer.

Drei Eigenschaften sind dabei bewusst so gebaut:

* **Er formatiert nichts um.** Beim Laden merkt er sich, welcher Baustein
  einzeilig geschrieben ist und wo Leerzeilen stehen, und setzt das beim
  Speichern wieder ein. Wer einen Satz ändert, sieht im Git-Diff genau eine
  geänderte Zeile – nicht die ganze Datei.
* **Er kennt die Kennungen.** Eine Seitenkennung steht an sieben Stellen
  (Dateiname, `id`, `slugs`, `nav`, `sequence`, `footerLinks`, `parent`) und in
  jedem `{{href:…}}`. Umbenennen fasst alle an, in allen drei Sprachen, und
  entfernt das verwaiste Ausgabeverzeichnis mit – `build.js` räumt dort nicht
  auf.
* **Er speichert nichts Kaputtes.** Vor jedem Schreiben läuft dieselbe Prüfung,
  an der sonst `npm run build` scheitern würde: fehlende Adresse, unbekanntes
  Bild, Verweis ins Leere.

Neue Bilder kommen über den Dialog **Bild auswählen** in den Bestand – siehe
[Bilder](#bilder). Der Editor bietet zur Auswahl nur an, was in
`src/image-manifest.json` steht.

### „Website nicht auf dem neuesten Stand“

Die fertigen Seiten liegen im Projektordner und sind zugleich das, was
hochgeladen wird. Sie entstehen nur beim Erzeugen – ein gespeicherter Text oder
ein gelöschtes Bild ändert sie nicht. Läuft beides auseinander, sagt es die
Statuszeile in Rot, und **Prüfen** erzeugt die Seiten erst neu, bevor es prüft.

Ohne das prüft man den Stand von gestern. Nach dem Löschen eines Bildes meldete
die Prüfung sieben *defekte Bildverweise* – zu Recht: gelöscht war richtig, nur
stand die Seite noch vom Erzeugen davor und nannte eine Datei, die es nicht mehr
gab. Beim Start liest der Editor den Zustand an den Zeitstempeln ab; danach führt
er ihn selbst mit.

Zwei Tests laufen ohne Bildschirm. Der erste prüft das Datenmodell, der zweite
drückt auf die Schaltflächen der wirklich angezeigten Dialoge:

```bash
.venv/bin/python -m editor.selftest
QT_QPA_PLATFORM=offscreen .venv/bin/python -m editor.uitest
```

Den zweiten gibt es, weil eine Attrappe der Sicherheitsabfrage einmal einen
Fehler verdeckt hat: `QMessageBox.question()` liefert in PySide6 eine einfache
Zahl, keinen Enum-Wert. Der Vergleich mit `is` war deshalb immer falsch, und
Löschen blieb wirkungslos. Vergleiche auf Antworten von Dialogen gehören mit
`==` geschrieben.

## Inhalte von Hand ändern

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
unter `slugs` in `site.<sprache>.json`. Der Editor tut beides von selbst.

## Prüfungen

`npm run check` führt zwei Skripte aus. Beide müssen ohne Beanstandung
durchlaufen. Geprüft werden die **erzeugten Seiten**, nicht der Inhalt unter
`src/` – auf der Kommandozeile gehört deshalb `npm run build` davor.

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

### Die Wortgleichheitsprüfung ist abgeschlossen

Bis zum 2. August 2026 lief zusätzlich `tools/check-content.mjs`. Das Skript
zerlegte jede Seite der Vorlage von 2003 in überlappende Wortfolgen von acht
Wörtern und wies nach, dass jede davon in der neuen deutschen Fassung
wiederzufinden ist. Es war der Beleg für die Auflage, alle Texte inhaltlich
unverändert zu übernehmen.

**Letztes Ergebnis: 10.025 Wortfolgen geprüft, 17 erklärte Abweichungen,
0 unerklärt fehlend.** Die erklärten Abweichungen waren ausschließlich
typografischer Art – Kodierungsartefakte (`Brottasche ?` → `–`), Leerzeichen
mitten im Wort (`E rst wenn` → `Erst wenn`), Tippfehler (`den richtigen Patz`
→ `Platz`), fehlende Leerzeichen (`auf,aber`) und Trennungen aus dem
Zeilenumbruch der alten Seite (`Tusset-` + `kapelle`). Historische
Rechtschreibung (`daß`, `mußte`), sprachliche Eigenheiten und alle inhaltlichen
Angaben blieben unangetastet; ein Widerspruch in der Vorlage – das
Einweihungsdatum 1987 statt 1985 auf der Seite über Emil Weber – steht im
Wortlaut samt kenntlich gemachtem Hinweis.

Das Skript wurde danach entfernt. Zwei Gründe: Sein Zweck, die einmalige
Ersterfassung zu belegen, ist erfüllt. Und es las die Vorlage aus einem fest
verdrahteten Pfad **außerhalb des Projekts** – auf keinem anderen Rechner wäre
es lauffähig gewesen, und jede künftige Textpflege hätte es fehlschlagen lassen.

## Bilder

`bilder/` ist die Bildquelle des Projekts – 315 Dateien, alle in der
Versionsverwaltung. `npm run images` frischt daraus den ausgelieferten Satz auf:

* WebP je Bild, aber nur wenn es kleiner ist als das JPEG. Bei 52 der kleinen
  Aufnahmen ist es das nicht – dort wird bewusst keine WebP-Variante angelegt.
* Größenleiter 700/1000/1400 px nur für die drei Bilder über 800 px Breite, und
  auch dort nur Stufen, die höchstens 80 % der Nativbreite haben.
* Thumbnails `-400` nur für Bilder, die tatsächlich größer sind. 55 der 116
  Aufnahmen liegen von sich aus darunter und werden in Nativgröße ausgeliefert.
* zuletzt `src/image-manifest.json` über `tools/make-manifest.mjs`.

Der Lauf ist idempotent; `FORCE=1` erzwingt eine Neuberechnung. Gebraucht werden
ImageMagick und Node.js.

**Der Bildbestand ist der harte Constraint dieses Projekts.** Nur drei Dateien
sind groß: `ntkaltar.jpg` (1994×789), `ntkwinterbild.jpg` (1448×1086) und
`altetk/tusset_alt.jpg` (1087×1447). Die übrigen 114 sind 125–581 px breit.
Deshalb ist allein das Hero-Bild formatfüllend; alles andere erscheint in
Nativgröße in der Textspalte.

### Neue Bilder kommen über den Editor

Im Dialog **Bild auswählen** stehen drei Knöpfe: *Bild aufnehmen*, *Bild
ersetzen* und *Bild löschen*. Der Editor legt die Datei in `bilder/` ab und ruft
dafür dieselben Betriebsarten des Bildskripts auf, die auch von Hand nutzbar
sind:

```
tools/build-images.sh --add     <datei> <ziel>   Bild aufnehmen
tools/build-images.sh --replace <datei> <ziel>   Bild ersetzen
tools/build-images.sh --remove           <ziel>  Bild entfernen
```

`<ziel>` ist ein Pfad relativ zu `bilder/`. Angenommen werden JPG, PNG, GIF,
WebP und TIFF; abgelegt wird immer als `.jpg` mit Qualität 82, weil
Größenleiter und WebP-Varianten ausschließlich aus JPEG-Dateien entstehen. Der
Dateiname wird dabei auf Kleinschreibung, Bindestriche und ASCII gebracht –
`Prüf Bild~1.JPG` wird zu `pruef-bild-1.jpg`.

Gelöscht werden darf nur, was auf **keiner** Seite in **keiner** Sprache
verwendet wird; die Bildergalerie zählt mit. Der Knopf bleibt sonst gesperrt und
nennt den Grund. `--remove` räumt einen Ordner mit auf, der dadurch leer würde.

Jeder dieser drei Eingriffe macht die erzeugten Seiten veraltet – sie nennen
Dateinamen, Maße und Größenstufen. Der Editor merkt sich das und sagt es in der
Statuszeile; **Website erzeugen** bringt sie auf den Stand.

Zwei Dinge bleiben danach von Hand zu tun: neu aufgenommene Bilder gehören in
einen Commit (`git add bilder/…`), und ein Bild in einem Galerieordner erscheint
in der Bildergalerie erst nach einem Lauf von `tools/make-gallery.mjs` – mit
einer Bildunterschrift, die dort in drei Sprachen einzutragen ist.

### Herkunft des Bestands

Die Bilder stammen aus dem Archiv der Altsite von 2003. Bis Juli 2026 las
`npm run images` sie über einen fest verdrahteten Pfad außerhalb des Projekts
ein; das ist entfallen, aus demselben Grund wie bei der Wortgleichheitsprüfung
oben. Beim Übernehmen wurden die Dateinamen normalisiert (Kleinschreibung,
`.JPG` → `.jpg`, `~` → `-`) – das behob `SM~neubauer~und~emil.jpg` und
`lr~schumertl~und~emil.jpg`, die in der Vorlage über absolute `http://`-Adressen
mit `%7E` eingebunden werden mussten.

Am 26.07.2026 ging das Archivverzeichnis durch einen relativen Pfad verloren und
wurde aus `bilder/` zurückgestellt: 113 der 114 Dateien bitgleich (mit `cp -p`
kopiert, die Zeitstempel von 2003 und die Byte-Größen stimmten überein). Nicht
bitgleich wiederherstellbar war `altetk/tusset_alt.jpg` – das Original mit
Qualität 90 und 905.651 Bytes ist verloren, vorhanden ist eine Neukodierung mit
Qualität 82 bei gleichen Pixelmaßen. Falls ein Backup auftaucht, sollte es diese
Datei ersetzen.

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
