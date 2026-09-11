# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Dialog to compute the harmonic vibrational partition function

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from pyckett.clitools.vibpartitionfunction import Temperatures as DEFAULT_TEMPERATURES
from pyckett.clitools.vibpartitionfunction import vibpartitionfunction_at_temperature
from pyckett.gui.qt_models.pandas_table_model import PandasTableModel


def _parse_float_list(text):
    text = text.strip()
    if not text:
        return []
    return [float(x) for x in text.replace(",", " ").split()]


class VibPartitionFunctionDialog(QDialog):
    """Harmonic-approximation vibrational partition function, from pyckett.clitools.vibpartitionfunction.

    Q(vib, T) = prod(1 / (1 - exp(-v_i * h * c / (k * T)))) over the given
    vibrational fundamentals v_i (in cm-1) - standalone, since it only needs
    the fundamentals themselves rather than any open project file.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vibrational Partition Function")
        self.resize(520, 460)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.energies_edit = QLineEdit()
        self.energies_edit.setPlaceholderText("Fundamentals in cm⁻¹, e.g. 500, 800, 1200")
        form.addRow("Vibrational energies", self.energies_edit)

        self.temperatures_edit = QLineEdit(", ".join(f"{t:g}" for t in DEFAULT_TEMPERATURES))
        form.addRow("Temperatures [K]", self.temperatures_edit)
        layout.addLayout(form)

        calc_row = QHBoxLayout()
        calc_row.addStretch(1)
        calculate_button = QPushButton("Calculate")
        calculate_button.clicked.connect(self._calculate)
        calc_row.addWidget(calculate_button)
        layout.addLayout(calc_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.table = QTableView()
        layout.addWidget(self.table, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self._calculate()

    def _calculate(self):
        try:
            energies = _parse_float_list(self.energies_edit.text())
            temperatures = sorted(set(_parse_float_list(self.temperatures_edit.text())), reverse=True)
        except ValueError as exc:
            self.status_label.setText(f"Invalid input: {exc}")
            return

        if not temperatures:
            temperatures = list(DEFAULT_TEMPERATURES)

        rows = []
        for T in temperatures:
            q = vibpartitionfunction_at_temperature(energies, T)
            rows.append({"T [K]": T, "Q(vib)": round(q, 4), "log₁₀ Q(vib)": round(np.log10(q), 4)})

        self.table.setModel(PandasTableModel(pd.DataFrame(rows)))
        self.status_label.setText(f"{len(energies)} vibrational mode(s).")
