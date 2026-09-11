# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Application icon loading

import sys
from importlib import resources

from PyQt6.QtGui import QIcon


def load_app_icon():
    """Return the application icon.

    Uses the glass-style variant on macOS (see resources/icon_mac.png),
    the plain artwork everywhere else.
    """
    name = "icon_mac.png" if sys.platform == "darwin" else "icon.png"
    ref = resources.files("pyckett.gui") / "resources" / name
    with resources.as_file(ref) as path:
        return QIcon(str(path))
