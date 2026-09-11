# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : "spfit" tab - run SPFIT virtually, and show fitted parameters/output/residuals

from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QToolBox, QVBoxLayout, QWidget

from pyckett.gui.fit_parsing import parse_fit_df
from pyckett.gui.widgets.fit_tab import FitTabWidget
from pyckett.gui.widgets.par_tab import ParTabWidget
from pyckett.gui.widgets.placeholder import PlaceholderWidget
from pyckett.gui.widgets.text_tab import TextTabWidget


class SpfitTabWidget(QWidget):
    """Run SPFIT and show its results in a toolbox: only one view open at a time.

    Rebuilt (like the *.par/*.lin/*.int tabs) whenever the project's tabs are
    resynced, so it always reflects the latest run - there is nothing here
    to edit, so nothing is ever lost by rebuilding it. The residuals plot
    itself is not embedded here - "Open Residuals Plot" (bottom row, next to
    "Run SPFIT") opens it in its own resizable window (see
    ProjectWidget.open_residuals_plot), which is why it survives this tab
    being torn down and rebuilt on every run.
    """

    def __init__(
        self, project, run_callback, refresh_titles_callback=None,
        open_residuals_plot_callback=None, parent=None,
    ):
        super().__init__(parent)
        self.project = project
        self.refresh_titles_callback = refresh_titles_callback

        layout = QVBoxLayout(self)

        toolbox = QToolBox()

        var_doc = project.get("var")
        toolbox.addItem(
            ParTabWidget(project, var_doc, read_only=True)
            if var_doc is not None
            else PlaceholderWidget("Run SPFIT to see the fitted parameters."),
            "Fitted Parameters",
        )

        msg_doc = project.get_text("SPFIT Output")
        toolbox.addItem(
            TextTabWidget(msg_doc) if msg_doc is not None
            else PlaceholderWidget("Run SPFIT to see its output."),
            "Output",
        )

        fit_doc = project.get_text("SPFIT Residuals (.fit)")
        toolbox.addItem(
            FitTabWidget(fit_doc) if fit_doc is not None
            else PlaceholderWidget("Run SPFIT to see the residuals."),
            "Residuals",
        )

        layout.addWidget(toolbox, 1)

        # Bottom, right-aligned - consistent with the *.par/*.lin/*.int tabs'
        # Save buttons.
        run_row = QHBoxLayout()
        run_row.addStretch(1)
        run_button = QPushButton("Run SPFIT")
        run_button.clicked.connect(run_callback)
        run_row.addWidget(run_button)

        residuals_df = self._residuals_df(fit_doc)
        plot_button = QPushButton("Open Residuals Plot")
        plot_button.setEnabled(residuals_df is not None and open_residuals_plot_callback is not None)
        if residuals_df is not None and open_residuals_plot_callback is not None:
            plot_button.clicked.connect(lambda: open_residuals_plot_callback(residuals_df))
        run_row.addWidget(plot_button)

        layout.addLayout(run_row)

    def _residuals_df(self, fit_doc):
        if fit_doc is None:
            return None
        try:
            return parse_fit_df(fit_doc.data)
        except Exception:
            return None
