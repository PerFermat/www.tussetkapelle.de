"""Oberfläche des Editors.

Kein Modul hier öffnet selbst eine Datei – geschrieben wird ausschließlich über
``editor.model.ContentRepository``.
"""

from .mainwindow import MainWindow

__all__ = ["MainWindow"]
