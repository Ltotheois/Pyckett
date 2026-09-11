# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Shared red/orange "flagged" highlight colors for table rows

from PyQt6.QtGui import QColor

# Solid, saturated colors (not pastel) paired with a fixed text color, so
# flagged rows keep sufficient contrast in both light and dark mode - the
# ambient theme's own text color is deliberately not used here since it
# would only be readable against one of the two backgrounds it's tuned for.
FLAG_TEXT_COLOR = QColor("#ffffff")
FLAG_RED = QColor("#c0392b")
FLAG_ORANGE = QColor("#a15c00")
