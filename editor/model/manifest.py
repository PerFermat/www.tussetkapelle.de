"""Bildbestand: Maße, Dateigröße und vorhandene Größenstufen.

Quelle ist src/image-manifest.json, erzeugt von tools/make-manifest.mjs aus dem
Bestand in bilder/. Ein Bild, das dort nicht steht, lässt build.js abbrechen
(„Bild nicht im Manifest“) – der Editor bietet deshalb nur an, was hier
verzeichnet ist.

Die Maße sind auch inhaltlich wichtig: 114 der 117 Bilder sind zwischen 125 und
581 Pixel breit. Die Oberfläche zeigt die echte Breite an, damit niemand ein
kleines Bild dort einplant, wo es groß erscheinen soll – vergrößert wird nie.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path as FsPath

from .jsonio import load_file

__all__ = ["ImageInfo", "ImageManifest"]


@dataclass(frozen=True)
class ImageInfo:
    src: str
    width: int
    height: int
    size_bytes: int
    has_webp: bool

    @property
    def folder(self) -> str:
        return self.src.rsplit("/", 1)[0] if "/" in self.src else ""

    @property
    def filename(self) -> str:
        return self.src.rsplit("/", 1)[-1]

    @property
    def dimensions(self) -> str:
        return f"{self.width} × {self.height} Pixel"

    @property
    def size_label(self) -> str:
        kb = self.size_bytes / 1024
        return f"{kb:.0f} kB" if kb < 1024 else f"{kb / 1024:.1f} MB"


#: Klartext für die Ordner des Bestands.
FOLDER_LABELS = {
    "": "Ohne Ordner",
    "altetk": "Alte Tussetkapelle",
    "altetk/gnadenbilder": "Alte Kapelle – Gnadenbilder",
    "altetk/geschichten": "Alte Kapelle – Geschichten",
    "altetk/kapelleundwallern": "Alte Kapelle – Kapelle und Wallern",
    "altetk/kreuzwege": "Alte Kapelle – Kreuzwege",
    "altetk/restaurierung": "Alte Kapelle – Restaurierung",
    "fotogalerie": "Bildergalerie",
    "fotogalerie/fotosatk": "Galerie – alte Kapelle 1983",
    "fotogalerie/fotosntk": "Galerie – neue Kapelle",
    "initiatoren": "Initiatoren",
    "kontakt": "Kontakt",
    "neuetk": "Neue Tussetkapelle",
    "neuetk/anfahrt": "Neue Kapelle – Anfahrt",
    "neuetk/einleitung": "Neue Kapelle – Einleitung",
    "neuetk/einweihung": "Neue Kapelle – Einweihung 1985",
    "neuetk/entstehung": "Neue Kapelle – Wiederaufbau",
    "neuetk/kreuzwegbilder": "Neue Kapelle – Kreuzwegbilder",
    "neuetk/kreuzwegweihe": "Neue Kapelle – Kreuzwegweihe 1987",
}


class ImageManifest:
    """Nur lesend. Neue Bilder kommen über tools/build-images.sh dazu."""

    def __init__(self, path: FsPath, images_dir: FsPath) -> None:
        self.path = path
        self.images_dir = images_dir
        data, _, _ = load_file(path)
        self._images = {
            src: ImageInfo(
                src=src,
                width=int(m.get("w", 0)),
                height=int(m.get("h", 0)),
                size_bytes=int(m.get("bytes", 0)),
                has_webp=bool(m.get("webp")),
            )
            for src, m in data.items()
        }

    def __contains__(self, src: object) -> bool:
        return src in self._images

    def __len__(self) -> int:
        return len(self._images)

    def get(self, src: str) -> ImageInfo | None:
        return self._images.get(src)

    def all(self) -> list[ImageInfo]:
        return sorted(self._images.values(), key=lambda i: i.src)

    def file_for(self, src: str) -> FsPath:
        """Pfad zur Bilddatei auf der Platte, für die Vorschau."""
        return self.images_dir / src

    def by_folder(self) -> dict[str, list[ImageInfo]]:
        out: dict[str, list[ImageInfo]] = {}
        for info in self.all():
            out.setdefault(info.folder, []).append(info)
        return dict(sorted(out.items()))

    @staticmethod
    def folder_label(folder: str) -> str:
        return FOLDER_LABELS.get(folder, folder or "Ohne Ordner")
