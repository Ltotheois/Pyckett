#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : CLI tool to compute vibrational partition function

import numpy as np
import argparse


Temperatures = [
    300.000,
    225.000,
    150.000,
    75.000,
    37.500,
    18.750,
    9.37,
]

k = 1.380649e-23
h = 6.62607015e-34
c = 299792458

cm1_to_Joules = h * c * 100
factor = cm1_to_Joules / k


def vibpartitionfunction_at_temperature(vibenergies, T):
    Bfactors = [np.exp(-v * h * c / k / T * 100) for v in vibenergies]
    q = np.prod([1 / (1 - Bfactor) for Bfactor in Bfactors])
    return q


def vibpartitionfunction():
    parser = argparse.ArgumentParser(
        prog="Vibrational Partitionfunction",
        epilog="Calculate vibrational partition function in harmonic approximation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "vibenergies",
        nargs="*",
        type=float,
        help="Vibrational energies of fundamentals in cm-1",
    )
    parser.add_argument(
        "--temperatures",
        "-T",
        metavar="T",
        nargs="*",
        type=float,
        help="Additional temperatures in Kelvin to evaluate the partition function for",
    )

    args = parser.parse_args()

    if args.temperatures:
        Temperatures.extend(args.temperatures)
        Temperatures.sort(reverse=True)

    calc_partition_function(
        args.vibenergies,
        Temperatures,
        print_output=True,
    )


def calc_partition_function(
    vibenergies,
    temperatures,
    print_output=False,
):

    partition_functions = {
        T: vibpartitionfunction_at_temperature(vibenergies, T) for T in temperatures
    }

    if print_output:
        print(f"Vibrational partition function for {len(vibenergies)} modes\n")

        print("| Temp [K] |         Q(VIB)  |      log Q(VIB) |")
        print("| -------- | --------------- | --------------- |")

        for key, value in partition_functions.items():
            print(f"| {key:8.2f} | {value:15.4f} | {np.log10(value):15.4f} |")

    return partition_functions
