# Pyckett

Pyckett is a python wrapper around the SPFIT/SPCAT package (*H. M. Pickett, "The Fitting and Prediction of Vibration-Rotation Spectra with Spin Interactions," **J. Mol. Spectrosc. 148,** 371-377 (1991)*).

Install the package with pip by using the following command

```
pip install pyckett
```

If SPFIT and SPCAT cannot be executed via the commands *spfit* and *spcat* (if they are not in your PATH or have different names) point to them by setting the *PYCKETT_SPFIT_PATH* and *PYCKETT_SPCAT_PATH* environment variables to their full paths.

If you want to acknowledge LLWP, please cite the paper [On the Spectroscopy of Phosphaalkynes: Millimeter- and Submillimeter-Wave Study of C2H5CP](https://doi.org/10.1021/acs.jpca.4c02566).

# Documentation

Currently, the documentation is limited to the docstrings of the main library.
To easily access the docstrings you can run
```
pip install pdoc
pdoc pyckett
```
after having installed Pyckett.

The CLI tools provide help texts via the -h or --help flags.

# CLI Tools

Pyckett provides a set of command line utilities which perform common steps of an iterative fitting process.

*pyckett_add* helps adding new parameters to the fit, *pyckett_omit* is used for evaluating which parameters can be omitted.

*pyckett_separatefits* can be used to separate a global fit into separate fits for each state.

*pyckett_uncertainties* evaluates the uncertainties of the parameters.

*pyckett_partitionfunction* calculates the partition function for different temperatures.

*pyckett_auto* automatically builds up the Hamiltonian step by step.

*pyckett_fit* and *pyckett_cat* are shortcuts to SPFIT and SPCAT, respectively.


See the respective help functions (by adding *--help* after the command) to see their syntax.

# Examples

You can read files from the SPFIT/SPCAT universe with the following syntax

```python
var_dict = pyckett.parvar_to_dict(r"path/to/your/project/molecule.var")
par_dict = pyckett.parvar_to_dict(r"path/to/your/project/molecule.par")
int_dict = pyckett.int_to_dict(r"path/to/your/project/molecule.int")
lin_df = pyckett.lin_to_df(r"path/to/your/project/molecule.lin")
cat_df = pyckett.cat_to_df(r"path/to/your/project/molecule.cat")
egy_df = pyckett.egy_to_df(r"path/to/your/project/molecule.egy")

erham_df = pyckett.erhamlines_to_df(r"path/to/your/project/molecule.in")
```

## Finalize cat file

This function merges the cat and lin dataframes, sums up duplicate values in the cat file and allows to translate quantum numbers:

```python
fin_cat_df, fin_lin_df = pyckett.finalize(cat_df, lin_df, qn_tdict, qn)
```

## Find candidates for double-resonance measurements

This function finds possible transition arrangements for double-resonance measurements.
Input two cat dataframes with the transitions that are in the range of your probe and pump source.

```python
results_df = pyckett.get_dr_candidates(cat_df1, cat_df2)
```

## Check Crossings

```python
pyckett.check_crossings(egy_df, [1], range(10))
```

## Plot Mixing Coefficients

```python
pyckett.mixing_coefficient(egy_df, "qn4 == 1 and qn2 < 20 and qn1 < 20 and qn1==qn2+qn3")
```
