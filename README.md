# Pyckett

Pyckett is a python wrapper around the SPFIT/SPCAT package (*H. M. Pickett, "The Fitting and Prediction of Vibration-Rotation Spectra with Spin Interactions," **J. Molec. Spectroscopy 148,** 371-377 (1991)*).

Install the package with pip by using the following command

```
pip install pyckett
```

# Examples

You can read files from the SPFIT/SPCAT universe with the following syntax

```python
var_dict = parvar_to_dict(r"path/to/your/project/molecule.var")
par_dict = parvar_to_dict(r"path/to/your/project/molecule.par")
int_dict = int_to_dict(r"path/to/your/project/molecule.int")
lin_df = lin_to_df(r"path/to/your/project/molecule.lin")
cat_df = cat_to_df(r"path/to/your/project/molecule.cat")
egy_df = egy_to_df(r"path/to/your/project/molecule.egy")
```

## Best Candidate to add to Fit

```python
cands = [[140101, 0.0, 1e+37], [410101, 0.0, 1e+37]]
add_parameter(par_dict, lin_df, cands, r"SPFIT_SPCAT")
```

## Best Candidate to neglect from Fit

```python
cands = [320101, 230101]
ommit_parameter(par_dict, lin_df, cands, r"SPFIT_SPCAT")
```

## Check Crossings

```python
check_crossings(egy_df, [1], range(10))
```

## Plot Mixing Coefficients

```python
mixing_coefficient(egy_df, "qn4 == 1 and qn2 < 20 and qn1 < 20 and qn1==qn2+qn3")
```
