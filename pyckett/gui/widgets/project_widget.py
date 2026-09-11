# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : One project's inner tab strip (open files + Actions tab), with drag-and-drop

import pyckett
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QTabBar, QTabWidget, QVBoxLayout, QWidget

from pyckett.gui.fit_parsing import parse_fit_df
from pyckett.gui.project import VERSIONED_KINDS, Document
from pyckett.gui.widgets.add_parameter_tab import AddParameterTabWidget
from pyckett.gui.widgets.empty_file_tab import EmptyFileTabWidget
from pyckett.gui.widgets.energy_levels_plot_widget import EnergyLevelsPlotWidget
from pyckett.gui.widgets.int_tab import IntTabWidget
from pyckett.gui.widgets.lin_tab import LinTabWidget
from pyckett.gui.widgets.omit_parameter_tab import OmitParameterTabWidget
from pyckett.gui.widgets.par_tab import ParTabWidget
from pyckett.gui.widgets.partition_function_widget import PartitionFunctionWidget
from pyckett.gui.widgets.predictions_plot_widget import PredictionsPlotWidget
from pyckett.gui.widgets.residuals_plot_widget import ResidualsPlotWidget
from pyckett.gui.widgets.spcat_tab import SpcatTabWidget
from pyckett.gui.widgets.spfit_tab import SpfitTabWidget
from pyckett.gui.widgets.text_tab import TextTabWidget
from pyckett.gui.workers import FunctionWorker

# Kinds that always get a tab, even with no file loaded yet - these are the
# three files every fit needs, so it should always be obvious how to load one.
ALWAYS_PRESENT_KINDS = ("par", "lin", "int")

# Kinds/labels absorbed into the "spfit"/"spcat" composite tabs instead of
# getting their own top-level tab. "fit"/"out" are always the SPFIT/SPCAT
# result documents (never loaded from disk - see project.TEXT_LIKE_KINDS'
# docstring), so kind alone identifies them; the informational fallback
# message from _copy_par_to_var reuses the "SPFIT Output" label but keeps
# kind "text" (it isn't a real output file - Save All must skip it), so it
# still needs the label check.
ABSORBED_KINDS = ("var", "cat", "egy", "fit", "out")
ABSORBED_TEXT_LABELS = ("SPFIT Output",)

SPFIT_KEY = ("spfit", None)
SPCAT_KEY = ("spcat", None)
ADD_KEY = ("add", None)
OMIT_KEY = ("omit", None)

# Kinds "Save All" (menu) writes, in addition to ALWAYS_PRESENT_KINDS: every
# other real, on-disk-shaped result the app produces. The informational
# "text" kind is deliberately excluded - it has no real file behind it (see
# ABSORBED_TEXT_LABELS above).
SAVE_ALL_KINDS = ALWAYS_PRESENT_KINDS + ("var", "cat", "egy", "fit", "out")

FILE_FILTERS = {
    "par": "Parameter Files (*.par)",
    "var": "Variable Files (*.var)",
    "lin": "Line Files (*.lin)",
    "int": "Intensity Files (*.int)",
    "cat": "Catalog Files (*.cat)",
    "egy": "Energy Files (*.egy)",
    "fit": "Fit Files (*.fit)",
    "out": "Output Files (*.out)",
}


def short_tab_tag(document):
    """A tab tag named after the file extension, or a short tag for other text."""
    if document.kind != "text":
        return document.kind
    if document.path is not None and document.path.suffix:
        return document.path.suffix.lstrip(".")
    return document.label[:6]


class ProjectWidget(QWidget):
    """The inner tab strip for one Project: one tab per open Document, plus Add/Omit.

    Tabs are labeled with a short tag (the file extension, e.g. "par"/"lin")
    rather than the full filename, to keep the strip compact; the full name
    (with a trailing "*" while unsaved) is available as the tab's tooltip.
    """

    new_project_requested = pyqtSignal(object)
    title_changed = pyqtSignal()
    status_message = pyqtSignal(str)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setAcceptDrops(True)
        self._workers = []
        # Popped-out plot windows (residuals/energy-levels/predictions),
        # keyed by a short name - see _open_plot_window. Kept here (rather
        # than on the spfit/spcat tab widgets, which are torn down and
        # rebuilt on every run) so an open plot window survives a re-run
        # instead of getting closed out from under the user.
        self._plot_windows = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        layout.addWidget(self.tabs)

        self.add_widget = AddParameterTabWidget(self.project, self.sync_tabs)
        self.add_widget.new_project_requested.connect(self.new_project_requested)
        self.add_widget._tab_key = ADD_KEY

        self.omit_widget = OmitParameterTabWidget(self.project, self.sync_tabs)
        self.omit_widget.new_project_requested.connect(self.new_project_requested)
        self.omit_widget._tab_key = OMIT_KEY

        self.sync_tabs()

    # -- drag and drop --------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.load_file(path)
        event.acceptProposedAction()

    def open_files_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Open Files")
        for path in paths:
            self.load_file(path)

    def load_file(self, path):
        try:
            document = Document.load(path)
        except Exception as exc:
            QMessageBox.critical(self, "Failed to Load File", f"{path}:\n{exc}")
            return

        self.project.add_document(document)
        if document.kind in VERSIONED_KINDS:
            self.project.snapshot(f"Loaded {document.label}")
        self.sync_tabs()
        self.title_changed.emit()

    # -- saving -------------------------------------------------------------

    def save(self):
        """Save this project's *.par/*.lin/*.int files to their current paths (or ask for one).

        Unconditional - writes all three regardless of whether they have
        unsaved changes, since "does this need saving?" is a harder question
        for a user to answer than "did I just save?".
        """
        self._save_documents(d for d in self.project.documents if d.kind in ALWAYS_PRESENT_KINDS)

    def save_all(self):
        """Save every par/var/lin/int/cat/egy/fit/out document to disk, unconditionally."""
        self._save_documents(d for d in self.project.documents if d.kind in SAVE_ALL_KINDS)

    def _save_documents(self, documents):
        documents = list(documents)
        if not documents:
            self.status_message.emit("Nothing to save.")
            return

        saved_labels = []
        for document in documents:
            path = document.path
            if path is None:
                chosen, _ = QFileDialog.getSaveFileName(
                    self, f"Save {document.label}", "", FILE_FILTERS.get(document.kind, "All Files (*)")
                )
                if not chosen:
                    continue
                path = chosen

            try:
                self.project.save_document(document, path)
            except Exception as exc:
                QMessageBox.critical(self, "Save Failed", f"Could not save {document.label}:\n{exc}")
                continue
            saved_labels.append(document.label)

        if saved_labels:
            self.status_message.emit(f"Saved {', '.join(saved_labels)}.")
            self.sync_tabs()

    # -- plot windows ---------------------------------------------------

    def _open_plot_window(self, key, title, build_widget, df):
        """Show a plot in its own top-level, freely resizable window.

        A QToolBox section can't be resized independently of the tab it
        lives in, which makes it a poor fit for a plot the user actually
        wants to size up and work with. If a window for ``key`` is already
        open, it's just refreshed in place (new data, but the user's
        current zoom/query/size/position are kept) and raised, rather than
        spawning a duplicate; otherwise ``build_widget()`` is called to
        construct a fresh one.
        """
        existing = self._plot_windows.get(key)
        if existing is not None:
            existing.set_dataframe(df)
            existing.raise_()
            existing.activateWindow()
            return existing

        widget = build_widget()
        widget.setParent(self, Qt.WindowType.Window)
        widget.setWindowTitle(f"{self.project.name} – {title}")
        widget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        widget.resize(900, 650)
        widget.destroyed.connect(lambda: self._plot_windows.pop(key, None))
        self._plot_windows[key] = widget
        widget.show()
        widget.raise_()
        widget.activateWindow()
        return widget

    def _refresh_plot_window_if_open(self, key, df):
        """Push fresh data into an already-open plot window after a new run.

        Never opens a window itself - if the user hasn't opened this plot,
        a fresh SPFIT/SPCAT run shouldn't pop one open on their behalf.
        """
        existing = self._plot_windows.get(key)
        if existing is not None:
            existing.set_dataframe(df)

    def open_residuals_plot(self, df):
        return self._open_plot_window(
            "residuals", "Residuals Plot",
            lambda: ResidualsPlotWidget(df, self.project, self.refresh_tab_titles),
            df,
        )

    def open_predictions_plot(self, df):
        return self._open_plot_window(
            "predictions", "Predictions Plot", lambda: PredictionsPlotWidget(df), df,
        )

    def open_energy_levels_plot(self, df):
        return self._open_plot_window(
            "energy_levels", "Energy Levels Plot", lambda: EnergyLevelsPlotWidget(df), df,
        )

    def open_partition_function(self, df):
        return self._open_plot_window(
            "partition_function", "Partition Function", lambda: PartitionFunctionWidget(df, self.project), df,
        )

    # -- SPFIT / SPCAT (virtual) -------------------------------------------

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
        self.status_message.emit("Action failed.")
        QMessageBox.critical(self, "Action Failed", message)

    def run_spfit(self):
        par_doc = self.project.get("par")
        lin_doc = self.project.get("lin")
        if par_doc is None or lin_doc is None:
            QMessageBox.warning(self, "Missing Files", "Running SPFIT needs an open *.par and *.lin file.")
            return

        if len(lin_doc.data) == 0:
            # SPFIT has nothing to fit against an empty *.lin and won't run
            # through at all - copying *.par straight to *.var instead still
            # lets SPCAT predict from the starting parameters before any
            # assignments exist.
            QMessageBox.warning(
                self, "No Assignments Yet",
                "The *.lin file has no assignments yet, so SPFIT can't fit anything.\n\n"
                "The *.par file will be copied directly to *.var instead, so you can "
                "still run SPCAT to see predictions from your starting parameters.",
            )
            self._copy_par_to_var(par_doc)
            return

        self.status_message.emit("Running SPFIT…")
        self._run_worker(
            pyckett.run_spfit_v, par_doc.copy_data(), lin_doc.copy_data(), on_done=self._on_spfit_done
        )

    def _copy_par_to_var(self, par_doc):
        self.project.add_document(Document("var", par_doc.copy_data(), label="var.var", dirty=False))
        self.project.add_document(
            Document(
                "text",
                "*.lin was empty, so SPFIT was not run - *.par was copied directly to *.var instead.",
                label="SPFIT Output", dirty=False,
            )
        )
        self.status_message.emit("Copied *.par to *.var (no assignments to fit yet).")
        self.sync_tabs()

    def _on_spfit_done(self, result):
        self.status_message.emit("SPFIT run complete.")

        if "var" in result:
            self.project.add_document(Document("var", result["var"], label="var.var", dirty=False))
        if result.get("msg"):
            self.project.add_document(Document("out", result["msg"], label="SPFIT Output", dirty=False))
        if result.get("fit"):
            self.project.add_document(
                Document("fit", result["fit"], label="SPFIT Residuals (.fit)", dirty=False)
            )
            try:
                self._refresh_plot_window_if_open("residuals", parse_fit_df(result["fit"]))
            except Exception:
                pass  # an already-open window just keeps showing its last-good data

        # Promote the fit results into the working *.par so the next
        # iteration (further edits, another SPFIT run, add/omit-parameter
        # testing) starts from the newly fitted values. This must come from
        # SPFIT's updated *.par output, not *.var: the third PARAMS column
        # means different things in each file - in *.par it is the allowed
        # change per fit iteration, in *.var it is the fitted uncertainty.
        # Copying *.var's column into *.par would silently turn every
        # parameter's step-size limit into its uncertainty.
        par_doc = self.project.get("par")
        if par_doc is not None and "par" in result:
            new_params = result["par"]["PARAMS"]

            def mutate(document):
                document.data["PARAMS"] = new_params

            self.project.mutate("par", "Updated with SPFIT fit results", mutate)

        self.sync_tabs()

    def run_spcat(self):
        var_doc = self.project.get("var")
        int_doc = self.project.get("int")
        if var_doc is None or int_doc is None:
            QMessageBox.warning(
                self, "Missing Files",
                "SPCAT needs a fitted *.var (run SPFIT first) and an open *.int file.",
            )
            return
        self.status_message.emit("Running SPCAT…")
        self._run_worker(
            pyckett.run_spcat_v, var_doc.copy_data(), int_doc.copy_data(), on_done=self._on_spcat_done
        )

    def _on_spcat_done(self, result):
        self.status_message.emit("SPCAT run complete.")
        if result.get("cat") is not None:
            self.project.add_document(Document("cat", result["cat"], label="var.cat", dirty=False))
            self._refresh_plot_window_if_open("predictions", result["cat"])
        if result.get("egy") is not None:
            self.project.add_document(Document("egy", result["egy"], label="var.egy", dirty=False))
            self._refresh_plot_window_if_open("energy_levels", result["egy"])
            self._refresh_plot_window_if_open("partition_function", result["egy"])
        if result.get("msg"):
            self.project.add_document(Document("out", result["msg"], label="SPCAT Output", dirty=False))
        self.sync_tabs()

    # -- tab management ---------------------------------------------------

    def _build_tab_widget(self, document):
        if document.kind == "par":
            return ParTabWidget(
                self.project, document, read_only=False,
                run_action=("Run SPFIT", self.run_spfit),
            )
        if document.kind == "lin":
            return LinTabWidget(self.project, document)
        if document.kind == "int":
            return IntTabWidget(self.project, document)
        return TextTabWidget(document)

    def _tab_label(self, document):
        return f"{short_tab_tag(document)}{'*' if document.dirty else ''}"

    def _load_file_for_kind(self, kind):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Load *.{kind} File", "", FILE_FILTERS.get(kind, "All Files (*)")
        )
        if path:
            self.load_file(path)

    def _make_empty_tab_widget(self, kind):
        widget = EmptyFileTabWidget(kind)
        widget._tab_key = (kind, None)
        widget.load_requested.connect(lambda: self._load_file_for_kind(kind))
        return widget

    def _add_document_tab(self, document):
        widget = self._build_tab_widget(document)
        widget._tab_key = (document.kind, document.label)
        if hasattr(widget, "changed"):
            widget.changed.connect(lambda w=widget: self._on_document_changed(w))
        index = self.tabs.addTab(widget, self._tab_label(document))
        self.tabs.setTabToolTip(index, document.display_title)
        return widget

    def _on_document_changed(self, widget):
        self._refresh_tab_title(widget)
        # Editing *.par's PARAMS or *.lin's row count can change *.par's
        # auto-managed NPAR/NLINE (Project.sync_par_fields); reflect that on
        # *.par's own tab too, without a full sync_tabs() rebuild - unless
        # NVIB itself changed enough to replace PARAMS/IDIP ids or *.lin's
        # data outright (vib_state_encoding_changed), in which case whatever
        # tab(s) are open would otherwise keep showing stale data, so a full
        # rebuild is needed instead.
        if widget.document.kind in ("par", "lin") and self.project.sync_par_fields():
            if self.project.vib_state_encoding_changed:
                self.project.vib_state_encoding_changed = False
                self.sync_tabs()
                self._drain_project_warnings()
                return

            par_doc = self.project.get("par")
            for index in range(self.tabs.count()):
                other = self.tabs.widget(index)
                if getattr(other, "document", None) is par_doc:
                    self.tabs.setTabText(index, self._tab_label(par_doc))
                    self.tabs.setTabToolTip(index, par_doc.display_title)
                    break

    def _drain_project_warnings(self):
        warnings = self.project.pending_warnings
        if warnings:
            QMessageBox.warning(self, "Heads Up", "\n\n".join(warnings))
            self.project.pending_warnings = []

    def _add_fixed_tab(self, widget, key, label, current_key, select_index):
        """Add a non-closable, non-file tab (spfit/spcat/add/omit) and track selection."""
        widget._tab_key = key
        index = self.tabs.addTab(widget, label)
        self.tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, None)
        return index if key == current_key else select_index

    def sync_tabs(self):
        """Rebuild every tab from the project's current state.

        Called after any structural change (files loaded, an action applied,
        history restored) - not on routine edits, which just update a tab's
        title/tooltip in place via ``_refresh_tab_title``. *.par/*.lin/*.int
        always get a tab, showing a "load a file" placeholder when the
        project doesn't have one open yet. *.var/*.cat/*.egy and the SPFIT/
        SPCAT output text don't get their own tabs - they're shown inside
        the "spfit"/"spcat" tabs alongside the button to (re)run them.
        """
        current_widget = self.tabs.currentWidget()
        current_key = getattr(current_widget, "_tab_key", None)

        while self.tabs.count():
            self.tabs.removeTab(0)

        documents_by_kind = {
            document.kind: document
            for document in self.project.documents
            if document.kind in ALWAYS_PRESENT_KINDS
        }
        other_documents = [
            d for d in self.project.documents
            if d.kind not in ALWAYS_PRESENT_KINDS
            and d.kind not in ABSORBED_KINDS
            and not (d.kind == "text" and d.label in ABSORBED_TEXT_LABELS)
        ]

        select_index = 0
        for kind in ALWAYS_PRESENT_KINDS:
            document = documents_by_kind.get(kind)
            if document is not None:
                widget = self._add_document_tab(document)
            else:
                widget = self._make_empty_tab_widget(kind)
                index = self.tabs.addTab(widget, kind)
                self.tabs.setTabToolTip(index, f"No *.{kind} file loaded")
            # *.par/*.lin/*.int are essential - never let them be closed, whether
            # loaded or still showing the empty-state placeholder.
            self.tabs.tabBar().setTabButton(
                self.tabs.count() - 1, QTabBar.ButtonPosition.RightSide, None
            )
            if widget._tab_key == current_key:
                select_index = self.tabs.count() - 1

        select_index = self._add_fixed_tab(
            SpfitTabWidget(
                self.project, self.run_spfit, self.refresh_tab_titles,
                open_residuals_plot_callback=self.open_residuals_plot,
            ),
            SPFIT_KEY, "spfit", current_key, select_index,
        )
        select_index = self._add_fixed_tab(
            SpcatTabWidget(
                self.project, self.run_spcat,
                open_predictions_plot_callback=self.open_predictions_plot,
                open_energy_levels_plot_callback=self.open_energy_levels_plot,
                open_partition_function_callback=self.open_partition_function,
            ),
            SPCAT_KEY, "spcat", current_key, select_index,
        )

        for document in sorted(other_documents, key=lambda d: (d.kind, d.label)):
            widget = self._add_document_tab(document)
            if widget._tab_key == current_key:
                select_index = self.tabs.count() - 1

        select_index = self._add_fixed_tab(self.add_widget, ADD_KEY, "add", current_key, select_index)
        select_index = self._add_fixed_tab(self.omit_widget, OMIT_KEY, "omit", current_key, select_index)

        self.tabs.setCurrentIndex(select_index)
        self.title_changed.emit()
        self.project.vib_state_encoding_changed = False
        self._drain_project_warnings()

    def _refresh_tab_title(self, widget):
        index = self.tabs.indexOf(widget)
        if index != -1:
            document = widget.document
            self.tabs.setTabText(index, self._tab_label(document))
            self.tabs.setTabToolTip(index, document.display_title)
        self.title_changed.emit()

    def refresh_tab_titles(self):
        """Refresh every open tab's title/tooltip from its document's dirty state.

        Unlike sync_tabs(), this never tears down or rebuilds any widget -
        used after a mutation made from outside the normal per-tab edit path
        (deleting a line from the residuals plot mutates *.lin directly, but
        rebuilding the whole "spfit" tab over that would blow away whatever
        the user was doing in the plot).
        """
        for index in range(self.tabs.count()):
            document = getattr(self.tabs.widget(index), "document", None)
            if document is not None:
                self.tabs.setTabText(index, self._tab_label(document))
                self.tabs.setTabToolTip(index, document.display_title)
        self.title_changed.emit()

    def _close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget in (self.add_widget, self.omit_widget):
            return

        document = getattr(widget, "document", None)
        if document is not None:
            if document.dirty:
                confirmation = QMessageBox.question(
                    self, "Unsaved Changes", f"Discard unsaved changes to {document.label}?"
                )
                if confirmation != QMessageBox.StandardButton.Yes:
                    return
            self.project.remove_document(document)
        self.sync_tabs()

    @property
    def has_unsaved_changes(self):
        return self.project.has_unsaved_changes
