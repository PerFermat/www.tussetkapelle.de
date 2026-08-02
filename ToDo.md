# ToDo und interne Hinweise

Diese Datei ist **nicht Teil der Website**. Sie sammelt Hinweise, die den
Besucher nichts angehen, sowie die Punkte, die noch von Hand erledigt werden
müssen.

---

## 1. Was Sie noch selbst eintragen müssen

### Impressum

In `src/content/de/impressum.json`, `en/impressum.json` und `ls/impressum.json`
stehen Platzhalter in spitzen Klammern `⟨…⟩`:

* Name des Anbieters (Person oder Körperschaft)
* Straße und Hausnummer, Postleitzahl und Ort
* Telefonnummer
* Name des inhaltlich Verantwortlichen

Ein Impressum ist für eine in Deutschland betriebene Website nach § 5 DDG
verpflichtend.

### Datenschutzerklärung

In `src/content/*/datenschutz.json` fehlen noch:

* Speicherdauer der Server-Protokolldateien beim Hosting-Anbieter
* Name und Anschrift des Hosting-Anbieters
* Mit dem Hosting-Anbieter ist ein Vertrag zur Auftragsverarbeitung nach
  Art. 28 DSGVO zu schließen.

### Kontaktdaten auf der Besuchsseite

Aus dem Bestand übernommen und vermutlich veraltet:

* Betreuerin: Frau Therese Friedsam, Hauptstraße 1, Tel. 08550/763
* Anmeldung für Gottesdienste: Pfarrer Max Richtsfeld, Tel. 08550/274

Bitte prüfen und gegebenenfalls ersetzen. Die Angaben stehen in
`src/content/de/besuch.json` und in den Fassungen für Englisch und Leichte
Sprache.

### Nach dem Hochladen

* Die Datei `sitemap.xml` bei der Google Search Console anmelden.
* Prüfen, ob der Server `404.html` bei unbekannten Adressen ausliefert.
  Bei Apache genügt in der `.htaccess`: `ErrorDocument 404 /404.html`
* Prüfen, ob der Server `https` erzwingt.

---

## 2. Entscheidungen, die auf der Website nicht erwähnt werden

### Nicht eingebundenes Bild

`bilder/neuetk/anfahrt/karte.gif` ist **nicht** eingebunden. Der
Kartenausschnitt trägt den Aufdruck „©2002 Microsoft Corp ©2002 Navteq“. Eine
Weiterveröffentlichung wäre urheberrechtlich ungeklärt. Die Datei bleibt im
Verzeichnis `bilder/` liegen, falls die Rechtelage geklärt wird.

Die Anfahrt steht als Text auf der Besuchsseite, dazu ein Verweis auf
OpenStreetMap mit den Koordinaten.

### Weggefallene Dienste der alten Fassung

Diese Angebote gab es früher, sie sind seit Jahren abgeschaltet und werden auf
der neuen Website **nicht erwähnt**:

* Gästebuch über `cgi09.kundenserver.de`
* Kontaktformular über `cgi09.puretec.de`
* Routenplaner bei `portale.web.de`

An ihre Stelle tritt die E-Mail-Adresse `info@tussetkapelle.de`.

### Keine eingebettete Landkarte

Es ist bewusst keine Karte von Google oder OpenStreetMap eingebettet, sondern
nur ein normaler Verweis gesetzt. Eingebettete Karten übertragen beim
Seitenaufbau Daten an den Kartenanbieter und wären ohne Einwilligung des
Besuchers datenschutzrechtlich angreifbar. Auf der Website wird das nicht
erläutert.

### Aktualisierte Verweise

Drei Adressen der alten Linkliste waren nicht mehr erreichbar und wurden
ersetzt:

| Alt | Neu |
|---|---|
| `http://www.dbb-ev.de` | `https://boehmerwaldbund.de/` |
| `http://www.npsumava.cz` | `https://www.npsumava.cz/de/` bzw. `/en/` je nach Sprache |
| `http://www.obermoldau.de` | `http://webmuzeum.sumava.cz/retour-1996/mesta/horni-vltavice/index_de.htm` |

Die übrigen Verweise der Liste sind unverändert. Ob sie noch erreichbar sind,
wurde nicht geprüft.

---

## 3. Abweichungen vom Wortlaut der Vorlage

Bis zum **2. August 2026** verglich `node tools/check-content.mjs` jede
Wortfolge der Vorlage mit der neuen deutschen Fassung. Letztes Ergebnis:
**10.025 Wortfolgen geprüft, 17 erklärte Abweichungen, 0 unerklärt fehlend.**

Das Skript ist seither entfernt. Sein Zweck – die einmalige Ersterfassung zu
belegen – ist erfüllt, und es las die Vorlage aus einem fest verdrahteten Pfad
außerhalb des Projekts. Ab jetzt sind Textänderungen ausdrücklich vorgesehen
und werden über den Inhaltseditor (`npm run editor`) vorgenommen.

Berichtigt wurden damals ausschließlich:

* Kodierungsfehler, etwa `Brottasche ?` statt eines Gedankenstrichs
* Buchstaben mit eingeschobenem Leerzeichen: `E rst` → `Erst`, `I m Sommer` → `Im Sommer`
* Tippfehler: `den richtigen Patz` → `Platz`, `HI. Bruder Konrad` → `Hl.`
* fehlende Leerzeichen: `auf,aber`, `Mädchenauf`
* Trennungen durch den Zeilenumbruch der alten Seite: `Tusset-` + `kapelle`

**Nicht** angetastet wurden die historische Rechtschreibung (`daß`, `mußte`),
sprachliche Eigenheiten und alle inhaltlichen Angaben.

### Ein inhaltlicher Widerspruch

Auf der Seite über Emil Weber steht als Einweihungsdatum der **27. Juli 1987**.
Alle anderen Seiten nennen den **27. Juli 1985**. Der Wortlaut wurde
unverändert übernommen; darunter steht eine gekennzeichnete Anmerkung, die auf
die abweichende Jahreszahl hinweist.

Falls Sie wissen, welche Angabe richtig ist: die Anmerkung steht in
`src/content/de/emil-weber.json` und kann entfernt oder die Jahreszahl
berichtigt werden.

---

## 4. Zum Bildbestand

Am 26.07.2026 ging beim Aufbereiten der Bilder das Verzeichnis `bilder/` im
Quellarchiv verloren. 113 der 114 Dateien konnten bitgleich wiederhergestellt
werden; die Original-Zeitstempel von 2003 und die Dateigrößen belegen das.

Eine Datei ist nur als Neukodierung vorhanden:

* `bilder/altetk/tusset_alt.jpg`
  Original: 1087×1447 px, Qualität 90, 905.651 Bytes
  Vorhanden: gleiche Pixelmaße, Qualität 82, 760.186 Bytes

Im Archiv liegt sie als `tusset_alt.NEUKODIERT-q82.jpg` neben einer Notiz
`FEHLBESTAND.txt`. **Falls Sie das Original noch haben**, legen Sie es bitte
als `tusset_alt.jpg` dorthin zurück und starten Sie
`npm run images && node tools/make-manifest.mjs && npm run build`.
Die Pipeline greift dann automatisch wieder auf das Original zu.
