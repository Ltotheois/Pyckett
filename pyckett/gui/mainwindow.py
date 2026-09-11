# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Main window - outer tab strip of open projects, menu, drag-and-drop

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QKeySequence
from PyQt6.QtWidgets import QDialog, QInputDialog, QMainWindow, QMessageBox, QTabWidget

from pyckett.gui import molecule_templates
from pyckett.gui.icon import load_app_icon
from pyckett.gui.parameter_lookup import ROTATIONAL_DICTS, default_kind, set_parameter_comments
from pyckett.gui.project import Document, Project
from pyckett.gui.rename_states import apply_state_rename
from pyckett.gui.widgets.history_dialog import HistoryDialog
from pyckett.gui.widgets.project_widget import ProjectWidget
from pyckett.gui.widgets.rename_states_dialog import RenameStatesDialog
from pyckett.gui.widgets.report_dialog import ReportDialog
from pyckett.gui.widgets.vib_partition_function_dialog import VibPartitionFunctionDialog

SPIN_URL = "https://spin.astro.uni-koeln.de/"
PYCKETT_URL = "https://github.com/Ltotheois/Pyckett/"

_MOLECULE_KINDS = {
    "Linear Molecule…": ("Linear Molecule", lambda: molecule_templates.linear_par()),
    "Symmetric Top Molecule…": ("Symmetric Top Molecule", lambda: molecule_templates.symmetric_top_par()),
    "Asymmetric Top (A-Reduction)…": (
        "Asymmetric Top (A-Reduction)", lambda: molecule_templates.asymmetric_top_par("a_reduction")
    ),
    "Asymmetric Top (S-Reduction)…": (
        "Asymmetric Top (S-Reduction)", lambda: molecule_templates.asymmetric_top_par("s_reduction")
    ),
}


class MainWindow(QMainWindow):
    """Top-level window: an outer tab strip where each tab is one open Project."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pyckett")
        self.setWindowIcon(load_app_icon())
        self.resize(1150, 780)
        self.setAcceptDrops(True)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_project_tab)
        self.tabs.tabBarDoubleClicked.connect(self._rename_project_tab)
        self.setCentralWidget(self.tabs)

        self._build_menu()
        self.statusBar().showMessage("Drag *.par/*.lin/*.int files onto the window to open them.")

        self.new_project()

    def _build_menu(self):
        menu = self.menuBar().addMenu("&File")
        self._add_action(menu, "New Project", self.new_project, "Ctrl+N")
        self._add_action(menu, "Open Files…", self._open_files, "Ctrl+O")
        menu.addSeparator()
        self._add_action(menu, "Save", self._save, "Ctrl+S")
        self._add_action(menu, "Save All", self._save_all, "Ctrl+Shift+S")
        menu.addSeparator()
        self._add_action(menu, "History…", self._show_history, "Ctrl+H")
        menu.addSeparator()
        self._add_action(menu, "Close Project", self._close_current_project, "Ctrl+W")

        molecule_menu = self.menuBar().addMenu("&New Molecule")
        self._add_action(
            molecule_menu, "Linear Molecule…", lambda: self._new_molecule("Linear Molecule…")
        )
        self._add_action(
            molecule_menu, "Symmetric Top Molecule…", lambda: self._new_molecule("Symmetric Top Molecule…")
        )
        molecule_menu.addSeparator()
        self._add_action(
            molecule_menu, "Asymmetric Top (A-Reduction)…",
            lambda: self._new_molecule("Asymmetric Top (A-Reduction)…"),
        )
        self._add_action(
            molecule_menu, "Asymmetric Top (S-Reduction)…",
            lambda: self._new_molecule("Asymmetric Top (S-Reduction)…"),
        )

        tools_menu = self.menuBar().addMenu("&Tools")
        self._add_action(tools_menu, "Rename States…", self._rename_states)
        self._add_action(tools_menu, "Set Parameter Comments…", self._set_parameter_comments)
        tools_menu.addSeparator()
        self._add_action(tools_menu, "Create Report…", self._create_report)
        self._add_action(tools_menu, "Vibrational Partition Function…", self._vibrational_partition_function)

        info_menu = self.menuBar().addMenu("&Info")
        self._add_action(info_menu, "Open SPIN Website", lambda: self._open_url(SPIN_URL))
        self._add_action(info_menu, "Pyckett on GitHub…", lambda: self._open_url(PYCKETT_URL))

    def _add_action(self, menu, text, slot, shortcut=None):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    # -- project management ----------------------------------------------

    def new_project(self, name=None):
        project = Project(name=name or f"Project {self.tabs.count() + 1}")
        return self._add_project_widget(project)

    def _new_molecule(self, kind_key):
        """Create a new project prefilled with a starting *.par/*.lin/*.int for a molecule type.

        Linear/Symmetric Top use real reference values (OCS/CH3CN, from
        https://spin.astro.uni-koeln.de/chapter/LinearMoleculeInPickett/) so
        they're a genuinely working starting point, not just plausible in
        shape; Asymmetric Top's rotational constants, QROT, and frequency
        limits are still placeholders (right parameters, right sign
        conventions, not real numbers for any actual molecule). *.int's
        QROT/frequency limits are always placeholders regardless of type.
        """
        project_name, build_par = _MOLECULE_KINDS[kind_key]
        project_widget = self.new_project(name=project_name)
        project = project_widget.project

        project.add_document(Document("par", build_par(), label="new.par", dirty=True))
        project.add_document(Document("lin", molecule_templates.empty_lin(), label="new.lin", dirty=True))
        project.add_document(Document("int", molecule_templates.default_int(), label="new.int", dirty=True))
        project.snapshot("Created from template")

        project_widget.sync_tabs()
        self.statusBar().showMessage(
            "Created a starting template - review the rotational constants, QROT, "
            "and frequency limits before running SPCAT.",
            8000,
        )

    def _add_project_widget(self, project):
        widget = ProjectWidget(project)
        widget.new_project_requested.connect(self._add_project_widget)
        widget.title_changed.connect(lambda w=widget: self._refresh_project_tab_title(w))
        widget.status_message.connect(self.statusBar().showMessage)
        index = self.tabs.addTab(widget, project.name)
        self.tabs.setCurrentIndex(index)
        return widget

    def _refresh_project_tab_title(self, widget):
        index = self.tabs.indexOf(widget)
        if index != -1:
            marker = "*" if widget.has_unsaved_changes else ""
            self.tabs.setTabText(index, f"{widget.project.name}{marker}")

    def _rename_project_tab(self, index):
        widget = self.tabs.widget(index)
        if widget is None:
            return
        name, accepted = QInputDialog.getText(self, "Rename Project", "Name:", text=widget.project.name)
        if accepted and name.strip():
            widget.project.name = name.strip()
            self._refresh_project_tab_title(widget)

    def _current_project_widget(self):
        return self.tabs.currentWidget()

    # -- menu actions -------------------------------------------------------

    def _open_files(self):
        widget = self._current_project_widget() or self.new_project()
        widget.open_files_dialog()

    def _save(self):
        project_widget = self._current_project_widget()
        if project_widget is not None:
            project_widget.save()

    def _save_all(self):
        project_widget = self._current_project_widget()
        if project_widget is not None:
            project_widget.save_all()

    def _show_history(self):
        project_widget = self._current_project_widget()
        if project_widget is None:
            return
        dialog = HistoryDialog(project_widget.project, self)
        dialog.restored.connect(lambda kinds: project_widget.sync_tabs())
        dialog.exec()

    def _rename_states(self):
        project_widget = self._current_project_widget()
        if project_widget is None:
            return
        project = project_widget.project
        if project.get("par") is None:
            QMessageBox.information(self, "Rename States", "Open a *.par file first.")
            return

        dialog = RenameStatesDialog(project, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        translation = dialog.translation()
        if not translation:
            return

        apply_state_rename(project, translation, state_qn_index=dialog.state_qn_index())
        project_widget.sync_tabs()
        self.statusBar().showMessage(f"Renamed {len(translation)} vibrational state(s).", 5000)

    def _set_parameter_comments(self):
        project_widget = self._current_project_widget()
        if project_widget is None:
            return
        project = project_widget.project
        par_doc = project.get("par")
        if par_doc is None:
            QMessageBox.information(self, "Set Parameter Comments", "Open a *.par file first.")
            return

        kinds = list(ROTATIONAL_DICTS.keys())
        kind, accepted = QInputDialog.getItem(
            self, "Set Parameter Comments", "Reduction type:",
            kinds, kinds.index(default_kind(par_doc.data)), editable=False,
        )
        if not accepted:
            return

        updated = []

        def mutate(document):
            updated.append(set_parameter_comments(document.data, kind))

        project.mutate("par", f"Set parameter comments ({kind})", mutate)
        project_widget.sync_tabs()
        self.statusBar().showMessage(f"Updated {updated[0]} parameter comment(s).", 5000)

    def _create_report(self):
        project_widget = self._current_project_widget()
        if project_widget is None:
            return
        project = project_widget.project
        if project.get("lin") is None:
            QMessageBox.information(self, "Create Report", "Open a *.lin file first.")
            return

        dialog = ReportDialog(project, self)
        dialog.exec()

    def _vibrational_partition_function(self):
        dialog = VibPartitionFunctionDialog(self)
        dialog.exec()

    def _open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def _close_current_project(self):
        index = self.tabs.currentIndex()
        if index != -1:
            self._close_project_tab(index)

    def _close_project_tab(self, index):
        widget = self.tabs.widget(index)
        if widget is not None and widget.has_unsaved_changes:
            confirmation = QMessageBox.question(
                self, "Unsaved Changes",
                f"Project '{widget.project.name}' has unsaved changes. Close anyway?",
            )
            if confirmation != QMessageBox.StandardButton.Yes:
                return
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.new_project()

    # -- whole-window drag and drop -----------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        widget = self._current_project_widget() or self.new_project()
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                widget.load_file(path)
        event.acceptProposedAction()

    def closeEvent(self, event):
        dirty_widgets = [
            self.tabs.widget(i) for i in range(self.tabs.count()) if self.tabs.widget(i).has_unsaved_changes
        ]
        if dirty_widgets:
            names = ", ".join(w.project.name for w in dirty_widgets)
            confirmation = QMessageBox.question(
                self, "Unsaved Changes",
                f"These projects have unsaved changes: {names}\nQuit anyway?",
            )
            if confirmation != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()
