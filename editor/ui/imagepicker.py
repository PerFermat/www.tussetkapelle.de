"""Bildauswahl mit Vorschau – und die Pflege des Bildbestands.

Angeboten wird ausschließlich, was in src/image-manifest.json steht. Ein Bild,
das dort fehlt, lässt build.js abbrechen („Bild nicht im Manifest“) – der
Editor kann also gar nicht erst etwas auswählen, das später Ärger macht.

Die echten Maße stehen bei jedem Bild. Das ist bei diesem Bestand wichtig:
114 der 117 Aufnahmen sind zwischen 125 und 581 Pixel breit. Ein 200 Pixel
breites Foto lässt sich nicht groß darstellen, ohne dass es zerfällt – die
Website vergrößert deshalb grundsätzlich nicht.

Hier stehen auch die drei Eingriffe in den Bildbestand: aufnehmen, ersetzen,
löschen. Gelöscht werden darf nur, was auf keiner Seite verwendet wird; die
dafür nötige Auskunft bringt der Aufrufer als ``used`` mit.
"""

from __future__ import annotations

from pathlib import Path

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
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..imagejobs import ImageJob, derived_files, human_size
from ..model import ImageInfo, ImageManifest
from .imageimport import ImageImportDialog
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
        root: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bild auswählen")
        self.resize(940, 680)
        self._manifest = manifest
        # Das Bild im gerade bearbeiteten Feld zählt als verwendet, auch wenn
        # der Wechsel noch nicht übernommen ist – sonst ließe es sich in genau
        # diesem Moment löschen.
        self._used = (used or set()) | ({current} if current else set())
        self._chosen = current
        self._root = root or manifest.path.parent.parent
        self._job = ImageJob(self._root, self)
        # Wurde am Bildbestand etwas geändert, muss die Website neu erzeugt
        # werden: die fertigen Seiten nennen Dateinamen, Maße und Größenstufen.
        # Der Aufrufer fragt das nach dem Schließen ab.
        self.images_changed = False

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

        self.import_button = QPushButton("Bild aufnehmen …")
        self.import_button.clicked.connect(self.import_image)
        self.replace_button = QPushButton("Bild ersetzen …")
        self.replace_button.clicked.connect(self.replace_image)
        self.delete_button = QPushButton("Bild löschen")
        self.delete_button.clicked.connect(self.delete_image)

        top = QHBoxLayout()
        top.addWidget(self.filter_edit, 1)
        top.addWidget(self.unused_only)

        bottom = QHBoxLayout()
        bottom.addWidget(self.import_button)
        bottom.addWidget(self.replace_button)
        bottom.addWidget(self.delete_button)
        bottom.addStretch(1)
        bottom.addWidget(self.buttons)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addLayout(top)
        layout.addWidget(self.grid, 1)
        layout.addWidget(self.details)
        layout.addLayout(bottom)

        self._fill(current)

    # -- Aufbau ------------------------------------------------------------ #

    def _fill(self, current: str) -> None:
        """Baut das Raster auf. Nach jedem Eingriff in den Bestand erneut."""
        self.grid.blockSignals(True)
        self.grid.clear()
        self.grid.blockSignals(False)

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
        self._apply_filter()
        self._show_details(self.grid.currentItem())

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

    def _show_details(self, item: QListWidgetItem | None = None) -> None:
        item = item if item is not None else self.grid.currentItem()
        if item is None:
            self.details.setText("Kein Bild ausgewählt.")
            self.replace_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.delete_button.setToolTip("")
            return

        src = item.data(Qt.ItemDataRole.UserRole)
        info: ImageInfo | None = self._manifest.get(src)
        if info is None:
            return

        folder = ImageManifest.folder_label(info.folder)
        note = ""
        if info.width < 400:
            note = "  ·  Kleines Bild – es wird in der Textspalte in Originalgröße gezeigt."

        in_use = src in self._used
        self.replace_button.setEnabled(True)
        self.delete_button.setEnabled(not in_use)
        self.delete_button.setToolTip(
            "Dieses Bild wird verwendet und kann nicht gelöscht werden."
            if in_use
            else f"„{src}“ mit allen Größenstufen entfernen"
        )

        usage = (
            "Wird auf mindestens einer Seite verwendet – deshalb nicht löschbar."
            if in_use
            else "Wird auf keiner Seite verwendet."
        )
        self.details.setText(
            f"<b>{folder}</b> · {info.src}<br>{info.dimensions} · {info.size_label}"
            f"{' · WebP vorhanden' if info.has_webp else ''}{note}<br>{usage}"
        )

    # -- Bestand pflegen ---------------------------------------------------- #

    @property
    def _selected_src(self) -> str:
        item = self.grid.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else ""

    def import_image(self) -> None:
        dialog = ImageImportDialog(self._manifest, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.source is None:
            return
        if self._job.add(dialog.source, dialog.target):
            self._manifest.reload()
            self.images_changed = True
            self._fill(dialog.target)

    def replace_image(self) -> None:
        src = self._selected_src
        if not src:
            return
        dialog = ImageImportDialog(self._manifest, replace=src, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.source is None:
            return
        if self._job.replace(dialog.source, src):
            self._manifest.reload()
            self.images_changed = True
            self._fill(src)

    def delete_image(self) -> None:
        """Löscht ein Bild – nur, wenn es auf keiner Seite verwendet wird."""
        src = self._selected_src
        if not src or src in self._used:
            return

        files = derived_files(self._manifest.images_dir, src)
        names = " · ".join(path.name for path in files)
        total = sum(path.stat().st_size for path in files if path.exists())

        answer = QMessageBox.question(
            self,
            "Bild löschen?",
            f"„{src}“ löschen?\n\n"
            f"Entfernt werden {len(files)} Dateien ({human_size(total)}):\n"
            f"{names}\n\n"
            "Das Bild wird auf keiner Seite verwendet. Rückgängig machen lässt "
            "sich das nicht – wiederherstellbar ist es nur über die "
            "Versionsverwaltung.\n\n"
            "Danach muss die Website neu erzeugt werden.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        # Mit „==“, nicht mit „is“: question() liefert in PySide6 eine einfache
        # Zahl, keinen Enum-Wert. Derselbe Vergleich hat schon einmal dafür
        # gesorgt, dass ein Löschen wirkungslos blieb.
        if answer != QMessageBox.StandardButton.Yes:
            return

        row = self.grid.currentRow()
        if self._job.remove(src):
            self._manifest.reload()
            self.images_changed = True
            if self._chosen == src:
                self._chosen = ""
            self._fill("")
            if self.grid.count():
                self.grid.setCurrentRow(min(row, self.grid.count() - 1))

    # -- Ergebnis ----------------------------------------------------------- #

    def accept(self) -> None:
        item = self.grid.currentItem()
        self._chosen = item.data(Qt.ItemDataRole.UserRole) if item else self._chosen
        super().accept()

    @property
    def selected(self) -> str:
        return self._chosen
