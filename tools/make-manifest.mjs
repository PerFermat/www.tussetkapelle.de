/**
 * Erzeugt src/image-manifest.json aus dem Bestand in bilder/.
 *
 * Der Builder liest daraus Maße und verfügbare Größenstufen, damit in den
 * Inhaltsdateien nur der Bildpfad stehen muss. Dadurch sind width/height
 * (gegen Layout-Sprünge) und srcset immer korrekt und müssen nie händisch
 * nachgezogen werden.
 *
 * Aufruf: node tools/make-manifest.mjs
 */
import { execFileSync } from 'node:child_process';
import { readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const IMG_DIR = join(ROOT, 'bilder');
const OUT = join(ROOT, 'src', 'image-manifest.json');

/** Erkennt abgeleitete Dateien wie foo-400.jpg oder foo-1400.webp. */
const DERIVED = /^(.*)-(\d{3,4})\.(jpg|webp)$/;

function walk(dir, acc = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name);
    if (entry.isDirectory()) walk(p, acc);
    else acc.push(p);
  }
  return acc;
}

const files = walk(IMG_DIR).map((p) => relative(IMG_DIR, p).split('\\').join('/'));

// Maße ALLER Bilder holen, auch der abgeleiteten. Der Dateiname einer Stufe
// nennt nur die angeforderte Boxgröße: aus 300x446 wird bei "-resize 400x400>"
// tatsächlich 269x400. Für korrekte srcset-Deskriptoren zählt die echte Breite.
const bases = files.filter((f) => /\.(jpg|gif|png)$/.test(f) && !DERIVED.test(f));
const measurable = files.filter((f) => /\.(jpg|gif|png|webp)$/.test(f));
const dims = new Map();
const CHUNK = 150;
for (let i = 0; i < measurable.length; i += CHUNK) {
  const slice = measurable.slice(i, i + CHUNK);
  const out = execFileSync(
    'identify',
    ['-format', '%w %h %i\n', ...slice.map((f) => join(IMG_DIR, f) + '[0]')],
    { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 },
  );
  for (const line of out.trim().split('\n')) {
    const m = line.match(/^(\d+) (\d+) (.*?)(?:\[0\])?$/);
    if (!m) continue;
    dims.set(relative(IMG_DIR, m[3]).split('\\').join('/'), {
      w: +m[1],
      h: +m[2],
    });
  }
}

const present = new Set(files);
const manifest = {};

for (const f of bases) {
  const d = dims.get(f);
  if (!d) {
    console.error(`WARNUNG: keine Maße für ${f}`);
    continue;
  }
  const ext = f.slice(f.lastIndexOf('.'));
  const stem = f.slice(0, f.lastIndexOf('.'));

  // Vorhandene Größenstufen sammeln (nur die, die es wirklich gibt).
  const boxes = new Set();
  for (const cand of present) {
    const m = cand.match(DERIVED);
    if (m && m[1] === stem) boxes.add(+m[2]);
  }

  const steps = [];
  for (const box of [...boxes].sort((a, b) => a - b)) {
    const jpgName = `${stem}-${box}${ext === '.gif' ? '.jpg' : ext}`;
    const webpName = `${stem}-${box}.webp`;
    const hasJpg = present.has(jpgName);
    const hasWebp = present.has(webpName);
    // Echte Breite der Stufe, nicht die Boxgröße aus dem Dateinamen.
    const real = dims.get(hasJpg ? jpgName : webpName);
    if (!real) continue;
    // Stufen, die nicht schmaler als das Original sind, bringen nichts.
    if (real.w >= d.w) continue;
    steps.push({ box, w: real.w, h: real.h, jpg: hasJpg, webp: hasWebp });
  }

  manifest[f] = {
    w: d.w,
    h: d.h,
    bytes: statSync(join(IMG_DIR, f)).size,
    // WebP der Nativgröße – fehlt, wenn WebP nicht kleiner war als das JPEG.
    webp: present.has(`${stem}.webp`),
    steps,
  };
}

writeFileSync(OUT, JSON.stringify(manifest, null, 1) + '\n');

const nSteps = Object.values(manifest).reduce((s, m) => s + m.steps.length, 0);
const nWebp = Object.values(manifest).filter((m) => m.webp).length;
console.log(
  `image-manifest.json: ${Object.keys(manifest).length} Bilder, ` +
    `${nWebp} mit WebP, ${nSteps} Größenstufen`,
);
