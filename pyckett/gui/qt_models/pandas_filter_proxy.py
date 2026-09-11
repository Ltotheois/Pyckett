# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Filters a PandasTableModel's rows using a pandas .query() string

from PyQt6.QtCore import QSortFilterProxyModel


class PandasFilterProxyModel(QSortFilterProxyModel):
    """Shows only the rows a pandas query string matches, leaving the source model untouched.

    Relies on the source DataFrame having a plain 0..n-1 RangeIndex (true for
    every DataFrame produced in this app), so a row's index value doubles as
    its row position.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._accepted_rows = None  # None means no filter - show everything
        self._query = ""

    def set_query(self, query):
        """Apply a pandas query string (blank clears the filter).

        Returns
        -------
        str or None
            An error message if the query is invalid (the previous filter is
            kept in that case), otherwise None.
        """
        self._query = query or ""
        source_model = self.sourceModel()
        if source_model is None:
            return None

        if not self._query.strip():
            self._accepted_rows = None
            self.invalidateFilter()
            return None

        try:
            filtered = source_model.dataframe().query(self._query)
        except Exception as exc:
            return str(exc)

        self._accepted_rows = set(filtered.index)
        self.invalidateFilter()
        return None

    def reapply(self):
        """Re-run the current query against the (possibly changed) source data."""
        return self.set_query(self._query)

    def filterAcceptsRow(self, source_row, source_parent):
        if self._accepted_rows is None:
            return True
        return source_row in self._accepted_rows
