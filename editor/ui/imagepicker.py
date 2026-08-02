"""Bildauswahl mit Vorschau.

Angeboten wird ausschließlich, was in src/image-manifest.json steht. Ein Bild,
das dort fehlt, lässt build.js abbrechen („Bild nicht im Manifest“) – der
Editor kann also gar nicht erst etwas auswählen, das später Ärger macht.

Die echten Maße stehen bei jedem Bild. Das ist bei diesem Bestand wichtig:
114 der 117 Aufnahmen sind zwischen 125 und 581 Pixel breit. Ein 200 Pixel
breites Foto lässt sich nicht groß darstellen, ohne dass es zerfällt – die
Website vergrößert deshalb grundsätzlich nicht.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..model import ImageInfo, ImageManifest
from .theme import Color

__all__ = ["ImagePickerDialog", "thumbnail"]

THUMB = QSize(150, 112)


def thumbnail(manifest: ImageManifest, src: str, size: QSize = THUMB) -> QPixmap:
    """Vorschaubild auf Cremegrund, damit helle Motive nicht verschwimmen."""
    canvas = QPixmap(size)
    canvas.fill(QColor(Color.CREAM))
    path = manifest.file_for(src)
    if path.exists():
        source = QPixmap(str(path))
        if not source.isNull():
            scaled = source.scaled(
                size - QSize(8, 8),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter = QPainter(canvas)
            painter.drawPixmap(
                (size.width() - scaled.width()) // 2,
                (size.height() - scaled.height()) // 2,
                scaled,
            )
            painter.end()
    return canvas


class ImagePickerDialog(QDialog):
    def __init__(
        self,
        manifest: ImageManifest,
        current: str = "",
        used: set[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bild auswählen")
        self.resize(940, 680)
        self._manifest = manifest
        self._used = used or set()
        self._chosen = current

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Bild suchen – Dateiname oder Ordner …")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._apply_filter)

        self.unused_only = QCheckBox("Nur noch nicht verwendete Bilder")
        self.unused_only.toggled.connect(self._apply_filter)

        self.grid = QListWidget()
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setIconSize(THUMB)
        self.grid.setGridSize(QSize(THUMB.width() + 26, THUMB.height() + 58))
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setMovement(QListView.Movement.Static)
        self.grid.setSpacing(6)
        self.grid.setWordWrap(True)
        self.grid.setUniformItemSizes(True)
        self.grid.currentItemChanged.connect(self._show_details)
        self.grid.itemDoubleClicked.connect(lambda _: self.accept())

        self.details = QLabel("Kein Bild ausgewählt.")
        self.details.setProperty("rolle", "hinweis")
        self.details.setWordWrap(True)
        self.details.setMinimumHeight(46)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Übernehmen")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        top = QHBoxLayout()
        top.addWidget(self.filter_edit, 1)
        top.addWidget(self.unused_only)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addLayout(top)
        layout.addWidget(self.grid, 1)
        layout.addWidget(self.details)
        layout.addWidget(self.buttons)

        self._fill(current)

    # -- Aufbau ------------------------------------------------------------ #

    def _fill(self, current: str) -> None:
        by_folder = self._manifest.by_folder()
        for folder, images in by_folder.items():
            label = ImageManifest.folder_label(folder)
            for info in images:
                item = QListWidgetItem(QIcon(thumbnail(self._manifest, info.src)), info.filename)
                item.setData(Qt.ItemDataRole.UserRole, info.src)
                item.setData(Qt.ItemDataRole.UserRole + 1, f"{info.src} {label}".casefold())
                item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
                mark = "" if info.src in self._used else "  ·  noch nicht verwendet"
                item.setToolTip(
                    f"{label}\n{info.src}\n{info.dimensions}  ·  {info.size_label}{mark}"
                )
                if info.src not in self._used:
                    item.setForeground(QColor(Color.GOLD_TEXT))
                self.grid.addItem(item)
                if info.src == current:
                    self.grid.setCurrentItem(item)
        if self.grid.currentItem() is not None:
            self.grid.scrollToItem(self.grid.currentItem())

    # -- Bedienung --------------------------------------------------------- #

    def _apply_filter(self) -> None:
        needle = self.filter_edit.text().strip().casefold()
        only_unused = self.unused_only.isChecked()
        for row in range(self.grid.count()):
            item = self.grid.item(row)
            src = item.data(Qt.ItemDataRole.UserRole)
            haystack = item.data(Qt.ItemDataRole.UserRole + 1)
            hidden = (needle and needle not in haystack) or (only_unused and src in self._used)
            item.setHidden(bool(hidden))

    def _show_details(self, item: QListWidgetItem | None) -> None:
        if item is None:
            self.details.setText("Kein Bild ausgewählt.")
            return
        info: ImageInfo | None = self._manifest.get(item.data(Qt.ItemDataRole.UserRole))
        if info is None:
            return
        folder = ImageManifest.folder_label(info.folder)
        note = ""
        if info.width < 400:
            note = "  ·  Kleines Bild – es wird in der Textspalte in Originalgröße gezeigt."
        self.details.setText(
            f"<b>{folder}</b> · {info.src}<br>{info.dimensions} · {info.size_label}"
            f"{' · WebP vorhanden' if info.has_webp else ''}{note}"
        )

    def accept(self) -> None:
        item = self.grid.currentItem()
        self._chosen = item.data(Qt.ItemDataRole.UserRole) if item else self._chosen
        super().accept()

    @property
    def selected(self) -> str:
        return self._chosen
