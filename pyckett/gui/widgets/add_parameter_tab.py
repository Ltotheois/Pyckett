# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : "Add" tab - test which parameter to add to the fit

import copy

import pandas as pd
import pyckett
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
)

from pyckett.clitools.addparameters import addparameters_core
from pyckett.gui.qt_models.pandas_table_model import PandasTableModel
from pyckett.gui.widgets.parameter_search_dialog import ParameterSearchDialog
from pyckett.gui.widgets.parameter_test_tab_base import ParameterTestTabWidget


def _parse_int_list(text):
    text = text.strip()
    if not text:
        return None
    return [int(x) for x in text.replace(",", " ").split()]


def _parse_float_list(text):
    text = text.strip()
    if not text:
        return None
    return [float(x) for x in text.replace(",", " ").split()]


class AddParameterTabWidget(ParameterTestTabWidget):
    """Test which parameter(s) to add to the fit; apply a candidate or open it in a new project.

    Leaving the parameter queue empty auto-detects every viable candidate
    from the Reduction/Skip settings below (as before). Building up a queue
    instead - via "Add by Label…" (searches POSSIBLE_PARAMS_* the same way
    as the *.par tab's "Add Parameter by Label" dialog) or "Add by ID…" -
    tests only those parameters, all in the same run: a way to compare a
    hand-picked batch head-to-head instead of wading through every
    auto-detected candidate.

    "Apply to Current Project" and "Open in New Project" are available both
    as buttons and via right-click on a results row.
    """

    def __init__(self, project, refresh_callback, parent=None):
        super().__init__(project, refresh_callback, parent=parent)
        self._build_form(QVBoxLayout(self))

    def _build_form(self, layout):
        form = QFormLayout()
        self.reduction_combo = QComboBox()
        self.reduction_combo.addItems(["A-Reduction", "S-Reduction", "Linear"])
        form.addRow("Reduction", self.reduction_combo)

        self.stateqn_spin = QSpinBox()
        self.stateqn_spin.setRange(1, 12)
        self.stateqn_spin.setValue(4)
        form.addRow("State quantum number index", self.stateqn_spin)

        self.newinteraction_edit = QLineEdit()
        self.newinteraction_edit.setPlaceholderText("States to find new interactions for (optional)")
        form.addRow("New interaction states", self.newinteraction_edit)

        self.initialvalues_edit = QLineEdit()
        self.initialvalues_edit.setPlaceholderText("default 1e-37")
        form.addRow("Initial values", self.initialvalues_edit)
        layout.addLayout(form)

        layout.addWidget(QLabel(
            "Parameter queue (optional - leave empty to auto-detect candidates below; "
            "when non-empty, only these are tested):"
        ))
        self.queue_list = QListWidget()
        self.queue_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.queue_list.setMaximumHeight(90)
        layout.addWidget(self.queue_list)

        queue_row = QHBoxLayout()
        add_label_button = QPushButton("Add by Label…")
        add_label_button.clicked.connect(self._add_by_label)
        add_id_button = QPushButton("Add by ID…")
        add_id_button.clicked.connect(self._add_by_id)
        remove_queued_button = QPushButton("Remove Selected")
        remove_queued_button.clicked.connect(self._remove_queued)
        clear_queue_button = QPushButton("Clear Queue")
        clear_queue_button.clicked.connect(self.queue_list.clear)
        queue_row.addWidget(add_label_button)
        queue_row.addWidget(add_id_button)
        queue_row.addWidget(remove_queued_button)
        queue_row.addWidget(clear_queue_button)
        queue_row.addStretch(1)
        layout.addLayout(queue_row)

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

    def _reduction_value(self):
        return {"A-Reduction": None, "S-Reduction": "s_reduction", "Linear": "linear"}[
            self.reduction_combo.currentText()
        ]

    # -- parameter queue ----------------------------------------------------

    def _add_by_label(self):
        par_doc = self.project.get("par")
        if par_doc is None:
            QMessageBox.warning(self, "No *.par File", "Open a *.par file first.")
            return
        dialog = ParameterSearchDialog(par_doc.data, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.selected_parameter()
        if selected is None:
            return
        self._add_queue_item(*selected)

    def _add_by_id(self):
        text, accepted = QInputDialog.getText(self, "Add by ID", "Parameter IDs, comma-separated:")
        if not accepted:
            return
        try:
            ids = _parse_int_list(text)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Input", str(exc))
            return
        for param_id in ids or []:
            self._add_queue_item(param_id, "")

    def _add_queue_item(self, param_id, comment):
        existing_ids = {
            self.queue_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.queue_list.count())
        }
        if param_id in existing_ids:
            return
        label = f"{param_id}  —  {comment}" if comment else str(param_id)
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, param_id)
        self.queue_list.addItem(item)

    def _remove_queued(self):
        for item in self.queue_list.selectedItems():
            self.queue_list.takeItem(self.queue_list.row(item))

    def _queued_ids(self):
        return [self.queue_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.queue_list.count())]

    def _run(self):
        par_doc, lin_doc = self._require_par_lin()
        if par_doc is None:
            return

        try:
            newinteraction = _parse_int_list(self.newinteraction_edit.text())
            initialvalues = _parse_float_list(self.initialvalues_edit.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Input", str(exc))
            return

        paramids = self._queued_ids() or None

        par_copy = par_doc.copy_data()
        if self.parupdate_cb.isChecked():
            par_copy.update(pyckett.PARUPDATE)
        else:
            par_copy["NPAR"] = max(par_copy["NPAR"], len(par_copy["PARAMS"]) + 1)

        vib_digits = pyckett.get_vib_digits(par_copy)
        stateqn = self.stateqn_spin.value()
        kwargs = dict(
            VIB_DIGITS=vib_digits,
            ALL_STATES=pyckett.get_all_states(vib_digits),
            qnu=f"qnu{stateqn}",
            qnl=f"qnl{stateqn}",
            parameters=self._reduction_value(),
            skipfixed=self.skipfixed_cb.isChecked(),
            skipinterstate=self.skipinterstate_cb.isChecked(),
            skiprotational=self.skiprotational_cb.isChecked(),
            skipglobal=self.skipglobal_cb.isChecked(),
            newinteraction=newinteraction,
            initialvalues=initialvalues,
            bestparfile=None,
            parameters_to_test=paramids,
            sort_by_wrms=self.sortwrms_cb.isChecked(),
            report=False,
        )

        self.status_label.setText("Running…")
        self.progress.show()
        self._run_worker(addparameters_core, par_copy, lin_doc.copy_data(), on_done=self._on_finished, **kwargs)

    def _on_finished(self, result):
        self.progress.hide()
        init_stats, best_stats, results = result
        self._results = results

        best_index = next((i for i, r in enumerate(results) if r is best_stats), None)

        rows = []
        for stats in results:
            failed = stats["mw_rms"] is None
            rows.append(
                {
                    "ID": stats["id"][0],
                    "Comment": stats["params"][-1][3] if len(stats["params"][-1]) > 3 else "",
                    "MW RMS [kHz]": float("nan") if failed else stats["mw_rms"] * 1000,
                    "WRMS": stats["stats"]["wrms"],
                    "Rejected Lines": stats["stats"]["rejected_lines"],
                    "Diverging": stats["stats"]["diverging"],
                    "Initial Value": stats["params"][-1][1],
                    "Final Value": stats["par"][-1][1],
                }
            )

        self.results_table.setModel(PandasTableModel(pd.DataFrame(rows)))

        init_line = (
            f"Initial: MW RMS = {init_stats['mw_rms'] * 1000:.2f} kHz, WRMS = {init_stats['wrms']:.2f}, "
            f"rejected = {init_stats['stats']['rejected_lines']}, diverging = {init_stats['stats']['diverging']}."
        )
        if best_index is not None:
            self.status_label.setText(
                f"{init_line} Best candidate: parameter {best_stats['id'][0]} (row {best_index + 1} below, pre-selected)."
            )
            self.results_table.selectRow(best_index)
        else:
            self.status_label.setText(f"{init_line} No candidate improved on the initial fit.")

    def _selected_result(self):
        selection_model = self.results_table.selectionModel()
        rows = selection_model.selectedRows() if selection_model else []
        if not rows or not self._results:
            QMessageBox.information(self, "No Selection", "Select a result row first.")
            return None
        return self._results[rows[0].row()]

    def _apply_selected(self):
        stats = self._selected_result()
        if stats is None:
            return
        new_params = copy.deepcopy(stats["par"])

        def mutate(document):
            document.data["PARAMS"] = new_params

        self.project.mutate("par", f"Applied candidate parameter {stats['id'][0]}", mutate)
        self.refresh_callback()

    def _open_selected(self):
        stats = self._selected_result()
        if stats is None:
            return
        new_project = self.project.clone_with_new_par(
            f"{self.project.name} (+{stats['id'][0]})", stats["par"]
        )
        self.new_project_requested.emit(new_project)
