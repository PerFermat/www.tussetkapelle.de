/**
 * Renderer für die Inhaltsblöcke.
 *
 * Die Inhaltsdateien nennen bei Bildern nur den Pfad. Maße, WebP-Varianten und
 * srcset kommen aus src/image-manifest.json. Damit sind width/height immer
 * gesetzt (kein Layout-Sprung beim Laden) und kein Bild wird über seine
 * Nativbreite hinaus vergrößert – bei einem Bestand aus 125–580 px breiten
 * Aufnahmen ist das die wichtigste Regel überhaupt.
 */

import { icon } from './icons.mjs';

/* --- Hilfen -------------------------------------------------------------- */

const AMP = /&(?!(?:[a-zA-Z][a-zA-Z0-9]*|#\d+|#x[0-9a-fA-F]+);)/g;

/** Escaping für Text, der als Attribut oder reiner Textknoten landet. */
export const esc = (s = '') =>
  String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

/**
 * Für Inhaltstext, der bewusst Inline-Markup enthalten darf
 * (<strong>, <em>, <a>, <br>, <span lang>). Nur nackte & werden abgesichert,
 * damit bestehende Entities wie &nbsp; erhalten bleiben.
 */
export const inline = (s = '') => String(s).replace(AMP, '&amp;');

const attr = (name, value) =>
  value === undefined || value === null || value === false ? '' : ` ${name}="${esc(value)}"`;

/* --- Bilder -------------------------------------------------------------- */

/**
 * Erzeugt ein <picture> mit srcset.
 *
 * @param {object} ctx    Build-Kontext, enthält manifest und base (Pfadtiefe)
 * @param {string} src    Pfad relativ zu bilder/, z. B. "altetk/tusset_alt.jpg"
 */
export function picture(ctx, src, opts = {}) {
  const m = ctx.manifest[src];
  if (!m) throw new Error(`Bild nicht im Manifest: ${src}`);

  const {
    alt = '',
    sizes,
    className,
    loading = 'lazy',
    fetchpriority,
    decoding = 'async',
    width,
    height,
    style,
  } = opts;

  const dot = src.lastIndexOf('.');
  const stem = src.slice(0, dot);
  const ext = src.slice(dot); // .jpg | .gif | .png
  const url = (p) => ctx.asset(`bilder/${p}`);

  // Kandidaten von klein nach groß; die Nativgröße bildet die letzte Stufe.
  const jpgSet = [];
  const webpSet = [];
  for (const s of m.steps) {
    if (s.jpg) jpgSet.push(`${url(`${stem}-${s.box}${ext === '.gif' ? '.jpg' : ext}`)} ${s.w}w`);
    if (s.webp) webpSet.push(`${url(`${stem}-${s.box}.webp`)} ${s.w}w`);
  }
  jpgSet.push(`${url(src)} ${m.w}w`);
  if (m.webp) webpSet.push(`${url(`${stem}.webp`)} ${m.w}w`);

  // Ohne echte Auswahl ist srcset nur Ballast.
  const useSets = m.steps.length > 0;
  const sizesAttr = sizes || `(min-width: 60rem) ${m.w}px, 100vw`;

  const img =
    `<img${attr('src', url(src))}` +
    (useSets ? attr('srcset', jpgSet.join(', ')) + attr('sizes', sizesAttr) : '') +
    attr('width', width ?? m.w) +
    attr('height', height ?? m.h) +
    attr('alt', alt) +
    attr('loading', loading) +
    attr('decoding', decoding) +
    attr('fetchpriority', fetchpriority) +
    attr('class', className) +
    attr('style', style) +
    '>';

  if (!m.webp) return img;

  const source =
    `<source type="image/webp"${attr('srcset', webpSet.join(', '))}` +
    (useSets ? attr('sizes', sizesAttr) : '') +
    '>';

  return `<picture>${source}${img}</picture>`;
}

/** <figure> mit Bildunterschrift, Ausrichtung und Nativbreiten-Deckel. */
export function figure(ctx, f) {
  const m = ctx.manifest[f.src];
  if (!m) throw new Error(`Bild nicht im Manifest: ${f.src}`);

  const align = f.align || 'center';
  const capWidth = Math.min(m.w, f.max || m.w);
  // --fig-w begrenzt die Anzeige auf die echte Bildbreite (kein Upscaling).
  const style = `--fig-w:${capWidth}px`;

  const sizes =
    align === 'right' || align === 'left'
      ? `(min-width: 60rem) ${Math.min(capWidth, 430)}px, 100vw`
      : `(min-width: 60rem) ${capWidth}px, 100vw`;

  const img = picture(ctx, f.src, {
    alt: f.alt ?? '',
    sizes,
    loading: f.eager ? 'eager' : 'lazy',
    fetchpriority: f.eager ? 'high' : undefined,
  });

  const caption = f.caption
    ? `<figcaption class="figcaption">${inline(f.caption)}</figcaption>`
    : '';

  return (
    `<figure class="figure figure--${align}"${attr('style', style)}>` +
    `<div class="figure__frame">${img}</div>${caption}</figure>`
  );
}

/* --- Blocktypen ---------------------------------------------------------- */

const renderers = {
  p: (ctx, b) =>
    `<p${attr('class', b.lede ? 'prose__lede' : null)}${attr('lang', b.lang)}>${inline(
      b.html,
    )}</p>`,

  h2: (ctx, b) => `<h2${attr('id', b.id)}>${inline(b.text)}</h2>`,
  h3: (ctx, b) => `<h3${attr('id', b.id)}>${inline(b.text)}</h3>`,

  fig: (ctx, b) => figure(ctx, b),

  figrow: (ctx, b) =>
    `<div class="figrow">${b.items.map((f) => figure(ctx, { ...f, align: 'center' })).join('')}</div>`,

  list: (ctx, b) => {
    const tag = b.ordered ? 'ol' : 'ul';
    return `<${tag}>${b.items.map((i) => `<li>${inline(i)}</li>`).join('')}</${tag}>`;
  },

  /* Beschreibungsliste, z. B. „Wissenswertes für die Besucher": Altar,
     Altarstein, Kruzifix, Gussplatte, Schmiedeeisengitter, Kreuzweg, Glocke. */
  dl: (ctx, b) =>
    '<dl class="deflist">' +
    b.items
      .map((i) => `<dt>${inline(i.term)}</dt><dd>${inline(i.html)}</dd>`)
      .join('') +
    '</dl>',

  /* Der Brief des tschechischen Restaurators von 1988 als eigenes Dokument. */
  letter: (ctx, b) =>
    '<div class="letter">' +
    (b.meta ? `<p class="letter__meta">${inline(b.meta)}</p>` : '') +
    (b.blocks || []).map((x) => render(ctx, x)).join('') +
    (b.sign ? `<p class="letter__sign">${inline(b.sign)}</p>` : '') +
    '</div>',

  note: (ctx, b) =>
    '<aside class="note">' +
    (b.title ? `<p class="note__title">${inline(b.title)}</p>` : '') +
    (b.html ? `<p>${inline(b.html)}</p>` : '') +
    (b.blocks || []).map((x) => render(ctx, x)).join('') +
    '</aside>',

  quote: (ctx, b) =>
    `<blockquote class="quote"><p>${inline(b.html)}</p>` +
    (b.cite ? `<cite>${inline(b.cite)}</cite>` : '') +
    '</blockquote>',

  sources: (ctx, b) => `<p class="sources">${inline(b.html)}</p>`,

  table: (ctx, b) =>
    '<div class="table-scroll"><table class="table">' +
    (b.caption ? `<caption>${inline(b.caption)}</caption>` : '') +
    (b.head
      ? `<thead><tr>${b.head.map((h) => `<th scope="col">${inline(h)}</th>`).join('')}</tr></thead>`
      : '') +
    '<tbody>' +
    b.rows
      .map(
        (r) =>
          '<tr>' +
          r
            .map((c, i) =>
              i === 0
                ? `<th scope="row">${inline(c)}</th>`
                : `<td>${inline(c)}</td>`,
            )
            .join('') +
          '</tr>',
      )
      .join('') +
    '</tbody></table></div>',

  /**
   * Eine Kreuzwegstation: Überschrift, Bild und Text bilden eine Einheit.
   *
   * Mit umflossenen Bildern (float) verschiebt sich der Text der 14 Stationen
   * gegeneinander, sobald ein Absatz länger ist als das Bild hoch – dann steht
   * Bild 5 neben Text 6. Als Raster bleibt jede Station für sich geschlossen
   * und Bild und Text stehen auf jeder Bildschirmbreite beieinander.
   */
  station: (ctx, b) => {
    const m = ctx.manifest[b.src];
    if (!m) throw new Error(`Bild nicht im Manifest: ${b.src}`);
    const img = picture(ctx, b.src, {
      alt: b.alt ?? '',
      sizes: `(min-width: 60rem) ${m.w}px, (min-width: 40rem) 40vw, 100vw`,
    });
    return (
      `<section class="station station--${b.flip ? 'right' : 'left'}">` +
      `<h3 class="station__title"${attr('id', b.id)}>${inline(b.title)}</h3>` +
      `<figure class="station__media" style="--fig-w:${m.w}px">${img}</figure>` +
      `<div class="station__text"><p>${inline(b.html)}</p></div>` +
      '</section>'
    );
  },

  /* Erklärkasten für Leichte Sprache. */
  explain: (ctx, b) =>
    '<aside class="ls-explain">' +
    `<p><span class="ls-explain__word">${inline(b.word)}</span><br>${inline(b.html)}</p>` +
    '</aside>',

  /* Untergeordnete Seiten als Kachelreihe (Kapitelübersicht). */
  chapters: (ctx, b) => renderChapterGroups(ctx, b),

  /* Nur für Sonderfälle, absichtlich sparsam. */
  raw: (ctx, b) => b.html,
};

export function render(ctx, block) {
  const fn = renderers[block.t];
  if (!fn) throw new Error(`Unbekannter Blocktyp: ${block.t}`);
  return fn(ctx, block);
}

export function renderBlocks(ctx, blocks = []) {
  return blocks.map((b) => render(ctx, b)).join('\n');
}

/* --- Kapitelübersicht ---------------------------------------------------- */

function renderChapterGroups(ctx, b) {
  return b.groups
    .map(
      (g) =>
        '<section class="chapter-group">' +
        `<h2 class="chapter-group__title">${inline(g.title)}</h2>` +
        '<div class="chapters">' +
        g.items
          .map((it) => {
            const page = ctx.pageById(it.id);
            const img = it.img
              ? `<div class="chapter-card__media">${picture(ctx, it.img, {
                  alt: '',
                  sizes: '(min-width: 60rem) 280px, 45vw',
                })}</div>`
              : '';
            return (
              '<article class="chapter-card">' +
              img +
              '<div class="chapter-card__body">' +
              `<h3 class="chapter-card__title"><a href="${esc(ctx.href(it.id))}">${inline(
                it.title || page.title,
              )}</a></h3>` +
              (it.sub ? `<p class="chapter-card__sub">${inline(it.sub)}</p>` : '') +
              '</div></article>'
            );
          })
          .join('') +
        '</div></section>',
    )
    .join('');
}

/* --- Galerie ------------------------------------------------------------- */

/** Ein Galeriebild: Thumbnail als Link auf das Vollbild, Lightbox per JS. */
export function galleryItem(ctx, it) {
  const m = ctx.manifest[it.src];
  if (!m) throw new Error(`Bild nicht im Manifest: ${it.src}`);

  const portrait = m.h > m.w;
  const thumb = picture(ctx, it.src, {
    alt: it.alt ?? it.caption ?? '',
    sizes: '(min-width: 60rem) 220px, (min-width: 30rem) 30vw, 45vw',
    width: undefined,
    height: undefined,
  });

  return (
    `<figure class="gallery-item${portrait ? ' gallery-item--portrait' : ''}">` +
    `<a class="gallery-item__link" href="${esc(ctx.asset(`bilder/${it.src}`))}"` +
    ' data-lightbox' +
    attr('data-caption', it.caption || '') +
    attr('data-w', m.w) +
    attr('data-h', m.h) +
    '>' +
    thumb +
    `<span class="gallery-item__zoom">${icon('zoom')}</span>` +
    '</a>' +
    (it.caption ? `<figcaption>${inline(it.caption)}</figcaption>` : '') +
    '</figure>'
  );
}
