# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Dialog for browsing and restoring a project's version history

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class HistoryDialog(QDialog):
    """Lists a project's *.par/*.lin/*.int snapshots, oldest first, with a Restore action.

    Restoring never deletes newer snapshots (the store is append-only) - it
    replaces the project's current par/lin/int content and records a fresh
    snapshot of that fact, so nothing is ever lost.
    """

    restored = pyqtSignal(list)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(f"History — {project.name}")
        self.resize(520, 360)

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["When", "Label", "Files"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        restore_button = QPushButton("Restore Selected")
        restore_button.clicked.connect(self._restore_selected)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(restore_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self._reload()

    def _reload(self):
        snapshots = list(reversed(self.project.history.list_snapshots()))
        self.table.setRowCount(len(snapshots))
        for row, snapshot in enumerate(snapshots):
            self.table.setItem(row, 0, QTableWidgetItem(snapshot["timestamp"]))
            self.table.setItem(row, 1, QTableWidgetItem(snapshot["label"]))
            self.table.setItem(row, 2, QTableWidgetItem(", ".join(snapshot["kinds"])))
            self.table.item(row, 0).setData(1000, snapshot["id"])

    def _restore_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        snapshot_id = self.table.item(rows[0].row(), 0).data(1000)

        confirmation = QMessageBox.question(
            self,
            "Restore Snapshot",
            "Restore the project's parameters/assignments to this point?\n"
            "This does not delete any history — it can be undone by restoring again.",
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        restored_kinds = self.project.restore_snapshot(snapshot_id)
        self._reload()
        self.restored.emit(restored_kinds)
