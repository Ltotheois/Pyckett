# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Shared plumbing for the "Add" and "Omit" parameter-testing tabs

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QMenu, QMessageBox, QWidget

from pyckett.gui.workers import FunctionWorker


class ParameterTestTabWidget(QWidget):
    """Base for the Add/Omit-parameter tabs: background runs plus a results table.

    Subclasses build their own form/results table and set ``self.results_table``
    to it, then call ``self._enable_results_context_menu()`` once it exists.
    "Apply to Current Project" and "Open in New Project" are reachable both
    via buttons the subclass adds and via a right-click menu on the results
    table (``_apply_selected``/``_open_selected``, implemented by subclasses).
    """

    new_project_requested = pyqtSignal(object)

    def __init__(self, project, refresh_callback, parent=None):
        super().__init__(parent)
        self.project = project
        self.refresh_callback = refresh_callback
        self._results = []
        self._workers = []
        self.results_table = None

    # -- background runs --------------------------------------------------

    def _run_worker(self, func, *args, on_done, **kwargs):
        worker = FunctionWorker(func, *args, **kwargs)
        self._workers.append(worker)

        def cleanup():
            if worker in self._workers:
                self._workers.remove(worker)

        worker.finished_ok.connect(on_done)
        worker.finished_ok.connect(cleanup)
        worker.finished_error.connect(self._on_worker_error)
        worker.finished_error.connect(cleanup)
        worker.start()
        return worker

    def _on_worker_error(self, message):
        QMessageBox.critical(self, "Action Failed", message)

    def _require_par_lin(self):
        par_doc = self.project.get("par")
        lin_doc = self.project.get("lin")
        if par_doc is None or lin_doc is None:
            QMessageBox.warning(self, "Missing Files", "This action needs an open *.par and *.lin file.")
            return None, None
        return par_doc, lin_doc

    # -- results table right-click menu ------------------------------------

    def _enable_results_context_menu(self):
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._show_results_context_menu)

    def _show_results_context_menu(self, pos):
        index = self.results_table.indexAt(pos)
        if not index.isValid():
            return
        self.results_table.selectRow(index.row())

        menu = QMenu(self)
        apply_action = menu.addAction("Apply to Current Project")
        open_action = menu.addAction("Open in New Project")
        chosen = menu.exec(self.results_table.viewport().mapToGlobal(pos))
        if chosen == apply_action:
            self._apply_selected()
        elif chosen == open_action:
            self._open_selected()

    # Subclasses implement:
    #   _apply_selected(self)
    #   _open_selected(self)
