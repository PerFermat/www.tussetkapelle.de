/**
 * Inline-SVG-Symbole.
 *
 * Bewusst als Code und nicht als Bilddateien: keine zusätzlichen Requests,
 * skaliert scharf auf jedem Bildschirm, färbt sich über `currentColor` mit und
 * berührt nicht die Vorgabe „nur vorhandene Bilder verwenden" – das betrifft
 * die historischen Fotos, nicht die Bedienoberfläche.
 *
 * Alle Symbole: 24x24-Raster, Strichzeichnung, damit sie zur zurückhaltenden
 * Anmutung des Erinnerungsortes passen.
 */

const line = (body, extra = '') =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" ` +
  `stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"${
    extra ? ' ' + extra : ''
  }>${body}</svg>`;

export const icons = {
  /* Wortmarke und Zeitleiste: die Kapelle als Strichzeichnung mit Turm,
     Vordach und den beiden Rundfenstern des Originalbaus. */
  chapel: () =>
    line(
      '<path d="M12 2v3"/><path d="M10.5 3.5h3"/>' +
        '<path d="M12 5 9.5 8.5h5L12 5Z"/>' +
        '<path d="M10 8.5v3h4v-3"/>' +
        '<path d="M4 15 12 10l8 5"/>' +
        '<path d="M5.5 14.2V22h13v-7.8"/>' +
        '<path d="M10 22v-4.5h4V22"/>' +
        '<circle cx="8" cy="17" r="1"/><circle cx="16" cy="17" r="1"/>',
    ),

  book: () =>
    line(
      '<path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H10a2 2 0 0 1 2 2v14a1.5 1.5 0 0 0-1.5-1.5H5.5A1.5 1.5 0 0 1 4 16V4.5Z"/>' +
        '<path d="M20 4.5A1.5 1.5 0 0 0 18.5 3H14a2 2 0 0 0-2 2v14a1.5 1.5 0 0 1 1.5-1.5h5A1.5 1.5 0 0 0 20 16V4.5Z"/>',
    ),

  camera: () =>
    line(
      '<path d="M3 8.5A1.5 1.5 0 0 1 4.5 7h2.2a1.5 1.5 0 0 0 1.25-.67l.8-1.2A1.5 1.5 0 0 1 10 4.5h4a1.5 1.5 0 0 1 1.25.67l.8 1.2A1.5 1.5 0 0 0 17.3 7h2.2A1.5 1.5 0 0 1 21 8.5v9A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5v-9Z"/>' +
        '<circle cx="12" cy="13" r="3.5"/>',
    ),

  pin: () =>
    line(
      '<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Z"/>' +
        '<circle cx="12" cy="10" r="2.5"/>',
    ),

  clock: () => line('<circle cx="12" cy="12" r="9"/><path d="M12 7v5.2l3.2 2"/>'),

  /* Vertreibung: eine gehende Gestalt mit Bündel. */
  walking: () =>
    line(
      '<circle cx="13" cy="4.5" r="2"/>' +
        '<path d="M13 6.5 11 12l3 2 .6 7"/>' +
        '<path d="M11 12 8 15l-1 6"/>' +
        '<path d="M13 8.5l4 1.5"/>' +
        '<path d="M17 10l2.5-1"/>',
    ),

  hammer: () =>
    line(
      '<path d="M14.5 3.5 21 10l-2.5 2.5-2.2-2.2-6.6 6.6a2 2 0 0 1-2.8 0l-.8-.8a2 2 0 0 1 0-2.8l6.6-6.6-2.2-2.2L14.5 3.5Z"/>' +
        '<path d="M6 18l-2.5 2.5"/>',
    ),

  cross: () => line('<path d="M12 3v18"/><path d="M6.5 8.5h11"/>'),

  people: () =>
    line(
      '<circle cx="9" cy="8" r="3"/>' +
        '<path d="M3.5 20v-1.5A4.5 4.5 0 0 1 8 14h2a4.5 4.5 0 0 1 4.5 4.5V20"/>' +
        '<path d="M16 5.6a3 3 0 0 1 0 5.8"/>' +
        '<path d="M17.5 14.2a4.5 4.5 0 0 1 3 4.3V20"/>',
    ),

  mail: () =>
    line(
      '<rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="M3.5 6.5 12 13l8.5-6.5"/>',
    ),

  phone: () =>
    line(
      '<path d="M6.5 3.5h3l1.5 4-2 1.5a10 10 0 0 0 6 6l1.5-2 4 1.5v3a2 2 0 0 1-2 2C11.6 19.5 4.5 12.4 4.5 5.5a2 2 0 0 1 2-2Z"/>',
    ),

  route: () =>
    line(
      '<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/>' +
        '<path d="M6 8.5V13a3 3 0 0 0 3 3h6.5"/>',
    ),

  external: () =>
    line('<path d="M14 4h6v6"/><path d="M20 4l-8.5 8.5"/><path d="M18 14v5a1.5 1.5 0 0 1-1.5 1.5H5.5A1.5 1.5 0 0 1 4 19V7.5A1.5 1.5 0 0 1 5.5 6h5"/>'),

  zoom: () =>
    line('<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21"/><path d="M8 10.5h5M10.5 8v5"/>'),

  chevronRight: () => line('<path d="M9 5l7 7-7 7"/>'),
  chevronLeft: () => line('<path d="M15 5l-7 7 7 7"/>'),
  chevronDown: () => line('<path d="M5 9l7 7 7-7"/>'),
  close: () => line('<path d="M5 5l14 14M19 5 5 19"/>'),
  menu: () => line('<path d="M3.5 7h17M3.5 12h17M3.5 17h17"/>'),

  /* --- Sprachsymbole ---------------------------------------------------- */

  /* Deutschland: Schwarz, Rot, Gold. */
  flagDe: () =>
    '<svg class="langs__flag" viewBox="0 0 22 16" aria-hidden="true" focusable="false">' +
      '<rect width="22" height="16" fill="#f6f6f6"/>' +
      '<rect width="22" height="5.34" y="0" fill="#1a1a1a"/>' +
      '<rect width="22" height="5.33" y="5.34" fill="#c8102e"/>' +
      '<rect width="22" height="5.33" y="10.67" fill="#f0c400"/>' +
    '</svg>',

  /* Vereinigtes Königreich, vereinfacht. */
  flagEn: () =>
    '<svg class="langs__flag" viewBox="0 0 22 16" aria-hidden="true" focusable="false">' +
      '<rect width="22" height="16" fill="#012169"/>' +
      '<path d="M0 0l22 16M22 0L0 16" stroke="#fff" stroke-width="3.2"/>' +
      '<path d="M0 0l22 16M22 0L0 16" stroke="#c8102e" stroke-width="1.8"/>' +
      '<path d="M11 0v16M0 8h22" stroke="#fff" stroke-width="5.2"/>' +
      '<path d="M11 0v16M0 8h22" stroke="#c8102e" stroke-width="3"/>' +
    '</svg>',

  /* Leichte Sprache.
     WICHTIG: Das offizielle Logo für Leichte Sprache (Inclusion Europe /
     Netzwerk Leichte Sprache) ist markenrechtlich geschützt und wird hier
     NICHT nachgebildet. Dies ist ein eigenes, neutrales Zeichen: ein Blatt
     mit kurzen Textzeilen und einem Häkchen – „einfach zu lesen". */
  flagLs: () =>
    '<svg class="langs__flag" viewBox="0 0 22 16" aria-hidden="true" focusable="false">' +
      '<rect width="22" height="16" rx="2" fill="#2e5c8a"/>' +
      '<path d="M5 5.2h9M5 8h7.5M5 10.8h5" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>' +
      '<path d="M14 10.6l1.9 1.9 3.3-3.9" stroke="#ffd24d" stroke-width="1.8" ' +
        'stroke-linecap="round" stroke-linejoin="round" fill="none"/>' +
    '</svg>',
};

/** Symbol ausgeben; unbekannte Namen fallen sichtbar auf, statt still zu fehlen. */
export function icon(name) {
  const fn = icons[name];
  if (!fn) throw new Error(`Unbekanntes Symbol: ${name}`);
  return fn();
}
