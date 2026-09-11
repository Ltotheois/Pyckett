# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Filesystem locations used by the Pyckett GUI

import os
import sys
from pathlib import Path


def app_data_dir():
    """Return the directory the GUI stores its own data in (history snapshots, etc).

    Returns
    -------
    Path
        The application data directory. Created if it does not exist yet.
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    directory = base / "PyckettGUI"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def history_dir():
    """Return the directory holding per-project version history snapshots."""
    directory = app_data_dir() / "history"
    directory.mkdir(parents=True, exist_ok=True)
    return directory
