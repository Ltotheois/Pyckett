#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : CLI tool to compute partition function of egy file

import pyckett
import numpy as np
import argparse


recommended_use = """
Recommended procedure for determining the partition function

Determine the partition function for the ground state unless all vibrational states are treated correctly.
Set Jmax and Kmax sufficiently high for convergence but not too high (too avoid rollover). When in doubt check with the --convergence option.
"""

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

# This is the factor that is used in Pickett's spcat procedure
# The factor can be found in the file calcat.c in line 97
factor_pickett = 1.43878

# Uncomment the following line to check if the result fits to the spcat value
# factor = factor_pickett


def partitionfunction_at_temperature(egy_df, T, factor=factor):
    egy_df["tmp"] = (2 * egy_df["qn1"] + 1) * np.exp(-egy_df["egy"] * factor / T)
    return egy_df["tmp"].sum()


def partitionfunction():
    parser = argparse.ArgumentParser(
        prog="Partitionfunction",
        epilog=recommended_use,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("egyfile", type=str, help="Filename of the .egy file")
    parser.add_argument(
        "--temperatures",
        "-T",
        metavar="T",
        nargs="*",
        type=float,
        help="Additional temperatures in Kelvin to evaluate the partition function for",
    )
    parser.add_argument(
        "--pickett",
        "-p",
        dest="use_pickett_factor",
        action="store_true",
        help="Use the (less precise) numeric values from SPCAT",
    )
    parser.add_argument(
        "--convergence",
        "-c",
        dest="convergence",
        action="store_true",
        help="Produce convergence plot",
    )

    args = parser.parse_args()

    egyfilename = args.egyfile

    if args.temperatures:
        Temperatures.extend(args.temperatures)
        Temperatures.sort(reverse=True)

    egy_df = pyckett.egy_to_df(egyfilename)
    calc_partition_function(
        egy_df,
        Temperatures,
        convergence_plot=args.convergence,
        print_output=True,
        use_pickett_factor=args.use_pickett_factor,
    )


def calc_partition_function(
    egy_df,
    temperatures,
    print_output=False,
    convergence_plot=False,
    use_pickett_factor=False,
):
    Jmax = egy_df["qn1"].max()
    Kamax = egy_df["qn2"].max()
    Kcmax = egy_df["qn3"].max()

    tmp_factor = factor_pickett if use_pickett_factor else factor

    partition_functions = {
        T: partitionfunction_at_temperature(egy_df, T, factor=tmp_factor)
        for T in temperatures
    }

    if print_output:
        print(
            f"Partition function with J_max = {Jmax}, Ka_max = {Kamax}, Kc_max = {Kcmax}"
        )
        for key, value in partition_functions.items():
            print(f"T = {key:6.2f}; Q = {value:12.4f}; log Q = {np.log10(value):7.4f}")

    if convergence_plot:
        import matplotlib.pyplot as plt

        Js = np.arange(0, Jmax)
        results = np.zeros((len(temperatures), len(Js)))

        for i, Jupper in enumerate(Js):
            tmp_df = egy_df.loc[egy_df["qn1"] <= Jupper].copy()

            for j, T in enumerate(temperatures):
                pf = partitionfunction_at_temperature(tmp_df, T, factor=tmp_factor)
                results[j, i] = pf

        for j, T in enumerate(temperatures):
            ys = results[j, :]
            plt.plot(Js, ys, label=f"{T=} K")

        plt.xlabel(r"$J_{max}$")
        plt.ylabel("$Q$")
        plt.legend()
        plt.show()

    return partition_functions
