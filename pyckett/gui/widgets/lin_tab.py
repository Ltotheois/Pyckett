# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Tab widget for editing *.lin assignment files

import pyckett
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QPushButton, QTableView, QVBoxLayout

from pyckett.gui.qt_models.lin_table_model import LinTableModel
from pyckett.gui.qt_models.pandas_filter_proxy import PandasFilterProxyModel
from pyckett.gui.widgets.duplicates_dialog import DuplicatesDialog
from pyckett.gui.widgets.query_bar import QueryBarWidget
from pyckett.gui.widgets.tab_base import EditableTabWidget


class LinTabWidget(EditableTabWidget):
    """Editable table view of a *.lin Document."""

    file_dialog_filter = "Line Files (*.lin);;All Files (*)"

    def __init__(self, project, document, parent=None):
        super().__init__(project, document, parent=parent)

        layout = QVBoxLayout(self)

        self.query_bar = QueryBarWidget()
        self.query_bar.query_changed.connect(self._on_query_changed)
        layout.addWidget(self.query_bar)

        self.model = LinTableModel(document.data)
        self.model.dataChanged.connect(self._mark_dirty)
        self.model.dataChanged.connect(lambda *_: self._refilter())
        self.model.modelReset.connect(self._refilter)

        self.proxy = PandasFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        layout.addWidget(self.table)

        # Row actions share a row with Save/Save As to save vertical space.
        toolbar = QHBoxLayout()
        add_button = QPushButton("Add Line")
        add_button.clicked.connect(self._add_row)
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self._remove_selected)
        sort_button = QPushButton("Sort by Frequency")
        sort_button.clicked.connect(self._sort)
        duplicates_button = QPushButton("Remove Duplicates…")
        duplicates_button.clicked.connect(self._remove_duplicates)
        toolbar.addWidget(add_button)
        toolbar.addWidget(remove_button)
        toolbar.addWidget(sort_button)
        toolbar.addWidget(duplicates_button)
        toolbar.addStretch(1)
        save_as_button = QPushButton("Save As…")
        save_as_button.clicked.connect(lambda: self.save(save_as=True))
        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save(save_as=False))
        toolbar.addWidget(save_as_button)
        toolbar.addWidget(save_button)
        layout.addLayout(toolbar)

    def _on_query_changed(self, text):
        error = self.proxy.set_query(text)
        self.query_bar.set_error(error)

    def _refilter(self):
        error = self.proxy.reapply()
        self.query_bar.set_error(error)

    def _sync_document(self):
        self.document.data = self.model.dataframe()
        self._mark_dirty()

    def _add_row(self):
        self.model.append_row(self.model.new_row_defaults())
        self._sync_document()

    def _remove_selected(self):
        rows = {self.proxy.mapToSource(index).row() for index in self.table.selectionModel().selectedRows()}
        self.model.remove_rows(rows)
        self._sync_document()

    def _sort(self):
        sorted_df = self.model.dataframe().sort_values(["x", "error"]).reset_index(drop=True)
        self.model.set_dataframe(sorted_df)
        self._sync_document()

    def _remove_duplicates(self):
        dialog = DuplicatesDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        keep, sort = dialog.options()

        df = self.model.dataframe()
        qn_labels = [f"qn{ul}{i + 1}" for ul in "ul" for i in range(pyckett.QUANTA)]
        n_duplicates = int(df.duplicated(subset=qn_labels, keep=keep).sum())
        kept_df = df.drop_duplicates(subset=qn_labels, keep=keep)
        if sort:
            kept_df = kept_df.sort_values(["x", "error"])
        kept_df = kept_df.reset_index(drop=True)

        def mutate(document):
            document.data = kept_df

        self.project.mutate("lin", "Removed duplicate assignments", mutate)
        self.model.set_dataframe(kept_df)
        self._mark_dirty()
        QMessageBox.information(self, "Duplicates Removed", f"Removed {n_duplicates} duplicate line(s).")
