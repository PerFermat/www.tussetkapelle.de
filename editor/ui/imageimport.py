"""Ein Bild aufnehmen oder ersetzen.

Der Dialog fragt drei Dinge ab – welche Datei, in welchen Ordner, unter welchem
Namen – und zeigt den Zielpfad, der sich daraus ergibt. Alles Weitere macht
``tools/build-images.sh``: die Umsetzung nach JPEG, die Größenstufen, die
WebP-Varianten und das Bildverzeichnis.

Beim Ersetzen steht der Zielpfad fest. Ein Bild umzubenennen wäre etwas anderes:
der Name steht in den Inhaltsdateien und müsste dort überall nachgezogen werden.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QImageReader, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..imagejobs import IMAGE_FILTER, human_size, normalize_name, split_target
from ..model import ImageManifest
from .theme import Color

__all__ = ["ImageImportDialog"]

PREVIEW = QSize(260, 200)

#: Ordner, aus denen sich die Bildergalerie bedient – die Zuordnung steht in
#: tools/make-gallery.mjs. Ein neues Bild dort erscheint erst nach einem
#: Galerielauf, und dann ohne Bildunterschrift: die sind redaktionell in drei
#: Sprachen verfasst und lassen sich nicht ableiten.
GALLERY_FOLDERS = (
    "altetk/gnadenbilder",
    "altetk/kapelleundwallern",
    "altetk/kreuzwege",
    "altetk/renovierung",
    "fotogalerie/fotosatk",
    "initiatoren",
    "kontakt",
    "neuetk/einleitung",
    "neuetk/einweihung",
    "neuetk/entstehung",
    "neuetk/kreuzwegbilder",
    "neuetk/kreuzwegweihe",
)


def feeds_gallery(target: str) -> bool:
    """Landet ein Bild an dieser Stelle in der Bildergalerie?"""
    folder = target.rsplit("/", 1)[0] if "/" in target else ""
    # Bilder ohne Ordner zeigt die Galerie im Abschnitt „Die neue Kapelle“.
    return not folder or folder.startswith(GALLERY_FOLDERS)


class ImageImportDialog(QDialog):
    def __init__(
        self,
        manifest: ImageManifest,
        *,
        replace: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._manifest = manifest
        self._replace = replace
        self._source: Path | None = None
        self._width = 0

        self.setWindowTitle("Bild ersetzen" if replace else "Bild aufnehmen")
        self.resize(660, 520)

        # -- Datei ---------------------------------------------------------- #
        self.file_label = QLabel("Noch keine Datei gewählt.")
        self.file_label.setWordWrap(True)
        choose = QPushButton("Datei wählen …")
        choose.clicked.connect(self._choose_file)

        self.preview = QLabel()
        self.preview.setFixedSize(PREVIEW)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet(
            f"background: {Color.CREAM}; border: 1px solid {Color.LINE}; border-radius: 6px;"
        )
        self.preview.setText("Vorschau")

        self.source_info = QLabel()
        self.source_info.setProperty("rolle", "hinweis")
        self.source_info.setWordWrap(True)

        # -- Ziel ----------------------------------------------------------- #
        # Bekannte Ordner in Klartext; wer einen neuen anlegen will, trägt den
        # Pfad ein (deshalb editierbar). Was dabei herauskommt, steht darunter
        # in der Zeile „Wird abgelegt als“.
        self.folder = QComboBox()
        self.folder.setEditable(True)
        self.folder.lineEdit().setPlaceholderText("Ordner, z. B. neuetk/anfahrt")
        for value in sorted(self._manifest.by_folder()):
            self.folder.addItem(ImageManifest.folder_label(value), value)
            self.folder.setItemData(
                self.folder.count() - 1, value or "bilder/", Qt.ItemDataRole.ToolTipRole
            )
        self.folder.currentTextChanged.connect(self._refresh)

        self.name = QLineEdit()
        self.name.setPlaceholderText("dateiname.jpg")
        self.name.textEdited.connect(self._refresh)

        self.target_label = QLabel()
        self.target_label.setProperty("rolle", "feld")
        self.target_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setProperty("rolle", "warnung")
        self.warning.hide()

        # -- Aufbau --------------------------------------------------------- #
        head = QHBoxLayout()
        head.setSpacing(14)
        head.addWidget(self.preview)
        right = QVBoxLayout()
        right.addWidget(choose)
        right.addWidget(self.file_label)
        right.addWidget(self.source_info)
        right.addStretch(1)
        head.addLayout(right, 1)

        form = QFormLayout()
        form.setSpacing(8)
        form.addRow("Ordner", self.folder)
        form.addRow("Dateiname", self.name)
        form.addRow("Wird abgelegt als", self.target_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Ersetzen" if replace else "Aufnehmen"
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(head)
        layout.addLayout(form)
        layout.addWidget(self.warning)
        layout.addStretch(1)
        layout.addWidget(self.buttons)

        if replace:
            folder, filename = split_target(replace)
            index = self.folder.findData(folder)
            if index >= 0:
                self.folder.setCurrentIndex(index)
            else:
                self.folder.setCurrentText(folder)
            self.name.setText(filename)
            # Beim Ersetzen ist der Zielpfad festgelegt: derselbe Name, dasselbe
            # Bild an allen Stellen, an denen es eingebunden ist.
            self.folder.setEnabled(False)
            self.name.setEnabled(False)

        self._refresh()

    # -- Auswahl ------------------------------------------------------------ #

    def _choose_file(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Bild wählen", str(Path.home()), IMAGE_FILTER
        )
        if not chosen:
            return
        self._source = Path(chosen)
        self.file_label.setText(str(self._source))
        self._show_preview()
        if not self._replace:
            self.name.setText(normalize_name(self._source.name))
        self._refresh()

    def _show_preview(self) -> None:
        if self._source is None:
            return
        reader = QImageReader(str(self._source))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            self.preview.setText("Diese Datei lässt sich nicht lesen.")
            self.source_info.setText("")
            self._source = None
            return

        canvas = QPixmap(PREVIEW)
        canvas.fill(QColor(Color.CREAM))
        scaled = QPixmap.fromImage(image).scaled(
            PREVIEW - QSize(12, 12),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter = QPainter(canvas)
        painter.drawPixmap(
            (PREVIEW.width() - scaled.width()) // 2,
            (PREVIEW.height() - scaled.height()) // 2,
            scaled,
        )
        painter.end()
        self.preview.setPixmap(canvas)

        self.source_info.setText(
            f"{image.width()} × {image.height()} Pixel  ·  "
            f"{human_size(self._source.stat().st_size)}  ·  "
            f"{self._source.suffix.lstrip('.').upper()}"
        )
        self._width = image.width()

    # -- Zielpfad und Warnungen --------------------------------------------- #

    def _current_folder(self) -> str:
        """Der Ordnerpfad – aus der Beschriftung oder frei eingetragen."""
        text = self.folder.currentText().strip()
        index = self.folder.findText(text)
        if index >= 0:
            return str(self.folder.itemData(index) or "").strip("/")
        return text.strip("/")

    @property
    def target(self) -> str:
        # Beim Ersetzen bleibt der Pfad, wie er ist. Er steht in den
        # Inhaltsdateien; ihn zu normalisieren würde aus `tusset_alt.jpg` ein
        # `tusset-alt.jpg` machen und alle Verweise darauf ins Leere schicken.
        if self._replace:
            return self._replace
        folder = self._current_folder()
        name = normalize_name(self.name.text()) if self.name.text().strip() else ""
        return f"{folder}/{name}" if folder and name else name

    @property
    def source(self) -> Path | None:
        return self._source

    def _refresh(self) -> None:
        target = self.target
        self.target_label.setText(f"bilder/{target}" if target else "—")

        problems: list[str] = []
        if self._source is None:
            problems.append("Es ist noch keine Datei gewählt.")
        if not target or target.endswith("/"):
            problems.append("Der Dateiname fehlt.")
        elif not self._replace and target in self._manifest:
            problems.append(
                f"Unter „{target}“ gibt es schon ein Bild. Wählen Sie einen "
                "anderen Namen – oder ersetzen Sie das vorhandene Bild."
            )

        hints: list[str] = []
        if self._source is not None and self._width:
            if self._width < 400:
                hints.append(
                    f"Das Bild ist nur {self._width} Pixel breit. Es wird in der "
                    "Textspalte in Originalgröße gezeigt – vergrößert wird nie."
                )
            if self._replace:
                old = self._manifest.get(self._replace)
                if old is not None:
                    hints.append(
                        f"Bisher: {old.dimensions}, {old.size_label}. "
                        f"Neu: {self._width} Pixel breit."
                    )
        if target and not self._replace and feeds_gallery(target):
            hints.append(
                "Dieser Ordner speist auch die Bildergalerie. Dort erscheint das "
                "Bild erst nach einem Galerielauf und braucht dann noch eine "
                "Bildunterschrift in drei Sprachen."
            )

        text = "\n".join(problems + hints)
        self.warning.setText(text)
        self.warning.setVisible(bool(text))
        # Rot nur, wenn etwas im Weg steht. Ein Hinweis darauf, dass die Galerie
        # später noch eine Bildunterschrift braucht, ist kein Fehler.
        self.warning.setProperty("rolle", "warnung" if problems else "hinweis")
        self.warning.style().unpolish(self.warning)
        self.warning.style().polish(self.warning)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(not problems)
