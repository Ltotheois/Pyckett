# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Tab widget for editing *.par files (and viewing *.var read-only)

import pyckett
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from pyckett.gui.qt_models.editable_list_model import ListTableModel
from pyckett.gui.severity_colors import FLAG_ORANGE, FLAG_RED, FLAG_TEXT_COLOR
from pyckett.gui.widgets.parameter_search_dialog import ParameterSearchDialog
from pyckett.gui.widgets.tab_base import EditableTabWidget

# NPAR/NLINE/NXPAR are hidden: the GUI keeps them correct automatically
# (Project.sync_par_fields), so they'd never need the user's attention.
# DATE isn't meaningful to the user either.
GENERAL_KEYS = ["TITLE", "NITR", "THRESH", "ERRTST", "FRAC", "CAL"]
STATE_KEYS = [
    "CHR", "SPIND", "NVIB", "KNMIN", "KNMAX", "IXX", "IAX",
    "WTPL", "WTMN", "VSYM", "EWT", "DIAG", "XOPT",
]
# CHR is text, the rest are all integers (see pyckett.parvar_to_dict).
STATE_FORMATTERS = [str] + [str] * (len(STATE_KEYS) - 1)
STATE_PARSERS = [str] + [int] * (len(STATE_KEYS) - 1)

PARAM_HEADERS = ["ID", "Value", "Uncertainty", "Comment"]
NEW_PARAM_ROW = [0, 1e-37, 1e37, ""]


def _parse_like(original, text):
    text = text.strip()
    if isinstance(original, str):
        return text
    value = float(text)
    if isinstance(original, int) and value % 1 == 0:
        return int(value)
    return value


class ParTabWidget(EditableTabWidget):
    """Editable view of a *.par Document (or read-only view of *.var).

    ``run_action``, if given, is an ``(label, callback)`` pair for a button
    placed before the Save/Save As buttons - used for the "Run SPFIT"
    button on the *.par tab and the "Run SPCAT" button on the *.var tab.
    """

    file_dialog_filter = "Parameter Files (*.par *.var);;All Files (*)"

    def __init__(self, project, document, read_only=False, run_action=None, parent=None):
        super().__init__(project, document, read_only=read_only, parent=parent)
        par = document.data
        self.header_fields = {}

        # Normalize PARAMS rows to a fixed [id, value, uncertainty, comment]
        # shape so the table model can index columns positionally.
        for row in par["PARAMS"]:
            while len(row) < 4:
                row.append("")

        outer = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_container = QWidget()
        scroll.setWidget(form_container)
        form_layout = QVBoxLayout(form_container)

        form_layout.addWidget(self._build_header_group("General", GENERAL_KEYS, par))
        form_layout.addWidget(self._build_header_group("Base State", STATE_KEYS, par))
        form_layout.addWidget(self._build_states_group(par))

        form_layout.addStretch(1)

        # General/Base-State/States on the left, Parameters on the right,
        # with a mouse-draggable divider between them.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(self._build_params_group(par["PARAMS"]))
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        if run_action is not None:
            run_label, run_callback = run_action
            run_button = QPushButton(run_label)
            run_button.clicked.connect(run_callback)
            buttons.addWidget(run_button)
        if not read_only:
            save_as_button = QPushButton("Save As…")
            save_as_button.clicked.connect(lambda: self.save(save_as=True))
            save_button = QPushButton("Save")
            save_button.clicked.connect(lambda: self.save(save_as=False))
            buttons.addWidget(save_as_button)
            buttons.addWidget(save_button)
        if run_action is not None or not read_only:
            outer.addLayout(buttons)

    def _build_header_group(self, title, keys, par):
        group = QGroupBox(title)
        layout = QFormLayout(group)
        for key in keys:
            if key not in par:
                continue
            field = QLineEdit(str(par[key]))
            field.setReadOnly(self.read_only)
            if not self.read_only:
                field.editingFinished.connect(lambda k=key, f=field: self._update_header(k, f))
            layout.addRow(key, field)
            self.header_fields[key] = field
        return group

    def _update_header(self, key, field):
        try:
            new_value = _parse_like(self.document.data[key], field.text())
        except ValueError:
            field.setText(str(self.document.data[key]))
            return
        if new_value != self.document.data[key]:
            self.document.data[key] = new_value
            self._mark_dirty()

    # -- additional vibrational states (*.par STATES) -----------------------

    def _build_states_group(self, par):
        group = QGroupBox("Additional Vibrational States")
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel(
            "Each row is one extra state beyond the Base State above. The last "
            "row's VSYM must be ≥ 0; every row before it is kept at VSYM < 0 "
            "automatically - that's how the *.par format knows how many "
            "state lines to expect."
        ))

        self.states_model = ListTableModel(
            par["STATES"],
            STATE_KEYS,
            editable_columns=set() if self.read_only else set(range(len(STATE_KEYS))),
            formatters=STATE_FORMATTERS,
            parsers=STATE_PARSERS,
            column_keys=STATE_KEYS,
        )
        self.states_model.dataChanged.connect(self._mark_dirty)
        self.states_model.modelReset.connect(self._mark_dirty)

        self.states_table = QTableView()
        self.states_table.setModel(self.states_model)
        self.states_table.setMaximumHeight(160)
        layout.addWidget(self.states_table)

        if not self.read_only:
            toolbar = QHBoxLayout()
            add_button = QPushButton("Add State")
            add_button.clicked.connect(self._add_state)
            remove_button = QPushButton("Remove Selected")
            remove_button.clicked.connect(self._remove_selected_states)
            toolbar.addWidget(add_button)
            toolbar.addWidget(remove_button)
            toolbar.addStretch(1)
            layout.addLayout(toolbar)

        return group

    def _new_state_row(self):
        """Seed a new state from the last existing one (or the Base State if there isn't one)."""
        states = self.document.data["STATES"]
        template = states[-1] if states else self.document.data
        return {key: template.get(key, 0) for key in STATE_KEYS}

    def _fix_vsym_chain(self):
        """Keep VSYM < 0 for every state but the last, which needs VSYM >= 0.

        This is exactly what tells *.par's own reader how many extra state
        lines to expect, so the file only round-trips correctly if it holds -
        applied automatically after Add/Remove so the user doesn't have to
        manage it by hand, but never overrides a value the user typed in
        directly at some other time.
        """
        par = self.document.data
        chain = [par] + par["STATES"]
        for i, state in enumerate(chain):
            is_last = i == len(chain) - 1
            current = state.get("VSYM", 0)
            if is_last and current < 0:
                state["VSYM"] = 0
            elif not is_last and current >= 0:
                state["VSYM"] = -1

        base_field = self.header_fields.get("VSYM")
        if base_field is not None:
            base_field.setText(str(par["VSYM"]))

    def _add_state(self):
        self.states_model.append_row(self._new_state_row())
        self._fix_vsym_chain()
        self.states_model.layoutChanged.emit()

    def _remove_selected_states(self):
        rows = {index.row() for index in self.states_table.selectionModel().selectedRows()}
        if not rows:
            return
        self.states_model.remove_rows(rows)
        self._fix_vsym_chain()
        self.states_model.layoutChanged.emit()

    # -- parameters -----------------------------------------------------------

    def _uncertainty_row_color(self, params):
        """Flag fitted parameters whose uncertainty is large relative to their value.

        Red: uncertainty exceeds the parameter's own value (effectively
        unconstrained). Orange: uncertainty is more than 10% but at most
        100% of the value. Only meaningful for *.var (fitted values) - *.par's
        third column is an allowed-change limit, not a statistical
        uncertainty, so this is only used in read-only (*.var) mode.
        """
        rel_uncertainties = pyckett.check_uncertainties({"PARAMS": params})

        def row_color(row):
            rel = rel_uncertainties.get(row[0])
            if rel is None:
                return None
            if rel > 1:
                return (FLAG_RED, FLAG_TEXT_COLOR)
            if rel > 0.1:
                return (FLAG_ORANGE, FLAG_TEXT_COLOR)
            return None

        return row_color

    def _build_params_group(self, params):
        group = QGroupBox("Parameters")
        layout = QVBoxLayout(group)

        self.params_model = ListTableModel(
            params,
            PARAM_HEADERS,
            editable_columns=set() if self.read_only else {0, 1, 2, 3},
            formatters=[str, lambda v: f"{v:.6e}", lambda v: f"{v:.3e}", str],
            parsers=[int, float, float, str],
            row_color_fn=self._uncertainty_row_color(params) if self.read_only else None,
        )
        self.params_model.dataChanged.connect(self._mark_dirty)
        self.params_model.modelReset.connect(self._mark_dirty)

        self.params_table = QTableView()
        self.params_table.setModel(self.params_model)
        layout.addWidget(self.params_table)

        if not self.read_only:
            toolbar = QHBoxLayout()
            add_button = QPushButton("Add Parameter")
            add_button.clicked.connect(lambda: self.params_model.append_row(list(NEW_PARAM_ROW)))
            search_button = QPushButton("Add Parameter by Label…")
            search_button.clicked.connect(self._add_parameter_by_label)
            remove_button = QPushButton("Remove Selected")
            remove_button.clicked.connect(self._remove_selected_params)
            toolbar.addWidget(add_button)
            toolbar.addWidget(search_button)
            toolbar.addWidget(remove_button)
            toolbar.addStretch(1)
            layout.addLayout(toolbar)

        return group

    def _remove_selected_params(self):
        rows = {index.row() for index in self.params_table.selectionModel().selectedRows()}
        self.params_model.remove_rows(rows)

    def _add_parameter_by_label(self):
        dialog = ParameterSearchDialog(self.document.data, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        result = dialog.selected_parameter()
        if result is None:
            return
        param_id, label = result
        self.params_model.append_row([param_id, 1e-37, 1e37, label])
