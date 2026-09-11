# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : "spcat" tab - run SPCAT virtually, and show predictions/energy levels/output

from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QToolBox, QVBoxLayout, QWidget

from pyckett.gui.widgets.placeholder import PlaceholderWidget
from pyckett.gui.widgets.readonly_table_tab import ReadOnlyTableTabWidget
from pyckett.gui.widgets.text_tab import TextTabWidget


class SpcatTabWidget(QWidget):
    """Run SPCAT and show its results in a toolbox: only one view open at a time.

    Rebuilt (like the *.par/*.lin/*.int tabs) whenever the project's tabs are
    resynced. The predictions/energy-levels plots and the partition function
    table are not embedded here - "Open Predictions Plot"/"Open Energy
    Levels Plot"/"Partition Function" (bottom row, next to "Run SPCAT")
    each open theirs in its own resizable window (see
    ProjectWidget.open_predictions_plot/open_energy_levels_plot/
    open_partition_function), which is why they survive this tab being torn
    down and rebuilt on every run.
    """

    def __init__(
        self, project, run_callback,
        open_predictions_plot_callback=None, open_energy_levels_plot_callback=None,
        open_partition_function_callback=None,
        parent=None,
    ):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        toolbox = QToolBox()

        cat_doc = project.get("cat")
        toolbox.addItem(
            ReadOnlyTableTabWidget(project, cat_doc) if cat_doc is not None
            else PlaceholderWidget("Run SPCAT to see the predicted transitions."),
            "Predictions",
        )

        egy_doc = project.get("egy")
        toolbox.addItem(
            ReadOnlyTableTabWidget(project, egy_doc) if egy_doc is not None
            else PlaceholderWidget("Run SPCAT to see the energy levels."),
            "Energy Levels",
        )

        msg_doc = project.get_text("SPCAT Output")
        toolbox.addItem(
            TextTabWidget(msg_doc) if msg_doc is not None
            else PlaceholderWidget("Run SPCAT to see its output."),
            "Output",
        )

        layout.addWidget(toolbox, 1)

        # Bottom, right-aligned - consistent with the *.par/*.lin/*.int tabs'
        # Save buttons.
        run_row = QHBoxLayout()
        run_row.addStretch(1)
        run_button = QPushButton("Run SPCAT")
        run_button.clicked.connect(run_callback)
        run_row.addWidget(run_button)

        predictions_button = QPushButton("Open Predictions Plot")
        predictions_button.setEnabled(cat_doc is not None and open_predictions_plot_callback is not None)
        if cat_doc is not None and open_predictions_plot_callback is not None:
            predictions_button.clicked.connect(lambda: open_predictions_plot_callback(cat_doc.data))
        run_row.addWidget(predictions_button)

        energy_levels_button = QPushButton("Open Energy Levels Plot")
        energy_levels_button.setEnabled(egy_doc is not None and open_energy_levels_plot_callback is not None)
        if egy_doc is not None and open_energy_levels_plot_callback is not None:
            energy_levels_button.clicked.connect(lambda: open_energy_levels_plot_callback(egy_doc.data))
        run_row.addWidget(energy_levels_button)

        partition_function_button = QPushButton("Partition Function")
        partition_function_button.setEnabled(egy_doc is not None and open_partition_function_callback is not None)
        if egy_doc is not None and open_partition_function_callback is not None:
            partition_function_button.clicked.connect(lambda: open_partition_function_callback(egy_doc.data))
        run_row.addWidget(partition_function_button)

        layout.addLayout(run_row)
