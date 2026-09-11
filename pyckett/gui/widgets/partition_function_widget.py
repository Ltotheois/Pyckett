# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Rotational partition function (total + per vibrational state) from a *.egy file

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableView, QVBoxLayout, QWidget

from pyckett.clitools.partitionfunction import Temperatures as DEFAULT_TEMPERATURES
from pyckett.clitools.partitionfunction import factor as FACTOR
from pyckett.clitools.partitionfunction import factor_pickett as FACTOR_PICKETT
from pyckett.clitools.partitionfunction import partitionfunction_at_temperature
from pyckett.gui.parameter_lookup import v_column_position
from pyckett.gui.qt_models.pandas_table_model import PandasTableModel


class PartitionFunctionWidget(QWidget):
    """Rotational partition function Q(T) of the current *.egy file.

    Follows pyckett.clitools.partitionfunction's definition (Q = sum(we *
    exp(-egy * factor / T))) applied to the whole file for "Total", and -
    when the molecule has more than one vibrational state - again to each
    state's own energy levels individually (grouped by the same qn-slot
    v_column_position() already uses for the *.lin v column, since *.egy's
    quantum numbers follow the same per-level layout).

    Embedded as its own resizable pop-out window (see
    ProjectWidget.open_partition_function), same as the residuals/
    predictions/energy-levels plots, since it's another *.egy-derived result.
    """

    def __init__(self, df, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.df = df

        layout = QVBoxLayout(self)

        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel("Temperatures [K]:"))
        self.temperatures_edit = QLineEdit(", ".join(f"{t:g}" for t in DEFAULT_TEMPERATURES))
        controls_row.addWidget(self.temperatures_edit, 1)
        self.pickett_factor_cb = QCheckBox("Use SPCAT's factor")
        self.pickett_factor_cb.toggled.connect(self.update_table)
        controls_row.addWidget(self.pickett_factor_cb)
        self.log_cb = QCheckBox("Show log₁₀(Q)")
        self.log_cb.toggled.connect(self.update_table)
        controls_row.addWidget(self.log_cb)
        recalc_button = QPushButton("Recalculate")
        recalc_button.clicked.connect(self.update_table)
        controls_row.addWidget(recalc_button)
        layout.addLayout(controls_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.table = QTableView()
        layout.addWidget(self.table, 1)

        self.update_table()

    def set_dataframe(self, df):
        """Point this widget at a fresh *.egy dataframe, e.g. after a new SPCAT run."""
        self.df = df
        self.update_table()

    def _temperatures(self):
        text = self.temperatures_edit.text().strip()
        if not text:
            return list(DEFAULT_TEMPERATURES)
        return sorted({float(x) for x in text.replace(",", " ").split()}, reverse=True)

    def _v_column(self):
        """Return the *.egy qn-column holding the vibrational state, or None."""
        par_doc = self.project.get("par") if self.project is not None else None
        if par_doc is None:
            return None
        position = v_column_position(par_doc.data)
        if position is None:
            return None
        column = f"qn{position}"
        return column if column in self.df.columns else None

    def _q_series(self, subset, temperatures, factor):
        subset = subset.copy()
        return {T: partitionfunction_at_temperature(subset, T, factor=factor) for T in temperatures}

    def update_table(self):
        df = self.df
        if df is None or len(df) == 0:
            self.table.setModel(PandasTableModel(pd.DataFrame()))
            self.status_label.setText("No *.egy data yet - run SPCAT first.")
            return

        try:
            temperatures = self._temperatures()
        except ValueError as exc:
            self.status_label.setText(f"Invalid temperature: {exc}")
            return

        factor = FACTOR_PICKETT if self.pickett_factor_cb.isChecked() else FACTOR

        columns = {"Total": self._q_series(df, temperatures, factor)}

        v_column = self._v_column()
        n_states = 0
        if v_column is not None:
            states = sorted(df[v_column].unique())
            n_states = len(states)
            for v in states:
                columns[f"v={int(v)}"] = self._q_series(df.loc[df[v_column] == v], temperatures, factor)

        table_df = pd.DataFrame(columns)
        table_df.index.name = "T [K]"
        if self.log_cb.isChecked():
            table_df = np.log10(table_df)
        table_df = table_df.round(4).reset_index()

        self.table.setModel(PandasTableModel(table_df))

        jmax, kamax, kcmax = df["qn1"].max(), df["qn2"].max(), df["qn3"].max()
        state_note = f", {n_states} vibrational state(s)" if v_column is not None else ""
        self.status_label.setText(f"J_max = {jmax}, Ka_max = {kamax}, Kc_max = {kcmax}{state_note}")
