# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Placeholder shown for a *.par/*.lin/*.int slot with no file loaded yet

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class EmptyFileTabWidget(QWidget):
    """Message + a button to load a file, shown while a project has no *.<kind> file yet."""

    load_requested = pyqtSignal()

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind

        layout = QVBoxLayout(self)
        layout.addStretch(1)

        message = QLabel(f"No *.{kind} file is currently loaded.")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        load_button = QPushButton(f"Load *.{kind} File…")
        load_button.clicked.connect(self.load_requested)
        button_row.addWidget(load_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        layout.addStretch(1)
