# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Shared behavior for the editable *.par/*.lin/*.int tab widgets

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget


class EditableTabWidget(QWidget):
    """Base class for a tab that edits one Document belonging to a Project.

    Subclasses call ``self._mark_dirty()`` whenever the user changes
    something, and provide a save file-dialog filter via ``file_dialog_filter``.
    ``changed`` fires after any edit or save so the containing ProjectWidget
    can refresh the tab's title (dirty marker).
    """

    changed = pyqtSignal()
    file_dialog_filter = "All Files (*)"

    def __init__(self, project, document, read_only=False, parent=None):
        super().__init__(parent)
        self.project = project
        self.document = document
        self.read_only = read_only

    def _mark_dirty(self):
        self.document.dirty = True
        self.changed.emit()

    def save(self, save_as=False):
        path = None if (save_as or self.document.path is None) else self.document.path
        if path is None:
            chosen, _ = QFileDialog.getSaveFileName(
                self, f"Save {self.document.label}", "", self.file_dialog_filter
            )
            if not chosen:
                return False
            path = chosen

        try:
            self.project.save_document(self.document, path)
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            return False

        self.changed.emit()
        return True
