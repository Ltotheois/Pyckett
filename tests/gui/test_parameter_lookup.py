# -*- coding: utf-8 -*-
#!/usr/bin/env python3

# Author: Luis Bonah
# Description : Tests for molecule-type/reduction detection and the
#                 "Add Parameter by Label"/"Set Parameter Comments" actions

import unittest
from pathlib import Path

import pyckett

from pyckett.gui.parameter_lookup import (
    _base_id,
    default_kind,
    full_parameter_id,
    set_parameter_comments,
)

RESOURCES = Path(__file__).resolve().parent.parent / "resources"

VIB_DIGITS = 1


def _par_with_params(spind, knmax, base_ids):
    """base_ids are POSSIBLE_PARAMS_*-style type-only codes (e.g. 100 for A,
    500 for d1) - encoded here into real, state-0 PARAMS ids, exactly as
    they'd appear in an actual *.par file."""
    return {
        "SPIND": spind,
        "KNMIN": 0,
        "KNMAX": knmax,
        "NVIB": 1,
        "PARAMS": [
            [full_parameter_id(base_id, VIB_DIGITS, 0), 1.0, 1e37, ""] for base_id in base_ids
        ],
    }


class TestDefaultKind(unittest.TestCase):
    def test_linear_molecule_always_defaults_to_linear(self):
        par = {"KNMIN": 0, "KNMAX": 0, "SPIND": 1, "NVIB": 1, "PARAMS": [[50000, 1.0, 1e37, ""]]}
        self.assertEqual(default_kind(par), "Linear")

    def test_no_params_yet_defaults_to_a_reduction(self):
        par = _par_with_params(spind=1, knmax=20, base_ids=[])
        self.assertEqual(default_kind(par), "A-Reduction")

    def test_only_shared_terms_is_ambiguous_and_falls_back_to_a_reduction(self):
        # A, B, C and the low-order quartic terms are identical codes in
        # both POSSIBLE_PARAMS_A and POSSIBLE_PARAMS_S.
        par = _par_with_params(spind=1, knmax=20, base_ids=[100, 200, 300, 2, 11, 20])
        self.assertEqual(default_kind(par), "A-Reduction")

    def test_s_reduction_specific_code_preselects_s_reduction(self):
        # 500 (d1) only exists in POSSIBLE_PARAMS_S.
        par = _par_with_params(spind=1, knmax=20, base_ids=[100, 200, 300, 2, 11, 20, 500])
        self.assertEqual(default_kind(par), "S-Reduction")

    def test_a_reduction_specific_code_preselects_a_reduction(self):
        # 410 (deltaK) only exists in POSSIBLE_PARAMS_A.
        par = _par_with_params(spind=1, knmax=20, base_ids=[100, 200, 300, 2, 11, 20, 410])
        self.assertEqual(default_kind(par), "A-Reduction")

    def test_mixing_a_and_s_specific_codes_is_ambiguous(self):
        par = _par_with_params(spind=1, knmax=20, base_ids=[410, 500])
        self.assertEqual(default_kind(par), "A-Reduction")

    def test_real_ch2o_fixture_has_s_reduction_terms(self):
        # ch2o.par was actually fit with S-reduction sextic/octic terms
        # (500/501/600/601/700), so it should now preselect S-Reduction
        # instead of always defaulting to A-Reduction.
        par = pyckett.parvar_to_dict(RESOURCES / "ch2o.par")
        self.assertEqual(default_kind(par), "S-Reduction")

    def test_real_mecn_fixture_stays_ambiguous(self):
        # MeCN.par (symmetric top) only uses shared/torsion-specific codes,
        # no S-reduction-exclusive ones - stays at the A-Reduction fallback.
        par = pyckett.parvar_to_dict(RESOURCES / "MeCN.par")
        self.assertEqual(default_kind(par), "A-Reduction")


class TestSetParameterComments(unittest.TestCase):
    def test_rotational_parameter_gets_its_label(self):
        par = _par_with_params(spind=1, knmax=20, base_ids=[100, 200])
        par["PARAMS"][0][3] = ""
        par["PARAMS"][1][3] = "wrong label"

        updated = set_parameter_comments(par, "A-Reduction")

        self.assertEqual(updated, 2)
        self.assertEqual(par["PARAMS"][0][3], "A")
        self.assertEqual(par["PARAMS"][1][3], "B")

    def test_reduction_specific_label_depends_on_chosen_kind(self):
        # base id 500 is "d1" under S-Reduction but doesn't exist under A-Reduction.
        par = _par_with_params(spind=1, knmax=20, base_ids=[500])

        set_parameter_comments(par, "S-Reduction")
        self.assertEqual(par["PARAMS"][0][3], pyckett.POSSIBLE_PARAMS_S[500][0])

    def test_unmatched_parameter_is_left_untouched(self):
        par = _par_with_params(spind=1, knmax=20, base_ids=[500])  # S-only code
        par["PARAMS"][0][3] = "my manual note"

        updated = set_parameter_comments(par, "A-Reduction")  # 500 not in A-Reduction

        self.assertEqual(updated, 0)
        self.assertEqual(par["PARAMS"][0][3], "my manual note")

    def test_already_correct_comment_is_not_recounted(self):
        par = _par_with_params(spind=1, knmax=20, base_ids=[100])
        par["PARAMS"][0][3] = "A"

        updated = set_parameter_comments(par, "A-Reduction")

        self.assertEqual(updated, 0)
        self.assertEqual(par["PARAMS"][0][3], "A")

    def test_interaction_parameter_uses_interaction_dict_regardless_of_rotational_kind(self):
        interaction_id = full_parameter_id(2000, VIB_DIGITS, v1=0, v2=1)  # "Ga", v1 != v2
        par = _par_with_params(spind=1, knmax=20, base_ids=[])
        par["PARAMS"].append([interaction_id, 1.0, 1e37, ""])

        for kind in ("A-Reduction", "S-Reduction"):
            par["PARAMS"][0][3] = ""
            set_parameter_comments(par, kind)
            self.assertEqual(par["PARAMS"][0][3], pyckett.POSSIBLE_PARAMS_INTERACTION[2000][0])

    def test_global_rotational_parameter_still_gets_its_label(self):
        all_states = pyckett.get_all_states(VIB_DIGITS)
        global_id = full_parameter_id(100, VIB_DIGITS, v1=all_states)
        par = _par_with_params(spind=1, knmax=20, base_ids=[])
        par["PARAMS"].append([global_id, 1.0, 1e37, ""])

        set_parameter_comments(par, "A-Reduction")
        self.assertEqual(par["PARAMS"][0][3], "A")

    def test_real_ch2o_fixture_gets_correct_s_reduction_labels(self):
        # ch2o.par's comments are already correctly labeled - blank them
        # first so the action actually has something to (re)fill in.
        par = pyckett.parvar_to_dict(RESOURCES / "ch2o.par")
        vib_digits = pyckett.get_vib_digits(par)
        for param in par["PARAMS"]:
            param[3] = ""

        updated = set_parameter_comments(par, "S-Reduction")
        self.assertEqual(updated, len(par["PARAMS"]))

        for param in par["PARAMS"]:
            base = _base_id(param[0], vib_digits)
            expected = pyckett.POSSIBLE_PARAMS_S.get(base, (None,))[0]
            if expected is not None:
                self.assertEqual(param[3], expected)


if __name__ == "__main__":
    unittest.main()
