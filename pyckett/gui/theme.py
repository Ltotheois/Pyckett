# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Light/dark theme detection

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication


def is_dark_theme():
    """Whether the application is currently in dark mode."""
    return QGuiApplication.instance().styleHints().colorScheme() == Qt.ColorScheme.Dark
