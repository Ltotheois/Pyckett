# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Read-only DataFrame viewer, used for *.cat/*.egy output tabs

from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QTableView, QVBoxLayout, QWidget

from pyckett.gui.project import SAVERS
from pyckett.gui.qt_models.pandas_filter_proxy import PandasFilterProxyModel
from pyckett.gui.qt_models.pandas_table_model import PandasTableModel
from pyckett.gui.widgets.query_bar import QueryBarWidget


class ReadOnlyTableTabWidget(QWidget):
    """Read-only, filterable DataFrame table with an optional Export button.

    *.cat/*.egy content is an SPFIT/SPCAT output, not something the user
    hand-edits, but they may still want to filter it down or save it to disk.
    """

    def __init__(self, project, document, parent=None):
        super().__init__(parent)
        self.project = project
        self.document = document

        layout = QVBoxLayout(self)

        self.query_bar = QueryBarWidget()
        self.query_bar.query_changed.connect(self._on_query_changed)
        layout.addWidget(self.query_bar)

        self.model = PandasTableModel(document.data)
        self.proxy = PandasFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        layout.addWidget(self.table)

        if document.kind in SAVERS:
            toolbar = QHBoxLayout()
            toolbar.addStretch(1)
            export_button = QPushButton("Export…")
            export_button.clicked.connect(self._export)
            toolbar.addWidget(export_button)
            layout.addLayout(toolbar)

    def _on_query_changed(self, text):
        error = self.proxy.set_query(text)
        self.query_bar.set_error(error)

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, f"Export {self.document.label}")
        if not path:
            return
        try:
            self.document.save(path)
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
