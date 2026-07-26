/**
 * Nachweis: alle Bilder der Altsite sind übernommen.
 *
 * Prüft zweierlei:
 *   1. Jedes Bild aus dem Bestand ist auf mindestens einer Seite eingebunden.
 *   2. Jedes eingebundene Bild existiert auch als Datei.
 *
 * Aufruf: node tools/check-images.mjs
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(join(ROOT, 'src/image-manifest.json'), 'utf8'));

/** Bewusst nicht eingebundene Bilder – jedes mit Begründung. */
const EXPECTED_UNUSED = {
  'neuetk/anfahrt/karte.gif':
    'Kartenausschnitt mit dem Aufdruck „©2002 Microsoft Corp ©2002 Navteq“. ' +
    'Eine Weiterveröffentlichung ist urheberrechtlich ungeklärt; die Anfahrt ' +
    'steht auf der Besuchsseite als Text.',
};

/* --- Alle HTML-Dateien einsammeln ---------------------------------------- */

const pages = [];
(function collect(d) {
  for (const e of readdirSync(d)) {
    // Nur auf oberster Ebene ausschließen: die Galerie in Leichter Sprache
    // liegt unter /ls/bilder/ und darf nicht mit dem Bildordner /bilder/
    // verwechselt werden.
    if (d === ROOT && ['bilder', 'src', 'tools', 'node_modules', '.git', '.claude'].includes(e))
      continue;
    const p = join(d, e);
    if (statSync(p).isDirectory()) collect(p);
    else if (/\.html$/.test(e)) pages.push(p);
  }
})(ROOT);

/* --- Referenzen sammeln --------------------------------------------------- */

const referenced = new Set();
const brokenRefs = [];

// Erfasst src, srcset und href – Galeriebilder sind zugleich Links auf die Datei.
const IMG_REF = /(?:src|href)="([^"]*\/bilder\/[^"]+)"|srcset="([^"]*)"/g;

for (const page of pages) {
  const html = readFileSync(page, 'utf8');
  for (const m of html.matchAll(IMG_REF)) {
    const urls = m[1]
      ? [m[1]]
      : m[2].split(',').map((s) => s.trim().split(/\s+/)[0]);
    for (const url of urls) {
      if (!url.includes('/bilder/')) continue;
      const rel = url.slice(url.indexOf('/bilder/') + '/bilder/'.length);
      if (!existsSync(join(ROOT, 'bilder', rel))) {
        brokenRefs.push({ page: relative(ROOT, page), rel });
        continue;
      }
      // Abgeleitete Größenstufen auf ihr Basisbild zurückführen.
      const base = rel.replace(/-(\d{3,4})\.(jpg|webp)$/, (_, __, ext) => `.${ext}`);
      referenced.add(base.replace(/\.webp$/, '.jpg'));
      referenced.add(base);
      referenced.add(rel);
    }
  }
}

/* --- Auswertung ----------------------------------------------------------- */

const all = Object.keys(manifest);
const unused = all.filter((p) => !referenced.has(p));
const unexpected = unused.filter((p) => !(p in EXPECTED_UNUSED));

console.log('Bildabdeckung');
console.log(`  Bilder im Bestand      : ${all.length}`);
console.log(`  geprüfte Seiten        : ${pages.length}`);
console.log(`  eingebunden            : ${all.length - unused.length}`);
console.log(`  bewusst nicht genutzt  : ${unused.length - unexpected.length}`);
console.log(`  unerwartet ungenutzt   : ${unexpected.length}`);
console.log(`  defekte Verweise       : ${brokenRefs.length}`);

let failed = false;

if (unexpected.length) {
  failed = true;
  console.log('\nUNERWARTET NICHT EINGEBUNDEN:');
  for (const p of unexpected) console.log(`  · ${p}`);
}

if (brokenRefs.length) {
  failed = true;
  console.log('\nDEFEKTE BILDVERWEISE:');
  for (const b of brokenRefs) console.log(`  · ${b.page}: bilder/${b.rel}`);
}

if (failed) process.exit(1);

console.log('\nErgebnis: alle Bilder sind eingebunden, kein Verweis ist defekt.');
if (unused.length) {
  console.log('\nBewusst nicht eingebunden:');
  for (const p of unused) console.log(`  ${p}\n      ${EXPECTED_UNUSED[p]}\n`);
}
