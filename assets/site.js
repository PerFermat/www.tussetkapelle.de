/* ==========================================================================
   Tussetkapelle Philippsreut – Verhalten der Seite.

   Drei Dinge, sonst nichts: mobile Navigation, Aufklappmenü „Geschichte"
   und die Galerie-Lightbox. Keine Bibliothek, keine Cookies, kein
   localStorage, keine Netzwerkzugriffe.

   Alles ist so gebaut, dass die Seite ohne JavaScript vollständig nutzbar
   bleibt: die Navigation ist im Markup ausgeklappt vorhanden, und jedes
   Galeriebild ist ein gewöhnlicher Link auf die Bilddatei.
   ========================================================================== */

(() => {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  /* --- 1. Mobile Navigation --------------------------------------------- */

  const burger = $('.burger');
  const mobileNav = $('.mobile-nav');

  if (burger && mobileNav) {
    const setOpen = (open) => {
      burger.setAttribute('aria-expanded', String(open));
      mobileNav.hidden = !open;
      // Hintergrund für Tastatur und Screenreader stilllegen.
      document.body.style.overflow = open ? 'hidden' : '';
      if (open) {
        const first = $('a, button', mobileNav);
        if (first) first.focus();
      }
    };

    burger.addEventListener('click', () => {
      setOpen(burger.getAttribute('aria-expanded') !== 'true');
    });

    // Nach dem Sprung auf eine Ankermarke schließen.
    mobileNav.addEventListener('click', (e) => {
      if (e.target.closest('a')) setOpen(false);
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && burger.getAttribute('aria-expanded') === 'true') {
        setOpen(false);
        burger.focus();
      }
    });

    // Beim Wechsel auf Desktopbreite aufräumen.
    matchMedia('(min-width: 60rem)').addEventListener('change', (ev) => {
      if (ev.matches) setOpen(false);
    });
  }

  /* --- 2. Aufklappmenü „Geschichte" ------------------------------------- */

  $$('.nav__item--has-panel').forEach((item) => {
    const toggle = $('.nav__toggle', item);
    const panel = $('.nav__panel', item);
    if (!toggle || !panel) return;

    let hoverTimer;
    const open = () => {
      clearTimeout(hoverTimer);
      toggle.setAttribute('aria-expanded', 'true');
      panel.hidden = false;
    };
    const close = () => {
      toggle.setAttribute('aria-expanded', 'false');
      panel.hidden = true;
    };
    // Kleine Verzögerung, damit das Menü beim Überstreichen nicht flackert.
    const closeSoon = () => {
      clearTimeout(hoverTimer);
      hoverTimer = setTimeout(close, 180);
    };

    toggle.addEventListener('click', () => {
      toggle.getAttribute('aria-expanded') === 'true' ? close() : open();
    });

    item.addEventListener('mouseenter', open);
    item.addEventListener('mouseleave', closeSoon);

    // Bei Tastaturbedienung schließen, sobald der Fokus das Menü verlässt.
    item.addEventListener('focusout', (e) => {
      if (!item.contains(e.relatedTarget)) close();
    });

    toggle.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        open();
        const first = $('a', panel);
        if (first) first.focus();
      }
    });

    panel.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      close();
      toggle.focus();
    });
  });

  /* --- 3. Lightbox ------------------------------------------------------ */

  const dialog = $('.lightbox');
  const links = $$('[data-lightbox]');

  // <dialog> ist Voraussetzung. Fehlt es, bleiben die Links funktionsfähig.
  if (!dialog || !links.length || typeof dialog.showModal !== 'function') return;

  const stage = $('.lightbox__stage img', dialog);
  const caption = $('.lightbox__caption', dialog);
  const counter = $('.lightbox__count', dialog);
  const btnPrev = $('.lightbox__nav--prev', dialog);
  const btnNext = $('.lightbox__nav--next', dialog);
  const btnClose = $('.lightbox__close', dialog);
  const countLabel = dialog.dataset.countLabel || '{i} / {n}';

  // Nur Bilder derselben Galeriegruppe bilden eine Blätterfolge.
  const items = links.map((a) => ({
    el: a,
    href: a.getAttribute('href'),
    caption: a.dataset.caption || '',
    w: a.dataset.w,
    h: a.dataset.h,
  }));

  let index = -1;
  let opener = null;

  const render = () => {
    const it = items[index];
    if (!it) return;
    // Maße vorab setzen: verhindert das Springen beim Laden.
    if (it.w) stage.width = it.w;
    if (it.h) stage.height = it.h;
    stage.src = it.href;
    stage.alt = it.caption;
    caption.textContent = it.caption;
    counter.textContent = countLabel
      .replace('{i}', String(index + 1))
      .replace('{n}', String(items.length));
    btnPrev.disabled = index === 0;
    btnNext.disabled = index === items.length - 1;

    // Nachbarbilder vorladen, damit das Blättern flüssig wirkt.
    [index - 1, index + 1].forEach((i) => {
      if (items[i]) new Image().src = items[i].href;
    });
  };

  const go = (delta) => {
    const next = index + delta;
    if (next < 0 || next >= items.length) return;
    index = next;
    render();
  };

  links.forEach((a, i) => {
    a.addEventListener('click', (e) => {
      // Modifiziertes Klicken (neuer Tab) nicht abfangen.
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
      e.preventDefault();
      index = i;
      opener = a;
      render();
      dialog.showModal();
    });
  });

  btnPrev.addEventListener('click', () => go(-1));
  btnNext.addEventListener('click', () => go(1));
  btnClose.addEventListener('click', () => dialog.close());

  dialog.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      go(-1);
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      go(1);
    }
    // Escape schließt <dialog> von sich aus.
  });

  // Klick auf die Fläche neben dem Bild schließt.
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog || e.target.classList.contains('lightbox__inner')) {
      dialog.close();
    }
  });

  // Wischen auf Touchgeräten.
  let touchX = null;
  dialog.addEventListener(
    'touchstart',
    (e) => {
      touchX = e.changedTouches[0].clientX;
    },
    { passive: true },
  );
  dialog.addEventListener(
    'touchend',
    (e) => {
      if (touchX === null) return;
      const dx = e.changedTouches[0].clientX - touchX;
      if (Math.abs(dx) > 45) go(dx < 0 ? 1 : -1);
      touchX = null;
    },
    { passive: true },
  );

  // Fokus dorthin zurückgeben, wo die Lightbox geöffnet wurde.
  dialog.addEventListener('close', () => {
    stage.removeAttribute('src');
    if (opener) {
      opener.focus();
      opener = null;
    }
  });
})();
