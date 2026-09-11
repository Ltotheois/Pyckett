# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Stick-spectrum plot of the current *.cat predictions

import numpy as np
from matplotlib.collections import LineCollection

from pyckett.gui.widgets.plot_widget_base import DEFAULT_COLOR, PlotWidgetBase

DEFAULT_X_EXPR = "x"
DEFAULT_Y_EXPR = "y"


class PredictionsPlotWidget(PlotWidgetBase):
    """A stick spectrum of the current *.cat predictions: frequency vs intensity.

    Same Query/Color subsets controls as the other plots (x-axis/y-axis
    default to the predicted frequency and intensity, but are still
    pandas.eval expressions like everywhere else); drawn as vertical lines
    from a zero baseline rather than a scatter of dots, so there's no lasso
    multi-select here - a single "point" isn't a meaningful unit to select
    on a stick spectrum the way it is for residuals/energy levels.

    Embedded as a section of the "spcat" tab's toolbox.
    """

    SUPPORTS_LASSO = False

    def __init__(self, df, parent=None):
        super().__init__(df, DEFAULT_X_EXPR, DEFAULT_Y_EXPR, parent=parent)

    def _setup_artists(self):
        self.points = LineCollection([], linewidths=1)
        self.ax.add_collection(self.points)

    def _render(self, xs, ys, colors):
        segments = [[(x, 0.0), (x, y)] for x, y in zip(xs, ys)]
        self.points.set_segments(segments)
        self.points.set_color(list(colors) if len(colors) else [DEFAULT_COLOR])

    def _y_axis_limits(self, ys):
        ymax = float(np.max(ys))
        return 0.0, (ymax * 1.05 or 1.0)
