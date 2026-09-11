# -*- coding: utf-8 -*-
#!/usr/bin/env python3

# Author: Luis Bonah
# Description : Tests for the Pyckett GUI's version history store

import shutil
import tempfile
import unittest
from pathlib import Path

from pyckett.gui.history import HistoryStore


class TestHistoryStore(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def make_store(self):
        return HistoryStore("test-project", base_dir=self.base_dir)

    def test_snapshot_and_restore_round_trip(self):
        store = self.make_store()
        snap_id = store.snapshot("Initial", {"par": "PAR CONTENT", "lin": "LIN CONTENT"})
        self.assertIsNotNone(snap_id)

        restored = store.restore(snap_id)
        self.assertEqual(restored, {"par": "PAR CONTENT", "lin": "LIN CONTENT"})

    def test_identical_snapshot_is_skipped(self):
        store = self.make_store()
        first_id = store.snapshot("Initial", {"par": "SAME"})
        second_id = store.snapshot("No real change", {"par": "SAME"})

        self.assertIsNotNone(first_id)
        self.assertIsNone(second_id)
        self.assertEqual(len(store.list_snapshots()), 1)

    def test_changed_content_creates_new_snapshot(self):
        store = self.make_store()
        store.snapshot("Initial", {"par": "A"})
        second_id = store.snapshot("Edited", {"par": "B"})

        self.assertIsNotNone(second_id)
        self.assertEqual(len(store.list_snapshots()), 2)

    def test_list_snapshots_is_ordered_oldest_first(self):
        store = self.make_store()
        store.snapshot("First", {"par": "A"})
        store.snapshot("Second", {"par": "B"})
        store.snapshot("Third", {"par": "C"})

        labels = [s["label"] for s in store.list_snapshots()]
        self.assertEqual(labels, ["First", "Second", "Third"])

    def test_partial_kinds_are_recorded(self):
        store = self.make_store()
        snap_id = store.snapshot("Only lin", {"lin": "LIN ONLY"})
        restored = store.restore(snap_id)
        self.assertEqual(restored, {"lin": "LIN ONLY"})

    def test_restore_unknown_snapshot_raises(self):
        store = self.make_store()
        with self.assertRaises(FileNotFoundError):
            store.restore("0099_nonexistent")

    def test_projects_are_isolated(self):
        store_a = HistoryStore("project-a", base_dir=self.base_dir)
        store_b = HistoryStore("project-b", base_dir=self.base_dir)

        store_a.snapshot("A change", {"par": "A"})
        self.assertEqual(store_b.list_snapshots(), [])

    def test_list_snapshots_survives_missing_directory(self):
        store = self.make_store()
        shutil.rmtree(store.directory)
        self.assertEqual(store.list_snapshots(), [])

    def test_snapshot_recreates_directory_if_it_vanished(self):
        # Regression test: a project's history directory can disappear out
        # from under a running app (e.g. external cleanup, the user deleting
        # it by hand) - snapshot() must self-heal rather than crash with
        # FileNotFoundError.
        store = self.make_store()
        store.snapshot("Initial", {"par": "A"})
        shutil.rmtree(store.directory)

        snap_id = store.snapshot("After directory vanished", {"par": "B"})
        self.assertIsNotNone(snap_id)
        self.assertEqual(store.restore(snap_id), {"par": "B"})


if __name__ == "__main__":
    unittest.main()
