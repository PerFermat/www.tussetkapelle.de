/**
 * Die vier Seitentypen: Startseite, Langtext, Kapitelübersicht, Galerie.
 */

import { esc, inline, renderBlocks, picture, galleryItem } from './blocks.mjs';
import { icon } from './icons.mjs';
import { breadcrumb } from './layout.mjs';

const attr = (n, v) =>
  v === undefined || v === null || v === false ? '' : ` ${n}="${esc(v)}"`;

/* --- Seitenkopf der Unterseiten ------------------------------------------ */

function pageHead(ctx) {
  const p = ctx.page;
  return (
    '<div class="page-head"><div class="wrap">' +
    (p.kicker ? `<p class="page-head__eyebrow">${inline(p.kicker)}</p>` : '') +
    `<h1 class="page-head__title">${inline(p.title)}</h1>` +
    (p.subtitle ? `<p class="page-head__sub">${inline(p.subtitle)}</p>` : '') +
    '</div></div>'
  );
}

/* --- Startseite ---------------------------------------------------------- */

function hero(ctx, h) {
  // Das einzige Bild der Seite, das über die volle Breite läuft. Es ist auch
  // das größte im Bestand (1994x789) – alle anderen sind 125–580 px breit und
  // würden hier zwangsläufig unscharf.
  const img = picture(ctx, h.img, {
    alt: h.alt,
    loading: 'eager',
    fetchpriority: 'high',
    sizes: '100vw',
  });

  return (
    '<section class="hero">' +
    `<div class="hero__media">${img}</div>` +
    '<div class="hero__veil"></div>' +
    '<div class="wrap hero__inner"><div class="hero__text">' +
    `<h1 class="hero__title">${inline(h.title)}</h1>` +
    `<p class="hero__subtitle">${inline(h.subtitle)}</p>` +
    '<hr class="rule">' +
    `<p class="hero__lede">${inline(h.lede)}</p>` +
    `<a class="btn btn--gold" href="${esc(ctx.href(h.cta.to))}">` +
    `${esc(h.cta.label)}${icon('chevronRight')}</a>` +
    '</div></div></section>'
  );
}

function tiles(ctx, list) {
  return (
    '<div class="tiles">' +
    list
      .map((t) => {
        const href = esc(ctx.href(t.to));
        return (
          '<article class="tile">' +
          `<a class="tile__hit" href="${href}" tabindex="-1" aria-hidden="true"><span>${esc(
            t.title,
          )}</span></a>` +
          `<div class="tile__media">${picture(ctx, t.img, {
            alt: t.alt ?? '',
            sizes: '(min-width: 64rem) 300px, (min-width: 40rem) 45vw, 92vw',
          })}</div>` +
          '<div class="tile__body">' +
          `<span class="tile__badge">${icon(t.icon)}</span>` +
          // h2, nicht h3: die Kacheln sind Abschnitte erster Ordnung unter der
          // Seitenüberschrift. Ein h3 an dieser Stelle wäre ein Sprung in der
          // Überschriftenordnung und für Screenreader-Navigation irritierend.
          `<h2 class="tile__title">${inline(t.title)}</h2>` +
          `<p class="tile__text">${inline(t.text)}</p>` +
          `<a class="arrow-link tile__more" href="${href}">${esc(t.more)}${icon(
            'chevronRight',
          )}</a>` +
          '</div></article>'
        );
      })
      .join('') +
    '</div>'
  );
}

function visitCard(ctx, v) {
  return (
    '<aside class="visit-card">' +
    '<div class="visit-card__head">' +
    icon('clock') +
    `<h2 class="visit-card__title">${inline(v.title)}</h2>` +
    '</div>' +
    '<hr class="rule rule--center">' +
    `<p class="visit-card__hours">${inline(v.openLabel)}<strong>${inline(
      v.hours,
    )}</strong></p>` +
    `<p class="visit-card__place">${icon('pin')}<span>${inline(v.place)}</span></p>` +
    `<a class="btn btn--green" href="${esc(ctx.href(v.cta.to))}">` +
    `${esc(v.cta.label)}${icon('chevronRight')}</a>` +
    '</aside>'
  );
}

function timeline(ctx, tl) {
  return (
    '<div class="wrap"><div class="timeline-panel">' +
    `<h2 class="section-title">${inline(tl.title)}</h2>` +
    '<ol class="timeline">' +
    tl.items
      .map(
        (i) =>
          '<li class="timeline__item">' +
          `<span class="timeline__marker">${icon(i.icon)}</span>` +
          '<div class="timeline__body">' +
          `<span class="timeline__when">${inline(i.when)}</span>` +
          `<p class="timeline__what">${inline(i.what)}</p>` +
          '</div></li>',
      )
      .join('') +
    '</ol></div></div>'
  );
}

function homePage(ctx) {
  const p = ctx.page;
  return [
    hero(ctx, p.hero),
    '<section class="section section--tight"><div class="wrap">',
    '<div class="home-grid">',
    tiles(ctx, p.tiles),
    visitCard(ctx, p.visit),
    '</div></div></section>',
    '<section class="section">',
    timeline(ctx, p.timeline),
    '</section>',
    p.blocks && p.blocks.length
      ? `<section class="section--paper"><div class="wrap"><div class="prose">${renderBlocks(
          ctx,
          p.blocks,
        )}</div></div></section>`
      : '',
  ].join('\n');
}

/* --- Langtext ------------------------------------------------------------ */

function articlePage(ctx) {
  return [
    pageHead(ctx),
    breadcrumb(ctx),
    '<div class="wrap"><article class="prose">',
    renderBlocks(ctx, ctx.page.blocks),
    '</article></div>',
  ].join('\n');
}

/* --- Kapitelübersicht ---------------------------------------------------- */

function hubPage(ctx) {
  const p = ctx.page;
  return [
    pageHead(ctx),
    breadcrumb(ctx),
    '<div class="wrap"><div class="prose">',
    renderBlocks(ctx, p.intro || []),
    '</div></div>',
    '<section class="section"><div class="wrap">',
    renderBlocks(ctx, p.blocks),
    '</div></section>',
  ].join('\n');
}

/* --- Galerie ------------------------------------------------------------- */

function galleryPage(ctx) {
  const p = ctx.page;

  const sections = p.sections
    .map(
      (s) =>
        '<section class="gallery-section">' +
        '<div class="gallery-section__head">' +
        `<h2 class="gallery-section__title">${inline(s.title)}</h2>` +
        (s.note ? `<p class="gallery-section__count">${inline(s.note)}</p>` : '') +
        '</div>' +
        '<div class="gallery-grid">' +
        s.items.map((it) => galleryItem(ctx, it)).join('') +
        '</div></section>',
    )
    .join('\n');

  return [
    pageHead(ctx),
    breadcrumb(ctx),
    '<div class="wrap"><div class="prose">',
    renderBlocks(ctx, p.intro || []),
    '</div></div>',
    '<section class="section"><div class="wrap">',
    sections,
    '</div></section>',
  ].join('\n');
}

/* --- Auswahl ------------------------------------------------------------- */

const byType = {
  home: homePage,
  article: articlePage,
  hub: hubPage,
  gallery: galleryPage,
};

export function renderPage(ctx) {
  const fn = byType[ctx.page.type || 'article'];
  if (!fn) throw new Error(`Unbekannter Seitentyp: ${ctx.page.type}`);
  return fn(ctx);
}

/** Nur Galerieseiten brauchen das Lightbox-Gerüst. */
export function needsLightbox(page) {
  return (page.type || 'article') === 'gallery';
}
