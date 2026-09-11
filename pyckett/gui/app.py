# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Entry point for the `pyckett` GUI command

import sys
import threading
import traceback
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QMessageBox

from pyckett.gui.icon import load_app_icon
from pyckett.gui.mainwindow import MainWindow
from pyckett.gui.paths import app_data_dir


def except_hook(exc_type, exception, exc_traceback):
    """Report an otherwise-unhandled exception instead of letting it crash the app.

    Mirrors LLWP's except_hook: still prints/logs the full traceback for
    debugging, but keeps the GUI alive and tells the user something went
    wrong instead of silently dying or dumping a traceback with no
    explanation.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.exit(0)

    sys.__excepthook__(exc_type, exception, exc_traceback)

    formatted = "".join(traceback.format_exception(exc_type, exception, exc_traceback))
    try:
        log_path = app_data_dir() / "crash.log"
        with open(log_path, "a+", encoding="utf-8") as file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{timestamp}:\n{formatted}\n\n")
    except Exception:
        pass

    app = QApplication.instance()
    if app is not None:
        QMessageBox.critical(
            None,
            "Unexpected Error",
            f"Something went wrong and the last action may not have completed:\n\n"
            f"{exception}\n\nDetails were written to {app_data_dir() / 'crash.log'}.",
        )


def main():
    sys.excepthook = except_hook
    threading.excepthook = lambda args: except_hook(*args[:3])

    app = QApplication(sys.argv)
    app.setApplicationName("Pyckett")
    app.setStyle("Fusion")
    app.setWindowIcon(load_app_icon())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
