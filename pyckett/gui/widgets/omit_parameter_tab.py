# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : "Omit" tab - test which parameter to omit from the fit

import copy

import pandas as pd
import pyckett
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from pyckett.clitools.omitparameters import omitparameters_core
from pyckett.gui.qt_models.pandas_table_model import PandasTableModel
from pyckett.gui.widgets.parameter_test_tab_base import ParameterTestTabWidget


class OmitParameterTabWidget(ParameterTestTabWidget):
    """Test which parameter to omit from the fit; apply a candidate or open it in a new project.

    "Apply to Current Project" and "Open in New Project" are available both
    as buttons and via right-click on a results row.
    """

    def __init__(self, project, refresh_callback, parent=None):
        super().__init__(project, refresh_callback, parent=parent)
        self._build_form(QVBoxLayout(self))

    def _build_form(self, layout):
        checks = QHBoxLayout()
        self.skipinterstate_cb = QCheckBox("Skip interstate")
        self.skiprotational_cb = QCheckBox("Skip rotational")
        self.skipfixed_cb = QCheckBox("Skip fixed")
        self.skipglobal_cb = QCheckBox("Skip global")
        self.sortwrms_cb = QCheckBox("Sort by WRMS")
        self.parupdate_cb = QCheckBox("Reset NPAR/NLINE/THRESH")
        self.parupdate_cb.setChecked(True)
        for widget in (
            self.skipinterstate_cb, self.skiprotational_cb, self.skipfixed_cb,
            self.skipglobal_cb, self.sortwrms_cb, self.parupdate_cb,
        ):
            checks.addWidget(widget)
        layout.addLayout(checks)

        run_row = QHBoxLayout()
        run_button = QPushButton("Run")
        run_button.clicked.connect(self._run)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        run_row.addWidget(run_button)
        run_row.addWidget(self.progress, 1)
        layout.addLayout(run_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.results_table = QTableView()
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._enable_results_context_menu()
        layout.addWidget(self.results_table, 1)

        apply_row = QHBoxLayout()
        apply_row.addStretch(1)
        apply_button = QPushButton("Apply to Current Project")
        apply_button.clicked.connect(self._apply_selected)
        open_button = QPushButton("Open in New Project")
        open_button.clicked.connect(self._open_selected)
        apply_row.addWidget(apply_button)
        apply_row.addWidget(open_button)
        layout.addLayout(apply_row)

    def _run(self):
        par_doc, lin_doc = self._require_par_lin()
        if par_doc is None:
            return

        par_copy = par_doc.copy_data()
        if self.parupdate_cb.isChecked():
            par_copy.update(pyckett.PARUPDATE)

        vib_digits = pyckett.get_vib_digits(par_copy)
        kwargs = dict(
            VIB_DIGITS=vib_digits,
            ALL_STATES=pyckett.get_all_states(vib_digits),
            skipglobal=self.skipglobal_cb.isChecked(),
            skipfixed=self.skipfixed_cb.isChecked(),
            skipinterstate=self.skipinterstate_cb.isChecked(),
            skiprotational=self.skiprotational_cb.isChecked(),
            sort_by_wrms=self.sortwrms_cb.isChecked(),
            report=False,
        )

        self.status_label.setText("Running…")
        self.progress.show()
        self._run_worker(omitparameters_core, par_copy, lin_doc.data, on_done=self._on_finished, **kwargs)

    def _on_finished(self, runs):
        self.progress.hide()
        self._results = runs

        rows = []
        for r in runs:
            failed = r["mw_rms"] is None
            rows.append(
                {
                    "ID": r["id"],
                    "MW RMS [kHz]": float("nan") if failed else r["mw_rms"] * 1000,
                    "WRMS": float("nan") if failed else r["wrms"],
                    "Rejected Lines": "" if failed else r["stats"]["rejected_lines"],
                    "Status": "FAILED (may be essential)" if failed else r["stats"]["diverging"],
                }
            )

        self.results_table.setModel(PandasTableModel(pd.DataFrame(rows)))
        self.status_label.setText(f"Tested {len(runs)} parameter(s).")

    def _selected_result(self):
        selection_model = self.results_table.selectionModel()
        rows = selection_model.selectedRows() if selection_model else []
        if not rows or not self._results:
            QMessageBox.information(self, "No Selection", "Select a result row first.")
            return None
        result = self._results[rows[0].row()]
        if result["mw_rms"] is None:
            QMessageBox.warning(
                self, "Run Failed",
                f"Omitting parameter {result['id']} made SPFIT fail; it may be essential.",
            )
            return None
        return result

    def _apply_selected(self):
        result = self._selected_result()
        if result is None:
            return
        new_params = copy.deepcopy(result["par"])

        def mutate(document):
            document.data["PARAMS"] = new_params

        self.project.mutate("par", f"Omitted candidate parameter {result['id']}", mutate)
        self.refresh_callback()

    def _open_selected(self):
        result = self._selected_result()
        if result is None:
            return
        new_project = self.project.clone_with_new_par(
            f"{self.project.name} (-{result['id']})", result["par"]
        )
        self.new_project_requested.emit(new_project)
