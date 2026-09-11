# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Shared LLWP-style scatter-plot core (x/y via pandas.eval,
#                 filtering via pandas.query, subset coloring via simple
#                 commands, lasso multi-select) for the residuals and
#                 energy-level plots

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvas, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.path import Path as MplPath
from matplotlib.widgets import LassoSelector
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMenu, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from pyckett.gui.theme import is_dark_theme

DEFAULT_COLOR = "tab:blue"
SELECTION_COLOR = "gold"


class PlotWidgetBase(QWidget):
    """A scatter plot over a dataframe with LLWP-style controls.

    x-axis/y-axis are pandas.eval expressions over the dataframe's columns;
    Query is a pandas.query filter for which rows are plotted at all; Color
    subsets take one "color; query" command per line (e.g. "red; qn1 < 20")
    to color matching points differently, applied in order so later lines
    can override earlier ones. Left-drag draws a lasso to highlight several
    points at once.

    Subclasses add anything that acts on a selection/click (e.g. deleting
    the underlying data a point came from) via the ``_build_extra_buttons``/
    ``_on_selection_changed`` hooks and their own canvas event handlers -
    this base has no notion of an editable source, since not every plotted
    dataframe (e.g. *.egy energy levels) maps back to one.

    Right-clicking the canvas always opens a context menu with "Save
    Figure…" and "Show/Hide Toolbar"; subclasses prepend their own
    point-specific actions (e.g. "Delete This Line from *.lin") via the
    ``_add_extra_context_menu_actions`` hook.

    A subclass that isn't point-based (e.g. a stick spectrum, drawn as
    vertical lines rather than dots) sets ``SUPPORTS_LASSO = False`` and
    overrides ``_setup_artists``/``_render``/``_y_axis_limits`` instead of
    using the default scatter + lasso-select machinery.
    """

    SUPPORTS_LASSO = True

    def __init__(self, df, default_x_expr, default_y_expr, y_presets=None, parent=None):
        super().__init__(parent)
        self.df = df
        self.default_x_expr = default_x_expr
        self.default_y_expr = default_y_expr
        self.y_presets = y_presets or {}
        self._plotted_df = df.iloc[0:0]
        self._selected_positions = []

        layout = QVBoxLayout(self)

        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        # Matplotlib's own alpha=0 patch isn't enough on its own - the Qt
        # widget underneath still paints an opaque (usually white) fill,
        # which is exactly what shows a white box instead of the app's
        # actual theme, especially in dark mode.
        self.canvas.setStyleSheet("background-color: transparent;")
        self.ax = self.fig.add_subplot(111)
        self.selection_ring = None
        self._setup_artists()
        self._apply_theme()
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.lasso = LassoSelector(self.ax, self._on_lasso_select, button=[1]) if self.SUPPORTS_LASSO else None

        self.canvas.mpl_connect("button_press_event", self._on_canvas_right_click)

        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.toolbar)

        axes_row = QHBoxLayout()
        axes_row.addWidget(QLabel("x-axis:"))
        self.x_field = QLineEdit(default_x_expr)
        self.x_field.setPlaceholderText(f"pandas expression, e.g. {default_x_expr}")
        axes_row.addWidget(self.x_field)
        axes_row.addWidget(QLabel("y-axis:"))
        self.y_field = QLineEdit(default_y_expr)
        self.y_field.setPlaceholderText(f"pandas expression, e.g. {default_y_expr}")
        if self.y_presets:
            self.y_field.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.y_field.customContextMenuRequested.connect(self._show_y_presets_menu)
        axes_row.addWidget(self.y_field)
        layout.addLayout(axes_row)

        query_row = QHBoxLayout()
        query_row.addWidget(QLabel("Query:"))
        self.query_field = QLineEdit()
        self.query_field.setPlaceholderText("pandas query to filter shown points, e.g. weight > 0")
        query_row.addWidget(self.query_field)
        layout.addLayout(query_row)

        layout.addWidget(QLabel("Color subsets (one 'color; query' per line, e.g. red; qn1 < 20):"))
        self.color_field = QPlainTextEdit()
        self.color_field.setMaximumHeight(70)
        self.color_field.setPlaceholderText("red; qn1 < 20\nblue; we == 0")
        layout.addWidget(self.color_field)

        buttons_row = QHBoxLayout()
        self.status_label = QLabel("")
        buttons_row.addWidget(self.status_label, 1)
        self._build_extra_buttons(buttons_row)
        update_button = QPushButton("Update")
        update_button.clicked.connect(self.update_plot)
        buttons_row.addWidget(update_button)
        layout.addLayout(buttons_row)

        self.update_plot()

    def _build_extra_buttons(self, buttons_row):
        """Hook: subclasses add buttons here, before "Update"."""

    def _on_selection_changed(self, n_selected):
        """Hook: subclasses react to the lasso selection changing (e.g. enable a button)."""

    def _setup_artists(self):
        """Hook: create ``self.points`` (and ``self.selection_ring`` if SUPPORTS_LASSO)."""
        self.points = self.ax.scatter([], [], marker=".", picker=True, pickradius=5)
        if self.SUPPORTS_LASSO:
            self.selection_ring = self.ax.scatter(
                [], [], marker="o", facecolors="none", edgecolors=SELECTION_COLOR, linewidths=1.5, zorder=3
            )

    def _render(self, xs, ys, colors):
        """Hook: push (xs, ys, colors) into ``self.points``."""
        offsets = np.column_stack([xs, ys]) if len(xs) else np.empty((0, 2))
        self.points.set_offsets(offsets)
        self.points.set_color(list(colors))

    def _y_axis_limits(self, ys):
        """Hook: (ymin, ymax) to autoscale to, given the plotted y-values."""
        ymin, ymax = float(np.min(ys)), float(np.max(ys))
        if ymin == ymax:
            ymin -= 1
            ymax += 1
        ypad = (ymax - ymin) * 0.05 or 1
        return ymin - ypad, ymax + ypad

    def set_dataframe(self, df):
        """Point this widget at a fresh dataframe, e.g. after a new run."""
        self.df = df
        self._clear_selection()
        self.update_plot()

    def _apply_theme(self):
        """Match the figure to the current light/dark Qt theme (see LLWP's PlotWidget).

        The figure/axes background is made transparent so the surrounding,
        already theme-aware Qt widget shows through, and text/spines/ticks
        are set to a color that stays readable against it. Applied once at
        construction - these widgets are rebuilt fresh on every run anyway,
        so they always pick up whatever theme is current then.
        """
        text_color = "white" if is_dark_theme() else "black"

        self.fig.patch.set_alpha(0)
        self.ax.set_facecolor("none")

        for spine in self.ax.spines.values():
            spine.set_color(text_color)
        self.ax.tick_params(colors=text_color)
        self.ax.xaxis.label.set_color(text_color)
        self.ax.yaxis.label.set_color(text_color)
        self.ax.title.set_color(text_color)

    def _on_canvas_right_click(self, event):
        if event.button != 3 or event.inaxes != self.ax:
            return

        menu = QMenu(self)
        self._add_extra_context_menu_actions(menu, event)
        if not menu.isEmpty():
            menu.addSeparator()

        save_action = menu.addAction("Save Figure…")
        save_action.triggered.connect(self.toolbar.save_figure)

        toolbar_action = menu.addAction("Show Toolbar" if self.toolbar.isHidden() else "Hide Toolbar")
        toolbar_action.triggered.connect(lambda: self.toolbar.setVisible(self.toolbar.isHidden()))

        menu.exec(QCursor.pos())

    def _add_extra_context_menu_actions(self, menu, event):
        """Hook: subclasses add point-specific actions (e.g. delete) before the generic Save/Toolbar ones."""

    def _show_y_presets_menu(self, pos):
        menu = QMenu(self)
        for label, expr in self.y_presets.items():
            action = menu.addAction(label)
            action.triggered.connect(lambda checked=False, e=expr: self.y_field.setText(e))
        menu.exec(self.y_field.mapToGlobal(pos))

    def _set_status(self, text, is_error=False):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: #c0392b;" if is_error else "")

    def update_plot(self):
        try:
            df = self.df
            query = self.query_field.text().strip()
            if query:
                df = df.query(query)
            df = df.copy()

            df["_color"] = DEFAULT_COLOR
            for line in self.color_field.toPlainText().splitlines():
                line = line.strip()
                if not line or ";" not in line:
                    continue
                color, subset_query = line.split(";", 1)
                indices = df.query(subset_query.strip()).index
                df.loc[indices, "_color"] = color.strip()

            x_expr = self.x_field.text().strip() or self.default_x_expr
            y_expr = self.y_field.text().strip() or self.default_y_expr
            xs = df.eval(x_expr).to_numpy(dtype=float)
            ys = df.eval(y_expr).to_numpy(dtype=float)
            colors = df["_color"].to_numpy()
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            return

        self._plotted_df = df
        self._clear_selection(redraw=False)

        self._render(xs, ys, colors)
        self.ax.set_xlabel(x_expr)
        self.ax.set_ylabel(y_expr)

        if len(xs):
            xmin, xmax = float(np.min(xs)), float(np.max(xs))
            xpad = (xmax - xmin) * 0.05 or 1
            self.ax.set_xlim(xmin - xpad, xmax + xpad)
            self.ax.set_ylim(*self._y_axis_limits(ys))

        self._set_status(f"{len(df)} point(s) shown.")
        self.canvas.draw_idle()

    # -- selection ----------------------------------------------------------

    def _on_lasso_select(self, verts):
        offsets = self.points.get_offsets()
        if len(offsets) == 0:
            return
        path = MplPath(verts)
        inside = path.contains_points(offsets)
        self._selected_positions = list(np.nonzero(inside)[0])
        self._refresh_selection_display()

    def _clear_selection(self, redraw=True):
        self._selected_positions = []
        if redraw:
            self._refresh_selection_display()

    def _refresh_selection_display(self):
        if self.selection_ring is None:
            return
        offsets = self.points.get_offsets()
        if self._selected_positions and len(offsets):
            self.selection_ring.set_offsets(offsets[self._selected_positions])
        else:
            self.selection_ring.set_offsets(np.empty((0, 2)))

        n = len(self._selected_positions)
        self._on_selection_changed(n)
        if n > 0:
            self._set_status(f"{n} point(s) selected.")
        self.canvas.draw_idle()
