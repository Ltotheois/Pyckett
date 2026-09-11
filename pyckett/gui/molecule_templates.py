# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Starting-point *.par/*.lin/*.int templates for a new molecule

import pandas as pd
import pyckett

from pyckett.gui.parameter_lookup import full_parameter_id

VIB_DIGITS = 1

# These header/base-state fields are advanced symmetry/statistics settings
# (nuclear spin statistics, special axis conventions, ...) that can't be
# sensibly guessed for an arbitrary molecule - they're set to simple,
# widely-applicable defaults and left for the user to adjust if their
# molecule needs something specific.
_BASE_HEADER = {
    "TITLE": "New Molecule",
    "DATE": "",
    "NPAR": 0,   # Project.sync_par_fields() corrects this once added to a project
    "NLINE": 0,  # likewise
    "NITR": 10,
    "NXPAR": 0,  # likewise
    "THRESH": 0,
    "ERRTST": 1000,
    "FRAC": 1,
    "CAL": 1,
}
_BASE_STATE = {
    "CHR": "",
    "NVIB": 1,
    "IXX": 0,
    "IAX": 1,
    "WTPL": 1,
    "WTMN": 1,
    "VSYM": 0,
    "EWT": 0,
}


def _base_par(spind, knmax, chr_value, nitr=10, errtst=1000, frac=1, **state_overrides):
    par = dict(_BASE_HEADER)
    par.update(_BASE_STATE)
    par["NITR"] = nitr
    par["ERRTST"] = errtst
    par["FRAC"] = frac
    par["SPIND"] = spind
    par["KNMIN"] = 0
    par["KNMAX"] = knmax
    # A blank CHR writes as an empty first column in *.par, which is
    # confusing to read back - always set it to something molecule-type
    # appropriate instead (Pickett itself just uses it to tag the parameter-
    # names file, so any distinguishing, non-blank letter is fine here).
    par["CHR"] = chr_value
    par.update(state_overrides)
    par["STATES"] = []
    par["PARAMS"] = []
    return par


def _param_rows(source_dict, base_ids_and_values, v1=0, v2=0):
    """Build PARAMS rows [id, value, uncertainty, label] from a POSSIBLE_PARAMS_* dict.

    Uncertainty is always 1e37 ("float freely") - these are starting
    guesses for a molecule with no assignments yet, not fixed values.
    """
    rows = []
    for base_id, value in base_ids_and_values:
        label = source_dict[base_id][0]
        param_id = full_parameter_id(base_id, VIB_DIGITS, v1, v2)
        rows.append([param_id, value, 1e37, label])
    return rows


def linear_par():
    """A linear molecule: KNMIN = KNMAX = 0, one rotational constant (B) + -D.

    Values are OCS's, from
    https://spin.astro.uni-koeln.de/chapter/LinearMoleculeInPickett/ - a
    real, working starting point rather than an arbitrary placeholder.
    Uncertainty is 1e37 ("float freely"), not the page's "1e-37" - the
    latter is a typo in that example (a later block on the same page
    corrects it to 1e+37), and 1e-37 would instead freeze both parameters.
    """
    par = _base_par(spind=-1, knmax=0, chr_value="L", errtst=1e37, frac=-1, EWT=-1)
    par["PARAMS"] = _param_rows(
        pyckett.POSSIBLE_PARAMS_LINEAR,
        [(1, 6081.49), (2, -1.29e-3)],
    )
    return par


def symmetric_top_par():
    """A symmetric top: SPIND < 0 requests symmetric-rotor quanta.

    Values are CH3CN's, from
    https://spin.astro.uni-koeln.de/chapter/LinearMoleculeInPickett/ - a
    real, working starting point rather than an arbitrary placeholder.

    A true symmetric top's Hamiltonian is expressed directly in powers of
    N^2/K^2 (id 100/1000/200/1100/2000 below - B, A-B, -DJ, -DJK, -DK)
    rather than pyckett's A/B/C-reduction TYP codes (POSSIBLE_PARAMS_A/S),
    which don't cover this representation - so these ids/labels are
    written out directly instead of going through _param_rows().
    """
    par = _base_par(
        spind=-1, knmax=30, chr_value="S", nitr=5, IAX=6, WTPL=2, WTMN=2, EWT=1, DIAG=0,
    )
    par["PARAMS"] = [
        [1000, 148900.0744965263, 1e37, "A-B"],
        [100, 9198.899102551335, 1e37, "B"],
        [2000, -2.825727761558185, 1e37, "-DK"],
        [1100, -0.1774063654292496, 1e37, "-DJK"],
        [200, -0.003807510349803836, 1e37, "-DJ"],
    ]
    return par


def asymmetric_top_par(reduction="a_reduction"):
    """An asymmetric top: A, B, C plus the 5 quartic centrifugal distortion terms.

    Parameters
    ----------
    reduction: str
        "a_reduction" (DJ, DJK, DK, deltaJ, deltaK) or "s_reduction"
        (DJ, DJK, DK, d1, d2).
    """
    is_s = reduction == "s_reduction"
    source = pyckett.POSSIBLE_PARAMS_S if is_s else pyckett.POSSIBLE_PARAMS_A
    quartic_ids = (2, 11, 20, 401, 500) if is_s else (2, 11, 20, 401, 410)

    par = _base_par(spind=1, knmax=20, chr_value="S" if is_s else "A")
    rotational = [(100, 9000.0), (200, 5000.0), (300, 3000.0)]
    quartic = [(qid, 1e-37) for qid in quartic_ids]
    par["PARAMS"] = _param_rows(source, rotational + quartic)
    return par


def default_int():
    """A generic *.int with a single a-type transition dipole moment of 1 Debye."""
    return {
        "TITLE": "New Molecule",
        "FLAGS": 1,
        "TAG": 1,
        "QROT": 1000.0,
        "FBGN": 0,
        "FEND": 100,
        "STR0": -10.0,
        "STR1": -10.0,
        "FQLIM": 500.0,
        "INTS": [[1, 1.0]],
    }


def empty_lin():
    """A *.lin with no assignments yet, but the correct columns/dtypes."""
    dtypes = pyckett.lin_dtypes_from_quanta()
    columns = list(dtypes.keys()) + ["filename"]
    df = pd.DataFrame(columns=columns)
    return df.astype({**dtypes, "filename": str})
