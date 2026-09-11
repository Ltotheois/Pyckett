# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Search pyckett's parameter-coding dictionaries by label

import pyckett

# Rotational parameters, keyed by reduction (which set of labels/codes
# applies); "Linear" covers linear molecules (KNMIN == KNMAX == 0).
ROTATIONAL_DICTS = {
    "A-Reduction": pyckett.POSSIBLE_PARAMS_A,
    "S-Reduction": pyckett.POSSIBLE_PARAMS_S,
    "Linear": pyckett.POSSIBLE_PARAMS_LINEAR,
}

# Interaction (off-diagonal, between two vibrational states) parameters.
INTERACTION_DICT = pyckett.POSSIBLE_PARAMS_INTERACTION

KINDS = ("A-Reduction", "S-Reduction", "Linear", "Interaction")


def is_linear_molecule(par):
    """A *.par header models a linear molecule when KNMIN and KNMAX are both 0."""
    return par.get("KNMIN", 0) == 0 and par.get("KNMAX", 0) == 0


def _base_id(param_id, vib_digits):
    """Strip a real PARAMS id down to its vibrational-state-independent type code.

    The inverse of full_parameter_id(): v1/v2 are zeroed out and the id is
    reformatted at vib_digits=0 (the same width POSSIBLE_PARAMS_* keys use),
    so the result can be looked up directly in those dicts regardless of
    which vibrational state(s) the real parameter happens to belong to.
    """
    parsed = pyckett.parse_param_id(param_id, vib_digits)
    parsed["v1"] = 0
    parsed["v2"] = 0
    return pyckett.format_param_id(parsed, 0)


def default_kind(par):
    """A reasonable default search dictionary for this *.par file.

    Linear molecules always default to "Linear". Otherwise, check which of
    A-Reduction/S-Reduction the file's already-used PARAMS ids exclusively
    belong to. Many low-order terms (A, B, C, DJ, DJK, DK, ...) are shared
    between both reductions (same code, same meaning), so those never
    discriminate - only a code that exists in just ONE of the two dicts
    (e.g. an S-reduction-specific sextic term) counts. If every such
    exclusive id found unanimously points at one reduction, preselect it
    (e.g. a molecule already fit with S-reduction terms defaults to
    S-Reduction); if none are found (only shared terms so far) or they
    disagree, fall back to "A-Reduction".
    """
    if is_linear_molecule(par):
        return "Linear"

    vib_digits = pyckett.get_vib_digits(par)
    found_a_exclusive = found_s_exclusive = False
    for param in par.get("PARAMS", []):
        base_id = _base_id(param[0], vib_digits)
        in_a = base_id in pyckett.POSSIBLE_PARAMS_A
        in_s = base_id in pyckett.POSSIBLE_PARAMS_S
        if in_a and not in_s:
            found_a_exclusive = True
        elif in_s and not in_a:
            found_s_exclusive = True

    if found_s_exclusive and not found_a_exclusive:
        return "S-Reduction"
    return "A-Reduction"


def set_parameter_comments(par, rotational_kind):
    """Set every PARAMS row's comment to its correct pyckett label.

    Rotational/diagonal parameters (v1 == v2, including the "global" -
    applies to all states - sentinel) are looked up in ``rotational_kind``'s
    dict (one of the ROTATIONAL_DICTS keys: "A-Reduction"/"S-Reduction"/
    "Linear" - see default_kind() for a reasonable choice to preselect).
    Interaction (off-diagonal, v1 != v2) parameters are always looked up in
    POSSIBLE_PARAMS_INTERACTION instead, regardless of rotational_kind,
    since interaction codes aren't reduction-specific.

    A parameter whose base id isn't found in the relevant dict is left
    untouched - its existing comment is kept rather than guessing wrong or
    blanking a manually written note.

    Returns
    -------
    int
        The number of PARAMS rows whose comment was actually changed.
    """
    vib_digits = pyckett.get_vib_digits(par)
    rotational_dict = ROTATIONAL_DICTS[rotational_kind]

    updated = 0
    for param in par.get("PARAMS", []):
        parsed = pyckett.parse_param_id(param[0], vib_digits)
        base_id = _base_id(param[0], vib_digits)
        source = rotational_dict if parsed["v1"] == parsed["v2"] else INTERACTION_DICT

        entry = source.get(base_id)
        if entry is None:
            continue

        label = entry[0]
        while len(param) < 4:
            param.append("")
        if param[3] != label:
            param[3] = label
            updated += 1

    return updated


def v_column_position(par):
    """Return the 1-indexed *.lin qn-slot the vibrational state id "v" belongs
    at, or None if there's only one vibrational state (no v column at all).

    Per SPFIT/SPCAT's quantum-number format (spinv.pdf, "Format of Quantum
    Numbers"): "If the number of vibrations is one, then v is not
    included." Once NVIB is at least 2, v appears right after N (and after
    K, or Ka/Kc):
        linear molecule (is_linear_molecule):  N, v, J, ...       -> 2
        symmetric top   (SPIND < 0):           N, K, v, J, ...    -> 3
        asymmetric top  (otherwise):           N, Ka, Kc, v, J...  -> 4
    """
    if abs(par.get("NVIB", 1)) < 2:
        return None
    if is_linear_molecule(par):
        return 2
    if par.get("SPIND", 1) < 0:
        return 3
    return 4


def _dict_for(kind):
    if kind == "Interaction":
        return INTERACTION_DICT
    return ROTATIONAL_DICTS[kind]


def search_labels(kind, query=""):
    """Search a parameter-coding dictionary by label.

    Parameters
    ----------
    kind: str
        One of "A-Reduction", "S-Reduction", "Linear", "Interaction".
    query: str
        Case-insensitive substring to filter labels by; empty returns everything.

    Returns
    -------
    list of (label, base_id)
        base_id is the vibrational-state-independent code stored in
        pyckett's POSSIBLE_PARAMS_* dictionaries - combine with a state (or
        pair of states, for interaction parameters) via full_parameter_id()
        to get a real, usable parameter id.
    """
    source = _dict_for(kind)
    query = query.strip().lower()
    # Preserve the dict's own definition order (e.g. A, B, C, then the
    # quartic terms, then sextic, ...) rather than re-sorting - that order
    # already reflects the physical/hierarchical grouping pyckett defines
    # POSSIBLE_PARAMS_* in, dicts keep insertion order.
    return [
        (label, base_id) for base_id, (label, _children) in source.items() if query in label.lower()
    ]


def full_parameter_id(base_id, vib_digits, v1, v2=None):
    """Combine a type-only base_id (from POSSIBLE_PARAMS_*) with vibrational state(s).

    Mirrors exactly how pyckett.clitools.addparameters builds candidate ids:
    a base_id encodes everything except which vibrational state(s) the
    parameter belongs to, so the state number(s) are merged in afterwards
    and the id is re-formatted at the file's real vib_digits width.

    Parameters
    ----------
    base_id: int
        A value from search_labels().
    vib_digits: int
        From pyckett.get_vib_digits(par).
    v1: int
        The vibrational state (rotational parameters: both v1 and v2 equal
        this; use pyckett.get_all_states(vib_digits) for a global parameter).
    v2: int or None
        The second vibrational state, for an interaction parameter. Defaults
        to v1 (i.e. a rotational/diagonal parameter).

    Returns
    -------
    int
        A full parameter id ready to use in a *.par PARAMS row.
    """
    if v2 is None:
        v2 = v1
    type_dict = pyckett.parse_param_id(base_id, 0)
    type_dict["v1"] = v1
    type_dict["v2"] = v2
    return pyckett.format_param_id(type_dict, vib_digits)
