# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : Parse *.fit residuals text into a DataFrame

import os
import tempfile

import pyckett


def parse_fit_df(content):
    """Parse *.fit text via pyckett.fit_to_df, which only reads from a real path."""
    fd, tmp_path = tempfile.mkstemp(suffix=".fit")
    try:
        with os.fdopen(fd, "w") as file:
            file.write(content)
        return pyckett.fit_to_df(tmp_path)
    finally:
        os.unlink(tmp_path)
