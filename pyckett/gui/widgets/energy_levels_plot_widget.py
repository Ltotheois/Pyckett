# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Energy-level plot (*.egy dataframe) - same controls as the
#                 residuals plot, no deletion (energy levels are a computed
#                 SPCAT output, not backed by an editable source file)

from pyckett.gui.widgets.plot_widget_base import PlotWidgetBase

DEFAULT_X_EXPR = "qn1"
DEFAULT_Y_EXPR = "egy"


class EnergyLevelsPlotWidget(PlotWidgetBase):
    """Scatter plot over a *.egy dataframe (iblk, indx, egy, err, pmix, we, qn1..N).

    Same x-axis/y-axis (pandas.eval), Query (pandas.query), and Color
    subsets controls as the residuals plot, plus lasso multi-select for
    visually highlighting a group of levels. There's no delete action here
    (matching LLWP's own Energy Levels window) since energy levels are a
    computed SPCAT output with no source assignments to remove.

    Embedded as a section of the "spcat" tab's toolbox.
    """

    def __init__(self, df, parent=None):
        super().__init__(df, DEFAULT_X_EXPR, DEFAULT_Y_EXPR, parent=parent)
