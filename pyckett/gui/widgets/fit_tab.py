# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Parsed, filterable view of SPFIT's *.fit residuals, with the raw text on demand

import pandas as pd
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QPlainTextEdit, QPushButton, QTableView, QVBoxLayout, QWidget

from pyckett.gui.fit_parsing import parse_fit_df
from pyckett.gui.qt_models.pandas_filter_proxy import PandasFilterProxyModel
from pyckett.gui.qt_models.pandas_table_model import PandasTableModel
from pyckett.gui.severity_colors import FLAG_ORANGE, FLAG_RED, FLAG_TEXT_COLOR
from pyckett.gui.widgets.placeholder import PlaceholderWidget
from pyckett.gui.widgets.query_bar import QueryBarWidget


def _deviation_row_color(row):
    """Flag fit residuals that deviate a lot from their assigned uncertainty.

    ``rel_dev`` (from pyckett.fit_to_df) is already the deviation expressed
    in units of the line's uncertainty (abs_dev / error_lin) - red above 10
    uncertainties, orange above 3, using the same colors as the *.par/*.var
    uncertainty highlighting.
    """
    rel = row.get("rel_dev")
    if rel is None or pd.isna(rel):
        return None
    if rel > 10:
        return (FLAG_RED, FLAG_TEXT_COLOR)
    if rel > 3:
        return (FLAG_ORANGE, FLAG_TEXT_COLOR)
    return None


class FitTabWidget(QWidget):
    """Filterable DataFrame view of a *.fit residuals text Document.

    Shown by default; "Show Full Output…" opens the complete raw SPFIT
    output (the *.fit content isn't the only thing SPFIT prints) in a
    dialog for when the table isn't enough. The graphical residuals plot
    lives as its own section of the "spfit" tab's toolbox, not here.
    """

    def __init__(self, text_document, parent=None):
        super().__init__(parent)
        self.text_document = text_document

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        raw_button = QPushButton("Show Full Output…")
        raw_button.clicked.connect(self._show_raw_output)
        toolbar.addWidget(raw_button)
        layout.addLayout(toolbar)

        try:
            df = parse_fit_df(text_document.data)
        except Exception as exc:
            layout.addWidget(PlaceholderWidget(f"Could not parse the residuals table:\n{exc}"))
            return

        self.query_bar = QueryBarWidget()
        self.query_bar.query_changed.connect(self._on_query_changed)
        layout.addWidget(self.query_bar)

        self.model = PandasTableModel(df, row_color_fn=_deviation_row_color)
        self.proxy = PandasFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        layout.addWidget(self.table, 1)

    def _on_query_changed(self, text):
        error = self.proxy.set_query(text)
        self.query_bar.set_error(error)

    def _show_raw_output(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.text_document.label)
        dialog.resize(700, 500)

        layout = QVBoxLayout(dialog)
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        editor.setPlainText(self.text_document.data)
        layout.addWidget(editor)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec()
