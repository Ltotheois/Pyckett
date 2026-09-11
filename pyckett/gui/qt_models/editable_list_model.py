# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Generic editable Qt table model over a plain list of row-lists

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt


class ListTableModel(QAbstractTableModel):
    """Editable table model for data shaped as a list of fixed-width rows.

    Used for the *.par PARAMS/STATES lists and the *.int INTS list, which are
    all plain Python lists (of lists, or of dicts when ``column_keys`` is
    given - see STATES). ``rows`` is kept as the live backing list, so
    callers can read it back directly after edits.
    """

    def __init__(
        self, rows, headers, editable_columns=None, formatters=None, parsers=None,
        row_color_fn=None, column_keys=None, parent=None,
    ):
        super().__init__(parent)
        self.rows = rows
        self.headers = list(headers)
        self.editable_columns = (
            set(range(len(self.headers))) if editable_columns is None else set(editable_columns)
        )
        self.formatters = formatters or [str] * len(self.headers)
        self.parsers = parsers or [str] * len(self.headers)
        # Optional row -> (background QColor, foreground QColor) | None hook,
        # e.g. to flag high-uncertainty fitted parameters. Returning both
        # colors (rather than just a background) guarantees the text stays
        # readable regardless of whether the app is in light or dark mode,
        # since the surrounding theme's own text color is not used here.
        self.row_color_fn = row_color_fn
        # When rows are dicts (e.g. *.par STATES entries) rather than plain
        # lists, column_keys maps each column index to the dict key to read/
        # write instead of a positional index.
        self.column_keys = list(column_keys) if column_keys is not None else None

    def _get_value(self, row, column):
        key = self.column_keys[column] if self.column_keys is not None else column
        return row[key]

    def _set_value(self, row, column, value):
        key = self.column_keys[column] if self.column_keys is not None else column
        row[key] = value

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return str(section + 1)

    def flags(self, index):
        base = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if index.column() in self.editable_columns:
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            value = self._get_value(self.rows[index.row()], index.column())
            return self.formatters[index.column()](value)
        if role in (Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole) and self.row_color_fn is not None:
            colors = self.row_color_fn(self.rows[index.row()])
            if colors is None:
                return None
            background, foreground = colors
            return background if role == Qt.ItemDataRole.BackgroundRole else foreground
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        try:
            parsed = self.parsers[index.column()](value)
        except (ValueError, TypeError):
            return False

        self._set_value(self.rows[index.row()], index.column(), parsed)
        self.dataChanged.emit(index, index, [role])
        return True

    def append_row(self, row):
        self.beginResetModel()
        self.rows.append(row)
        self.endResetModel()

    def remove_rows(self, row_indices):
        if not row_indices:
            return
        self.beginResetModel()
        for i in sorted(row_indices, reverse=True):
            del self.rows[i]
        self.endResetModel()
