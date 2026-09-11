# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Editable Qt table model for *.lin assignment data

import pyckett

from pyckett.gui.qt_models.pandas_table_model import PandasTableModel


def active_qn_columns(df):
    """Return the quantum-number columns that are actually in use, in order."""
    if len(df) == 0:
        n = pyckett.QUANTA
        return [f"qn{ul}{i + 1}" for ul in ("u", "l") for i in range(n)]

    active = pyckett.get_active_qns(df)
    return [qn for qn in active if active[qn]]


class LinTableModel(PandasTableModel):
    """Editable model for a *.lin DataFrame.

    Only the currently-active quantum-number columns (as reported by
    ``pyckett.get_active_qns``) are shown, but the underlying DataFrame keeps
    all of the columns ``pyckett.df_to_lin`` expects, so hidden/unused
    quantum-number columns stay filled with ``pyckett.SENTINEL``.
    """

    def __init__(self, df, parent=None):
        self.qn_columns = active_qn_columns(df)
        columns = self.qn_columns + ["x", "error", "weight", "comment"]
        super().__init__(df, columns=columns, editable_columns=set(columns), parent=parent)

    def format_value(self, column, raw_value):
        if column in self.qn_columns:
            if raw_value == pyckett.SENTINEL:
                return ""
            return str(int(raw_value))
        if column in ("x", "error"):
            return f"{raw_value:.4f}"
        if column == "weight":
            return f"{raw_value:.4g}"
        return "" if raw_value is None else str(raw_value)

    def parse_value(self, column, text):
        text = text.strip()
        if column in self.qn_columns:
            if not text:
                return pyckett.SENTINEL
            return int(pyckett.pickett_int(text))
        if column in ("x", "error", "weight"):
            return float(text)
        return text

    def new_row_defaults(self):
        """A full row (all underlying DataFrame columns) for a freshly added line."""
        row = {}
        for column in self._df.columns:
            if column.startswith("qn"):
                row[column] = pyckett.SENTINEL
            elif column in ("x", "error"):
                row[column] = 0.0
            elif column == "weight":
                row[column] = 1.0
            else:
                row[column] = ""
        return row
