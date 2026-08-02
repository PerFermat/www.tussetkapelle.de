"""Der Bestand: alle Seiten aller drei Sprachen.

Dies ist die einzige Stelle im Programm, die schreibt. Die Oberfläche ruft hier
an und fasst niemals selbst eine Datei an.

Der Grund für diese Strenge sind die Seitenkennungen. Eine Kennung wie
``emil-weber`` steht an sieben Stellen: im Dateinamen, im Feld ``id``, in
``slugs``, in ``nav``, in ``sequence``, in ``footerLinks``, im ``parent`` der
Unterseiten und in jedem Verweis ``{{href:emil-weber}}`` – und das dreimal, für
jede Sprachfassung. Wer nur eine davon vergisst, bekommt entweder eine Seite,
die aus dem Menü verschwindet, oder einen Abbruch beim Erzeugen. Solche
Änderungen dürfen nur geschlossen ablaufen, nie von Hand.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path as FsPath
from typing import Any

from . import jsonio
from .manifest import ImageManifest
from .page import Page
from .site import SiteConfig
from .validation import Problem, validate

__all__ = ["ContentRepository", "RepositoryError"]

LANGUAGES = ("de", "en", "ls")

_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class RepositoryError(RuntimeError):
    """Ein Vorgang wurde abgelehnt – die Meldung geht wörtlich in den Dialog."""


@dataclass
class NewPage:
    """Angaben zum Anlegen einer Seite, je Sprache ein Titel."""

    page_id: str
    parent: str
    titles: dict[str, str]
    after: str | None = None


class ContentRepository:
    def __init__(self, root: FsPath) -> None:
        self.root = root
        self.content_dir = root / "src" / "content"
        self.sites: dict[str, SiteConfig] = {}
        self.pages: dict[str, dict[str, Page]] = {}
        self.manifest = ImageManifest(root / "src" / "image-manifest.json", root / "bilder")
        self.load()

    # ------------------------------------------------------------------ #
    # Laden                                                              #
    # ------------------------------------------------------------------ #

    def load(self) -> None:
        self.sites.clear()
        self.pages.clear()
        for lang in LANGUAGES:
            site_path = self.content_dir / f"site.{lang}.json"
            if not site_path.exists():
                continue
            data, style, _ = jsonio.load_file(site_path)
            self.sites[lang] = SiteConfig(lang, site_path, data, style)

            pages: dict[str, Page] = {}
            lang_dir = self.content_dir / lang
            if lang_dir.is_dir():
                for f in sorted(lang_dir.glob("*.json")):
                    pdata, pstyle, _ = jsonio.load_file(f)
                    page_id = str(pdata.get("id") or f.stem)
                    pages[page_id] = Page(lang, page_id, f, pdata, pstyle)
            self.pages[lang] = pages

    @property
    def languages(self) -> tuple[str, ...]:
        return tuple(l for l in LANGUAGES if l in self.sites)

    def page(self, lang: str, page_id: str) -> Page | None:
        return self.pages.get(lang, {}).get(page_id)

    def page_ids(self) -> list[str]:
        """Alle Kennungen, in der Reihenfolge der deutschen Kapitelfolge."""
        seen: list[str] = ["home"]
        primary = self.sites.get("de") or next(iter(self.sites.values()), None)
        if primary:
            seen += [i for i in primary.sequence if i not in seen]
            seen += [i for i in primary.slugs if i not in seen]
        for pages in self.pages.values():
            seen += [i for i in sorted(pages) if i not in seen]
        return seen

    def children_of(self, lang: str, parent: str | None) -> list[Page]:
        """Unterseiten in der Reihenfolge der Kapitelfolge."""
        site = self.sites[lang]
        order = {pid: n for n, pid in enumerate(site.sequence)}
        kids = [p for p in self.pages[lang].values() if p.parent == parent]
        return sorted(kids, key=lambda p: (order.get(p.page_id, 10_000), p.title))

    # ------------------------------------------------------------------ #
    # Änderungen merken                                                   #
    # ------------------------------------------------------------------ #

    def touch(self, page: Page) -> None:
        page.dirty = True

    @property
    def dirty(self) -> bool:
        return any(p.dirty for pages in self.pages.values() for p in pages.values()) or any(
            s.dirty for s in self.sites.values()
        )

    def dirty_count(self) -> int:
        n = sum(1 for pages in self.pages.values() for p in pages.values() if p.dirty)
        return n + sum(1 for s in self.sites.values() if s.dirty)

    # ------------------------------------------------------------------ #
    # Speichern                                                           #
    # ------------------------------------------------------------------ #

    def problems(self) -> list[Problem]:
        return validate(self)

    def save_all(self, *, force: bool = False) -> list[FsPath]:
        """Schreibt alle geänderten Dateien. Fehler verhindern das Speichern."""
        errors = [p for p in self.problems() if p.is_error]
        if errors and not force:
            raise RepositoryError(_error_report(errors))

        written: list[FsPath] = []
        for site in self.sites.values():
            if site.dirty and jsonio.save_file(site.path, site.data, site.style):
                written.append(site.path)
            site.dirty = False
        for pages in self.pages.values():
            for page in pages.values():
                if page.dirty and jsonio.save_file(page.path, page.data, page.style):
                    written.append(page.path)
                page.dirty = False
        return written

    # ------------------------------------------------------------------ #
    # Seiten anlegen                                                      #
    # ------------------------------------------------------------------ #

    def check_new_id(self, page_id: str) -> None:
        if not _ID_RE.match(page_id):
            raise RepositoryError(
                f"„{page_id}“ ist als Kennung nicht zulässig.\n\n"
                "Erlaubt sind Kleinbuchstaben, Ziffern und Bindestriche, "
                "zum Beispiel „neue-seite“ oder „einweihung-1985“. "
                "Die Kennung wird Teil der Internetadresse."
            )
        for lang in self.languages:
            if page_id in self.pages[lang] or page_id in self.sites[lang].slugs:
                raise RepositoryError(f"Die Kennung „{page_id}“ ist schon vergeben.")

    def create_page(self, spec: NewPage) -> None:
        """Legt die Seite in allen Sprachen an.

        In allen dreien, weil der Sprachwechsler sonst für diese Seite auf die
        Startseite zurückfällt (build.js, ``hrefIn``). Eine leere Seite in einer
        Fassung ist besser als ein Link, der ins Nichts führt.
        """
        self.check_new_id(spec.page_id)
        parent_exists = any(spec.parent in self.pages[l] for l in self.languages)
        if not parent_exists:
            raise RepositoryError(f"Die übergeordnete Seite „{spec.parent}“ gibt es nicht.")

        for lang in self.languages:
            site = self.sites[lang]
            title = spec.titles.get(lang) or spec.titles.get("de") or spec.page_id
            slug = self._slug_for(lang, spec.page_id, spec.parent)

            data: dict[str, Any] = {
                "id": spec.page_id,
                "type": "article",
                "parent": spec.parent,
                "navLabel": title,
                "title": title,
                "description": title,
                "blocks": [],
            }
            path = self.content_dir / lang / f"{spec.page_id}.json"
            style = jsonio.Style(blank_before={("blocks",)})
            page = Page(lang, spec.page_id, path, data, style, dirty=True)
            self.pages[lang][spec.page_id] = page

            site.add_slug(spec.page_id, slug)
            site.insert_into_sequence(spec.page_id, spec.after or spec.parent)
            panel = site.nav_group_containing(spec.parent) or (
                site.nav_group_containing(spec.after) if spec.after else None
            )
            if panel is not None:
                items = panel["items"]
                anchor = spec.after if spec.after in items else spec.parent
                pos = items.index(anchor) + 1 if anchor in items else len(items)
                items.insert(pos, spec.page_id)

    def _slug_for(self, lang: str, page_id: str, parent: str) -> str:
        parent_slug = self.sites[lang].slugs.get(parent, "")
        return f"{parent_slug}/{page_id}" if parent_slug else page_id

    def duplicate_page(self, page_id: str, new_id: str) -> None:
        """Kopiert eine Seite samt Inhalt in allen Sprachen."""
        self.check_new_id(new_id)
        import copy

        for lang in self.languages:
            source = self.pages[lang].get(page_id)
            if source is None:
                continue
            site = self.sites[lang]
            data = copy.deepcopy(source.data)
            data["id"] = new_id
            data["title"] = f"{data.get('title', new_id)} (Kopie)"
            path = self.content_dir / lang / f"{new_id}.json"
            page = Page(lang, new_id, path, data, copy.deepcopy(source.style), dirty=True)
            self.pages[lang][new_id] = page
            site.add_slug(new_id, self._slug_for(lang, new_id, str(data.get("parent") or "home")))
            site.insert_into_sequence(new_id, page_id)

    # ------------------------------------------------------------------ #
    # Umbenennen                                                          #
    # ------------------------------------------------------------------ #

    def rename_page(self, old_id: str, new_id: str) -> list[FsPath]:
        """Benennt eine Seite in allen Sprachen um.

        Gibt die verwaisten Ausgabeverzeichnisse zurück, die dabei entfernt
        wurden. build.js räumt nicht auf: die alte index.html bliebe sonst
        liegen und würde weiter ausgeliefert.
        """
        page = next((self.pages[l].get(old_id) for l in self.languages if old_id in self.pages[l]), None)
        if page is None:
            raise RepositoryError(f"Die Seite „{old_id}“ gibt es nicht.")
        if not page.is_renamable:
            raise RepositoryError(
                f"Die Seite „{page.title}“ kann nicht umbenannt werden.\n\n"
                "Ihre Kennung steht fest in Navigation, Fußzeile und Vorlagen."
            )
        self.check_new_id(new_id)

        # Auch die Unterseiten ziehen um: ihre Adresse enthält die alte Kennung.
        removed = [
            d for pid in (old_id, *self._descendants_of(old_id)) for d in self._stale_output_dirs(pid)
        ]

        for lang in self.languages:
            site = self.sites[lang]
            old_page = self.pages[lang].pop(old_id, None)
            site.rename_id(old_id, new_id)

            if old_page is not None:
                old_page.data["id"] = new_id
                old_path = old_page.path
                old_page.page_id = new_id
                old_page.path = old_path.with_name(f"{new_id}.json")
                old_page.dirty = True
                self.pages[lang][new_id] = old_page
                if old_path.exists():
                    old_path.unlink()

            for other in self.pages[lang].values():
                if other.parent == old_id:
                    other.parent = new_id
                    other.dirty = True
                if _replace_links(other.data, old_id, new_id):
                    other.dirty = True

        for path in removed:
            shutil.rmtree(path, ignore_errors=True)
        return removed

    # ------------------------------------------------------------------ #
    # Löschen                                                             #
    # ------------------------------------------------------------------ #

    def referrers(self, page_id: str) -> list[tuple[str, str]]:
        """Wer verweist auf diese Seite? (Sprache, Seitenkennung)"""
        out: list[tuple[str, str]] = []
        needle = f"{{{{href:{page_id}}}}}"
        for lang in self.languages:
            for other in self.pages[lang].values():
                if other.page_id == page_id:
                    continue
                if other.parent == page_id or needle in jsonio.dump(other.data):
                    out.append((lang, other.page_id))
        return out

    def delete_page(self, page_id: str) -> list[FsPath]:
        page = next((self.pages[l].get(page_id) for l in self.languages if page_id in self.pages[l]), None)
        if page is None:
            raise RepositoryError(f"Die Seite „{page_id}“ gibt es nicht.")
        if not page.is_renamable:
            raise RepositoryError(
                f"Die Seite „{page.title}“ kann nicht gelöscht werden.\n\n"
                "Sie ist fest in Navigation, Fußzeile und Vorlagen eingetragen."
            )
        kids = [p.title for p in self.pages["de"].values() if p.parent == page_id]
        if kids:
            raise RepositoryError(
                f"„{page.title}“ hat noch Unterseiten:\n\n• " + "\n• ".join(kids) +
                "\n\nBitte diese zuerst verschieben oder löschen."
            )

        removed = self._stale_output_dirs(page_id)
        for lang in self.languages:
            gone = self.pages[lang].pop(page_id, None)
            self.sites[lang].remove_id(page_id)
            if gone is not None and gone.path.exists():
                gone.path.unlink()
        for path in removed:
            shutil.rmtree(path, ignore_errors=True)
        return removed

    def _stale_output_dirs(self, page_id: str) -> list[FsPath]:
        """Ausgabeverzeichnisse, die nach der Änderung niemand mehr erzeugt."""
        out: list[FsPath] = []
        for lang in self.languages:
            site = self.sites[lang]
            slug = site.slugs.get(page_id)
            if not slug:
                continue
            prefix = str(site.data.get("dir") or "")
            path = self.root / prefix / slug if prefix else self.root / slug
            if (path / "index.html").exists():
                out.append(path)
        return out

    # ------------------------------------------------------------------ #
    # Hierarchie                                                          #
    # ------------------------------------------------------------------ #

    def reparent(self, page_id: str, new_parent: str, after: str | None = None) -> list[FsPath]:
        """Hängt eine Seite unter eine andere und zieht die Adresse nach.

        Mit der Elternseite ändert sich die Adresse: aus
        ``/geschichte/emil-weber/`` wird ``/besuch/emil-weber/``. Das alte
        Verzeichnis muss weg – build.js räumt nicht auf, und die alte Seite
        bliebe sonst unter beiden Adressen erreichbar.
        """
        if page_id == new_parent:
            raise RepositoryError("Eine Seite kann nicht sich selbst untergeordnet werden.")
        if self._is_descendant(new_parent, page_id):
            raise RepositoryError(
                "Eine Seite kann nicht unter eine ihrer eigenen Unterseiten gehängt werden."
            )
        page = self.page("de", page_id) or next(
            (self.pages[l][page_id] for l in self.languages if page_id in self.pages[l]), None
        )
        if page is None or not page.is_renamable:
            raise RepositoryError("Diese Seite steht fest in der Navigation und bleibt, wo sie ist.")

        # Vor dem Ändern der Adressen ermitteln – danach zeigen sie woanders hin.
        descendants = [page_id, *self._descendants_of(page_id)]
        removed = [d for pid in descendants for d in self._stale_output_dirs(pid)]

        for lang in self.languages:
            target = self.pages[lang].get(page_id)
            if target is None:
                continue
            target.parent = new_parent
            target.dirty = True
            site = self.sites[lang]
            site.add_slug(page_id, self._slug_for(lang, page_id, new_parent))
            site.insert_into_sequence(page_id, after or new_parent)
            self._move_in_nav(site, page_id, new_parent, after)
            # Unterseiten erben die Adresse ihrer Elternseite.
            for child_id in self._descendants_of(page_id):
                child = self.pages[lang].get(child_id)
                if child is not None and child.parent:
                    site.add_slug(child_id, self._slug_for(lang, child_id, child.parent))

        for path in removed:
            shutil.rmtree(path, ignore_errors=True)
        return removed

    def _descendants_of(self, page_id: str) -> list[str]:
        """Alle Unterseiten, in der Tiefe zuerst nach Ebene geordnet."""
        pages = self.pages.get("de") or next(iter(self.pages.values()), {})
        out: list[str] = []
        level = [page_id]
        while level:
            level = [p.page_id for p in pages.values() if p.parent in level and p.page_id not in out]
            out += level
        return out

    @staticmethod
    def _move_in_nav(site: SiteConfig, page_id: str, new_parent: str, after: str | None) -> None:
        old_panel = site.nav_group_containing(page_id)
        if old_panel is not None:
            old_panel["items"] = [i for i in old_panel["items"] if i != page_id]
        target = site.nav_group_containing(new_parent) or (
            site.nav_group_containing(after) if after else None
        )
        if target is not None:
            items = target["items"]
            anchor = after if after in items else new_parent
            pos = items.index(anchor) + 1 if anchor in items else len(items)
            items.insert(pos, page_id)

    def _is_descendant(self, candidate: str, ancestor: str) -> bool:
        pages = self.pages.get("de") or next(iter(self.pages.values()), {})
        cur: str | None = candidate
        seen: set[str] = set()
        while cur and cur not in seen:
            if cur == ancestor:
                return True
            seen.add(cur)
            page = pages.get(cur)
            cur = page.parent if page else None
        return False

    def move_in_sequence(self, page_id: str, after: str | None) -> None:
        for lang in self.languages:
            self.sites[lang].insert_into_sequence(page_id, after)


# --------------------------------------------------------------------------- #
# Hilfen                                                                       #
# --------------------------------------------------------------------------- #


def _replace_links(node: Any, old_id: str, new_id: str) -> bool:
    """Ersetzt {{href:alt}} durch {{href:neu}}, beliebig tief. True bei Treffer."""
    needle, replacement = f"{{{{href:{old_id}}}}}", f"{{{{href:{new_id}}}}}"
    changed = False
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and needle in value:
                node[key] = value.replace(needle, replacement)
                changed = True
            elif isinstance(value, (dict, list)):
                changed |= _replace_links(value, old_id, new_id)
    elif isinstance(node, list):
        for n, value in enumerate(node):
            if isinstance(value, str) and needle in value:
                node[n] = value.replace(needle, replacement)
                changed = True
            elif isinstance(value, (dict, list)):
                changed |= _replace_links(value, old_id, new_id)
    return changed


def _error_report(errors: list[Problem]) -> str:
    head = (
        "Die Änderungen wurden nicht gespeichert, weil sie das Erzeugen der "
        "Website verhindern würden:\n\n"
    )
    lines = [f"• {p.where()}: {p.message}" for p in errors[:12]]
    if len(errors) > 12:
        lines.append(f"• … und {len(errors) - 12} weitere")
    return head + "\n".join(lines)
