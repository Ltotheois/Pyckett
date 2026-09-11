# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Residuals plot (*.fit dataframe), with LLWP-style point
#                 deletion plus lasso multi-select delete

from PyQt6.QtWidgets import QMessageBox, QPushButton

from pyckett.gui.widgets.plot_widget_base import PlotWidgetBase

DEFAULT_X_EXPR = "x_lin"
DEFAULT_Y_EXPR = "x_lin - x_cat"

QN_COLUMNS = [f"qnu{i + 1}" for i in range(6)] + [f"qnl{i + 1}" for i in range(6)]
X_MATCH_TOLERANCE = 1e-4

Y_PRESETS = {
    "Obs - Calc": "x_lin - x_cat",
    "Weighted Obs - Calc": "(x_lin - x_cat) / error_lin",
}


class ResidualsPlotWidget(PlotWidgetBase):
    """The residuals plot: same controls as PlotWidgetBase, plus deletion.

    Right-click a point to delete its assignment from the project's *.lin
    file (as in LLWP's residuals window), alongside the base class's Save
    Figure/Show-Hide Toolbar entries; left-drag draws a lasso to select
    several points at once, enabled by "Delete Selected".

    Embedded as a section of the "spfit" tab's toolbox, alongside the
    fitted parameters/output/residuals table.
    """

    def __init__(self, df, project, refresh_callback=None, parent=None):
        self.project = project
        self.refresh_callback = refresh_callback
        super().__init__(df, DEFAULT_X_EXPR, DEFAULT_Y_EXPR, Y_PRESETS, parent=parent)

    def _build_extra_buttons(self, buttons_row):
        self.delete_selected_button = QPushButton("Delete Selected")
        self.delete_selected_button.setEnabled(False)
        self.delete_selected_button.clicked.connect(self._delete_selected)
        buttons_row.addWidget(self.delete_selected_button)

    def _on_selection_changed(self, n_selected):
        self.delete_selected_button.setEnabled(n_selected > 0)

    # -- deleting assignments from *.lin -------------------------------------

    def _add_extra_context_menu_actions(self, menu, event):
        contains, info = self.points.contains(event)
        if not contains:
            return

        positions = list(info["ind"])
        points_df = self._plotted_df.iloc[positions]

        label = "Delete This Line from *.lin" if len(positions) == 1 else f"Delete These {len(positions)} Lines from *.lin"
        delete_action = menu.addAction(label)
        delete_action.triggered.connect(lambda: self._delete_points(points_df))

    def _delete_selected(self):
        if not self._selected_positions:
            return
        points_df = self._plotted_df.iloc[self._selected_positions]

        confirmation = QMessageBox.question(
            self, "Delete Selected Lines",
            f"Delete {len(points_df)} line(s) from the project's *.lin file?",
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        self._delete_points(points_df)
        self._clear_selection()

    def _delete_points(self, points_df):
        """Remove the *.lin rows matching these fit-dataframe points, and drop them from this plot."""
        lin_doc = self.project.get("lin") if self.project is not None else None
        if lin_doc is None:
            QMessageBox.warning(self, "No *.lin File", "This project has no open *.lin file.")
            return

        lin_df = lin_doc.data
        matched_lin_indices = set()
        for _, point in points_df.iterrows():
            mask = (lin_df[QN_COLUMNS] == point[QN_COLUMNS]).all(axis=1)
            mask &= (lin_df["x"] - point["x_lin"]).abs() < X_MATCH_TOLERANCE
            matched_lin_indices.update(lin_df.index[mask].tolist())

        if not matched_lin_indices:
            QMessageBox.information(
                self, "No Match",
                "Could not find a matching line in the current *.lin file - "
                "it may already have been edited since this fit was run.",
            )
            return

        matched_lin_indices = sorted(matched_lin_indices)

        def mutate(document):
            document.data = document.data.drop(index=matched_lin_indices).reset_index(drop=True)

        self.project.mutate(
            "lin", f"Deleted {len(matched_lin_indices)} line(s) from the residuals plot", mutate
        )

        # Drop the same points from this plot's own data so they disappear
        # immediately, without needing a fresh SPFIT run.
        self.df = self.df.drop(index=points_df.index)

        if self.refresh_callback:
            self.refresh_callback()

        self.update_plot()
