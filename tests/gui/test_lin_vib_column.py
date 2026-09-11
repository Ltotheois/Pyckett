# -*- coding: utf-8 -*-
#!/usr/bin/env python3

# Author: Luis Bonah
# Description : Tests for rearranging *.lin's fixed qn columns when the
#                 vibrational-state "v" identifier appears/disappears/moves

import unittest

import pandas as pd
import pyckett

from pyckett.gui.lin_vib_column import _build_column_mapping, reindex_lin_vib_column

S = pyckett.SENTINEL


def make_lin_df(rows_u, rows_l=None):
    """Build a minimal *.lin-shaped dataframe from lists of 6-quanta rows."""
    rows_l = rows_l if rows_l is not None else rows_u
    data = {}
    for i in range(6):
        data[f"qnu{i + 1}"] = [row[i] for row in rows_u]
    for i in range(6):
        data[f"qnl{i + 1}"] = [row[i] for row in rows_l]
    data["x"] = [100.0] * len(rows_u)
    data["error"] = [0.05] * len(rows_u)
    data["weight"] = [1.0] * len(rows_u)
    data["comment"] = [""] * len(rows_u)
    return pd.DataFrame(data)


class TestBuildColumnMapping(unittest.TestCase):
    def test_insert_at_position_2(self):
        mapping = _build_column_mapping(6, None, 2)
        self.assertEqual(
            mapping,
            [("copy", 0), ("default",), ("copy", 1), ("copy", 2), ("copy", 3), ("copy", 4)],
        )

    def test_remove_from_position_2(self):
        mapping = _build_column_mapping(6, 2, None)
        self.assertEqual(
            mapping,
            [("copy", 0), ("copy", 2), ("copy", 3), ("copy", 4), ("copy", 5), ("empty",)],
        )

    def test_move_from_2_to_4(self):
        mapping = _build_column_mapping(6, 2, 4)
        self.assertEqual(
            mapping,
            [("copy", 0), ("copy", 2), ("copy", 3), ("copy", 1), ("copy", 4), ("copy", 5)],
        )

    def test_move_from_4_to_2(self):
        mapping = _build_column_mapping(6, 4, 2)
        self.assertEqual(
            mapping,
            [("copy", 0), ("copy", 3), ("copy", 1), ("copy", 2), ("copy", 4), ("copy", 5)],
        )

    def test_noop_when_positions_equal(self):
        mapping = _build_column_mapping(6, 3, 3)
        self.assertEqual(mapping, [("copy", i) for i in range(6)])


class TestReindexLinVibColumn(unittest.TestCase):
    def test_insert_no_data_loss_when_trailing_slots_unused(self):
        # N, Ka, Kc active; qn4-6 already all-SENTINEL - plenty of room.
        df = make_lin_df([[5, 1, 4, S, S, S], [6, 2, 5, S, S, S]])
        new_df, dropped = reindex_lin_vib_column(df, None, 4)

        self.assertFalse(dropped)
        # N, Ka, Kc unchanged; v (position 4) defaults to 0; J/F slots empty.
        self.assertEqual(new_df["qnu1"].tolist(), [5, 6])
        self.assertEqual(new_df["qnu2"].tolist(), [1, 2])
        self.assertEqual(new_df["qnu3"].tolist(), [4, 5])
        self.assertEqual(new_df["qnu4"].tolist(), [0, 0])
        self.assertEqual(new_df["qnu5"].tolist(), [S, S])
        self.assertEqual(new_df["qnu6"].tolist(), [S, S])

    def test_insert_linear_shifts_j_and_f_over(self):
        # Linear molecule: N, J, F1, F2, F3, F all active - inserting v at
        # position 2 pushes the (unused) last slot off and shifts the rest.
        df = make_lin_df([[10, 20, 30, 40, 50, S]])
        new_df, dropped = reindex_lin_vib_column(df, None, 2)

        self.assertFalse(dropped)  # last slot (F) was already empty
        self.assertEqual(new_df.iloc[0][[f"qnu{i + 1}" for i in range(6)]].tolist(), [10, 0, 20, 30, 40, 50])

    def test_insert_warns_when_last_slot_has_real_data(self):
        df = make_lin_df([[10, 20, 30, 40, 50, 60]])  # all 6 slots genuinely used
        new_df, dropped = reindex_lin_vib_column(df, None, 2)

        self.assertTrue(dropped)
        self.assertEqual(new_df.iloc[0][[f"qnu{i + 1}" for i in range(6)]].tolist(), [10, 0, 20, 30, 40, 50])
        # The old value 60 (position 6) is gone - that's exactly the data loss being flagged.

    def test_remove_frees_last_slot(self):
        df = make_lin_df([[10, 1, 20, 30, 40, S]])  # symmetric top: N, K, v, J, F1, F
        new_df, dropped = reindex_lin_vib_column(df, 3, None)

        self.assertFalse(dropped)
        self.assertEqual(new_df.iloc[0][[f"qnu{i + 1}" for i in range(6)]].tolist(), [10, 1, 30, 40, S, S])

    def test_remove_never_reports_data_loss(self):
        # Removing v can't lose real data - the freed trailing slot was
        # already unused (that's what made room for v in the first place).
        df = make_lin_df([[10, 1, 20, 30, 40, 50]])
        _, dropped = reindex_lin_vib_column(df, 3, None)
        self.assertFalse(dropped)

    def test_applies_identically_to_upper_and_lower(self):
        df = make_lin_df([[5, 1, 4, S, S, S]], rows_l=[[6, 2, 3, S, S, S]])
        new_df, _ = reindex_lin_vib_column(df, None, 4)
        self.assertEqual(new_df.iloc[0][[f"qnl{i + 1}" for i in range(6)]].tolist(), [6, 2, 3, 0, S, S])

    def test_noop_returns_same_df_when_positions_equal(self):
        df = make_lin_df([[10, 1, 20, 30, 40, S]])
        new_df, dropped = reindex_lin_vib_column(df, 3, 3)
        self.assertIs(new_df, df)
        self.assertFalse(dropped)

    def test_result_dtype_stays_int64(self):
        df = make_lin_df([[10, 20, 30, 40, 50, S]])
        new_df, _ = reindex_lin_vib_column(df, None, 2)
        for i in range(6):
            self.assertEqual(new_df[f"qnu{i + 1}"].dtype, "int64")


if __name__ == "__main__":
    unittest.main()
