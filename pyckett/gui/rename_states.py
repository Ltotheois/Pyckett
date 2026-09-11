# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Core (Qt-free) logic for renaming/renumbering vibrational states
#                 across a project's *.par, *.lin, and *.int documents

import pyckett

DEFAULT_STATE_QN_INDEX = 4


def collect_state_ids(project, state_qn_index=DEFAULT_STATE_QN_INDEX):
    """Return the sorted, distinct vibrational-state ids currently in use.

    Looks at par's PARAMS (v1/v2, excluding the ALL_STATES "global" sentinel -
    that value never denotes a real, renameable state), lin's qnu{n}/qnl{n}
    columns at the given state quantum-number slot, and int's INTS (V1/V2).
    Any of the three documents may be absent.
    """
    states = set()

    par_doc = project.get("par")
    if par_doc is not None:
        vib_digits = pyckett.get_vib_digits(par_doc.data)
        all_states = pyckett.get_all_states(vib_digits)
        for param in par_doc.data["PARAMS"]:
            parsed = pyckett.parse_param_id(param[0], vib_digits)
            for key in ("v1", "v2"):
                if parsed[key] != all_states:
                    states.add(parsed[key])
        for state in par_doc.data["STATES"]:
            if "NVIB" in state:
                states.add(state["NVIB"])

        int_doc = project.get("int")
        if int_doc is not None:
            for idip, _dipole in int_doc.data["INTS"]:
                parsed = pyckett.parse_idip(idip, vib_digits)
                states.add(parsed["V1"])
                states.add(parsed["V2"])

    lin_doc = project.get("lin")
    if lin_doc is not None:
        qnu, qnl = f"qnu{state_qn_index}", f"qnl{state_qn_index}"
        if qnu in lin_doc.data.columns:
            states.update(lin_doc.data[qnu].unique().tolist())
        if qnl in lin_doc.data.columns:
            states.update(lin_doc.data[qnl].unique().tolist())

    return sorted(states)


def apply_state_rename(project, translation, state_qn_index=DEFAULT_STATE_QN_INDEX):
    """Apply a {old_state_id: new_state_id} translation to par/lin/int in place.

    A history snapshot is taken first. Only entries actually present in
    ``translation`` are remapped - any id not mentioned is left unchanged.
    The ALL_STATES "global" sentinel in par/PARAMS is never touched even if
    it happens to appear as a key, since it doesn't denote a real state.
    Vib_digits (and therefore id/IDIP width) is not changed here - only the
    state-id values are remapped, at whatever width the project currently
    uses; growing NVIB afterward is handled separately (see
    Project.sync_par_fields's automatic recode).
    """
    project.snapshot("Before renaming states")

    par_doc = project.get("par")
    lin_doc = project.get("lin")
    int_doc = project.get("int")

    if par_doc is not None:
        vib_digits = pyckett.get_vib_digits(par_doc.data)
        all_states = pyckett.get_all_states(vib_digits)

        for param in par_doc.data["PARAMS"]:
            parsed = pyckett.parse_param_id(param[0], vib_digits)
            changed = False
            for key in ("v1", "v2"):
                if parsed[key] != all_states and parsed[key] in translation:
                    parsed[key] = translation[parsed[key]]
                    changed = True
            if changed:
                param[0] = pyckett.format_param_id(parsed, vib_digits)

        for state in par_doc.data["STATES"]:
            if state.get("NVIB") in translation:
                state["NVIB"] = translation[state["NVIB"]]

        par_doc.dirty = True

        if int_doc is not None:
            for intline in int_doc.data["INTS"]:
                parsed = pyckett.parse_idip(intline[0], vib_digits)
                changed = False
                for key in ("V1", "V2"):
                    if parsed[key] in translation:
                        parsed[key] = translation[parsed[key]]
                        changed = True
                if changed:
                    intline[0] = pyckett.format_idip(parsed, vib_digits)
            int_doc.dirty = True

    if lin_doc is not None:
        qnu, qnl = f"qnu{state_qn_index}", f"qnl{state_qn_index}"
        if qnu in lin_doc.data.columns:
            lin_doc.data[qnu] = lin_doc.data[qnu].replace(translation)
        if qnl in lin_doc.data.columns:
            lin_doc.data[qnl] = lin_doc.data[qnl].replace(translation)
        lin_doc.dirty = True

    project.sync_par_fields()
