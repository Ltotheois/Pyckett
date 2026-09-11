# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Background-thread execution for long-running pyckett calls

import traceback

from PyQt6.QtCore import QThread, pyqtSignal


class FunctionWorker(QThread):
    """Runs a single callable on a background thread.

    Used for anything that shells out to SPFIT/SPCAT (run_spfit_v,
    run_spcat_v, addparameters_core, omitparameters_core) so the UI stays
    responsive. Connect to ``finished_ok``/``finished_error`` before calling
    ``start()``.
    """

    finished_ok = pyqtSignal(object)
    finished_error = pyqtSignal(str)

    def __init__(self, func, *args, parent=None, **kwargs):
        super().__init__(parent)
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._func(*self._args, **self._kwargs)
        except Exception:
            self.finished_error.emit(traceback.format_exc())
            return
        self.finished_ok.emit(result)
