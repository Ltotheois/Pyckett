# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : A pandas-query filter field, used above the *.lin/*.cat/*.egy tables

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


class QueryBarWidget(QWidget):
    """A single-line pandas .query() filter field.

    Clears immediately when emptied; a non-empty query is only applied on
    Enter, so a half-typed expression doesn't flash an error on every
    keystroke. ``set_error`` marks the field (border + tooltip) when the
    caller's proxy model rejected the query.
    """

    query_changed = pyqtSignal(str)

    def __init__(self, placeholder="pandas query, e.g. weight > 0 and qnu1 < 20", parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Filter:"))

        self.field = QLineEdit()
        self.field.setPlaceholderText(f"{placeholder}  (press Enter to apply)")
        self.field.returnPressed.connect(self._apply)
        self.field.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.field, 1)

    def _on_text_changed(self, text):
        if not text.strip():
            self._apply()

    def _apply(self):
        self.query_changed.emit(self.field.text().strip())

    def set_error(self, message):
        if message:
            self.field.setStyleSheet("border: 1px solid #c0392b;")
            self.field.setToolTip(message)
        else:
            self.field.setStyleSheet("")
            self.field.setToolTip("")
