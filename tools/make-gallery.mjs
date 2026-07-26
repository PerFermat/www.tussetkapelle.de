/**
 * Erzeugt src/content/de/galerie.json aus dem Bildmanifest.
 *
 * Der Sinn: die Galerie soll nachweislich JEDES Bild des Bestandes zeigen.
 * Würde man die 116 Einträge abtippen, fiele irgendwann eines durch. Deshalb
 * wird die Liste aus dem Manifest erzeugt; hier stehen nur die Zuordnung zu
 * Abschnitten und die Bildunterschriften.
 *
 * Bildunterschriften: wo das Original eine hat, ist sie wörtlich übernommen.
 * Für die 16 Aufnahmen atk1983_* gab es im Original keine sichtbare
 * Unterschrift, wohl aber sprechende Fensternamen im JavaScript
 * (turmalteKapelle1983, saeulealteKapelle1983 …). Diese Bezeichnungen des
 * Originalautors sind hier zu Unterschriften aufgelöst – nichts erfunden.
 *
 * Aufruf: node tools/make-gallery.mjs
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { en as CAP_EN, ls as CAP_LS } from './gallery-captions.mjs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(join(ROOT, 'src/image-manifest.json'), 'utf8'));

/** Bilder, die bewusst nicht in die Galerie kommen – mit Begründung. */
const EXCLUDE = {
  'neuetk/anfahrt/karte.gif':
    'Kartenausschnitt mit dem Aufdruck „©2002 Microsoft Corp ©2002 Navteq“ – ' +
    'urheberrechtlich ungeklärt, siehe README.',
};

/** Abschnitte in Anzeigereihenfolge: Titel + welche Bilder hineingehören. */
const SECTIONS = [
  {
    key: 'neu',
    titles: {
      de: 'Die neue Tussetkapelle',
      en: 'The new Tusset Chapel',
      ls: 'Die neue Tusset-Kapelle',
    },
    notes: {
      de: 'Die Kapelle in Philippsreut, wie sie heute steht.',
      en: 'The chapel in Philippsreut as it stands today.',
      ls: 'So sieht die Kapelle in Philippsreut heute aus.',
    },
    match: (p) => !p.includes('/') || p.startsWith('neuetk/einleitung/'),
  },
  {
    key: 'alt',
    titles: {
      de: 'Die alte Tussetkapelle im Böhmerwald',
      en: 'The old Tusset Chapel in the Bohemian Forest',
      ls: 'Die alte Tusset-Kapelle im Böhmer-Wald',
    },
    notes: {
      de: 'Der Tussetberg, die Gnadenkapelle und die Dörfer ringsum.',
      en: 'The Tussetberg, the pilgrimage chapel and the villages around it.',
      ls: 'Der Tusset-Berg, die Kapelle und die Dörfer in der Nähe.',
    },
    match: (p) =>
      p === 'altetk/tusset_alt.jpg' ||
      p.startsWith('altetk/kapelleundwallern/') ||
      p.startsWith('altetk/kreuzwege/'),
  },
  {
    key: 'gnadenbilder',
    titles: {
      de: 'Die Gnadenbilder',
      en: 'The miraculous images',
      ls: 'Die Bilder von Maria',
    },
    notes: {
      de: 'Die Bilder der Muttergottes vom Tussetberg.',
      en: 'The images of Our Lady of the Tussetberg.',
      ls: 'Diese Bilder zeigen Maria mit dem Jesus-Kind.',
    },
    match: (p) => p.startsWith('altetk/gnadenbilder/'),
  },
  {
    key: 'detail1983',
    titles: {
      de: 'Detailaufnahmen der alten Tussetkapelle ab April 1983',
      en: 'Detailed photographs of the old Tusset Chapel from April 1983',
      ls: 'Fotos von der alten Kapelle aus dem Jahr 1983',
    },
    notes: {
      de:
        'Die nachfolgenden Fotos belegen, in welchem desolaten Zustand sich die ' +
        'alte Tussetkapelle befand, als Emil Weber die gesamte Ruine und deren ' +
        'Bauteile 1983 vermessen hat.',
      en:
        'The following photographs show the desolate condition of the old Tusset ' +
        'Chapel when Emil Weber measured the whole ruin and its parts in 1983.',
      ls:
        'Emil Weber hat die alte Kapelle im Jahr 1983 genau ausgemessen. ' +
        'Die Fotos zeigen: Die Kapelle war fast ganz zerfallen.',
    },
    match: (p) => p.startsWith('fotogalerie/fotosatk/'),
  },
  {
    key: 'wiederaufbau',
    titles: {
      de: 'Der Wiederaufbau 1983 bis 1985',
      en: 'The reconstruction, 1983 to 1985',
      ls: 'Der Wieder-Aufbau von 1983 bis 1985',
    },
    notes: {
      de: 'Aus dem Bildbericht von Emil Weber.',
      en: 'From the photographic report by Emil Weber.',
      ls: 'Diese Fotos hat Emil Weber gemacht.',
    },
    match: (p) => p.startsWith('neuetk/entstehung/'),
  },
  {
    key: 'einweihung',
    titles: {
      de: 'Die Einweihung am 27. Juli 1985',
      en: 'The consecration on 27 July 1985',
      ls: 'Das Fest am 27. Juli 1985',
    },
    match: (p) => p.startsWith('neuetk/einweihung/'),
  },
  {
    key: 'kreuzwegweihe',
    titles: {
      de: 'Die Kreuzwegweihe am 15. August 1987',
      en: 'The blessing of the Stations of the Cross on 15 August 1987',
      ls: 'Das Fest für den Kreuz-Weg am 15. August 1987',
    },
    match: (p) => p.startsWith('neuetk/kreuzwegweihe/'),
  },
  {
    key: 'kreuzwegbilder',
    titles: {
      de: 'Die 14 Kreuzwegbilder',
      en: 'The 14 Stations of the Cross',
      ls: 'Die 14 Bilder vom Kreuz-Weg',
    },
    notes: {
      de: 'Gemalt von Helma Fritsche-Flügel auf Kupferplatten.',
      en: 'Painted by Helma Fritsche-Flügel on copper plates.',
      ls: 'Helma Fritsche-Flügel hat diese Bilder gemalt.',
    },
    match: (p) => p.startsWith('neuetk/kreuzwegbilder/'),
  },
  {
    key: 'restaurierung',
    titles: {
      de: 'Die Restaurierung der alten Kapelle 1987 bis 1990',
      en: 'The restoration of the old chapel, 1987 to 1990',
      ls: 'Die alte Kapelle wird repariert: 1987 bis 1990',
    },
    match: (p) => p.startsWith('altetk/renovierung/'),
  },
  {
    key: 'menschen',
    titles: {
      de: 'Emil Weber und die Initiatoren',
      en: 'Emil Weber and the initiators',
      ls: 'Emil Weber und seine Helfer',
    },
    match: (p) => p.startsWith('initiatoren/'),
  },
  {
    key: 'boehmerwald',
    titles: {
      de: 'Böhmerwald und Bayerischer Wald',
      en: 'The Bohemian Forest and the Bavarian Forest',
      ls: 'Der Böhmer-Wald und der Bayerische Wald',
    },
    match: (p) => p.startsWith('kontakt/'),
  },
];

const CAPTIONS_DE = {
  // --- Die neue Tussetkapelle ---
  'ntkaltar.jpg': 'Der Altarraum der neuen Tussetkapelle',
  'ntkwinterbild.jpg': 'Die neue Tussetkapelle im Winter',
  'zeichnungntkumkehr.jpg': 'Zeichnung der Tussetkapelle',
  'neuetk/einleitung/neuetk.jpg': 'Die neue Tussetkapelle in Philippsreut',
  'neuetk/einleitung/ntkaltetk.jpg': 'Die alte Tussetkapelle in verfallenem Zustand',
  'neuetk/einleitung/ntkgedenkstein.jpg': 'Der Gedenkstein vor der Kapelle',
  'neuetk/einleitung/ntkkarte.jpg': 'Die Lage der alten und der neuen Tussetkapelle',
  'neuetk/einleitung/ntksonnenuntergang.jpg': 'Die Kapelle im Abendlicht',
  'neuetk/einleitung/ntkemil_otto.jpg':
    'Emil Weber mit Bürgermeister Otto Damasko bei der Überreichung der Patenschafts-Urkunde',

  // --- Die alte Tussetkapelle ---
  'altetk/tusset_alt.jpg': 'Die alte Tussetkapelle auf dem Tussetberg',
  'altetk/kapelleundwallern/postkarte.jpg': 'Postkarte mit dem Wallerer Becken und dem Tussetberg',
  'altetk/kapelleundwallern/wallern.jpg': 'Wallern im Böhmerwald, einst Herberge am Goldenen Steig',
  'altetk/kapelleundwallern/gebhausklauser.jpg':
    'Wallern mit Hellgasse im Vordergrund. Das Eckhaus von der Kirche links (Frounzl) gehörte Jakob Klauser. Im Hintergrund der Tusset.',
  'altetk/kapelleundwallern/feuersturm.jpg':
    'Beim großen Feuersturm in Wallern am 22./23.7.1863 ging auch die Pfarrkirche unter und mit ihr das Gnadenbild der „Muttergottes vom Tussetberg“.',
  'altetk/kreuzwege/atkstationsbild.jpg':
    'Stationsbild des Guthausener Kreuzweges (nach Bayern gerettet und heute in der neuen Tussetkapelle)',
  'altetk/kreuzwege/atkverwuestet.jpg': 'Verwüstet und trostlos – das Innere der alten Kapelle (1980)',
  'altetk/kreuzwege/atkverfall.jpg':
    'Dem Verfall preisgegeben – Die Gnadenkapelle auf dem Tussetberg im Jahre 1980',
  'altetk/kreuzwege/atk1945.jpg': 'Das Innere der alten Tussetkapelle',
  'altetk/kreuzwege/atkzeichnung.jpg': 'Zeichnung der alten Tussetkapelle',
  'altetk/kreuzwege/boehmroehren.jpg': 'Das alte Böhmisch-Röhren',
  'altetk/kreuzwege/tussetgb.jpg': 'Tusset, Glöckelbauer (links die Kapelle mit dem Glockengestühl)',
  'altetk/kreuzwege/guthausen.jpg': 'Das Holzhauerdorf Guthausen am Nordhang des Tussetberges',
  'altetk/kreuzwege/stannakapelle.jpg': 'St.-Anna-Kapelle in Leimsgrub, erbaut um 1930.',

  // --- Die Gnadenbilder ---
  'altetk/gnadenbilder/ignazschraml.jpg': 'Ignaz Schraml',
  'altetk/gnadenbilder/gnbildischraml.jpg': 'Kopie des Gnadenbildes von Ignaz Schraml',
  'altetk/gnadenbilder/gnbildrauscher.jpg':
    'Tussetbild von Malermeister Karl Rauscher aus Wallern',
  'altetk/gnadenbilder/wallfahrtszettel.jpg': '„Wallfahrtszettel“ von der Tussetmadonna',
  'altetk/gnadenbilder/gnbildrestauriert.jpg':
    'Das aufgetauchte Gnadenbild nach der Restaurierung durch Frau Fritsche-Flügel',
  'altetk/gnadenbilder/rindenmadonna.jpg':
    'Die „Rindenmadonna“, die Frau Blechschmied bei der Vertreibung gerettet hat',

  // --- Der Wiederaufbau ---
  'neuetk/entstehung/emilweber.jpg': 'Emil Weber',
  'neuetk/entstehung/treffen1.jpg':
    'Erstes Zusammentreffen der Gemeindebetreuung von Obermoldau mit dem 1. Bürgermeister Otto Damasko in Philippsreut, 1982',
  'neuetk/entstehung/tkplan.jpg':
    'Aufgrund dieser Zeichnung wurden die Baugesuche entworfen und zur genehmigung eingereicht',
  'neuetk/entstehung/fenstertk.jpg': 'Fertige Fensterläden und Fenster (insgesamt 20 Stück)',
  'neuetk/entstehung/ruinetk.jpg':
    'Dem Verfall preisgegeben. (Die alte Tussetkapelle bei unserem ersten Besuch im April 1983)',
  'neuetk/entstehung/ewzimmern.jpg':
    '(Emil Weber bei der Zimmerarbeit im Sägewerk Ekstein in Uhingen)',
  'neuetk/entstehung/gemarbeiten.jpg':
    '(Bürgermeister Otto Damasko mit seinen Gemeindearbeitern beim Ausheben der Grundfeste)',
  'neuetk/entstehung/winterlager.jpg':
    '(Emil Weber vor dem Winterlager, vorne Dachsparren der Steinkapelle)',
  'neuetk/entstehung/lkwladen.jpg': 'Das Beladen des Transporters, 31. Mai 1984',
  'neuetk/entstehung/aufrichten.jpg': 'Das Aufrichten des Holzfachwerkes, Juni 1984',
  'neuetk/entstehung/spengler.jpg': 'Die Montage des Kupferdachs, Juli 1984',
  'neuetk/entstehung/tkfertig.jpg': 'Die fertiggestellte neue Tussetkapelle',

  // --- Die Einweihung 1985 ---
  'neuetk/einweihung/einladung.jpg': 'Die Einladung zur Einweihung',
  'neuetk/einweihung/tkinnen1.jpg': 'Der festlich geschmückte Innenraum',
  'neuetk/einweihung/festzug.jpg': 'Der Festzug durch das Dorf',
  'neuetk/einweihung/bwjugendgp.jpg': 'Die Böhmerwaldjugend in Tracht',
  'neuetk/einweihung/sm-neubauer-und-emil.jpg': 'Staatsminister Franz Neubauer und Emil Weber',
  'neuetk/einweihung/bwjugendzelt.jpg': 'Die Böhmerwaldjugend im Festzelt',
  'neuetk/einweihung/bischofeder.jpg': 'Bischof Dr. Franz Eder aus Passau',
  'neuetk/einweihung/gnadenbildtk.jpg': 'Das Gnadenbild auf der Birkenbahre',
  'neuetk/einweihung/lr-schumertl-und-emil.jpg': 'Landrat Schumertl und Emil Weber',
  'neuetk/einweihung/ntkregen.jpg': '„Auch der Himmel spendet uns sein Weihwasser!“',
  'neuetk/einweihung/ewgnadenbild.jpg': 'Emil Weber mit dem Gnadenbild',

  // --- Die Kreuzwegweihe 1987 ---
  'neuetk/kreuzwegweihe/stationsbilder.jpg': 'Die 14 Kreuzwegtafeln auf dem Dorfplatz',
  'neuetk/kreuzwegweihe/salnau.jpg': 'Kreuzwegtafel mit der Kirche von Salnau',
  'neuetk/kreuzwegweihe/geistlichkeit.jpg': 'Alle Pfarreien fanden sich zum Festakt ein',
  'neuetk/kreuzwegweihe/festakt.jpg': 'Der Festakt am Dorfplatz von Philippsreut',
  'neuetk/kreuzwegweihe/emilottqhelma.jpg':
    'Emil Weber mit der Malerin Helma Fritsche-Flügel',
  'neuetk/kreuzwegweihe/stbuebergabe.jpg':
    'Anschließend übergab Emil Weber an die Abordnungen der Stiftergemeinden ihre Bilder.',
  'neuetk/kreuzwegweihe/gerhardfranz.jpg':
    'In Böhmerwaldtracht die Söhne Emil Webers, Franz und Gerhard',
  'neuetk/kreuzwegweihe/stbweihe1.jpg':
    'Vor der Tussetkapelle weiht Pfarrer Pimmer die Stationsbilder',
  'neuetk/kreuzwegweihe/kreuzwegzug.jpg': 'Der Zug der Wallfahrer durch die Fluren',
  'neuetk/kreuzwegweihe/kwgebete.jpg': 'Pfarrer Pimmer spricht die Kreuzweg-Gebete',
  'neuetk/kreuzwegweihe/letztekwstation.jpg': 'Die letzte Kreuzwegstation',

  // --- Die Kreuzwegbilder ---
  'neuetk/kreuzwegbilder/st1marterl.jpg': 'Ein Marterl des Kreuzweges',
  'neuetk/kreuzwegbilder/kreuzweg.jpg': 'Der Kreuzweg in einem weiten Bogen über dem Dorf',
  'neuetk/kreuzwegbilder/st1.jpg': '1. Station – Jesus steht im Morgengrauen vor seinen Richtern',
  'neuetk/kreuzwegbilder/st2.jpg': '2. Station – Jesus nimmt das Kreuz auf die Schulter',
  'neuetk/kreuzwegbilder/st3.jpg': '3. Station – Jesus fällt zum ersten Mal auf steinigen Boden',
  'neuetk/kreuzwegbilder/st4.jpg': '4. Station – Die Begegnung Jesu mit seiner geliebten Mutter',
  'neuetk/kreuzwegbilder/st5.jpg': '5. Station – Simon hilft Jesus das Kreuz tragen',
  'neuetk/kreuzwegbilder/st6.jpg': '6. Station – Veronika reicht Jesus das Tuch dar',
  'neuetk/kreuzwegbilder/st7.jpg': '7. Station – Jesus fällt das zweite Mal unter dem Kreuz',
  'neuetk/kreuzwegbilder/st8.jpg': '8. Station – Jesus begegnet den weinenden Frauen',
  'neuetk/kreuzwegbilder/st9.jpg': '9. Station – Jesus fällt zum dritten Mal',
  'neuetk/kreuzwegbilder/st10.jpg': '10. Station – Jesus wird seiner Kleider beraubt',
  'neuetk/kreuzwegbilder/st11.jpg': '11. Station – Jesus wird an das Kreuz genagelt',
  'neuetk/kreuzwegbilder/st12.jpg': '12. Station – Der Gekreuzigte stirbt am Steinriegel',
  'neuetk/kreuzwegbilder/st13.jpg':
    '13. Station – Jesus, der Heiland der Welt, ruht im Schoß der Mutter',
  'neuetk/kreuzwegbilder/st14.jpg':
    '14. Station – Jesu Grablegung bei der alten Tussetkapelle, gewidmet dem Dorf Tusset',

  // --- Die Restaurierung ---
  'altetk/renovierung/atkruine1.jpg':
    'In diesem Zustand befand sich die alte Tussetkapelle im Mai 1987',
  'altetk/renovierung/atkruine2.jpg': 'Die alte Tussetkapelle, 1988',
  'altetk/renovierung/atkrenov1.jpg': 'Die restaurierte alte Tussetkapelle',
  'altetk/renovierung/atkrenov2.jpg': 'Die alte Tussetkapelle während der Restaurierung',
  'altetk/renovierung/atkrenov3.jpg': 'Die restaurierte alte Tussetkapelle von der Seite',
  'altetk/renovierung/atkrenov4.jpg': 'Naturschützer bei den Aufräumungsarbeiten',
  'altetk/renovierung/atkeinweihung.jpg':
    'Die Einweihung der erneuerten alten Tussetkapelle im August 1990',
  'altetk/renovierung/alteundneuetk.jpg': 'Die alte und die neue Tussetkapelle',

  // --- Emil Weber und die Initiatoren ---
  'initiatoren/emilweber.jpg': 'Emil Weber, Gemeindebetreuer von Obermoldau',
  'initiatoren/ottodamasko.jpg': 'Otto Damasko, 1. Bürgermeister von Philippsreut',
  'initiatoren/gerhardedlmann.jpg': 'Gerhard Edlmann, Architekt',
  'initiatoren/emilweber/sbew1.jpg': 'Emil Weber vor der neuen Tussetkapelle',
  'initiatoren/emilweber/weberfamilie.jpg': 'v.l. Marie, Liebreich, Franz, Anna und Emil Weber',
  'initiatoren/emilweber/urgrosselternemi.jpg': 'Emil Webers Großeltern väterlicherseits',
  'initiatoren/emilweber/elendbachl.jpg':
    'Links im Bild an der Wand lehnend die von Emil Webers Vater erzeugten Siebreifen',
  'initiatoren/emilweber/emilmarine.jpg': 'Emil Weber als Soldat bei der Kriegsmarine',
  'initiatoren/emilweber/hzmarieemil.jpg':
    'v.l. Emils Schwester Marie, seine Frau Maria, geb. Prinz, Emil und sein Schwager Karl Prinz',
  'initiatoren/emilweber/hzemilanna.jpg': 'Hochzeit von Emil Weber und Anna Spitzl, 1960',
  'initiatoren/emilweber/grabstein1.jpg': 'Der Grabstein von Emil Weber',

  // --- Böhmerwald ---
  'kontakt/haidmuehle.jpg': 'Landschaft bei Haidmühle',
  'kontakt/stubenbachsee.jpg': 'Der Stubenbachsee im Böhmerwald',
};

/* Die 16 Detailaufnahmen von 1983. Die Bezeichnungen stammen aus den
   Fensternamen des Original-JavaScripts in fotogalerie.htm. */
const ATK1983 = {
  1: 'Emil Weber bei der Vermessung der alten Kapelle, 1983',
  2: 'Der Turm der alten Kapelle, 1983',
  3: 'Eine Säule der alten Kapelle, 1983',
  4: 'Die Tür der alten Kapelle, 1983',
  5: 'Die Bänke der alten Kapelle, 1983',
  6: 'Ein Fenster der alten Kapelle, 1983',
  7: 'Die Empore der alten Kapelle, 1983',
  8: 'Die Empore der alten Kapelle, 1983',
  9: 'Eine Stütze der alten Kapelle, 1983',
  10: 'Der Eingang der alten Kapelle, 1983',
  11: 'Das Mauerwerk der alten Kapelle, 1983',
  12: 'Die Dachkonstruktion der alten Kapelle, 1983',
  13: 'Balken der alten Kapelle, 1983',
  14: 'Balken der alten Kapelle, 1983',
  15: 'Balken der alten Kapelle, 1983',
  16: 'Ein Fenster der alten Kapelle, 1983',
};
for (const [n, cap] of Object.entries(ATK1983)) {
  CAPTIONS_DE[`fotogalerie/fotosatk/atk1983_${n}.jpg`] = cap;
}

/* --- Zusammensetzen ------------------------------------------------------ */

const CAPTIONS = { de: CAPTIONS_DE, en: CAP_EN, ls: CAP_LS };

/** Seitenkopf je Sprache. */
const PAGE_TEXT = {
  de: {
    navLabel: 'Galerie',
    kicker: 'Bildergalerie',
    title: 'Fotogalerie Tussetkapelle',
    subtitle: 'Historische Bilder der alten und der neuen Tussetkapelle',
    description:
      'Alle Bilder der Tussetkapelle: die alte Gnadenkapelle im Böhmerwald, die ' +
      'Detailaufnahmen von 1983, der Wiederaufbau, die Einweihung 1985, der Kreuzweg ' +
      'und die Menschen, die den Wiederaufbau möglich gemacht haben.',
    intro:
      'Durch Klick aufs Bild werden diese vergrößert. Mit den Pfeiltasten blättern ' +
      'Sie weiter, mit Escape schließen Sie die Ansicht wieder.',
  },
  en: {
    navLabel: 'Gallery',
    kicker: 'Photo gallery',
    title: 'Photo gallery of the Tusset Chapel',
    subtitle: 'Historical photographs of the old and the new Tusset Chapel',
    description:
      'All the photographs of the Tusset Chapel: the old pilgrimage chapel in the ' +
      'Bohemian Forest, the detailed views of 1983, the reconstruction, the ' +
      'consecration of 1985, the Way of the Cross and the people who made the ' +
      'reconstruction possible.',
    intro:
      'Click on a picture to enlarge it. Use the arrow keys to move between ' +
      'pictures and press Escape to close the view again.',
  },
  ls: {
    navLabel: 'Bilder',
    kicker: 'Bilder',
    title: 'Bilder von der Tusset-Kapelle',
    subtitle: 'Alte und neue Bilder',
    description:
      'Hier sehen Sie alle Bilder von der Tusset-Kapelle. Von der alten Kapelle ' +
      'im Böhmer-Wald. Und von der neuen Kapelle in Philippsreut.',
    intro:
      'Hier sehen Sie viele Bilder. Klicken Sie auf ein Bild. Dann wird das Bild ' +
      'groß. Mit den Pfeil-Tasten sehen Sie das nächste Bild. Mit der Taste Escape ' +
      'machen Sie das Bild wieder zu.',
  },
};

const all = Object.keys(manifest)
  .filter((p) => !(p in EXCLUDE))
  .sort();

let report = [];

for (const lang of ['de', 'en', 'ls']) {
  const caps = CAPTIONS[lang];
  const used = new Set();
  const sections = [];
  const missing = [];

  for (const s of SECTIONS) {
    const items = all
      .filter((p) => !used.has(p) && s.match(p))
      .map((p) => {
        used.add(p);
        const caption = caps[p];
        if (caption === undefined) missing.push(p);
        return { src: p, caption: caption ?? '' };
      });
    if (!items.length) continue;
    const out = { title: s.titles[lang], items };
    if (s.notes) out.note = s.notes[lang];
    sections.push(out);
  }

  const orphans = all.filter((p) => !used.has(p));
  if (orphans.length) {
    console.error(`FEHLER (${lang}): keinem Abschnitt zugeordnet:\n  ` + orphans.join('\n  '));
    process.exit(1);
  }
  if (missing.length) {
    console.error(
      `FEHLER (${lang}): keine Bildunterschrift für:\n  ` + missing.join('\n  '),
    );
    process.exit(1);
  }

  const t = PAGE_TEXT[lang];
  const page = {
    id: 'galerie',
    type: 'gallery',
    parent: 'home',
    navLabel: t.navLabel,
    kicker: t.kicker,
    title: t.title,
    subtitle: t.subtitle,
    description: t.description,
    _quelle: 'inhalte/fotogalerie/fotogalerie.htm sowie alle Bilder der Altsite',
    _erzeugt:
      'Diese Datei wird von tools/make-gallery.mjs erzeugt. Nicht direkt bearbeiten. ' +
      'Bildunterschriften: Deutsch in make-gallery.mjs, Englisch und Leichte ' +
      'Sprache in gallery-captions.mjs.',
    intro: [{ t: 'p', lede: true, html: t.intro }],
    sections,
  };

  writeFileSync(
    join(ROOT, `src/content/${lang}/galerie.json`),
    JSON.stringify(page, null, 2) + '\n',
  );

  const total = sections.reduce((n, s) => n + s.items.length, 0);
  report.push(`${lang}: ${sections.length} Abschnitte, ${total} Bilder`);
}

console.log(
  `galerie.json erzeugt – ${report.join(' | ')} ` +
    `(${Object.keys(EXCLUDE).length} Bild bewusst ausgenommen)`,
);
