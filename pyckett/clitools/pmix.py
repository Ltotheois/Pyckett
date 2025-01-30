#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : CLI tool for showing parameter uncertainties

import argparse
import pyckett


def pmix():
    parser = argparse.ArgumentParser(prog="Plot mixing coefficients from .egy file")

    parser.add_argument("egyfile", type=str, help="Filename of the .egy file")
    parser.add_argument("queries", nargs="+", help="Queries for plots")

    args = parser.parse_args()

    egy = pyckett.egy_to_df(args.egyfile)

    pyckett.mixing_coefficient(egy, args.queries)
