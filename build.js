/**
 * Erzeugt die statische Website aus src/content/ und src/templates/.
 *
 *   node build.js
 *
 * Node 18, keine Abhängigkeiten. Ergebnis sind fertige HTML-Dateien im
 * Projektwurzelverzeichnis, die unverändert per FTP hochgeladen werden können.
 *
 * Aufbau:
 *   src/content/site.<lang>.json   Navigation, Slugs, Oberflächentexte
 *   src/content/<lang>/<id>.json   eine Datei je Seite
 *   src/image-manifest.json        Maße und Größenstufen (aus tools/)
 *
 * Deutsch liegt im Wurzelverzeichnis, Englisch unter /en/, Leichte Sprache
 * unter /ls/. Verlinkt wird nie über Pfade, sondern immer über Seiten-IDs –
 * dadurch kann eine Adresse geändert werden, ohne 60 Dateien anzufassen.
 */

import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { document_ } from './src/templates/layout.mjs';
import { renderPage, needsLightbox } from './src/templates/pages.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = join(ROOT, 'src');
const CONTENT = join(SRC, 'content');

/** Ausgabebasis, falls die Seite nicht auf der Domainwurzel liegt. */
const BASE = (process.env.SITE_BASE || '').replace(/\/$/, '');
const ORIGIN = process.env.SITE_ORIGIN || 'https://www.tussetkapelle.de';

const LANGS = ['de', 'en', 'ls'];

/** JSON lesen und im Fehlerfall sagen, WELCHE Datei defekt ist. */
function readJson(p) {
  const text = readFileSync(p, 'utf8');
  try {
    return JSON.parse(text);
  } catch (err) {
    // Häufigster Fehler beim Erfassen: ein ASCII-" statt des deutschen „…“
    // beendet den String vorzeitig. Zeilennummer dazu ersparen viel Suchen.
    const pos = Number((err.message.match(/position (\d+)/) || [])[1]);
    const line = Number.isFinite(pos) ? text.slice(0, pos).split('\n').length : '?';
    throw new Error(`${p}, Zeile ${line}: ${err.message}`);
  }
}

/* --- Einlesen ------------------------------------------------------------ */

const manifest = readJson(join(SRC, 'image-manifest.json'));

const sites = {};
const pagesByLang = {};

for (const lang of LANGS) {
  const sitePath = join(CONTENT, `site.${lang}.json`);
  if (!existsSync(sitePath)) {
    console.warn(`  übersprungen: ${lang} (site.${lang}.json fehlt noch)`);
    continue;
  }
  sites[lang] = readJson(sitePath);

  const dir = join(CONTENT, lang);
  const pages = {};
  if (existsSync(dir)) {
    for (const f of readdirSync(dir).filter((f) => f.endsWith('.json'))) {
      const page = readJson(join(dir, f));
      const id = page.id || f.replace(/\.json$/, '');
      page.id = id;
      pages[id] = page;
    }
  }
  pagesByLang[lang] = pages;
}

const activeLangs = LANGS.filter((l) => sites[l]);
if (!activeLangs.length) {
  console.error('FEHLER: keine Sprachdateien gefunden.');
  process.exit(1);
}

/* --- Adressen ------------------------------------------------------------ */

/** Verzeichnispfad einer Seite, z. B. "geschichte/emil-weber" oder "" */
function slugOf(lang, id) {
  const slugs = sites[lang].slugs;
  if (!(id in slugs)) {
    throw new Error(`Kein Slug für "${id}" in site.${lang}.json`);
  }
  return slugs[id];
}

/** Öffentliche Adresse, immer mit führendem und abschließendem Schrägstrich. */
function urlOf(lang, id) {
  const prefix = sites[lang].dir ? `/${sites[lang].dir}` : '';
  const slug = slugOf(lang, id);
  return `${BASE}${prefix}/${slug ? slug + '/' : ''}` || '/';
}

const site_slugs = (lang) => sites[lang].slugs;

/** Dateipfad im Ausgabeverzeichnis. */
function fileOf(lang, id) {
  const prefix = sites[lang].dir ? sites[lang].dir : '';
  const slug = slugOf(lang, id);
  return join(ROOT, prefix, slug, 'index.html');
}

/* --- Außenlinks ----------------------------------------------------------- */

/**
 * Sorgt dafür, dass jeder Verweis auf eine fremde Adresse in einem neuen
 * Browser-Tab öffnet.
 *
 * Das geschieht bewusst hier und nicht in den Inhaltsdateien: dort müsste man
 * es bei jedem einzelnen Verweis von Hand setzen und würde früher oder später
 * einen vergessen. Ergänzt werden:
 *
 *   target="_blank"            öffnet in einem neuen Tab
 *   rel="noopener noreferrer"  verhindert, dass die geöffnete Seite über
 *                              window.opener auf diese Seite zugreifen kann
 *   ein unsichtbarer Zusatz    nennt Screenreader-Nutzern den Tabwechsel,
 *                              der sonst unangekündigt geschähe (WCAG 3.2.5)
 */
function externalLinks(html, site) {
  const hint = site.ui.newTab;
  return html.replace(
    /<a\b([^>]*\bhref="https?:\/\/[^"]*"[^>]*)>([\s\S]*?)<\/a>/g,
    (whole, attrs, inner) => {
      // Verweise auf die eigene Domain sind keine Außenlinks.
      if (attrs.includes(ORIGIN)) return whole;

      let a = attrs;
      if (!/\btarget=/.test(a)) a += ' target="_blank"';

      if (/\brel="/.test(a)) {
        a = a.replace(/\brel="([^"]*)"/, (_, rel) => {
          const parts = new Set(rel.split(/\s+/).filter(Boolean));
          parts.add('noopener');
          parts.add('noreferrer');
          return `rel="${[...parts].join(' ')}"`;
        });
      } else {
        a += ' rel="noopener noreferrer"';
      }

      const marker = `<span class="visually-hidden">${hint}</span>`;
      const suffix = inner.includes(marker) ? '' : marker;
      return `<a${a}>${inner}${suffix}</a>`;
    },
  );
}

/* --- Kontext je Seite ---------------------------------------------------- */

function makeCtx(lang, page) {
  const site = sites[lang];
  const pages = pagesByLang[lang];

  /** Reihenfolge aller Kapitelseiten für die Blätternavigation. */
  const sequence = site.sequence || [];

  const ctx = {
    lang,
    site,
    page,
    manifest,
    allSites: activeLangs.map((l) => sites[l]),

    /** Statische Datei (CSS, JS, Bild) – wurzelrelativ. */
    asset: (p) => `${BASE}/${p}`,

    /** Adresse einer Seite in der aktuellen Sprache. */
    href: (id) => urlOf(lang, id),

    /** Adresse derselben Seite in einer anderen Sprache. */
    hrefIn: (otherLang, id) => {
      const s = sites[otherLang];
      if (!s) return urlOf(lang, id);
      // Fehlt die Seite in der anderen Fassung, führt der Link auf deren Start.
      return id in s.slugs ? urlOf(otherLang, id) : urlOf(otherLang, 'home');
    },

    absUrl: (path) => `${ORIGIN}${path}`,

    pageById: (id) => pages[id] || { id, title: id },

    /** Kurzes Navigationslabel, sonst der Seitentitel. */
    navLabel: (id) => {
      const p = pages[id];
      return (p && (p.navLabel || p.title)) || id;
    },

    /** Ist dieser Navigationseintrag der aktive Zweig? */
    isActive: (entry) => {
      if (entry.id === page.id) return true;
      if (!entry.panel) return false;
      return entry.panel.some((g) => g.items.includes(page.id));
    },

    /** Pfad von der Startseite zur aktuellen Seite. */
    trail: (id) => {
      const out = [];
      let cur = id;
      const seen = new Set();
      while (cur && !seen.has(cur)) {
        seen.add(cur);
        out.unshift(cur);
        cur = pages[cur] && pages[cur].parent;
      }
      if (out[0] !== 'home') out.unshift('home');
      return out;
    },

    /** Vorige und nächste Seite innerhalb der Kapitelfolge. */
    siblings: (id) => {
      const i = sequence.indexOf(id);
      if (i === -1) return {};
      return {
        prev: i > 0 ? pages[sequence[i - 1]] : null,
        next: i < sequence.length - 1 ? pages[sequence[i + 1]] : null,
      };
    },

    /**
     * hreflang-Verweise. Leichte Sprache bleibt außen vor: es gibt kein
     * BCP-47-Kennzeichen dafür, und ein falsches „de" würde die Fassung als
     * Dublette der deutschen Seite ausgeben. Sie wird stattdessen über
     * rel="alternate" ohne hreflang und den sichtbaren Sprachwechsler geführt.
     */
    hreflangs: (id) => {
      const out = [];
      for (const l of activeLangs) {
        if (l === 'ls') continue;
        const s = sites[l];
        if (!(id in s.slugs)) continue;
        out.push(
          `<link rel="alternate" hreflang="${s.htmlLang}" href="${ORIGIN}${urlOf(l, id)}">`,
        );
      }
      if ('de' in sites && id in sites.de.slugs) {
        out.push(`<link rel="alternate" hreflang="x-default" href="${ORIGIN}${urlOf('de', id)}">`);
      }
      if (sites.ls && id in sites.ls.slugs) {
        out.push(
          `<link rel="alternate" type="text/html" title="${sites.ls.label}" ` +
            `href="${ORIGIN}${urlOf('ls', id)}">`,
        );
      }
      return out.join('\n');
    },
  };

  return ctx;
}

/* --- Bauen --------------------------------------------------------------- */

console.log('Tussetkapelle – Website bauen\n');

let written = 0;
const sitemap = [];

for (const lang of activeLangs) {
  const pages = pagesByLang[lang];
  const ids = Object.keys(pages);
  if (!ids.length) {
    console.log(`  ${lang}: keine Inhaltsseiten`);
    continue;
  }

  for (const id of ids) {
    const page = pages[id];
    const ctx = makeCtx(lang, page);

    // Strukturierte Daten für die Startseite. Ausschließlich Angaben, die in
    // start.htm der Altsite stehen: Name, Ort, Öffnungszeiten, Weihedatum.
    if (id === 'home') {
      page.jsonLd = JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'PlaceOfWorship',
        additionalType: 'https://schema.org/LandmarksOrHistoricalBuildings',
        name: 'Tussetkapelle Philippsreut',
        alternateName: 'Neue Tussetkapelle',
        description: page.description,
        url: ctx.absUrl(ctx.href('home')),
        image: ctx.absUrl(ctx.asset('bilder/ntkaltar-1400.jpg')),
        address: {
          '@type': 'PostalAddress',
          addressLocality: 'Philippsreut',
          addressRegion: 'Bayern',
          addressCountry: 'DE',
        },
        openingHoursSpecification: {
          '@type': 'OpeningHoursSpecification',
          dayOfWeek: [
            'Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday',
          ],
          opens: '08:00',
          closes: '20:00',
        },
        isAccessibleForFree: true,
        foundingDate: '1985-07-27',
      });
    }

    const main = renderPage(ctx);
    let html = document_(ctx, main, { withLightbox: needsLightbox(page) });

    // In den Inhaltsdateien stehen interne Verweise als {{href:seiten-id}}.
    // Erst hier werden daraus Adressen – dadurch bleiben die Texte frei von
    // Pfaden und eine Adressänderung wirkt überall gleichzeitig.
    html = html.replace(/\{\{href:([a-z0-9-]+)\}\}/g, (_, id) => {
      if (!(id in site_slugs(lang))) {
        throw new Error(`${lang}/${page.id}: unbekannte Seiten-ID im Verweis "${id}"`);
      }
      return urlOf(lang, id);
    });

    html = externalLinks(html, sites[lang]);

    const out = fileOf(lang, id);
    mkdirSync(dirname(out), { recursive: true });
    writeFileSync(out, html);
    written++;

    sitemap.push({
      loc: `${ORIGIN}${urlOf(lang, id)}`,
      priority: id === 'home' ? '1.0' : page.parent === 'home' ? '0.8' : '0.6',
    });
  }
  console.log(`  ${lang}: ${ids.length} Seiten`);
}

/* --- Statische Dateien --------------------------------------------------- */

mkdirSync(join(ROOT, 'assets'), { recursive: true });
cpSync(join(SRC, 'assets'), join(ROOT, 'assets'), { recursive: true });

/* --- sitemap.xml und robots.txt ------------------------------------------ */

writeFileSync(
  join(ROOT, 'sitemap.xml'),
  '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    sitemap
      .map((e) => `  <url><loc>${e.loc}</loc><priority>${e.priority}</priority></url>`)
      .join('\n') +
    '\n</urlset>\n',
);

writeFileSync(
  join(ROOT, 'robots.txt'),
  `User-agent: *\nAllow: /\n\nSitemap: ${ORIGIN}${BASE}/sitemap.xml\n`,
);

/* --- 404-Seite ------------------------------------------------------------ */

/**
 * Die Fehlerseite wird für alle drei Sprachen zugleich geschrieben, weil der
 * Server bei einer unbekannten Adresse nicht wissen kann, welche Sprache
 * gemeint war. Sie nennt alle drei Startseiten.
 */
{
  const de = sites.de;
  const notFound = {
    id: 'home',
    type: 'article',
    title: 'Seite nicht gefunden',
    metaTitle: '404 – Seite nicht gefunden | Tussetkapelle Philippsreut',
    description:
      'Diese Adresse gibt es auf dieser Website nicht. Hier finden Sie den Weg ' +
      'zurück zur Startseite in Deutsch, Englisch oder Leichter Sprache.',
    kicker: 'Fehler 404',
    blocks: [
      {
        t: 'p',
        lede: true,
        html: 'Diese Adresse gibt es hier nicht. Vielleicht wurde die Seite verschoben, oder in der Adresse ist ein Tippfehler.',
      },
      { t: 'h2', text: 'Weiter zur Startseite' },
      {
        t: 'list',
        items: activeLangs.map(
          (l) => `<a href="${urlOf(l, 'home')}" hreflang="${sites[l].htmlLang}">${sites[l].label}</a>`,
        ),
      },
      { t: 'h2', text: 'This page does not exist' },
      {
        t: 'p',
        lang: 'en',
        html: `The address you requested is not available on this website. Please continue to the <a href="${urlOf(
          'en',
          'home',
        )}">English home page</a>.`,
      },
    ],
  };

  const ctx = makeCtx('de', notFound);
  // Der Kontext zeigt auf die Startseite; für die Fehlerseite selbst soll aber
  // keine kanonische Adresse behauptet und nicht indexiert werden.
  let html = document_(ctx, renderPage(ctx))
    .replace(/<link rel="canonical"[^>]*>\n?/, '')
    .replace(
      '<meta name="robots" content="index, follow">',
      '<meta name="robots" content="noindex, follow">',
    )
    .replace(/<link rel="alternate"[^>]*>\n?/g, '');

  html = html.replace(/\{\{href:([a-z0-9-]+)\}\}/g, (_, id) => urlOf('de', id));
  writeFileSync(join(ROOT, '404.html'), html);
  console.log('  404.html');
}

console.log(`\n${written} HTML-Dateien, sitemap.xml mit ${sitemap.length} Adressen.`);
