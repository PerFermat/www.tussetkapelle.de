/**
 * Struktur-, Verweis- und Barrierefreiheitsprüfung über alle erzeugten Seiten.
 *
 * Geprüft wird:
 *   · jeder interne Verweis zeigt auf eine vorhandene Datei
 *   · jedes <img> hat alt, width und height (letztere gegen Layout-Sprünge)
 *   · genau ein <h1> je Seite, keine Sprünge in der Überschriftenordnung
 *   · <html lang>, <title>, meta description und canonical sind gesetzt
 *   · kein Verweis auf einen fremden Server im Seitenaufbau (DSGVO)
 *   · Außenlinks tragen rel="noopener noreferrer"
 *   · keine unaufgelösten {{href:…}}-Platzhalter
 *
 * Aufruf: node tools/check-links.mjs
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

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

const problems = [];
const add = (page, msg) => problems.push(`${relative(ROOT, page)}: ${msg}`);

/** Löst einen wurzelrelativen Verweis in einen Dateipfad auf. */
function resolveLocal(url) {
  const clean = url.split('#')[0].split('?')[0];
  if (!clean.startsWith('/')) return null;
  const p = join(ROOT, clean);
  return clean.endsWith('/') ? join(p, 'index.html') : p;
}

let imgCount = 0;
let linkCount = 0;

for (const page of pages) {
  const html = readFileSync(page, 'utf8');

  /* --- Kopfangaben ---------------------------------------------------- */
  if (!/<html lang="[a-z-]+"/.test(html)) add(page, 'kein lang-Attribut an <html>');
  if (!/<title>[^<]{10,}<\/title>/.test(html)) add(page, 'kein oder zu kurzer <title>');
  if (!/<meta name="description" content="[^"]{40,}"/.test(html))
    add(page, 'keine oder zu kurze meta description');
  // Die Fehlerseite darf keine kanonische Adresse behaupten: sie wird unter
  // beliebigen, nicht existierenden Adressen ausgeliefert und ist noindex.
  const isErrorPage = page.endsWith('404.html');
  if (!isErrorPage && !/<link rel="canonical" href="http/.test(html))
    add(page, 'kein canonical');
  if (isErrorPage && !/<meta name="robots" content="noindex/.test(html))
    add(page, 'Fehlerseite ohne noindex');

  /* --- Überschriftenordnung ------------------------------------------- */
  const h1 = html.match(/<h1\b/g) || [];
  if (h1.length !== 1) add(page, `${h1.length} <h1> statt genau einem`);

  const levels = [...html.matchAll(/<h([1-6])\b/g)].map((m) => +m[1]);
  for (let i = 1; i < levels.length; i++) {
    if (levels[i] - levels[i - 1] > 1)
      add(page, `Überschriftensprung h${levels[i - 1]} → h${levels[i]}`);
  }

  /* --- Bilder ---------------------------------------------------------- */
  for (const m of html.matchAll(/<img\b[^>]*>/g)) {
    const tag = m[0];
    imgCount++;
    if (!/\salt="/.test(tag)) add(page, `<img> ohne alt: ${tag.slice(0, 90)}`);
    if (!/\swidth="\d+"/.test(tag) || !/\sheight="\d+"/.test(tag)) {
      // Das Bild in der Lightbox bekommt seine Maße erst zur Laufzeit.
      if (!tag.includes('lightbox') && !/^<img alt="">$/.test(tag))
        add(page, `<img> ohne width/height: ${tag.slice(0, 90)}`);
    }
  }

  /* --- Verweise -------------------------------------------------------- */
  for (const m of html.matchAll(/<a\b[^>]*href="([^"]+)"[^>]*>/g)) {
    const [tag, href] = m;
    linkCount++;

    if (href.startsWith('http')) {
      if (!/rel="[^"]*noopener/.test(tag) || !/rel="[^"]*noreferrer/.test(tag))
        add(page, `Außenlink ohne rel="noopener noreferrer": ${href}`);
      continue;
    }
    if (href.startsWith('mailto:') || href.startsWith('#')) continue;

    const target = resolveLocal(href);
    if (!target) {
      add(page, `nicht wurzelrelativer Verweis: ${href}`);
      continue;
    }
    if (!existsSync(target)) add(page, `Verweisziel fehlt: ${href}`);
  }

  /* --- Stylesheet, Skript, Favicon ------------------------------------- */
  for (const m of html.matchAll(/(?:href|src)="(\/assets\/[^"]+)"/g)) {
    if (!existsSync(join(ROOT, m[1]))) add(page, `Datei fehlt: ${m[1]}`);
  }

  /* --- DSGVO: nichts von fremden Servern im Seitenaufbau ---------------
   *
   * Gemeint sind ausschließlich Tags, die beim Aufbau der Seite tatsächlich
   * eine Ressource holen. canonical und hreflang tragen zwar absolute
   * Adressen, laden aber nichts – sie sind Metadaten für Suchmaschinen.
   */
  const FETCHING_REL = /rel="(?:stylesheet|icon|shortcut icon|preload|prefetch|preconnect|dns-prefetch|manifest|apple-touch-icon)"/i;

  for (const m of html.matchAll(/<(script|img|source|iframe|link|video|audio|embed|object)\b([^>]*)>/gi)) {
    const [, tag, attrs] = m;
    if (tag.toLowerCase() === 'link' && !FETCHING_REL.test(attrs)) continue;
    for (const u of attrs.matchAll(/(?:src|srcset|href|data)="([^"]+)"/g)) {
      for (const url of u[1].split(',').map((s) => s.trim().split(/\s+/)[0])) {
        if (/^https?:\/\//i.test(url) || url.startsWith('//')) {
          add(page, `lädt Ressource von absoluter Adresse: <${tag}> ${url}`);
        }
      }
    }
  }

  /* --- Reste ----------------------------------------------------------- */
  if (html.includes('{{href:')) add(page, 'unaufgelöster {{href:…}}-Platzhalter');
  if (/&amp;(?:uuml|auml|ouml|szlig);/.test(html))
    add(page, 'doppelt maskierte Entity (&amp;uuml; o. ä.) im Text');
}

console.log('Struktur- und Verweisprüfung');
console.log(`  Seiten          : ${pages.length}`);
console.log(`  Bilder          : ${imgCount}`);
console.log(`  Verweise        : ${linkCount}`);
console.log(`  Beanstandungen  : ${problems.length}`);

if (problems.length) {
  console.log('');
  for (const p of problems) console.log(`  · ${p}`);
  process.exit(1);
}

console.log('\nErgebnis: keine Beanstandungen.');
