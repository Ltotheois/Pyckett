# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Dialog to rename/renumber vibrational states across *.par/*.lin/*.int

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTableView,
    QVBoxLayout,
)

from pyckett.gui.qt_models.editable_list_model import ListTableModel
from pyckett.gui.rename_states import DEFAULT_STATE_QN_INDEX, collect_state_ids


class RenameStatesDialog(QDialog):
    """Lets the user renumber vibrational states, e.g. to focus on one or two
    states out of a large global fit.

    The table is auto-populated with every state id currently in use
    (discovered from *.par PARAMS/STATES, *.int INTS, and *.lin's qnu/qnl
    columns at the chosen state quantum-number slot); editing "New ID"
    builds a translation applied to all three documents on accept. Several
    old ids can be mapped to the same new id to deliberately merge/collapse
    states - that isn't an error, it's the main use case for "focus on one
    or two states".
    """

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project

        self.setWindowTitle("Rename/Renumber Vibrational States")
        self.resize(360, 480)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Edit the “New ID” column and press OK to renumber these "
            "vibrational states across the project's *.par, *.lin, and *.int "
            "files. Rows left unchanged are not touched; mapping several "
            "states to the same new id merges them."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        qn_row = QHBoxLayout()
        qn_row.addWidget(QLabel("State quantum number (qnu/qnl index):"))
        self.qn_spin = QSpinBox()
        self.qn_spin.setRange(1, 6)
        self.qn_spin.setValue(DEFAULT_STATE_QN_INDEX)
        self.qn_spin.valueChanged.connect(self._rebuild_rows)
        qn_row.addWidget(self.qn_spin)
        qn_row.addStretch(1)
        layout.addLayout(qn_row)

        self.table = QTableView()
        layout.addWidget(self.table, 1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.model = None
        self._rebuild_rows()

    def _rebuild_rows(self):
        states = collect_state_ids(self.project, state_qn_index=self.qn_spin.value())
        rows = [[state, state] for state in states]
        self.model = ListTableModel(
            rows,
            ["Current ID", "New ID"],
            editable_columns={1},
            formatters=[str, str],
            parsers=[int, int],
        )
        self.table.setModel(self.model)

    def state_qn_index(self):
        return self.qn_spin.value()

    def translation(self):
        """Return {old_id: new_id} for every row whose new id was actually changed."""
        return {row[0]: row[1] for row in self.model.rows if row[0] != row[1]}
