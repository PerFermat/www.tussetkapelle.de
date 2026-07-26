/**
 * Probe für den Browser: findet waagerechten Überlauf – auch den von Text,
 * der die Box nicht aufweitet und deshalb von getBoundingClientRect() allein
 * nicht gefunden wird.
 *
 * Einfügen über preview_eval. Gibt eine kurze Zusammenfassung zurück.
 */
(() => {
  const vw = document.documentElement.clientWidth;
  const boxes = [];
  const texts = [];

  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;

    // 1. Box ragt über den Viewport hinaus.
    if (r.right > vw + 1 || r.left < -1) {
      boxes.push(
        `${el.tagName.toLowerCase()}.${String(el.className).split(' ')[0]} ` +
          `[${Math.round(r.left)}…${Math.round(r.right)}]`,
      );
    }

    // 2. Inhalt ist breiter als die Box – typisch für zu große Schrift,
    //    lange Wörter oder <pre>. Nur Blockelemente ohne eigenes Scrollen.
    const style = getComputedStyle(el);
    if (style.overflowX === 'visible' && el.scrollWidth > el.clientWidth + 1) {
      texts.push(
        `${el.tagName.toLowerCase()}.${String(el.className).split(' ')[0]} ` +
          `(Inhalt ${el.scrollWidth}px in Box ${el.clientWidth}px): ` +
          `"${(el.textContent || '').trim().slice(0, 40)}"`,
      );
    }
  }

  return {
    viewport: vw,
    scrollWidth: document.documentElement.scrollWidth,
    hatWaagerechtesScrollen: document.documentElement.scrollWidth > vw + 1,
    boxenUeberViewport: boxes.slice(0, 10),
    inhaltBreiterAlsBox: texts.slice(0, 10),
  };
})();
