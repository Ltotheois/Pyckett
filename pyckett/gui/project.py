# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Non-Qt data model for projects and their open files

import copy
from pathlib import Path
from uuid import uuid4

import pyckett

from pyckett.gui.history import HistoryStore
from pyckett.gui.lin_vib_column import reindex_lin_vib_column
from pyckett.gui.parameter_lookup import v_column_position

# Kinds that only ever have a single open Document per project.
SINGLETON_KINDS = ("par", "var", "lin", "int", "cat", "egy")

# Kinds that participate in version history.
VERSIONED_KINDS = ("par", "lin", "int")

# Kinds whose data is already plain text (rendered/parsed as-is, no
# dict/dataframe conversion): the generic "text" kind (informational
# messages with no real file behind them), plus "fit"/"out" - SPFIT's
# residuals file and SPFIT/SPCAT's stdout report, both plain text on disk.
TEXT_LIKE_KINDS = ("text", "fit", "out")

LOADERS = {
    "par": pyckett.parvar_to_dict,
    "var": pyckett.parvar_to_dict,
    "lin": lambda src: pyckett.lin_to_df(src, sort=False),
    "int": pyckett.int_to_dict,
    "cat": pyckett.cat_to_df,
    "egy": pyckett.egy_to_df,
}

SAVERS = {
    "par": pyckett.dict_to_parvar,
    "var": pyckett.dict_to_parvar,
    "lin": pyckett.df_to_lin,
    "int": pyckett.dict_to_int,
    "cat": pyckett.df_to_cat,
    "egy": pyckett.df_to_egy,
}

# Kinds the user can hand-edit in the GUI (the rest are read-only viewers of
# SPFIT/SPCAT output).
EDITABLE_KINDS = ("par", "lin", "int")

SUFFIX_TO_KIND = {
    ".par": "par",
    ".var": "var",
    ".lin": "lin",
    ".int": "int",
    ".cat": "cat",
    ".egy": "egy",
}

KIND_LABELS = {
    "par": "Parameters",
    "var": "Fitted Parameters",
    "lin": "Assignments",
    "int": "Intensities",
    "cat": "Predictions",
    "egy": "Energy Levels",
    "fit": "Residuals",
    "out": "Output",
}


def infer_kind_from_suffix(path):
    """Infer a Document kind from a file's suffix, defaulting to 'text'."""
    return SUFFIX_TO_KIND.get(Path(path).suffix.lower(), "text")


class Document:
    """One open file (or in-memory result) inside a Project."""

    def __init__(self, kind, data, label, path=None, dirty=False):
        self.kind = kind
        self.data = data
        self.label = label
        self.path = Path(path) if path else None
        self.dirty = dirty

    @classmethod
    def load(cls, path, kind=None):
        """Load a Document from a file on disk."""
        path = Path(path)
        kind = kind or infer_kind_from_suffix(path)

        if kind in TEXT_LIKE_KINDS:
            with open(path, "r") as file:
                data = file.read()
        else:
            data = LOADERS[kind](path)

        return cls(kind, data, label=path.name, path=path, dirty=False)

    @classmethod
    def from_content(cls, kind, content, label, path=None, dirty=True):
        """Build a Document by parsing raw file content (e.g. from a history snapshot)."""
        if kind in TEXT_LIKE_KINDS:
            data = content
        else:
            data = LOADERS[kind](pyckett.str_to_stream(content))
        return cls(kind, data, label=label, path=path, dirty=dirty)

    def render(self):
        """Serialize this document's data back to file content.

        Returns
        -------
        str
            The content as it would be written to disk.
        """
        if self.kind in TEXT_LIKE_KINDS:
            return self.data
        return SAVERS[self.kind](self.data)

    def save(self, path=None):
        """Write this document's content to disk.

        Parameters
        ----------
        path: str, Path, or None
            Where to save. Falls back to the document's existing path.

        Returns
        -------
        Path
            The path that was written to.
        """
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError(f"Document '{self.label}' has no path to save to.")

        with open(target, "w+") as file:
            file.write(self.render())

        self.path = target
        # For par/lin/int/var/cat/egy the label is just the filename, so it
        # follows a Save As to a new path. text/fit/out's label is instead a
        # semantic slot ("SPFIT Output", ...) that project.get_text() and
        # the spfit/spcat tabs look documents up by - renaming it here would
        # silently disconnect it from its tab.
        if self.kind not in TEXT_LIKE_KINDS:
            self.label = target.name
        self.dirty = False
        return target

    def copy_data(self):
        """Return a deep, independent copy of this document's data."""
        if self.kind in TEXT_LIKE_KINDS:
            return self.data
        if hasattr(self.data, "columns"):
            # pandas DataFrame: .copy() already deep-copies its contents.
            return self.data.copy()
        return copy.deepcopy(self.data)

    @property
    def display_title(self):
        title = self.label or KIND_LABELS.get(self.kind, self.kind)
        return f"{title}*" if self.dirty else title


class Project:
    """A named, in-memory group of open Documents plus their version history.

    A project is a loose collection of files: they can each live at a
    different path on disk (or have no path at all yet), there is no shared
    working directory. Saving a document writes it back to its own path.
    """

    def __init__(self, name="Untitled Project", history_base_dir=None):
        self.id = str(uuid4())
        self.name = name
        self.documents = []
        self._history_base_dir = history_base_dir
        self.history = HistoryStore(self.id, base_dir=history_base_dir)
        # Tracks vib_digits/v_column_position for the *specific* par Document
        # instance last seen, so a freshly loaded/restored par file (a new
        # Document, even if it replaces the old one) is never mistaken for
        # an NVIB edit - see _sync_vib_state_encoding.
        self._vib_digits_doc = None
        self._known_vib_digits = None
        self._known_v_position = None
        # Non-blocking, user-facing notices raised by internal sync logic
        # (e.g. *.lin data discarded for lack of room) - Qt callers should
        # drain and display these after calling into project logic.
        self.pending_warnings = []
        # Set when sync_par_fields() replaced a document's *.data outright
        # (a PARAMS/IDIP recode, or a *.lin column reindex) rather than just
        # updating a header count - a lightweight tab-title refresh isn't
        # enough in that case, the affected tab's table model would keep
        # showing stale data. Qt callers should check-and-clear this after
        # calling sync_par_fields() to decide between a full tab rebuild and
        # a lightweight title-only refresh.
        self.vib_state_encoding_changed = False

    def add_document(self, document, replace_singleton=True):
        """Add a document to the project.

        For singleton kinds (par/var/bak/lin/int/cat/egy) this replaces any
        existing document of the same kind. Text-like documents (text/fit/
        out) are matched (and replaced) by label instead, so re-running an
        action updates its output tab instead of piling up duplicates.
        """
        if document.kind in SINGLETON_KINDS and replace_singleton:
            existing = self.get(document.kind)
            if existing is not None:
                self.documents.remove(existing)
        elif document.kind in TEXT_LIKE_KINDS:
            existing = next(
                (d for d in self.documents if d.kind in TEXT_LIKE_KINDS and d.label == document.label),
                None,
            )
            if existing is not None:
                self.documents.remove(existing)

        self.documents.append(document)
        self.sync_par_fields()
        return document

    def remove_document(self, document):
        if document in self.documents:
            self.documents.remove(document)

    def get(self, kind):
        """Return the (singleton) document of a given kind, or None."""
        return next((d for d in self.documents if d.kind == kind), None)

    def get_text(self, label):
        return next((d for d in self.documents if d.kind in TEXT_LIKE_KINDS and d.label == label), None)

    @property
    def has_unsaved_changes(self):
        return any(d.dirty for d in self.documents)

    def sync_par_fields(self):
        """Keep the GUI-managed *.par header fields correct, so the user never has to.

        NPAR/NLINE cap how many parameters/lines SPFIT actually reads, so
        they must always be at least the real count in the open *.par/*.lin
        documents or edits (an added parameter, a new assignment) would be
        silently ignored on the next fit; NXPAR (reserved for extra
        parameters) is always 0 for files edited through this GUI. None of
        the three need the user's attention, so the header form hides them
        and this keeps them correct on every load/edit instead.

        Returns
        -------
        bool
            True if any of these fields changed value.
        """
        par_doc = self.get("par")
        if par_doc is None:
            return False

        changed = self._sync_vib_state_encoding(par_doc)

        new_npar = len(par_doc.data["PARAMS"])
        if par_doc.data.get("NPAR") != new_npar:
            par_doc.data["NPAR"] = new_npar
            changed = True

        lin_doc = self.get("lin")
        if lin_doc is not None:
            new_nline = len(lin_doc.data)
            if par_doc.data.get("NLINE") != new_nline:
                par_doc.data["NLINE"] = new_nline
                changed = True

        if par_doc.data.get("NXPAR") != 0:
            par_doc.data["NXPAR"] = 0
            changed = True

        if changed:
            par_doc.dirty = True
        return changed

    def _sync_vib_state_encoding(self, par_doc):
        """Keep *.par/*.int/*.lin consistent whenever NVIB changes.

        Two independent things depend on NVIB and must each be kept in
        sync, on two different thresholds:

        - *.par PARAMS ids and *.int IDIPs pack v1/v2 at a width of
          vib_digits = number of decimal digits in NVIB (see
          recode_param_id_vib_digits/recode_idip_vib_digits) - this changes
          at every power-of-ten boundary (9 -> 10 states, 99 -> 100, ...).
        - *.lin only carries a "v" (vibrational state) quantum-number column
          at all once there are >= 2 vibrational states (spinv.pdf, "Format
          of Quantum Numbers": "If the number of vibrations is one, then v
          is not included") - a separate threshold (crossing 1 <-> 2
          states), at a molecule-type-dependent column position (see
          parameter_lookup.v_column_position).

        A freshly loaded/restored par document is a different object even
        though it replaces the project's old "par" singleton, so it's never
        mistaken for an in-place NVIB edit - its own PARAMS/IDIPs/*.lin are
        already consistent with its own NVIB.

        Returns
        -------
        bool
            True if anything changed (so par_doc.dirty should be set).
        """
        new_vib_digits = pyckett.get_vib_digits(par_doc.data)
        new_v_position = v_column_position(par_doc.data)

        if par_doc is not self._vib_digits_doc:
            self._vib_digits_doc = par_doc
            self._known_vib_digits = new_vib_digits
            self._known_v_position = new_v_position
            return False

        old_vib_digits = self._known_vib_digits
        old_v_position = self._known_v_position
        self._known_vib_digits = new_vib_digits
        self._known_v_position = new_v_position

        changed = False

        if new_vib_digits != old_vib_digits:
            for param in par_doc.data["PARAMS"]:
                param[0] = pyckett.recode_param_id_vib_digits(param[0], old_vib_digits, new_vib_digits)

            int_doc = self.get("int")
            if int_doc is not None:
                for intline in int_doc.data["INTS"]:
                    intline[0] = pyckett.recode_idip_vib_digits(intline[0], old_vib_digits, new_vib_digits)
                int_doc.dirty = True

            changed = True

        if new_v_position != old_v_position:
            lin_doc = self.get("lin")
            if lin_doc is not None:
                new_df, dropped_data = reindex_lin_vib_column(lin_doc.data, old_v_position, new_v_position)
                lin_doc.data = new_df
                lin_doc.dirty = True
                if dropped_data:
                    self.pending_warnings.append(
                        "Growing the number of vibrational states added a \"v\" quantum "
                        "number column to *.lin, but there was no room left in its fixed "
                        "6-quantum-number window - the last quantum number of some "
                        "assignments has been discarded. Please check the affected lines."
                    )

            changed = True

        if changed:
            self.vib_state_encoding_changed = True

        return changed

    def snapshot(self, label):
        """Record the project's current par/lin/int content as a new history snapshot."""
        contents = {}
        for kind in VERSIONED_KINDS:
            doc = self.get(kind)
            if doc is not None:
                contents[kind] = doc.render()
        if not contents:
            return None
        return self.history.snapshot(label, contents)

    def restore_snapshot(self, snapshot_id):
        """Restore par/lin/int documents to the content recorded in a snapshot.

        Returns
        -------
        list of str
            The kinds ("par"/"lin"/"int") that were restored.
        """
        contents = self.history.restore(snapshot_id)
        for kind, content in contents.items():
            existing = self.get(kind)
            label = existing.label if existing is not None else f"{kind}.{kind}"
            path = existing.path if existing is not None else None
            document = Document.from_content(kind, content, label=label, path=path, dirty=True)
            self.add_document(document)  # also re-syncs NPAR/NLINE/NXPAR
        self.snapshot(f"Restored from {snapshot_id}")
        return list(contents.keys())

    def mutate(self, kind, snapshot_label, mutate_fn):
        """Snapshot history, then apply mutate_fn(document) to the document of the given kind.

        Used for every action that changes par/lin/int content in place:
        manual saves, duplicate removal, and applying an add/omit-parameter
        candidate.
        """
        document = self.get(kind)
        if document is None:
            raise ValueError(f"Project has no open '{kind}' document.")
        self.snapshot(snapshot_label)
        mutate_fn(document)
        document.dirty = True
        self.sync_par_fields()
        return document

    def save_document(self, document, path=None):
        """Snapshot history, then save a par/lin/int document to disk."""
        if document.kind in VERSIONED_KINDS:
            self.snapshot(f"Before saving {document.label}")
        return document.save(path)

    def clone_with_new_par(self, name, new_params):
        """Create a new Project carrying over lin/int unchanged and PARAMS replaced.

        Used by the "Open in new project" action after testing an
        add/omit-parameter candidate: ``new_params`` is the candidate's
        PARAMS list (as returned in the "par" key of an add_parameter/
        omit_parameter result) - the rest of the *.par header is copied
        unchanged from the current project, matching how "Apply to current
        project" only ever swaps PARAMS. *.lin/*.int (which the candidate
        didn't change) are copied over as-is. Fit/prediction outputs (var/
        bak/cat/egy/text) are not carried over since they would be stale
        relative to the new parameters.
        """
        new_project = Project(name=name, history_base_dir=self._history_base_dir)

        par_doc = self.get("par")
        if par_doc is not None:
            new_par_data = par_doc.copy_data()
            new_par_data["PARAMS"] = copy.deepcopy(new_params)
            new_project.add_document(
                Document("par", new_par_data, label=par_doc.label, path=None, dirty=True)
            )

        for kind in ("lin", "int"):
            doc = self.get(kind)
            if doc is not None:
                new_project.add_document(
                    Document(kind, doc.copy_data(), label=doc.label, path=doc.path, dirty=False)
                )

        new_project.sync_par_fields()
        new_project.snapshot("Cloned with candidate parameters")
        return new_project
