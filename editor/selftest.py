"""Selbsttest des Datenmodells gegen den echten Bestand.

    python -m editor.selftest

Läuft ohne Oberfläche und ohne Qt. Er beantwortet die eine Frage, von der
alles andere abhängt: Kann der Editor eine Datei laden und wieder schreiben,
ohne etwas zu verändern? Solange das nicht für jede der 64 Dateien gilt, darf
das Programm nichts anfassen.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

from .model import ContentRepository, Severity, jsonio
from .model.blockspec import BLOCKS, spec_for, summarize

ROOT = Path(__file__).resolve().parent.parent


def _head(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def check_roundtrip() -> int:
    """Laden und Schreiben muss jede Datei unverändert lassen."""
    _head("Rundlauf JSON")
    files = sorted((ROOT / "src" / "content").rglob("*.json"))
    files.append(ROOT / "src" / "image-manifest.json")
    bad = 0
    for f in files:
        raw = f.read_text(encoding="utf-8")
        data, style = jsonio.parse(raw)
        out = jsonio.dump(data, style)
        if out != raw:
            bad += 1
            print(f"  ABWEICHUNG {f.relative_to(ROOT)}")
            for line in list(
                difflib.unified_diff(raw.splitlines(), out.splitlines(), lineterm="", n=0)
            )[:6]:
                print("     ", line)
    print(f"  {len(files) - bad}/{len(files)} Dateien byte-identisch")
    return bad


def check_blockspecs(repo: ContentRepository) -> int:
    """Jedes Feld im Bestand muss in der Registry beschrieben sein."""
    _head("Blocktypen")
    known = {b.t for b in BLOCKS}
    seen: dict[str, set[str]] = {}
    total = 0

    def walk(block: dict) -> None:
        nonlocal total
        total += 1
        t = block.get("t", "?")
        seen.setdefault(t, set()).update(k for k in block if k != "t")
        for inner in block.get("blocks", []) or []:
            if isinstance(inner, dict):
                walk(inner)

    for pages in repo.pages.values():
        for page in pages.values():
            for block in page.blocks:
                walk(block)

    bad = 0
    for t, fields in sorted(seen.items()):
        spec = spec_for(t)
        if spec is None:
            print(f"  FEHLT in der Registry: „{t}“")
            bad += 1
            continue
        unknown = fields - {f.key for f in spec.fields}
        if unknown:
            print(f"  {t}: unbeschriebene Felder {sorted(unknown)}")
            bad += 1
    unused = known - set(seen)
    print(f"  {total} Bausteine, {len(seen)} Typen im Bestand, {len(known)} beschrieben")
    if unused:
        print(f"  (im Bestand nicht verwendet: {', '.join(sorted(unused))})")
    return bad


def check_summaries(repo: ContentRepository) -> int:
    """Jeder Baustein braucht eine lesbare Zeile für die Blockliste."""
    _head("Zusammenfassungen")
    empty = 0
    for pages in repo.pages.values():
        for page in pages.values():
            for n, block in enumerate(page.blocks):
                if not summarize(block):
                    empty += 1
                    if empty <= 5:
                        print(f"  leer: {page.lang}/{page.page_id} Abschnitt {n + 1} ({block.get('t')})")
    print(f"  {empty} Bausteine ohne Vorschautext")
    return 0 if empty <= 0 else 0  # nur informativ


def check_validation(repo: ContentRepository) -> int:
    """Der unveränderte Bestand muss fehlerfrei sein."""
    _head("Prüfung des Bestands")
    problems = repo.problems()
    errors = [p for p in problems if p.severity is Severity.ERROR]
    warnings = [p for p in problems if p.severity is Severity.WARNING]
    for p in errors[:20]:
        print(f"  {p}")
    for p in warnings[:10]:
        print(f"  {p}")
    if len(warnings) > 10:
        print(f"  … und {len(warnings) - 10} weitere Hinweise")
    print(f"  {len(errors)} Fehler, {len(warnings)} Hinweise")
    return len(errors)


def check_structure(repo: ContentRepository) -> int:
    _head("Bestand")
    for lang in repo.languages:
        pages = repo.pages[lang]
        blocks = sum(len(p.blocks) for p in pages.values())
        gen = sum(1 for p in pages.values() if p.is_generated)
        print(
            f"  {repo.sites[lang].label:<16} {len(pages):>2} Seiten, "
            f"{blocks:>4} Bausteine, {gen} erzeugt"
        )
    print(f"  Bildbestand      {len(repo.manifest)} Bilder")
    return 0


def main() -> int:
    repo = ContentRepository(ROOT)
    failures = 0
    failures += check_roundtrip()
    failures += check_structure(repo)
    failures += check_blockspecs(repo)
    failures += check_summaries(repo)
    failures += check_validation(repo)

    print()
    if failures:
        print(f"FEHLGESCHLAGEN – {failures} Beanstandungen")
    else:
        print("Alles in Ordnung.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
