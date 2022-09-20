# Pyckett

Pyckett is a python wrapper around the SPFIT/SPCAT package (*H. M. Pickett, "The Fitting and Prediction of Vibration-Rotation Spectra with Spin Interactions," **J. Mol. Spectrosc. 148,** 371-377 (1991)*).

Install the package with pip by using the following command

```
pip install pyckett
```

# Examples

You can read files from the SPFIT/SPCAT universe with the following syntax

```python
import pyckett
var_dict = pyckett.parvar_to_dict(r"path/to/your/project/molecule.var")
par_dict = pyckett.parvar_to_dict(r"path/to/your/project/molecule.par")
int_dict = pyckett.int_to_dict(r"path/to/your/project/molecule.int")
lin_df = pyckett.lin_to_df(r"path/to/your/project/molecule.lin")
cat_df = pyckett.cat_to_df(r"path/to/your/project/molecule.cat")
egy_df = pyckett.egy_to_df(r"path/to/your/project/molecule.egy")

erham_df = pyckett.erhamlines_to_df(r"path/to/your/project/molecule.in")
```

## Best Candidate to add to Fit

```python
cands = [[140101, 0.0, 1e+37], [410101, 0.0, 1e+37]]
pyckett.add_parameter(par_dict, lin_df, cands, r"SPFIT_SPCAT")
```

## Best Candidate to neglect from Fit

```python
cands = [320101, 230101]
pyckett.ommit_parameter(par_dict, lin_df, cands, r"SPFIT_SPCAT")
```

## Finalize cat file

This function merges the cat and lin dataframes, sums up duplicate values in the cat file and allows to translate quantum numbers:

```python
fin_cat_df, fin_lin_df = pyckett.finalize(cat_df, lin_df, qn_tdict, qn)
```

## Find candidates for double-resonance measurement

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
