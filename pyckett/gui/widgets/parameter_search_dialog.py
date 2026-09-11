# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Dialog to look up a *.par parameter id by its human-readable label

import pyckett
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QVBoxLayout,
)

from pyckett.gui.parameter_lookup import KINDS, default_kind, full_parameter_id, search_labels


class ParameterSearchDialog(QDialog):
    """Search pyckett's parameter-coding dictionaries (POSSIBLE_PARAMS_*) by label.

    Rotational/linear parameters need one vibrational state (or "Global"
    for all states); interaction parameters need two. The dialog previews
    the resulting numeric parameter id live as the selection changes.
    """

    def __init__(self, par, parent=None):
        super().__init__(parent)
        self.par = par
        self.vib_digits = pyckett.get_vib_digits(par)
        self.all_states = pyckett.get_all_states(self.vib_digits)

        self.setWindowTitle("Add Parameter by Label")
        self.resize(480, 480)

        layout = QVBoxLayout(self)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(KINDS)
        self.type_combo.setCurrentText(default_kind(par))
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        type_row.addWidget(self.type_combo)
        layout.addLayout(type_row)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search by label, e.g. DJ, PhiK, Ga…")
        self.search_field.textChanged.connect(self._refresh_results)
        layout.addWidget(self.search_field)

        self.results_list = QListWidget()
        self.results_list.currentItemChanged.connect(self._update_preview)
        layout.addWidget(self.results_list, 1)

        state_form = QFormLayout()
        self.state1_spin = QSpinBox()
        self.state1_spin.setRange(0, max(self.all_states, 9))
        self.state1_spin.valueChanged.connect(self._update_preview)
        state_form.addRow("Vibrational state", self.state1_spin)

        self.state2_label = QLabel("Second state (interaction)")
        self.state2_spin = QSpinBox()
        self.state2_spin.setRange(0, max(self.all_states, 9))
        self.state2_spin.setValue(min(1, self.all_states))
        self.state2_spin.valueChanged.connect(self._update_preview)
        state_form.addRow(self.state2_label, self.state2_spin)

        self.global_checkbox = QCheckBox("Global (all vibrational states)")
        self.global_checkbox.toggled.connect(self._on_global_toggled)
        state_form.addRow(self.global_checkbox)
        layout.addLayout(state_form)

        self.preview_label = QLabel("Parameter ID: —")
        layout.addWidget(self.preview_label)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._on_type_changed(self.type_combo.currentText())
        self._refresh_results()

    def _on_type_changed(self, kind):
        is_interaction = kind == "Interaction"
        self.state2_spin.setVisible(is_interaction)
        self.state2_label.setVisible(is_interaction)
        self._refresh_results()

    def _on_global_toggled(self, checked):
        self.state1_spin.setEnabled(not checked)
        self.state2_spin.setEnabled(not checked)
        self._update_preview()

    def _refresh_results(self):
        kind = self.type_combo.currentText()
        query = self.search_field.text()
        self.results_list.clear()
        for label, base_id in search_labels(kind, query):
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, base_id)
            self.results_list.addItem(item)
        if self.results_list.count():
            self.results_list.setCurrentRow(0)
        else:
            self._update_preview()

    def _selected_base_id(self):
        item = self.results_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _states(self):
        if self.global_checkbox.isChecked():
            return self.all_states, self.all_states
        v1 = self.state1_spin.value()
        if self.type_combo.currentText() == "Interaction":
            return v1, self.state2_spin.value()
        return v1, v1

    def _update_preview(self, *_args):
        base_id = self._selected_base_id()
        if base_id is None:
            self.preview_label.setText("Parameter ID: —")
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return
        v1, v2 = self._states()
        param_id = full_parameter_id(base_id, self.vib_digits, v1, v2)
        self.preview_label.setText(f"Parameter ID: {param_id}  ({self.results_list.currentItem().text()})")
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def selected_parameter(self):
        """Return (id, label) for the chosen parameter, or None if nothing is selected."""
        base_id = self._selected_base_id()
        if base_id is None:
            return None
        v1, v2 = self._states()
        param_id = full_parameter_id(base_id, self.vib_digits, v1, v2)
        return param_id, self.results_list.currentItem().text()
