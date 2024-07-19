#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : CLI tool to run SPFIT/SPCAT

import os
import subprocess
import argparse

subprocess_kwargs = {
    "stdout": subprocess.PIPE,
    "stderr": subprocess.PIPE,
}


def runfit():
    parser = argparse.ArgumentParser(prog="Run SPFIT")
    parser.add_argument(
        "filenames", type=str, nargs="+", help="Filenames to pass to SPFIT"
    )
    args = parser.parse_args()

    path = os.environ.get("PYCKETT_SPFIT_PATH", "spfit")
    command = [path, *args.filenames]

    with subprocess.Popen(command, **subprocess_kwargs) as process:
        while process.poll() is None:
            text = process.stdout.read1().decode("utf-8")
            print(text, end="", flush=True)

        text = process.stdout.read().decode("utf-8")
        print(text)


def runpredictions():
    parser = argparse.ArgumentParser(prog="Run SPCAT")
    parser.add_argument(
        "filenames", type=str, nargs="+", help="Filenames to pass to SPCAT"
    )
    args = parser.parse_args()

    path = os.environ.get("PYCKETT_SPCAT_PATH", "spcat")
    command = [path, *args.filenames]

    with subprocess.Popen(command, **subprocess_kwargs) as process:
        while process.poll() is None:
            text = process.stdout.read1().decode("utf-8")
            print(text, end="", flush=True)

        text = process.stdout.read().decode("utf-8")
        print(text)
