# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Generic Qt table model wrapping a pandas DataFrame

import pandas as pd
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt


class PandasTableModel(QAbstractTableModel):
    """Read-only-by-default table model over a subset of a DataFrame's columns.

    Subclasses opt individual columns into editing by overriding
    ``editable_columns`` and the ``format_value``/``parse_value`` hooks for
    any column that needs custom display or parsing (e.g. Pickett's special
    integer notation).
    """

    def __init__(self, df, columns=None, editable_columns=(), row_color_fn=None, parent=None):
        super().__init__(parent)
        self._df = df
        self.columns = list(columns) if columns is not None else list(df.columns)
        self.editable_columns = set(editable_columns)
        # Optional row (pandas Series, all columns) -> (background QColor,
        # foreground QColor) | None hook, e.g. to flag rows that deviate a
        # lot from their uncertainty. Both colors are always returned
        # together so text stays readable in both light and dark mode.
        self.row_color_fn = row_color_fn

    def dataframe(self):
        return self._df

    def set_dataframe(self, df):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._df)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.columns[section]
        return str(section + 1)

    def flags(self, index):
        base = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if self.columns[index.column()] in self.editable_columns:
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    def format_value(self, column, raw_value):
        if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
            return ""
        return str(raw_value)

    def parse_value(self, column, text):
        return text

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            column = self.columns[index.column()]
            raw_value = self._df.iloc[index.row()][column]
            return self.format_value(column, raw_value)
        if role in (Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole) and self.row_color_fn is not None:
            colors = self.row_color_fn(self._df.iloc[index.row()])
            if colors is None:
                return None
            background, foreground = colors
            return background if role == Qt.ItemDataRole.BackgroundRole else foreground
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False

        column = self.columns[index.column()]
        try:
            parsed = self.parse_value(column, value)
        except (ValueError, TypeError):
            return False

        self._df.iloc[index.row(), self._df.columns.get_loc(column)] = parsed
        self.dataChanged.emit(index, index, [role])
        return True

    def remove_rows(self, row_indices):
        if not row_indices:
            return
        self.beginResetModel()
        self._df = self._df.drop(self._df.index[list(row_indices)]).reset_index(drop=True)
        self.endResetModel()

    def append_row(self, row_dict):
        self.beginResetModel()
        self._df = pd.concat([self._df, pd.DataFrame([row_dict])], ignore_index=True)
        self.endResetModel()
