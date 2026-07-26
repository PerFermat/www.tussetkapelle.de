/**
 * Seitengerüst: <head>, Kopfzeile mit Navigation, Sprachwahl, Fußzeile.
 *
 * Die Navigation liegt vollständig im Markup – auch das Aufklappmenü und die
 * mobile Fassung. JavaScript blendet nur ein und aus. Ohne JavaScript bleibt
 * die Seite damit vollständig bedienbar.
 */

import { esc, inline } from './blocks.mjs';
import { icon } from './icons.mjs';

const attr = (n, v) =>
  v === undefined || v === null || v === false ? '' : ` ${n}="${esc(v)}"`;

/* --- <head> -------------------------------------------------------------- */

function head(ctx) {
  const { page, site } = ctx;
  const title = page.metaTitle || `${page.title} – ${site.brand.name} ${site.brand.place}`;
  const canonical = ctx.absUrl(ctx.href(page.id));

  // hreflang nur zwischen Deutsch und Englisch. Für Leichte Sprache gibt es
  // kein BCP-47-Sprachkennzeichen; die Fassung wird über einen sichtbaren Link
  // und rel="alternate" erreichbar gemacht, nicht über hreflang.
  const alternates = ctx.hreflangs(page.id);

  const ogImage = ctx.absUrl(ctx.asset(page.ogImage || 'bilder/ntkaltar-1400.jpg'));

  return `<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(page.description || '')}">
<link rel="canonical" href="${esc(canonical)}">
${alternates}
<meta name="theme-color" content="#304332">
<meta name="robots" content="index, follow">
<meta property="og:type" content="website">
<meta property="og:site_name" content="${esc(site.brand.name)} ${esc(site.brand.place)}">
<meta property="og:locale" content="${esc(site.ogLocale)}">
<meta property="og:title" content="${esc(page.title)}">
<meta property="og:description" content="${esc(page.description || '')}">
<meta property="og:url" content="${esc(canonical)}">
<meta property="og:image" content="${esc(ogImage)}">
<meta property="og:image:alt" content="${esc(site.ui.heroAlt)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="${esc(ctx.asset('assets/favicon.svg'))}" type="image/svg+xml">
<link rel="stylesheet" href="${esc(ctx.asset('assets/site.css'))}">
${page.jsonLd ? `<script type="application/ld+json">${page.jsonLd}</script>` : ''}`;
}

/* --- Wortmarke ----------------------------------------------------------- */

/**
 * Wortmarke: Symbol links, daneben zwei Zeilen.
 *
 *   Kopfzeile   TUSSETKAPELLE / PHILIPPSREUT
 *   Fußzeile    Tussetkapelle Philippsreut / Erinnerungsort der Böhmerwäldler
 */
function brand(ctx, { small = false } = {}) {
  const { site } = ctx;
  const line1 = small
    ? `${site.brand.name} ${site.brand.place}`
    : site.brand.name;
  const line2 = small ? site.ui.tagline : site.brand.place;

  return (
    `<a class="brand${small ? ' brand--footer' : ''}" href="${esc(ctx.href('home'))}">` +
    icon('chapel') +
    '<span class="brand__lines">' +
    `<span class="brand__name">${esc(line1)}</span>` +
    `<span class="brand__place">${esc(line2)}</span>` +
    '</span></a>'
  );
}

/* --- Sprachwahl ---------------------------------------------------------- */

/**
 * Sprachwahl. Ohne Trennstriche zwischen den Einträgen.
 *
 * Die Beschriftung steht immer im Markup; wo nur die Symbole erscheinen sollen
 * (Kopfzeile auf schmalen Schirmen, Fußzeile auf breiten), blendet das
 * Stylesheet den Text visuell aus. Für Screenreader bleibt er erhalten, und
 * das Symbol trägt zusätzlich ein title-Attribut.
 */
function langs(ctx, variant) {
  const items = ctx.allSites.map((s) => {
    const current = s.lang === ctx.site.lang;
    const url = ctx.hrefIn(s.lang, ctx.page.id);
    // Fehlt eine Fassung, führt der Link auf deren Startseite statt ins Leere.
    return (
      '<li class="langs__item">' +
      `<a class="langs__link" href="${esc(url)}" lang="${esc(s.htmlLang)}"` +
      attr('aria-current', current ? 'true' : false) +
      attr('hreflang', s.htmlLang) +
      attr('title', s.label) +
      '>' +
      icon(s.flag) +
      `<span class="langs__label">${esc(s.label)}</span>` +
      '</a></li>'
    );
  });
  return (
    `<ul class="langs langs--${variant}" aria-label="${esc(ctx.site.ui.langNav)}">` +
    items.join('') +
    '</ul>'
  );
}

/* --- Kopfzeile ----------------------------------------------------------- */

function desktopNav(ctx) {
  const items = ctx.site.nav.map((entry) => {
    const active = ctx.isActive(entry);
    const label = ctx.navLabel(entry.id);

    if (!entry.panel) {
      return (
        `<li class="nav__item${active ? ' nav__item--active' : ''}">` +
        `<a class="nav__link" href="${esc(ctx.href(entry.id))}"` +
        attr('aria-current', ctx.page.id === entry.id ? 'page' : false) +
        `>${esc(label)}</a></li>`
      );
    }

    const panelId = `panel-${entry.id}`;
    const groups = entry.panel
      .map(
        (g) =>
          '<div class="nav__group">' +
          `<p class="nav__group-title">${esc(g.title)}</p>` +
          '<ul class="nav__sublist">' +
          g.items
            .map(
              (id) =>
                '<li>' +
                `<a class="nav__sublink" href="${esc(ctx.href(id))}"` +
                attr('aria-current', ctx.page.id === id ? 'page' : false) +
                `>${esc(ctx.navLabel(id))}</a></li>`,
            )
            .join('') +
          '</ul></div>',
      )
      .join('');

    return (
      `<li class="nav__item nav__item--has-panel${active ? ' nav__item--active' : ''}">` +
      `<button class="nav__toggle" type="button" aria-expanded="false" aria-controls="${panelId}">` +
      `${esc(label)}${icon('chevronDown')}</button>` +
      `<div class="nav__panel" id="${panelId}" hidden>${groups}</div>` +
      '</li>'
    );
  });

  return (
    `<nav class="nav" aria-label="${esc(ctx.site.ui.mainNav)}">` +
    `<ul class="nav__list">${items.join('')}</ul></nav>`
  );
}

function mobileNav(ctx) {
  const parts = ctx.site.nav.map((entry) => {
    const link =
      '<li>' +
      `<a class="mobile-nav__link" href="${esc(ctx.href(entry.id))}"` +
      attr('aria-current', ctx.page.id === entry.id ? 'page' : false) +
      `>${esc(ctx.navLabel(entry.id))}</a></li>`;

    if (!entry.panel) return link;

    const groups = entry.panel
      .map(
        (g) =>
          `<li><p class="mobile-nav__group">${esc(g.title)}</p></li>` +
          g.items
            .map(
              (id) =>
                '<li>' +
                `<a class="mobile-nav__sublink" href="${esc(ctx.href(id))}"` +
                attr('aria-current', ctx.page.id === id ? 'page' : false) +
                `>${esc(ctx.navLabel(id))}</a></li>`,
            )
            .join(''),
      )
      .join('');

    return link + groups;
  });

  // Die Sprachwahl steht bewusst NICHT hier drin: sie bleibt auch auf
  // schmalen Schirmen sichtbar in der Kopfzeile stehen, dort nur als Symbole.
  return (
    `<div class="mobile-nav" id="mobile-nav" hidden>` +
    `<div class="wrap"><nav aria-label="${esc(ctx.site.ui.mainNav)}">` +
    `<ul class="mobile-nav__list">${parts.join('')}</ul></nav>` +
    '</div></div>'
  );
}

function header(ctx) {
  return (
    '<header class="site-header">' +
    '<div class="wrap site-header__bar">' +
    brand(ctx) +
    desktopNav(ctx) +
    langs(ctx, 'header') +
    `<button class="burger" type="button" aria-expanded="false" aria-controls="mobile-nav" ` +
    `aria-label="${esc(ctx.site.ui.menu)}">` +
    `<span class="burger__open">${icon('menu')}</span>` +
    `<span class="burger__close">${icon('close')}</span>` +
    '</button>' +
    '</div>' +
    mobileNav(ctx) +
    '</header>'
  );
}

/* --- Brotkrumen ---------------------------------------------------------- */

function breadcrumb(ctx) {
  const trail = ctx.trail(ctx.page.id);
  if (trail.length < 2) return '';

  const crumbs = trail.map((id, i) => {
    const last = i === trail.length - 1;
    const label = ctx.navLabel(id);
    return last
      ? `<li aria-current="page">${esc(label)}</li>`
      : `<li><a href="${esc(ctx.href(id))}">${esc(label)}</a></li>`;
  });

  return (
    `<nav class="breadcrumb" aria-label="${esc(ctx.site.ui.breadcrumb)}">` +
    `<div class="wrap"><ol>${crumbs.join('')}</ol></div></nav>`
  );
}

/* --- Blätternavigation --------------------------------------------------- */

function pager(ctx) {
  const { prev, next } = ctx.siblings(ctx.page.id);
  if (!prev && !next) return '';

  const cell = (p, dir, label) =>
    p
      ? `<a class="pager__link pager__link--${dir}" href="${esc(ctx.href(p.id))}">` +
        `<span class="pager__dir">${esc(label)}</span>` +
        `<span class="pager__title">${esc(ctx.navLabel(p.id))}</span></a>`
      : '<span></span>';

  return (
    '<nav class="wrap pager" aria-label="' +
    esc(ctx.site.ui.pagerNav) +
    '">' +
    cell(prev, 'prev', ctx.site.ui.prev) +
    cell(next, 'next', ctx.site.ui.next) +
    '</nav>'
  );
}

/* --- Fußzeile ------------------------------------------------------------ */

function footer(ctx) {
  const links = ctx.site.footerLinks
    .map(
      (id) =>
        `<li><a href="${esc(ctx.href(id))}">${esc(ctx.navLabel(id))}</a></li>`,
    )
    .join('');

  return (
    '<footer class="site-footer">' +
    '<div class="wrap">' +
    '<div class="site-footer__top">' +
    brand(ctx, { small: true }) +
    `<ul class="site-footer__links">${links}</ul>` +
    langs(ctx, 'footer') +
    '</div>' +
    '<div class="site-footer__legal">' +
    `<span>${inline(ctx.site.ui.copyright)}</span>` +
    `<span>${inline(ctx.site.ui.sourceNote)}</span>` +
    '</div></div></footer>'
  );
}

/* --- Lightbox-Gerüst ----------------------------------------------------- */

function lightbox(ctx) {
  const u = ctx.site.ui;
  return (
    `<dialog class="lightbox" aria-label="${esc(u.lightboxLabel)}" ` +
    `data-count-label="${esc(u.lightboxCount)}">` +
    '<div class="lightbox__inner">' +
    '<div class="lightbox__top">' +
    '<p class="lightbox__count"></p>' +
    `<button class="lightbox__btn lightbox__close" type="button" aria-label="${esc(
      u.lightboxClose,
    )}">${icon('close')}</button>` +
    '</div>' +
    '<div class="lightbox__stage">' +
    `<button class="lightbox__btn lightbox__nav lightbox__nav--prev" type="button" ` +
    `aria-label="${esc(u.lightboxPrev)}">${icon('chevronLeft')}</button>` +
    '<img alt="">' +
    `<button class="lightbox__btn lightbox__nav lightbox__nav--next" type="button" ` +
    `aria-label="${esc(u.lightboxNext)}">${icon('chevronRight')}</button>` +
    '</div>' +
    '<div class="lightbox__bottom"><p class="lightbox__caption"></p></div>' +
    '</div></dialog>'
  );
}

/* --- Ganze Seite --------------------------------------------------------- */

export function document_(ctx, main, { withLightbox = false } = {}) {
  const classes = ctx.site.lang === 'ls' ? ' class="ls"' : '';
  return `<!DOCTYPE html>
<html lang="${esc(ctx.site.htmlLang)}"${classes}>
<head>
${head(ctx)}
</head>
<body>
<a class="skip-link" href="#inhalt">${esc(ctx.site.ui.skip)}</a>
${header(ctx)}
<main id="inhalt">
${main}
</main>
${pager(ctx)}
${footer(ctx)}
${withLightbox ? lightbox(ctx) : ''}
<script src="${esc(ctx.asset('assets/site.js'))}" defer></script>
</body>
</html>
`;
}

export { breadcrumb };
