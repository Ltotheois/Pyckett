# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Centered message shown where a result isn't available yet

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderWidget(QWidget):
    """A centered message, e.g. "Run SPFIT to see the fitted parameters."."""

    def __init__(self, message, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch(1)
