# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Rearrange a *.lin file's fixed qn1..qn{quanta} columns when
#                 the vibrational-state identifier "v" appears, disappears,
#                 or moves - see parameter_lookup.v_column_position and
#                 Project._sync_vib_state_encoding.

import pandas as pd
import pyckett

QUANTA = 6


def _build_column_mapping(quanta, old_position, new_position):
    """Return a length-``quanta`` list describing where each new qn slot's
    value comes from, moving whatever was at ``old_position`` to
    ``new_position`` (1-indexed; either may be None for "no v column") while
    keeping every other quantum number in its original relative order.

    Each entry is ("copy", old_index) | ("default",) | ("empty",), where
    old_index is 0-indexed into the original quanta columns.
    """
    other_slots = [i for i in range(quanta) if old_position is None or i != old_position - 1]

    result = [None] * quanta
    if new_position is not None:
        result[new_position - 1] = ("copy", old_position - 1) if old_position is not None else ("default",)

    remaining_targets = [i for i in range(quanta) if result[i] is None]
    for target, source in zip(remaining_targets, other_slots):
        result[target] = ("copy", source)
    for target in remaining_targets[len(other_slots):]:
        result[target] = ("empty",)

    return result


def reindex_lin_vib_column(lin_df, old_position, new_position, quanta=QUANTA):
    """Rearrange qnu*/qnl* so the "v" quantum number moves from
    ``old_position`` to ``new_position`` (either may be None), shifting
    every other quantum number to fill the gap or make room.

    A freshly appearing v column (old_position is None) defaults to 0 (the
    ground vibrational state) for every existing row - lines assigned
    before NVIB grew past 1 implicitly all belonged to that one state.

    Returns
    -------
    (new_df, dropped_data)
        dropped_data is True if a still-in-use quantum number was pushed off
        the end of the fixed qn1..qn{quanta} window (only possible when
        inserting a new v column into a *.lin file that already used every
        available slot) - the caller should warn before applying, since real
        assignments would be silently discarded.
    """
    if old_position == new_position:
        return lin_df, False

    mapping = _build_column_mapping(quanta, old_position, new_position)
    used_sources = {entry[1] for entry in mapping if entry[0] == "copy"}
    if old_position is not None:
        # The old v value itself is deliberately consumed (removed, or
        # copied into its new spot) - never "accidentally" dropped data,
        # even when it isn't a copy source (removing v with no replacement).
        used_sources.add(old_position - 1)

    new_df = lin_df.copy()
    dropped_data = False
    for ul in ("u", "l"):
        old_cols = [
            lin_df[f"qn{ul}{i + 1}"] if f"qn{ul}{i + 1}" in lin_df.columns
            else pd.Series(pyckett.SENTINEL, index=lin_df.index)
            for i in range(quanta)
        ]

        for i, col in enumerate(old_cols):
            if i not in used_sources and not (col == pyckett.SENTINEL).all():
                dropped_data = True

        for target_idx, entry in enumerate(mapping):
            name = f"qn{ul}{target_idx + 1}"
            kind = entry[0]
            if kind == "copy":
                new_df[name] = old_cols[entry[1]].to_numpy()
            elif kind == "default":
                new_df[name] = 0
            else:
                new_df[name] = pyckett.SENTINEL
            new_df[name] = new_df[name].astype("int64")

    return new_df, dropped_data
