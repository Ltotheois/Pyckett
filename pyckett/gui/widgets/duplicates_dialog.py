# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Dialog collecting options for removing duplicate *.lin assignments

from PyQt6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout


class DuplicatesDialog(QDialog):
    """Asks which duplicate to keep, and whether to re-sort afterwards."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Remove Duplicate Assignments")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.keep_combo = QComboBox()
        self.keep_combo.addItems(["last", "first"])
        form.addRow("Keep", self.keep_combo)

        self.sort_checkbox = QCheckBox("Sort by frequency after removing")
        form.addRow(self.sort_checkbox)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def options(self):
        """Return (keep, sort) - keep is 'last' or 'first', sort is a bool."""
        return self.keep_combo.currentText(), self.sort_checkbox.isChecked()
