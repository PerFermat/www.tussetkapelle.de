/**
 * Liest eine Seite der Altsite und gibt sie als lesbaren Klartext aus.
 *
 * Zweck: die Inhalte wortgetreu übernehmen zu können. Die Altsite ist
 * ISO-8859-1 kodiert, benutzt Layout-Tabellen und <font>-Tags; der reine Text
 * lässt sich daraus nicht mit einem Blick ablesen.
 *
 * Ausgabe:
 *   Absätze durch Leerzeilen getrennt
 *   [BILD  pfad  BxH]           an der Stelle, an der das Bild steht
 *   [LINK  text -> ziel]        für jeden Verweis
 *
 * Aufruf:  node tools/dump-source.mjs inhalte/kontakt/kontakt.htm
 *          node tools/dump-source.mjs --all
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const SRC = process.env.TK_SRC || '/home/michael/Dokumente/tussent/www.tussetkapelle.de';

const ENTITIES = {
  nbsp: ' ', auml: 'ä', ouml: 'ö', uuml: 'ü', Auml: 'Ä', Ouml: 'Ö', Uuml: 'Ü',
  szlig: 'ß', amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", euro: '€',
  eacute: 'é', egrave: 'è', agrave: 'à', ccedil: 'ç', deg: '°', laquo: '«',
  raquo: '»', bdquo: '„', ldquo: '“', rdquo: '”', sbquo: '‚', shy: '',
  ndash: '–', mdash: '—', hellip: '…', middot: '·', sect: '§', copy: '©',
};

function decode(s) {
  return s
    .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(+d))
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/&([a-zA-Z]+);/g, (m, name) => (name in ENTITIES ? ENTITIES[name] : m));
}

function dump(file) {
  const abs = join(SRC, file);
  // Latin-1 ist verlustfrei byteweise abbildbar.
  let html = readFileSync(abs, 'latin1');

  html = html
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<(script|style)[\s\S]*?<\/\1>/gi, '');

  // Bilder und Links durch Marker ersetzen, damit ihre Position erhalten bleibt.
  html = html.replace(/<img\b[^>]*>/gi, (tag) => {
    const src = (tag.match(/src\s*=\s*["']?([^"'\s>]+)/i) || [, '?'])[1];
    const w = (tag.match(/width\s*=\s*["']?(\d+)/i) || [, '?'])[1];
    const h = (tag.match(/height\s*=\s*["']?(\d+)/i) || [, '?'])[1];
    return `\n\n[BILD  ${src}  ${w}x${h}]\n\n`;
  });

  html = html.replace(/<a\b([^>]*)>([\s\S]*?)<\/a>/gi, (m, attrs, text) => {
    const href = (attrs.match(/href\s*=\s*["']?([^"'\s>]+)/i) || [, ''])[1];
    const label = text.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
    if (!href) return label;
    return `${label}[LINK -> ${href}]`;
  });

  // Blockgrenzen zu Umbrüchen machen, dann alle übrigen Tags entfernen.
  html = html
    .replace(/<br\b[^>]*>/gi, '\n')
    .replace(/<\/(p|div|tr|h[1-6]|li|table)\s*>/gi, '\n\n')
    .replace(/<(p|div|tr|h[1-6]|li|table)\b[^>]*>/gi, '\n')
    .replace(/<\/t[dh]\s*>/gi, '\n')
    .replace(/<[^>]+>/g, '');

  let text = decode(html);

  text = text
    .split('\n')
    .map((l) => l.replace(/[ \t ]+/g, ' ').trim())
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/^\s+|\s+$/g, '');

  // Zeilen, die nur aus Trennzeichen bestehen, verwerfen.
  const kept = text
    .split('\n\n')
    .map((b) => b.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim())
    .filter((b) => b && !/^[\s|·–—-]*$/.test(b));

  const words = kept.join(' ').split(/\s+/).filter(Boolean).length;

  return `${'='.repeat(78)}\nQUELLE: ${file}   (${words} Wörter)\n${'='.repeat(78)}\n\n${kept.join(
    '\n\n',
  )}\n`;
}

const args = process.argv.slice(2);

if (args[0] === '--all') {
  const walk = (d, acc = []) => {
    for (const e of readdirSync(d)) {
      const p = join(d, e);
      if (statSync(p).isDirectory()) walk(p, acc);
      else if (/\.html?$/i.test(e)) acc.push(relative(SRC, p));
    }
    return acc;
  };
  const files = ['start.htm', ...walk(join(SRC, 'inhalte')).sort()];
  for (const f of files) process.stdout.write(dump(f) + '\n');
} else if (args.length) {
  for (const f of args) process.stdout.write(dump(f));
} else {
  console.error('Aufruf: node tools/dump-source.mjs <datei.htm> | --all');
  process.exit(1);
}
