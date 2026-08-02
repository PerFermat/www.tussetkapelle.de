"""Datenmodell des Editors – ohne jede Abhängigkeit von Qt.

Alles hier ist ohne laufende Oberfläche testbar. Die Oberfläche unter
``editor.ui`` greift ausschließlich über ``ContentRepository`` zu und öffnet
selbst keine Datei.
"""

from .blockspec import BLOCKS, PAGE_FIELDS, BlockSpec, FieldKind, FieldSpec, spec_for, summarize
from .jsonio import JsonSyntaxError, Style, dump, load_file, parse, save_file
from .manifest import ImageInfo, ImageManifest
from .page import Page, PageKind
from .repository import ContentRepository, NewPage, RepositoryError
from .site import SiteConfig
from .validation import Problem, Severity, validate

__all__ = [
    "BLOCKS",
    "PAGE_FIELDS",
    "BlockSpec",
    "ContentRepository",
    "FieldKind",
    "FieldSpec",
    "ImageInfo",
    "ImageManifest",
    "JsonSyntaxError",
    "NewPage",
    "Page",
    "PageKind",
    "Problem",
    "RepositoryError",
    "Severity",
    "SiteConfig",
    "Style",
    "dump",
    "load_file",
    "parse",
    "save_file",
    "spec_for",
    "summarize",
    "validate",
]
