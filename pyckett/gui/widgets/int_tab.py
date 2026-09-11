# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Tab widget for editing *.int intensity/simulation-parameter files

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
)

from pyckett.gui.qt_models.editable_list_model import ListTableModel
from pyckett.gui.widgets.tab_base import EditableTabWidget

HEADER_KEYS = ["TITLE", "FLAGS", "TAG", "QROT", "FBGN", "FEND", "STR0", "STR1", "FQLIM", "TEMP", "MAXV"]
INT_HEADERS = ["IDIP", "Dipole"]
NEW_INT_ROW = [1, 1.0]


def _parse_like(original, text):
    text = text.strip()
    if isinstance(original, str):
        return text
    value = float(text)
    if isinstance(original, int) and value % 1 == 0:
        return int(value)
    return value


class IntTabWidget(EditableTabWidget):
    """Editable view of a *.int Document."""

    file_dialog_filter = "Intensity Files (*.int);;All Files (*)"

    def __init__(self, project, document, parent=None):
        super().__init__(project, document, parent=parent)
        int_dict = document.data

        layout = QVBoxLayout(self)

        header_group = QGroupBox("Settings")
        form = QFormLayout(header_group)
        for key in HEADER_KEYS:
            if key not in int_dict:
                continue
            field = QLineEdit(str(int_dict[key]))
            field.editingFinished.connect(lambda k=key, f=field: self._update_header(k, f))
            form.addRow(key, field)

        ints_group = QGroupBox("Dipole Moments")
        ints_layout = QVBoxLayout(ints_group)

        self.model = ListTableModel(
            int_dict["INTS"],
            INT_HEADERS,
            formatters=[str, lambda v: f"{v:.4f}"],
            parsers=[int, float],
        )
        self.model.dataChanged.connect(self._mark_dirty)
        self.model.modelReset.connect(self._mark_dirty)

        self.table = QTableView()
        self.table.setModel(self.model)
        ints_layout.addWidget(self.table)

        toolbar = QHBoxLayout()
        add_button = QPushButton("Add Dipole")
        add_button.clicked.connect(lambda: self.model.append_row(list(NEW_INT_ROW)))
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self._remove_selected)
        toolbar.addWidget(add_button)
        toolbar.addWidget(remove_button)
        toolbar.addStretch(1)
        ints_layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(header_group)
        splitter.addWidget(ints_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_as_button = QPushButton("Save As…")
        save_as_button.clicked.connect(lambda: self.save(save_as=True))
        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save(save_as=False))
        buttons.addWidget(save_as_button)
        buttons.addWidget(save_button)
        layout.addLayout(buttons)

    def _update_header(self, key, field):
        try:
            new_value = _parse_like(self.document.data[key], field.text())
        except ValueError:
            field.setText(str(self.document.data[key]))
            return
        if new_value != self.document.data[key]:
            self.document.data[key] = new_value
            self._mark_dirty()

    def _remove_selected(self):
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        self.model.remove_rows(rows)
