# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Per-project version history for *.par, *.lin, and *.int content

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone

from pyckett.gui.paths import history_dir

KINDS = ("par", "lin", "int")
_SNAPSHOT_RE = re.compile(r"^(\d{4})_")


def _hash_contents(contents):
    hasher = hashlib.sha256()
    for kind in KINDS:
        hasher.update(kind.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update((contents.get(kind) or "").encode("utf-8"))
        hasher.update(b"\0")
    return hasher.hexdigest()


class HistoryStore:
    """Append-only snapshot store for a project's *.par/*.lin/*.int content.

    Snapshots are kept outside of any project directory (under the user's app
    data directory, keyed by project id), so a project is never tied to a
    single folder and version history never interferes with a git repository
    the user might already have in their own working folders.
    """

    def __init__(self, project_id, base_dir=None):
        self.project_id = project_id
        self.directory = (base_dir or history_dir()) / project_id
        self.directory.mkdir(parents=True, exist_ok=True)

    def _snapshot_dirs(self):
        if not self.directory.is_dir():
            return []
        dirs = [
            d
            for d in self.directory.iterdir()
            if d.is_dir() and _SNAPSHOT_RE.match(d.name)
        ]
        return sorted(dirs, key=lambda d: d.name)

    def _next_index(self):
        dirs = self._snapshot_dirs()
        if not dirs:
            return 1
        last_index = int(_SNAPSHOT_RE.match(dirs[-1].name).group(1))
        return last_index + 1

    def snapshot(self, label, contents):
        """Record a new snapshot, unless it is identical to the previous one.

        Parameters
        ----------
        label: str
            Short human-readable description of why the snapshot was taken.
        contents: dict
            Maps a subset of {"par", "lin", "int"} to the file content that
            should be recorded for that kind.

        Returns
        -------
        str or None
            The id of the newly created snapshot, or None if it was skipped
            because it was identical to the previous snapshot.
        """
        contents = {kind: contents[kind] for kind in KINDS if kind in contents}
        new_hash = _hash_contents(contents)

        # Self-heal: the directory can vanish out from under a running
        # project (e.g. app-data cleanup, or the user deleting it by hand).
        self.directory.mkdir(parents=True, exist_ok=True)

        existing = self._snapshot_dirs()
        if existing:
            with open(existing[-1] / "meta.json", "r") as file:
                previous_meta = json.load(file)
            if previous_meta.get("hash") == new_hash:
                return None

        index = self._next_index()
        snapshot_id = f"{index:04d}_{label}"
        snapshot_dir = self.directory / snapshot_id
        snapshot_dir.mkdir(parents=True, exist_ok=False)

        for kind, content in contents.items():
            with open(snapshot_dir / f"{kind}.{kind}", "w+") as file:
                file.write(content)

        meta = {
            "label": label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kinds": sorted(contents.keys()),
            "hash": new_hash,
        }
        with open(snapshot_dir / "meta.json", "w+") as file:
            json.dump(meta, file, indent=2)

        return snapshot_id

    def list_snapshots(self):
        """List all recorded snapshots, oldest first.

        Returns
        -------
        list of dict
            Each dict holds id, label, timestamp, and kinds.
        """
        snapshots = []
        for snapshot_dir in self._snapshot_dirs():
            meta_path = snapshot_dir / "meta.json"
            if not meta_path.is_file():
                continue
            with open(meta_path, "r") as file:
                meta = json.load(file)
            snapshots.append(
                {
                    "id": snapshot_dir.name,
                    "label": meta.get("label", ""),
                    "timestamp": meta.get("timestamp", ""),
                    "kinds": meta.get("kinds", []),
                }
            )
        return snapshots

    def restore(self, snapshot_id):
        """Return the recorded content of a snapshot.

        Parameters
        ----------
        snapshot_id: str
            Id of the snapshot, as returned by list_snapshots().

        Returns
        -------
        dict
            Maps kind ("par"/"lin"/"int") to its recorded file content, for
            whichever kinds were part of that snapshot.
        """
        snapshot_dir = self.directory / snapshot_id
        if not snapshot_dir.is_dir():
            raise FileNotFoundError(f"No snapshot '{snapshot_id}' found.")

        contents = {}
        for kind in KINDS:
            path = snapshot_dir / f"{kind}.{kind}"
            if path.is_file():
                with open(path, "r") as file:
                    contents[kind] = file.read()
        return contents

    def delete_all(self):
        """Remove all snapshots for this project (used when a project is closed for good)."""
        shutil.rmtree(self.directory, ignore_errors=True)
