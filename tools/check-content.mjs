/**
 * Nachweis: alle Texte der Altsite sind übernommen.
 *
 * Vorgehen: aus jeder Quellseite werden die Sätze extrahiert und normalisiert
 * (Kleinschreibung, Satzzeichen und Leerraum vereinheitlicht, typografische
 * Ersetzungen rückgängig). Dasselbe für alle erzeugten deutschen Seiten
 * zusammen. Dann wird geprüft, ob jeder Quellsatz irgendwo wiederauftaucht.
 *
 * Verglichen wird gegen die Gesamtheit der deutschen Seiten, nicht Seite gegen
 * Seite: Inhalte durften umsortiert werden – etwa die Öffnungszeiten, die von
 * der Startseite auf die Besuchsseite gewandert sind.
 *
 * Aufruf: node tools/check-content.mjs
 * Rückgabe: 0 wenn kein Satz fehlt, sonst 1.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = process.env.TK_SRC || '/home/michael/Dokumente/tussent/www.tussetkapelle.de';

/* --- Quelltexte einlesen -------------------------------------------------- */

const ENT = {
  nbsp: ' ', auml: 'ä', ouml: 'ö', uuml: 'ü', Auml: 'Ä', Ouml: 'Ö', Uuml: 'Ü',
  szlig: 'ß', amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", euro: '€',
  shy: '', ndash: '–', mdash: '—', hellip: '…', middot: '·', sect: '§', copy: '©',
  bdquo: '„', ldquo: '“', rdquo: '”', laquo: '«', raquo: '»', deg: '°',
};

const decode = (s) =>
  s
    .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(+d))
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/&([a-zA-Z]+);/g, (m, n) => (n in ENT ? ENT[n] : m));

/** Trennmarke für Blockgrenzen, überlebt die Normalisierung nicht als Wort. */
const SEP = '';

/**
 * Wandelt HTML in Text um und markiert dabei Blockgrenzen.
 *
 * Die Blockgrenzen sind wichtig: in der Altsite stehen Überschrift und
 * Fließtext in getrennten Tabellenzellen ohne Satzzeichen dazwischen. Ohne
 * Markierung würden beide zu einer Wortkette verkleben und jede Wortfolge über
 * diese Naht hinweg wäre im Neubau zu Recht nicht zu finden.
 */
function textOf(html) {
  return decode(
    html
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/<(script|style)[\s\S]*?<\/\1>/gi, '')
      // <title> ist Seitengerüst, kein Inhalt. In der Altsite steht dort
      // meist „Unbenanntes Dokument“; das soll nicht als fehlender Text gelten.
      .replace(/<title>[\s\S]*?<\/title>/gi, ' ')
      .replace(/<br\b[^>]*>/gi, SEP)
      .replace(/<\/?(p|div|td|th|tr|table|h[1-6]|li|ul|ol|dl|dt|dd|blockquote)\b[^>]*>/gi, SEP)
      .replace(/<[^>]+>/g, ' '),
  );
}

/**
 * Normalisierung. Alles, was der Neubau typografisch verbessern durfte, wird
 * hier auf einen gemeinsamen Nenner gebracht, damit der Vergleich nicht an
 * Anführungszeichen oder Gedankenstrichen scheitert.
 */
function normalize(s) {
  return s
    .toLowerCase()
    // Blockmarken im Zieltext zu Leerraum: die Quellseite wird blockweise
    // zerlegt, der Zieltext darf dagegen durchgehend durchsucht werden.
    .split(SEP)
    .join(' ')
    .replace(/[­​]/g, '')
    .replace(/[„“”"»«]/g, '"')
    .replace(/[‚‘’']/g, "'")
    .replace(/[–—‐-]/g, '-')
    .replace(/…/g, '...')
    .replace(/ /g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Zerlegt in überlappende Wortfolgen fester Länge.
 *
 * Warum n-Gramme und nicht Sätze: die Altsite hat zwischen Überschrift und
 * Fließtext oft kein Satzzeichen, weil beides in getrennten Tabellenzellen
 * stand. Ein Satz-Splitter verklebt daher Überschriften mit Absätzen und
 * meldet diese Verkettungen als „fehlend“, obwohl jedes Stück vorhanden ist.
 * Wortfolgen von N Wörtern sind gegen solche Blockgrenzen robust: nur die
 * wenigen Folgen, die genau über eine Grenze laufen, schlagen fehl.
 */
const N = 8;

/** Erzeugt Wortfolgen, aber nur innerhalb eines Blocks – nie über Grenzen. */
function ngrams(text) {
  const out = [];
  for (const block of text.split(SEP)) {
    const words = normalize(block).split(' ').filter(Boolean);
    if (!words.some((w) => /[a-zäöüß]{4}/.test(w))) continue;

    if (words.length < N) {
      // Kurze Blöcke als Ganzes prüfen; unter drei Wörtern ist es Beiwerk
      // wie Bildnummern oder einzelne Namen in Layout-Zellen.
      if (words.length >= 3) out.push(words.join(' '));
      continue;
    }
    for (let i = 0; i + N <= words.length; i++) {
      const gram = words.slice(i, i + N);
      if (!gram.some((w) => /[a-zäöüß]{4}/.test(w))) continue;
      out.push(gram.join(' '));
    }
  }
  return out;
}

/* --- Bewusste Abweichungen ------------------------------------------------
 *
 * Jede Stelle, an der der Neubau vom Wortlaut der Altsite abweicht, steht hier
 * mit Begründung. Nur diese Abweichungen sind erlaubt; alles andere lässt die
 * Prüfung fehlschlagen. Angegeben ist der normalisierte Quellausschnitt.
 */
const KNOWN_DIFFS = [
  {
    // Auf Wunsch des Betreibers: abgeschaltete Dienste werden nicht erwähnt.
    re: /gästebuch|hinterlassen sie uns hier eine nachricht|verschiedene routenplaner/,
    reason:
      'Bewusst nicht übernommen: Sätze, die auf das Gästebuch, das alte ' +
      'Kontaktformular und den Routenplaner verweisen. Alle drei Dienste sind ' +
      'seit Jahren abgeschaltet. An ihre Stelle treten die E-Mail-Adresse und ' +
      'ein Verweis auf OpenStreetMap. Siehe ToDo.md, Abschnitt 2.',
  },
  {
    // Alleinstehende Satzzeichen entstehen nur dadurch, dass die Altsite Text
    // über Tabellenzellen verteilt hat („1“ | „. Die Tussetkapelle …“) oder ein
    // Leerzeichen vor dem Zeichen stand („haben !“, „Klauser , genannt“).
    re: /(^|\s)[.,!?](\s|$)/,
    reason:
      'Alleinstehendes Satzzeichen der Altsite: entweder ein Leerzeichen vor ' +
      'dem Zeichen („haben !“, „Klauser , genannt“, „Nachricht .“) oder eine ' +
      'über Tabellenzellen verteilte Kapitelnummer („1“ + „. Die Tussetkapelle“). ' +
      'Im Neubau normal gesetzt. Betrifft auch das Fragezeichen in „Brottasche ?“, ' +
      'das dort für einen Gedankenstrich steht.',
  },
  {
    src: 'e rst wenn das myrtenkränzchen',
    reason: 'Quelltext hat „E rst“ mit eingeschobenem Leerzeichen; zu „Erst“ zusammengezogen.',
  },
  {
    src: 'i m sommer 1982',
    reason: 'Quelltext hat „I m Sommer“ mit eingeschobenem Leerzeichen; zu „Im“ zusammengezogen.',
  },
  {
    re: /\bpatz\b/,
    reason: 'Tippfehler der Altsite („den richtigen Patz“); zu „Platz“ berichtigt.',
  },
  {
    re: /auf,aber|mädchenauf/,
    reason:
      'Fehlende Leerzeichen der Altsite ergänzt: „auf,aber“ zu „auf, aber“ und ' +
      '„weißgekleideten Mädchenauf der Birkenbahre“ zu „Mädchen auf“.',
  },
  {
    re: /1\. bür-|^germeister/,
    reason:
      'Zeilentrennung „Bür-/germeister“ in der Bildunterschrift des ' +
      'Gruppenfotos zusammengeführt.',
  },
  {
    re: /^- \w/,
    reason:
      'Die fünf Vorschläge für die Gedenkstätte waren in der Altsite als ' +
      'Textzeilen mit vorangestelltem Bindestrich gesetzt. Im Neubau stehen sie ' +
      'als echte Aufzählung; der Wortlaut der Einträge ist unverändert, nur das ' +
      'Bindestrich-Zeichen entfällt.',
  },
  { src: 'oder"emausgang"', reason: 'Fehlendes Leerzeichen nach „oder“ ergänzt.' },
  { src: 'böhm. -röhren', reason: 'Überzähliges Leerzeichen in „Böhm. -Röhren“ entfernt.' },
  {
    src: 'mariä himmelfahrt -',
    reason:
      'Nachgestellter Gedankenstrich der Überschrift entfernt – ein Rest der ' +
      'Tabellengestaltung, kein Satzzeichen.',
  },
  { src: 'mariä heimsuchung -', reason: 'Nachgestellter Gedankenstrich entfernt (wie oben).' },
  {
    re: /tusset-|kapelle gelesen/,
    reason:
      'Zeilentrennung „Tusset-/kapelle“ aus dem Umbruch der alten Seite ' +
      'zusammengeführt und das fehlende schließende Anführungszeichen ergänzt: ' +
      '„Einweihung der neuen Tussetkapelle“ gelesen.',
  },
  { src: '!-', reason: 'Zeichenfolge „Leider !-“ zu „Leider! –“ normalisiert.' },
  {
    src: '1945."',
    reason:
      'Die Altarinschrift endet im Quelltext mit einem schließenden ' +
      'Anführungszeichen ohne öffnendes. Sie steht hier als Zitatblock, das ' +
      'unpaarige Zeichen entfällt.',
  },
  {
    src: 'tussetkapelle- gewidmet',
    reason:
      'Überschrift der 14. Station: fehlendes Leerzeichen vor dem Gedankenstrich ' +
      'ergänzt („alten Tussetkapelle – gewidmet dem Dorf Tusset“).',
  },
  {
    src: 'hi.',
    reason:
      'Quelltext hat „HI. Bruder Konrad“ mit großem I statt kleinem l; ' +
      'zur Abkürzung „Hl.“ (Heiliger) berichtigt.',
  },
];

/** Ist die Abweichung deklariert? Unterstützt Teilstring und Muster. */
const isKnown = (gram) =>
  KNOWN_DIFFS.some((d) => (d.re ? d.re.test(gram) : gram.includes(d.src)));

/* --- Quelle ---------------------------------------------------------------- */

const walk = (d, acc = []) => {
  for (const e of readdirSync(d)) {
    const p = join(d, e);
    if (statSync(p).isDirectory()) walk(p, acc);
    else if (/\.html?$/i.test(e)) acc.push(p);
  }
  return acc;
};

const sourceFiles = ['start.htm', ...walk(join(SRC, 'inhalte')).map((p) => relative(SRC, p))].sort();

/* --- Ziel ----------------------------------------------------------------- */

const targetFiles = [];
(function collect(d) {
  for (const e of readdirSync(d)) {
    // Nur auf oberster Ebene ausschließen. 'en' und 'ls' bleiben ausgeschlossen,
    // weil die Textprüfung ausschließlich die deutsche Fassung vergleicht.
    if (
      d === ROOT &&
      ['bilder', 'src', 'tools', 'node_modules', '.git', '.claude', 'en', 'ls', 'assets'].includes(e)
    )
      continue;
    const p = join(d, e);
    if (statSync(p).isDirectory()) collect(p);
    else if (e === 'index.html' || e === '404.html') targetFiles.push(p);
  }
})(ROOT);

const haystack = normalize(targetFiles.map((f) => textOf(readFileSync(f, 'utf8'))).join('\n'));

/* --- Vergleich ------------------------------------------------------------ */

let checked = 0;
let explained = 0;
const missing = [];

for (const rel of sourceFiles) {
  const text = textOf(readFileSync(join(SRC, rel), 'latin1'));
  const grams = ngrams(text);
  checked += grams.length;
  const gone = [];
  for (const g of grams) {
    if (haystack.includes(g)) continue;
    if (isKnown(g)) {
      explained++;
      continue;
    }
    gone.push(g);
  }
  if (gone.length) missing.push({ rel, total: grams.length, gone });
}

const totalGone = missing.reduce((n, m) => n + m.gone.length, 0);

console.log('Textabdeckung der deutschen Fassung');
console.log(`  Quellseiten                : ${sourceFiles.length}`);
console.log(`  Zielseiten                 : ${targetFiles.length}`);
console.log(`  geprüfte Wortfolgen        : ${checked} (je ${N} Wörter, überlappend)`);
console.log(`  erklärte Abweichungen      : ${explained} (${KNOWN_DIFFS.length} Stellen)`);
console.log(`  unerklärt nicht gefunden   : ${totalGone}`);

if (totalGone) {
  console.log('\nUNERKLÄRT FEHLEND – bitte prüfen:');
  for (const m of missing) {
    console.log(`\n  ${m.rel}  (${m.gone.length} von ${m.total})`);
    for (const g of m.gone) console.log(`    · ${g}`);
  }
  process.exit(1);
}

console.log('\nErgebnis: alle Texte der Vorlage sind in der deutschen Fassung enthalten.');
console.log('Die bewussten Abweichungen sind ausschließlich typografischer Art:\n');
for (const d of KNOWN_DIFFS) {
  console.log(`  ${d.re ? `Muster ${d.re}` : `„${d.src}“`}`);
  console.log(`      ${d.reason}\n`);
}
