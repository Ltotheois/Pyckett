# -*- coding: utf-8 -*-
#!/usr/bin/env python3

# Author: Luis Bonah
# Description : Tests for the "New Molecule" starting-point *.par templates

import unittest

import pyckett

from pyckett.gui import molecule_templates


class TestChrIsNeverBlank(unittest.TestCase):
    """A blank CHR writes as an empty *.par first column, which is confusing
    to read back - every template should set a distinguishing, non-blank
    letter instead."""

    def test_linear(self):
        self.assertEqual(molecule_templates.linear_par()["CHR"], "L")

    def test_symmetric_top(self):
        self.assertEqual(molecule_templates.symmetric_top_par()["CHR"], "S")

    def test_asymmetric_top_a_reduction(self):
        self.assertEqual(molecule_templates.asymmetric_top_par("a_reduction")["CHR"], "A")

    def test_asymmetric_top_s_reduction(self):
        self.assertEqual(molecule_templates.asymmetric_top_par("s_reduction")["CHR"], "S")


class TestLinearSpindIsNegative(unittest.TestCase):
    def test_linear_par_uses_negative_spind(self):
        self.assertLess(molecule_templates.linear_par()["SPIND"], 0)


class TestRealReferenceMolecules(unittest.TestCase):
    """linear_par/symmetric_top_par use OCS/CH3CN from
    https://spin.astro.uni-koeln.de/chapter/LinearMoleculeInPickett/ as a
    genuinely working starting point rather than an arbitrary placeholder."""

    def test_ocs_params(self):
        par = molecule_templates.linear_par()
        self.assertEqual(
            par["PARAMS"],
            [[100, 6081.49, 1e37, "B"], [200, -1.29e-3, 1e37, "-D"]],
        )
        self.assertEqual(par["EWT"], -1)
        self.assertEqual(par["ERRTST"], 1e37)
        self.assertEqual(par["FRAC"], -1)

    def test_ocs_round_trips_through_dict_to_parvar(self):
        par = molecule_templates.linear_par()
        reloaded = pyckett.parvar_to_dict(pyckett.str_to_stream(pyckett.dict_to_parvar(par)))
        self.assertEqual(reloaded["PARAMS"], par["PARAMS"])
        self.assertEqual(reloaded["EWT"], -1)
        self.assertEqual(reloaded["SPIND"], -1)

    def test_ch3cn_params(self):
        par = molecule_templates.symmetric_top_par()
        self.assertEqual(
            par["PARAMS"],
            [
                [1000, 148900.0744965263, 1e37, "A-B"],
                [100, 9198.899102551335, 1e37, "B"],
                [2000, -2.825727761558185, 1e37, "-DK"],
                [1100, -0.1774063654292496, 1e37, "-DJK"],
                [200, -0.003807510349803836, 1e37, "-DJ"],
            ],
        )
        self.assertEqual(par["NITR"], 5)
        self.assertEqual((par["IAX"], par["WTPL"], par["WTMN"], par["EWT"], par["DIAG"]), (6, 2, 2, 1, 0))

    def test_ch3cn_round_trips_through_dict_to_parvar(self):
        par = molecule_templates.symmetric_top_par()
        reloaded = pyckett.parvar_to_dict(pyckett.str_to_stream(pyckett.dict_to_parvar(par)))
        self.assertEqual(reloaded["PARAMS"], par["PARAMS"])
        self.assertEqual(reloaded["IAX"], 6)
        self.assertEqual(reloaded["DIAG"], 0)


if __name__ == "__main__":
    unittest.main()
