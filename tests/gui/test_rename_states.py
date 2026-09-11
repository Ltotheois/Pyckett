# -*- coding: utf-8 -*-
#!/usr/bin/env python3

# Author: Luis Bonah
# Description : Tests for the vibrational-state rename/renumber core logic

import tempfile
import unittest
from pathlib import Path

import pyckett

from pyckett.gui.project import Document, Project
from pyckett.gui.rename_states import apply_state_rename, collect_state_ids

RESOURCES = Path(__file__).resolve().parent.parent / "resources"
PAR_PATH = RESOURCES / "MeCN.par"
LIN_PATH = RESOURCES / "MeCN.lin"
INT_PATH = RESOURCES / "MeCN.int"


class TestRenameStates(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.project = Project(name="Test", history_base_dir=Path(self.tmp_dir.name))
        self.project.add_document(Document.load(PAR_PATH))
        self.project.add_document(Document.load(LIN_PATH))
        self.project.add_document(Document.load(INT_PATH))

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_collect_state_ids_excludes_all_states_sentinel(self):
        # MeCN encodes its vibrational state in qn slot 3 (values 0,1,2,
        # matching NVIB=3) - qn slot 4 is a regular rotational quantum
        # number here (values run past 80), so it must be passed explicitly;
        # a molecule using the default slot 4 would not need to.
        par_doc = self.project.get("par")
        vib_digits = pyckett.get_vib_digits(par_doc.data)
        all_states = pyckett.get_all_states(vib_digits)

        states = collect_state_ids(self.project, state_qn_index=3)
        self.assertNotIn(all_states, states)
        self.assertEqual(states, [0, 1, 2])

    def test_rename_swaps_lin_columns(self):
        lin_doc = self.project.get("lin")
        states = collect_state_ids(self.project, state_qn_index=3)
        self.assertGreaterEqual(len(states), 2)
        a, b = states[0], states[1]

        n_a_before = int((lin_doc.data["qnu3"] == a).sum() + (lin_doc.data["qnl3"] == a).sum())
        n_b_before = int((lin_doc.data["qnu3"] == b).sum() + (lin_doc.data["qnl3"] == b).sum())

        apply_state_rename(self.project, {a: b, b: a}, state_qn_index=3)

        n_a_after = int((lin_doc.data["qnu3"] == a).sum() + (lin_doc.data["qnl3"] == a).sum())
        n_b_after = int((lin_doc.data["qnu3"] == b).sum() + (lin_doc.data["qnl3"] == b).sum())

        self.assertEqual(n_a_after, n_b_before)
        self.assertEqual(n_b_after, n_a_before)
        self.assertTrue(lin_doc.dirty)

    def test_rename_updates_params_and_leaves_global_alone(self):
        par_doc = self.project.get("par")
        vib_digits = pyckett.get_vib_digits(par_doc.data)
        all_states = pyckett.get_all_states(vib_digits)

        states = collect_state_ids(self.project, state_qn_index=3)
        a, b = states[0], states[1]

        original_v1v2 = [
            pyckett.parse_param_id(p[0], vib_digits) for p in par_doc.data["PARAMS"]
        ]
        global_ids_before = [p[0] for p, parsed in zip(par_doc.data["PARAMS"], original_v1v2) if parsed["v1"] == all_states]
        self.assertGreater(len(global_ids_before), 0)

        apply_state_rename(self.project, {a: b, b: a}, state_qn_index=3)

        translation = {a: b, b: a}
        for param, old_parsed in zip(par_doc.data["PARAMS"], original_v1v2):
            new_parsed = pyckett.parse_param_id(param[0], vib_digits)
            if old_parsed["v1"] == all_states:
                # Global parameters are untouched by a state rename.
                self.assertEqual(new_parsed["v1"], all_states)
                self.assertEqual(new_parsed["v2"], all_states)
            else:
                self.assertEqual(new_parsed["v1"], translation.get(old_parsed["v1"], old_parsed["v1"]))
                self.assertEqual(new_parsed["v2"], translation.get(old_parsed["v2"], old_parsed["v2"]))
        self.assertTrue(par_doc.dirty)

    def test_rename_updates_idips(self):
        int_doc = self.project.get("int")
        par_doc = self.project.get("par")
        vib_digits = pyckett.get_vib_digits(par_doc.data)

        original_idips = [line[0] for line in int_doc.data["INTS"]]
        states = collect_state_ids(self.project, state_qn_index=3)
        a, b = states[0], states[1]

        apply_state_rename(self.project, {a: b, b: a}, state_qn_index=3)

        for old_idip, line in zip(original_idips, int_doc.data["INTS"]):
            old_parsed = pyckett.parse_idip(old_idip, vib_digits)
            new_parsed = pyckett.parse_idip(line[0], vib_digits)
            expected_v1 = {a: b, b: a}.get(old_parsed["V1"], old_parsed["V1"])
            expected_v2 = {a: b, b: a}.get(old_parsed["V2"], old_parsed["V2"])
            self.assertEqual(new_parsed["V1"], expected_v1)
            self.assertEqual(new_parsed["V2"], expected_v2)
        self.assertTrue(int_doc.dirty)

    def test_rename_snapshots_history_first(self):
        n_before = len(self.project.history.list_snapshots())
        states = collect_state_ids(self.project)
        apply_state_rename(self.project, {states[0]: states[1], states[1]: states[0]})
        n_after = len(self.project.history.list_snapshots())
        self.assertEqual(n_after, n_before + 1)

    def test_rename_updates_states_entries(self):
        par_doc = self.project.get("par")
        if not par_doc.data["STATES"]:
            self.skipTest("MeCN.par has no extra STATES entries to test against")

        states = collect_state_ids(self.project, state_qn_index=3)
        a, b = states[0], states[1]
        original_nvibs = [s["NVIB"] for s in par_doc.data["STATES"]]

        apply_state_rename(self.project, {a: b, b: a}, state_qn_index=3)

        expected = [{a: b, b: a}.get(v, v) for v in original_nvibs]
        self.assertEqual([s["NVIB"] for s in par_doc.data["STATES"]], expected)


if __name__ == "__main__":
    unittest.main()
