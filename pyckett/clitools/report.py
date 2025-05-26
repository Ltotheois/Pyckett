#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : CLI tool for showing parameter uncertainties

import os
import argparse
import pyckett

def report():
    parser = argparse.ArgumentParser(prog="Summarize an analysis")

    parser.add_argument("linfile", type=str, help="Filename of the .lin file")
    parser.add_argument(
        "catfile", type=str, nargs="?", help="Filename of the .cat file"
    )

    parser.add_argument(
        "--noblends",
        action="store_false",
        default=None,
        dest='blends',
        help="Skip blend treatment",
    )

    parser.add_argument(
        "--noq",
        type=int,
        nargs=1,
        help="Specify number of quantum numbers",
    )

    args = parser.parse_args()


    linfname = args.linfile
    base, ext = os.path.splitext(linfname)
    if not ext:
        linfname = linfname + ".lin"

    catfname = args.catfile if args.catfile else linfname.replace(".lin", ".cat")

    lin = pyckett.lin_to_df(linfname, sort=False)
    try:
        cat = pyckett.cat_to_df(catfname, sort=False)
    except FileNotFoundError:
        cat = None
        pass

    report, _ = pyckett.create_report(lin, cat, blends=args.blends, noq=args.noq)
    print(report)