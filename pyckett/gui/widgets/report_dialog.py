# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Dialog to summarize a *.lin (+ optional *.cat) analysis, as in pyckett.clitools.report

import pyckett
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class ReportDialog(QDialog):
    """Text summary of the current project's *.lin (+ *.cat, if open), from pyckett.create_report.

    Same statistics as the "report" CLI tool (transition/line counts, min/max
    per quantum number, and - once a *.cat is open - RMS/WRMS against the
    predictions), plus a breakdown of transitions by type. Re-generated on
    demand rather than live, since noq/blend options change the result.
    """

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Create Report")
        self.resize(700, 600)

        layout = QVBoxLayout(self)

        options_row = QHBoxLayout()
        self.blends_cb = QCheckBox("Treat blends")
        self.blends_cb.setChecked(True)
        options_row.addWidget(self.blends_cb)

        self.noq_auto_cb = QCheckBox("Auto-detect quantum number count")
        self.noq_auto_cb.setChecked(True)
        self.noq_auto_cb.toggled.connect(lambda checked: self.noq_spin.setEnabled(not checked))
        options_row.addWidget(self.noq_auto_cb)

        self.noq_spin = QSpinBox()
        self.noq_spin.setRange(1, 12)
        self.noq_spin.setValue(6)
        self.noq_spin.setEnabled(False)
        options_row.addWidget(self.noq_spin)

        options_row.addStretch(1)
        generate_button = QPushButton("Generate")
        generate_button.clicked.connect(self._generate)
        options_row.addWidget(generate_button)
        layout.addLayout(options_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.text_view = QPlainTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        layout.addWidget(self.text_view, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self._generate()

    def _generate(self):
        lin_doc = self.project.get("lin")
        if lin_doc is None:
            self.text_view.setPlainText("")
            self.status_label.setText("This project has no open *.lin file.")
            return

        cat_doc = self.project.get("cat")
        cat_df = cat_doc.data if cat_doc is not None else None
        noq = None if self.noq_auto_cb.isChecked() else self.noq_spin.value()

        report_text, _ = pyckett.create_report(
            lin_doc.data, cat_df, blends=self.blends_cb.isChecked(), noq=noq
        )
        self.text_view.setPlainText(report_text)
        self.status_label.setText(
            "Report generated from *.lin"
            + (" and *.cat." if cat_df is not None else " (open a *.cat file too for RMS/WRMS against predictions).")
        )
