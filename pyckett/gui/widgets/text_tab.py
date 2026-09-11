# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Read-only viewer for raw SPFIT/SPCAT text output

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class TextTabWidget(QWidget):
    """Read-only monospace viewer for a text Document (SPFIT/SPCAT stdout, etc)."""

    def __init__(self, document, parent=None):
        super().__init__(parent)
        self.document = document

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.editor.setPlainText(document.data)
        layout.addWidget(self.editor)
