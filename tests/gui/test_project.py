# -*- coding: utf-8 -*-
#!/usr/bin/env python3

# Author: Luis Bonah
# Description : Tests for the Pyckett GUI's project/document data model

import tempfile
import unittest
from pathlib import Path

import pyckett

from pyckett.gui.project import Document, Project, infer_kind_from_suffix

RESOURCES = Path(__file__).resolve().parent.parent / "resources"
PAR_PATH = RESOURCES / "MeCN.par"
LIN_PATH = RESOURCES / "MeCN.lin"
INT_PATH = RESOURCES / "MeCN.int"
CH2O_PAR_PATH = RESOURCES / "ch2o.par"
CH2O_LIN_PATH = RESOURCES / "ch2o.lin"
CH2O_INT_PATH = RESOURCES / "ch2o.int"


class TestInferKind(unittest.TestCase):
    def test_known_suffixes(self):
        self.assertEqual(infer_kind_from_suffix("molecule.par"), "par")
        self.assertEqual(infer_kind_from_suffix("molecule.lin"), "lin")
        self.assertEqual(infer_kind_from_suffix("molecule.int"), "int")
        self.assertEqual(infer_kind_from_suffix("molecule.var"), "var")
        self.assertEqual(infer_kind_from_suffix("molecule.cat"), "cat")
        self.assertEqual(infer_kind_from_suffix("molecule.egy"), "egy")

    def test_unknown_suffix_is_text(self):
        self.assertEqual(infer_kind_from_suffix("readme.txt"), "text")
        self.assertEqual(infer_kind_from_suffix("noextension"), "text")


class TestDocumentRoundTrip(unittest.TestCase):
    def test_load_par(self):
        doc = Document.load(PAR_PATH)
        self.assertEqual(doc.kind, "par")
        self.assertFalse(doc.dirty)
        self.assertGreater(len(doc.data["PARAMS"]), 0)

    def test_load_lin(self):
        doc = Document.load(LIN_PATH)
        self.assertEqual(doc.kind, "lin")
        self.assertGreater(len(doc.data), 0)
        self.assertIn("x", doc.data.columns)

    def test_load_int(self):
        doc = Document.load(INT_PATH)
        self.assertEqual(doc.kind, "int")
        self.assertIn("INTS", doc.data)

    def test_save_round_trips_par_params(self):
        doc = Document.load(PAR_PATH)
        original_ids = [p[0] for p in doc.data["PARAMS"]]

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "copy.par"
            doc.save(out_path)
            self.assertFalse(doc.dirty)

            reloaded = Document.load(out_path)
            reloaded_ids = [p[0] for p in reloaded.data["PARAMS"]]
            self.assertEqual(original_ids, reloaded_ids)

    def test_save_round_trips_lin_rows(self):
        doc = Document.load(LIN_PATH)
        n_rows = len(doc.data)

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "copy.lin"
            doc.save(out_path)

            reloaded = Document.load(out_path)
            self.assertEqual(len(reloaded.data), n_rows)

    def test_from_content_round_trips_through_render(self):
        doc = Document.load(PAR_PATH)
        content = doc.render()

        restored = Document.from_content("par", content, label="par.par")
        self.assertEqual(
            [p[0] for p in restored.data["PARAMS"]],
            [p[0] for p in doc.data["PARAMS"]],
        )

    def test_copy_data_is_independent(self):
        doc = Document.load(PAR_PATH)
        copied = doc.copy_data()
        copied["PARAMS"][0][1] = 12345.0
        self.assertNotEqual(doc.data["PARAMS"][0][1], 12345.0)


class TestProject(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.history_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def make_project(self):
        project = Project(name="Test", history_base_dir=self.history_dir)
        project.add_document(Document.load(PAR_PATH))
        project.add_document(Document.load(LIN_PATH))
        project.add_document(Document.load(INT_PATH))
        return project

    def test_get_returns_singleton_document(self):
        project = self.make_project()
        self.assertEqual(project.get("par").kind, "par")
        self.assertIsNone(project.get("var"))

    def test_adding_same_kind_replaces_previous(self):
        project = self.make_project()
        first_par = project.get("par")
        project.add_document(Document.load(PAR_PATH))
        second_par = project.get("par")

        self.assertIsNot(first_par, second_par)
        self.assertEqual(sum(1 for d in project.documents if d.kind == "par"), 1)

    def test_snapshot_and_restore(self):
        project = self.make_project()
        project.snapshot("Initial load")
        initial_snapshot_id = project.history.list_snapshots()[0]["id"]

        par_doc = project.get("par")
        original_value = par_doc.data["PARAMS"][0][1]
        par_doc.data["PARAMS"][0][1] = 999.0
        project.snapshot("Edited a parameter")
        self.assertEqual(len(project.history.list_snapshots()), 2)

        project.restore_snapshot(initial_snapshot_id)
        restored_value = project.get("par").data["PARAMS"][0][1]
        self.assertEqual(restored_value, original_value)

        # Restoring appends rather than deleting/rewriting existing history entries.
        snapshots_after_restore = project.history.list_snapshots()
        self.assertGreaterEqual(len(snapshots_after_restore), 2)
        self.assertEqual(snapshots_after_restore[0]["id"], initial_snapshot_id)

    def test_mutate_snapshots_before_changing(self):
        project = self.make_project()

        def bump_first_param(document):
            document.data["PARAMS"][0][1] += 1.0

        project.mutate("par", "Bump first parameter", bump_first_param)

        self.assertTrue(project.get("par").dirty)
        self.assertEqual(len(project.history.list_snapshots()), 1)

    def test_clone_with_new_par_copies_lin_and_int_unchanged(self):
        project = self.make_project()
        new_params = project.get("par").copy_data()["PARAMS"]
        new_params[0][1] = 42.0

        clone = project.clone_with_new_par("Candidate", new_params)

        self.assertEqual(clone.get("par").data["PARAMS"][0][1], 42.0)
        self.assertIsNone(clone.get("par").path)
        self.assertTrue(clone.get("par").dirty)

        self.assertEqual(len(clone.get("lin").data), len(project.get("lin").data))
        self.assertFalse(clone.get("lin").dirty)

    def test_loading_par_and_lin_syncs_npar_nline_nxpar(self):
        project = self.make_project()
        par_doc = project.get("par")
        lin_doc = project.get("lin")

        self.assertEqual(par_doc.data["NPAR"], len(par_doc.data["PARAMS"]))
        self.assertEqual(par_doc.data["NLINE"], len(lin_doc.data))
        self.assertEqual(par_doc.data["NXPAR"], 0)

    def test_sync_par_fields_tracks_params_count(self):
        project = self.make_project()
        par_doc = project.get("par")
        par_doc.data["PARAMS"].append([999999, 1e-37, 1e37, ""])

        self.assertTrue(project.sync_par_fields())
        self.assertEqual(par_doc.data["NPAR"], len(par_doc.data["PARAMS"]))
        self.assertTrue(par_doc.dirty)

    def test_sync_par_fields_tracks_lin_row_count(self):
        project = self.make_project()
        par_doc = project.get("par")
        lin_doc = project.get("lin")
        original_nline = par_doc.data["NLINE"]
        lin_doc.data = lin_doc.data.iloc[:-1].reset_index(drop=True)

        self.assertTrue(project.sync_par_fields())
        self.assertEqual(par_doc.data["NLINE"], len(lin_doc.data))
        self.assertNotEqual(par_doc.data["NLINE"], original_nline)

    def test_sync_par_fields_is_idempotent(self):
        project = self.make_project()
        project.sync_par_fields()
        self.assertFalse(project.sync_par_fields())

    def test_sync_par_fields_without_par_is_a_noop(self):
        project = Project(name="Test", history_base_dir=self.history_dir)
        project.add_document(Document.load(LIN_PATH))
        self.assertFalse(project.sync_par_fields())

    def test_apply_add_parameter_candidate_updates_npar(self):
        project = self.make_project()
        par_doc = project.get("par")
        new_params = par_doc.copy_data()["PARAMS"]
        new_params.append([999999, 1e-37, 1e37, ""])

        def mutate(document):
            document.data["PARAMS"] = new_params

        project.mutate("par", "Applied candidate", mutate)
        self.assertEqual(par_doc.data["NPAR"], len(new_params))

        # The original project's par is untouched.
        self.assertNotEqual(project.get("par").data["PARAMS"][0][1], 42.0)

    def test_growing_nvib_recodes_params_and_idips(self):
        project = self.make_project()
        par_doc = project.get("par")
        int_doc = project.get("int")

        self.assertEqual(pyckett.get_vib_digits(par_doc.data), 1)
        original_param_ids = [p[0] for p in par_doc.data["PARAMS"]]
        original_idips = [line[0] for line in int_doc.data["INTS"]]

        par_doc.data["NVIB"] = 10  # 9 -> 10 states: vib_digits 1 -> 2
        self.assertTrue(project.sync_par_fields())

        expected_param_ids = [
            pyckett.recode_param_id_vib_digits(pid, 1, 2) for pid in original_param_ids
        ]
        expected_idips = [
            pyckett.recode_idip_vib_digits(idip, 1, 2) for idip in original_idips
        ]

        self.assertEqual([p[0] for p in par_doc.data["PARAMS"]], expected_param_ids)
        self.assertEqual([line[0] for line in int_doc.data["INTS"]], expected_idips)
        self.assertTrue(par_doc.dirty)
        self.assertTrue(int_doc.dirty)

        # A global ("all states") parameter must stay global at the new width,
        # not be reinterpreted as the literal state index it used to share a
        # code with (this is the ALL_STATES sentinel case from format_param_id).
        old_all_states = pyckett.get_all_states(1)
        new_all_states = pyckett.get_all_states(2)
        for old_id, new_id in zip(original_param_ids, expected_param_ids):
            old_parsed = pyckett.parse_param_id(old_id, 1)
            if old_parsed["v1"] == old_all_states and old_parsed["v2"] == old_all_states:
                new_parsed = pyckett.parse_param_id(new_id, 2)
                self.assertEqual(new_parsed["v1"], new_all_states)
                self.assertEqual(new_parsed["v2"], new_all_states)

    def test_loading_a_new_par_does_not_trigger_a_recode(self):
        # A freshly loaded/restored par is a different Document instance, even
        # though it replaces the project's old "par" singleton - it must not
        # be mistaken for an in-place NVIB edit on the previous file.
        project = self.make_project()
        original_param_ids = [p[0] for p in project.get("par").data["PARAMS"]]

        project.add_document(Document.load(PAR_PATH))

        self.assertEqual(
            [p[0] for p in project.get("par").data["PARAMS"]], original_param_ids
        )

    def test_unrelated_sync_does_not_recode_when_vib_digits_unchanged(self):
        project = self.make_project()
        par_doc = project.get("par")
        original_param_ids = [p[0] for p in par_doc.data["PARAMS"]]

        par_doc.data["PARAMS"].append([999999, 1e-37, 1e37, ""])
        project.sync_par_fields()

        self.assertEqual(
            [p[0] for p in par_doc.data["PARAMS"]], original_param_ids + [999999]
        )

    def test_growing_nvib_warns_when_last_qn_slot_has_real_data(self):
        project = Project(name="ch2o", history_base_dir=self.history_dir)
        project.add_document(Document.load(CH2O_PAR_PATH))
        project.add_document(Document.load(CH2O_LIN_PATH))
        par_doc = project.get("par")
        lin_doc = project.get("lin")

        # Force the last qn slot into "actually used" territory.
        lin_doc.data["qnu6"] = 5
        self.assertEqual(project.pending_warnings, [])

        par_doc.data["NVIB"] = 2
        project.sync_par_fields()

        self.assertEqual(len(project.pending_warnings), 1)
        self.assertIn("discarded", project.pending_warnings[0])

    def test_growing_nvib_from_one_inserts_v_column_for_asymmetric_top(self):
        # ch2o: asymmetric top (SPIND > 0, KNMAX > 0), NVIB=1 - no v column
        # at all yet. qnu4-6/qnl4-6 are already unused, so growing to 2
        # states should insert v at position 4 with no data loss.
        project = Project(name="ch2o", history_base_dir=self.history_dir)
        project.add_document(Document.load(CH2O_PAR_PATH))
        project.add_document(Document.load(CH2O_LIN_PATH))
        par_doc = project.get("par")
        lin_doc = project.get("lin")

        self.assertEqual(par_doc.data["NVIB"], 1)
        original_qnu = lin_doc.data[[f"qnu{i + 1}" for i in range(6)]].copy()

        par_doc.data["NVIB"] = 2
        changed = project.sync_par_fields()

        self.assertTrue(changed)
        self.assertTrue(project.vib_state_encoding_changed)
        self.assertEqual(project.pending_warnings, [])  # no data loss - room was free
        self.assertTrue(lin_doc.dirty)

        new_qnu = lin_doc.data
        self.assertEqual(new_qnu["qnu1"].tolist(), original_qnu["qnu1"].tolist())  # N unchanged
        self.assertEqual(new_qnu["qnu2"].tolist(), original_qnu["qnu2"].tolist())  # Ka unchanged
        self.assertEqual(new_qnu["qnu3"].tolist(), original_qnu["qnu3"].tolist())  # Kc unchanged
        self.assertEqual(new_qnu["qnu4"].tolist(), [0] * len(new_qnu))  # new v column, defaults to 0
        self.assertEqual(new_qnu["qnu5"].tolist(), original_qnu["qnu4"].tolist())  # J shifted over

    def test_shrinking_nvib_to_one_removes_v_column_for_symmetric_top(self):
        # MeCN: symmetric top (SPIND < 0), NVIB=3, v at position 3 (qnu3
        # holds the real torsional-state values 0/1/2, per its *.lin file).
        project = self.make_project()
        par_doc = project.get("par")
        lin_doc = project.get("lin")

        self.assertEqual(sorted(lin_doc.data["qnu3"].unique().tolist()), [0, 1, 2])
        original_qnu = lin_doc.data[[f"qnu{i + 1}" for i in range(6)]].copy()

        par_doc.data["NVIB"] = 1
        changed = project.sync_par_fields()

        self.assertTrue(changed)
        self.assertTrue(project.vib_state_encoding_changed)
        self.assertTrue(lin_doc.dirty)

        new_qnu = lin_doc.data
        self.assertEqual(new_qnu["qnu1"].tolist(), original_qnu["qnu1"].tolist())  # N unchanged
        self.assertEqual(new_qnu["qnu2"].tolist(), original_qnu["qnu2"].tolist())  # K unchanged
        # v (old position 3) is gone; J (old position 4) shifted into its place.
        self.assertEqual(new_qnu["qnu3"].tolist(), original_qnu["qnu4"].tolist())
        self.assertEqual(new_qnu["qnu6"].tolist(), [pyckett.SENTINEL] * len(new_qnu))  # freed slot

    def test_v_column_position_unaffected_by_pure_digit_width_growth(self):
        # Growing 9 -> 10 states (vib_digits 1 -> 2) doesn't change *whether*
        # or *where* v appears - only crossing the 1 <-> 2 state threshold
        # does. Confirms the two thresholds are tracked independently.
        project = self.make_project()
        par_doc = project.get("par")
        lin_doc = project.get("lin")
        original_qnu3 = lin_doc.data["qnu3"].tolist()

        par_doc.data["NVIB"] = 10
        project.sync_par_fields()

        self.assertEqual(lin_doc.data["qnu3"].tolist(), original_qnu3)


if __name__ == "__main__":
    unittest.main()
