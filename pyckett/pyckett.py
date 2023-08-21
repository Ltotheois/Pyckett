#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : SPFIT/SPCAT wrapping Library


import os
import io
import subprocess
import tempfile
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor

## Constants
SENTINEL = np.iinfo(np.int64).min
ZEROTHRESHOLD = 1E-30
ZERO = 1E-37

SPFIT_PATH = os.environ.get("PYCKETT_SPFIT_PATH")
SPCAT_PATH = os.environ.get("PYCKETT_SPCAT_PATH")

QNLABELS = ['qnu1', 'qnu2', 'qnu3', 'qnu4', 'qnu5', 'qnu6', 'qnl1', 'qnl2', 'qnl3', 'qnl4', 'qnl5', 'qnl6']
QNLABELS_ENERGY = ['qn1', 'qn2', 'qn3', 'qn4', 'qn5', 'qn6']

class pickett_int(np.int64):
	def __new__(cls, value):
		if type(value) is np.int64:
			return(value)
		
		value = value.strip()
		if not value:
			return(SENTINEL)

		init_char = value[0]
		if init_char.isnumeric():
			return np.int64(value)
		
		elif init_char.isalpha():
			return np.int64(str(ord(init_char.upper())-55) + value[1:])
			
		# Special case for ERHAM cat files
		# ERHAM writes ** for quantum numbers higher than 99
		elif all([x == "*" for x in value]):
			return(np.int64(99))


cat_dtypes = {
	'x':		np.float64,
	'error':	np.float64,
	'y':		np.float64,
	'degfreed':	pickett_int,
	'elower':	np.float64,
	'usd':		pickett_int,
	'tag':		pickett_int,
	'qnfmt':	pickett_int,
	'qnu1':		pickett_int,
	'qnu2':		pickett_int,
	'qnu3':		pickett_int,
	'qnu4':		pickett_int,
	'qnu5':		pickett_int,
	'qnu6':		pickett_int,
	'qnl1':		pickett_int,
	'qnl2':		pickett_int,
	'qnl3':		pickett_int,
	'qnl4':		pickett_int,
	'qnl5':		pickett_int,
	'qnl6':		pickett_int,
}

cat_widths = {
	'x':		13,
	'error':	 8,
	'y':		 8,
	'degfreed':	 2,
	'elower':	10,
	'usd':		 3,
	'tag':		 7,
	'qnfmt':	 4,
	'qnu1':		 2,
	'qnu2':		 2,
	'qnu3':		 2,
	'qnu4':		 2,
	'qnu5':		 2,
	'qnu6':		 2,
	'qnl1':		 2,
	'qnl2':		 2,
	'qnl3':		 2,
	'qnl4':		 2,
	'qnl5':		 2,
	'qnl6':		 2,
}

lin_dtypes = {
	'qnu1':		pickett_int,
	'qnu2':		pickett_int,
	'qnu3':		pickett_int,
	'qnu4':		pickett_int,
	'qnu5':		pickett_int,
	'qnu6':		pickett_int,
	'qnl1':		pickett_int,
	'qnl2':		pickett_int,
	'qnl3':		pickett_int,
	'qnl4':		pickett_int,
	'qnl5':		pickett_int,
	'qnl6':		pickett_int,
	'x':		np.float64,
	'error':	np.float64,
	'weight':	np.float64,
	'comment':	str,
}

egy_dtypes = {
	'iblk':		np.int64,
	'indx':		np.int64,
	'egy':		np.float64,
	'err':		np.float64,
	'pmix':		np.float64,
	'we':		np.int64,
	':':		str,
	'qn1':		pickett_int,
	'qn2':		pickett_int,
	'qn3':		pickett_int,
	'qn4':		pickett_int,
	'qn5':		pickett_int,
	'qn6':		pickett_int,
}

egy_widths = {
	'iblk':		 6,
	'indx':		 5,
	'egy':		18,
	'err':		18,
	'pmix':		11,
	'we':		 5,
	':':		 1,
	'qn1':		 3,
	'qn2':		 3,
	'qn3':		 3,
	'qn4':		 3,
	'qn5':		 3,
	'qn6':		 3,
}

# IS1,IS2,JQ,NQ,J,NN,FREQ,BLE,ER
erham_dtypes = {
	"is1":		np.int64, 
	"is2": 		np.int64,
	"qnu1":		np.int64,
	"tauu":		np.int64,
	"qnl1":		np.int64,
	"taul":		np.int64,
	"x":		np.float64,
	"weight":	np.float64,
	"error":	np.float64,
	"comment":	str,
}

# If NPAR and NLINE are too large it causes problems with spfit and spcat compiled for MacOs
# If NPAR and NLINE should be set bigger, this can be done safely with scientific notation
PARUPDATE = {
	"NPAR": 999999,
	"NLINE": 999999,
	"NITR": 20,
	"THRESH ": 0,
}

# Helper functions
def str_to_stream(string):
	return(io.StringIO(string))

def format_(value, formatspecifier):
	integer = formatspecifier.endswith("d")
	
	if integer:
		totallength, decimals = int(formatspecifier[:-1]), 0
	else:
		tmp = formatspecifier[:-1].split(".")
		totallength, decimals = map(int, tmp)
	
	if integer:
		value = int(value)
	
	negative = (value < 0)
	integerlength = totallength - negative - decimals - (decimals != 0)
	
	maxvalue = 10**integerlength
	maxascii = maxvalue * 3.6
	
	if abs(value) < maxvalue:
		return((f"{{:{formatspecifier}}}".format(value)))
	
	elif integer and abs(value) < maxascii:
		firsttwodigits = value // 10 ** (int(np.log10(value)) - 1)
		tmp = chr(55 + firsttwodigits)
		return((tmp + f"{{:{formatspecifier}}}".format(value)[2:]))
		
	else:
		return((f"{{:{formatspecifier}}}".format((maxvalue-0.1**decimals)*(-1)**negative)))

def get_active_qns(df):
	if not len(df):
		raise Exception(f"You are trying to get the active quantum numbers of an empty dataframe.")
	
	qns = {f"qn{ul}{i+1}": True for ul in ("u", "l") for i in range(6)}
	for qn in qns.keys():
		unique_values = df[qn].unique()
		if len(unique_values) == 1 and unique_values[0] == SENTINEL:
			qns[qn] = False
	
	return(qns)

def get_vib_digits(par):
	vib_digits = int(np.log10(abs(par["NVIB"]))) + 1
	return(vib_digits)

def get_all_states(vib_digits):
	all_states = 10 ** (vib_digits) - 1
	return(all_states)

def get_par_digits(vib_digits):
	return({
		'v1': vib_digits,
		'v2': vib_digits,
		'NSQ': 1,
		'KSQ': 1,
		'TYP': 2,
		'NS': 1,
		'I1': 1,
		'I2': 1,
		'FF': 2,
		'EX': 1,
	})

def parse_fit_result(message, var_dict):
	results = {}
	
	startindex = message.rfind("MICROWAVE RMS =") + len("MICROWAVE RMS =")
	stopindex = message.find(" MHz", startindex)
	rms = float(message[startindex:stopindex])
	
	results["rms"] = rms
	
	startindex = message.rfind("RMS ERROR=") + len("RMS ERROR=")
	stopindex = message.find("\n", startindex)
	OLDWRMS, WRMS = message[startindex:stopindex].split()
	
	results["wrms_old"] = OLDWRMS
	results["wrms"] = WRMS
	
	start_of_last_cycle = message.rfind("Finished Quantum")
	
	rejected_index = message.rfind("Lines rejected from fit")
	if rejected_index != -1 and rejected_index > start_of_last_cycle:
		tmp_index = message.rfind("\n", 0, rejected_index)
		rejected_lines = int(message[tmp_index:rejected_index])
	else:
		rejected_lines = 0
	
	results["rejected_lines"] = rejected_lines
	
	fit_diverging = message.rfind("Fit Diverging")
	
	if fit_diverging > start_of_last_cycle:
		fit_diverging = "LAST"
	elif fit_diverging > -1:
		fit_diverging = "PREVIOUS"
	else:
		fit_diverging = "NEVER"	
	
	results["diverging"] = fit_diverging

	results["paramuncertainties"] = check_uncertainties(var_dict)

	return(results)

def check_uncertainties(var_dict):
	params = var_dict["PARAMS"]
	rel_uncs = {}
	for par in params:
		id, value, uncertainty = par[:3]
		if value == 0:
			rel_unc = np.inf
		else:
			rel_unc = abs(uncertainty / value)
		rel_uncs[id] = rel_unc

	return(rel_uncs)

def parse_param_id(tmp, vib_digits):
	tmp = abs(tmp)
	result = {}
	for label, digits in get_par_digits(vib_digits).items():
		if digits == 0:
			continue
		tmp, result[label] = divmod(tmp, 10**digits)
	return(result)

def format_param_id(dict_, vib_digits):
	param_id = 0
	factor = 1
	for label, digits in get_par_digits(vib_digits).items():
		if digits == 0:
			continue
		# @Luis: Think about throwing an error here when the value is higher than the digits value!
		param_id += dict_.get(label, 0) * factor
		factor *= 10**digits
	return(param_id)


# Format functions
def cat_to_df(fname, sort=True):
	widths = cat_widths.values()
	columns = cat_dtypes.keys()
	converters = cat_dtypes.copy()
	
	data = pd.read_fwf(fname, widths=widths, names=columns, converters=converters, skip_blank_lines=True, comment="#").astype(cat_dtypes)
	data["y"] = 10 ** data["y"]
	data["filename"] = str(fname)
	
	if sort:
		data.sort_values("x", inplace=True)
	return(data)

def lin_to_df(fname, sort=True, zeroes_as_empty=False):
	widths = range(0, 37, 3)
	column_names = list(lin_dtypes.keys())
	
	data = []
	tmp_file = open(fname, "r") if not isinstance(fname, io.StringIO) else fname
	with tmp_file as file:
		for line in file:
			if not line.strip() or line.startswith(("#", "/", "\\")):
				continue

			tmp = line[36:].split(maxsplit=3)
			tmp[0] = lin_dtypes['x'](tmp[0])
			tmp[1] = lin_dtypes['error'](tmp[1])
			
			if len(tmp) == 2:
				tmp.extend((1, ""))
			elif len(tmp) >= 3:
				dtype = lin_dtypes['weight']
				try:
					tmp[2] = dtype(tmp[2])
					if len(tmp) == 3:
						tmp.append("")
				except ValueError:
					comment = " ".join(tmp[2:]).strip()
					if len(tmp) == 3:
						tmp.append(comment)
					else:
						tmp[3] = comment
					tmp[2] = 1
			
			
			tmp_line_content = [pickett_int(line[i:j]) for i, j in zip(widths[:-1], widths[1:])] + tmp
			data.append(tmp_line_content)
	
	data = pd.DataFrame(data, columns=column_names).astype(lin_dtypes)
	data["filename"] = str(fname)
	
	## Set correct columns for data
	qns_labels = column_names[0:12]
	noq = len(qns_labels)
	for i in range(len(qns_labels)):
		if all(SENTINEL == data[qns_labels[i]]):
			noq = i
			break
		
		# Zeros_as_empty supports AABS format where empty quantum numbers are denoted as zero
		# This can lead to ambiguous results if there are all-zero columns
		if zeroes_as_empty and all(0 == data[qns_labels[i]]):
			noq = i
			break
	noq = noq // 2

	columns_qn = [f"qn{ul}{i+1}" for ul in ('u', 'l') for i in range(noq)] + [f"qn{ul}{i+1}" for ul in ('u', 'l') for i in range(noq, 6)]
	data.columns = columns_qn + list(data.columns[12:])

	if sort:
		data.sort_values("x", inplace=True)
	return(data)

def df_to_cat(df):
	lines = []

	for index, row in df.iterrows():
		freq = format_(row["x"], "13.4f")
		error = format_(row["error"], "8.4f")
		intens = np.log10(row["y"]) if row["y"] > 0 else 0
		intens = format_(intens, "8.4f")
		dof = format_(row["degfreed"], "2d")
		elower = format_(row["elower"], "10.4f")
		usd = format_(row["usd"], "3d")
		tag = format_(row["tag"], "7d")
		qnfmt = format_(row["qnfmt"], "4d")

		qnsstring = ""
		for qnlabel in QNLABELS:
			qn = row[qnlabel]
			if qn == SENTINEL:
				qnsstring += "  "
			else:
				qnsstring += format_(row[qnlabel], "2d")

		lines.append(f"{freq}{error}{intens}{dof}{elower}{usd}{tag}{qnfmt}{qnsstring}")
	lines.append("")
	
	return("\n".join(lines))

def df_to_lin(df):
	lines = []

	for index, row in df.iterrows():
		qnsstring = ""
		padstring = ""
		for qnlabel in QNLABELS:
			if SENTINEL == row[qnlabel]:
				padstring += "   "
			else:
				qnsstring += format_(row[qnlabel],"3d")
		qnsstring = qnsstring + padstring
		comment = row["comment"].strip() if row["comment"] else ""
		
		freq = format_(row["x"], "13.4f")
		error = format_(row["error"], "8.4f")
		weight = format_(row["weight"], "13.4f")
		lines.append(f"{qnsstring} {freq} {error} {weight}  {comment}")
	lines.append("")
	
	return("\n".join(lines))

def egy_to_df(fname, sort=True):
	widths = egy_widths.values()
	columns = egy_dtypes.keys()
	converters = egy_dtypes

	data = pd.read_fwf(fname, widths=widths, names=columns, converters=converters, skip_blank_lines=True, comment="#").astype(egy_dtypes)
	
	data = data.drop(columns=[':'])
	data["filename"] = str(fname)
	
	if sort:
		data.sort_values("egy", inplace=True)
	return(data)

def df_to_egy(df):
	lines = []

	for index, row in df.iterrows():
		iblk = format_(row["iblk"], "5d")
		indx = format_(row["indx"], "5d")
		egy  = format_(row["egy"], "18.6f")
		err  = format_(row["err"], "18.6f")
		pmix = format_(row["pmix"], "11.6f")
		we   = format_(row["we"], "5d")

		qnsstring = ""
		for qnlabel in QNLABELS_ENERGY:
			qn = row[qnlabel]
			if qn == SENTINEL:
				qnsstring += "   "
			else:
				qnsstring += format_(row[qnlabel], "3d")

		lines.append(f" {iblk}{indx}{egy}{err}{pmix}{we}:{qnsstring}")
	lines.append("")
	
	return("\n".join(lines))

def parvar_to_dict(fname):
	result = {}
	tmp_file = open(fname, "r") if not isinstance(fname, io.StringIO) else fname
	with tmp_file as file:
		result["TITLE"] = file.readline().replace("\n", "")
		
		keys = ['NPAR', 'NLINE', 'NITR', 'NXPAR', 'THRESH', 'ERRTST', 'FRAC', 'CAL']
		result.update({key: value for key, value in zip(keys, file.readline().split())})
		
		keys = ['CHR', 'SPIND', 'NVIB', 'KNMIN', 'KNMAX', 'IXX', 'IAX', 'WTPL', 'WTMN', 'VSYM', 'EWT', 'DIAG', 'XOPT']
		result.update({key: value for key, value in zip(keys, file.readline().split())})
		
		for key, value in result.items():
			if key not in ["TITLE", "CHR"]:
				value = np.float64(value)
				if value % 1 == 0:
					result[key] = int(value)
				else:
					result[key] = value
		
		result['STATES'] = []
		if result['VSYM'] < 0:
			for x in range(abs(result['NVIB'])-1):
				line = file.readline()[1:]
				keys = ['SPIND', 'NVIB', 'KNMIN', 'KNMAX', 'IXX', 'IAX', 'WTPL', 'WTMN', 'VSYM', 'EWT', 'DIAG', 'XOPT'] #Only their in case list is changed to dict
				stateline = [int(value) for key, value in zip(keys, line.split())]
				result['STATES'].append(stateline)
				if stateline[8] > 0:
					break
		
		result['PARAMS'] = []
		for line in file:
			try:
				if not line.strip():
					continue
				keys = ["IDPAR", "PAR", "ERPAR", "LABEL"] #Only here in case list is changed to dict
				funcs = [int, np.float64, np.float64, lambda x: x.replace("/", "")]
				paramline = [func(value) for key, value, func in zip(keys, line.split(), funcs)]
			
				result['PARAMS'].append(paramline)
			except:
				break
			
	return(result)

def dict_to_parvar(dct):
	output = []
	output.append(dct["TITLE"])
	
	formats = ['{:4.0f}', ' {:6.0f}', ' {:5.0f}', ' {:4.0f}', '   {: .4e}', '   {: .4e}', '   {: .4e}', ' {:13.4f}']
	
	values = [dct[key] for key in ['NPAR', 'NLINE', 'NITR', 'NXPAR', 'THRESH', 'ERRTST', 'FRAC', 'CAL'] if key in dct]
	line = "".join([fs.format(x) for x, fs in zip(values, formats)])
	output.append(line)
	
	formats = [' {:4.0f}', ' {:3.0f}', ' {:3.0f}', ' {:4.0f}', ' {:4.0f}', ' {:4.0f}', ' {:4.0f}', ' {:4.0f}', ' {: 7.0f}', ' {:4.0f}', ' {:1.0f}', ' {:4.0f}']
	
	values = [dct[key] for key in ['SPIND', 'NVIB', 'KNMIN', 'KNMAX', 'IXX', 'IAX', 'WTPL', 'WTMN', 'VSYM', 'EWT', 'DIAG', 'XOPT'] if key in dct ]
	line = f"{dct['CHR']}"+ "".join([fs.format(x) for x, fs in zip(values, formats)])
	output.append(line)
	
	for state in dct["STATES"]:
		line = "".join([fs.format(x) for x, fs in zip(state, formats)])
		output.append(line)
	
	for param in dct['PARAMS']:
		comment = ""
		if len(param) > 3:
			comment = f"/{param[3]}"
		output.append(f"{param[0]:13} {param[1]: .15e} {param[2]: .8e} {comment}")
	
	output = "\n".join(output)
	return(output)

def int_to_dict(fname):
	result = {}
	tmp_file = open(fname, "r") if not isinstance(fname, io.StringIO) else fname
	with tmp_file as file:
		result["TITLE"] = file.readline().replace("\n", "")
		
		keys = ['FLAGS', 'TAG', 'QROT', 'FBGN', 'FEND', 'STR0', 'STR1', 'FQLIM', 'TEMP', 'MAXV']
		funcs = [int, int, np.float64, int, int, np.float64, np.float64, np.float64, np.float64, int]
		result.update({key: func(value) for key, value, func in zip(keys, file.readline().split(), funcs)})
		
		result['INTS'] = []
		for line in file:
			keys = ['IDIP', 'DIPOLE']
			funcs = [int, np.float64]
			intline = [func(value) for key, value, func in zip(keys, line.split(), funcs)]
			
			result['INTS'].append(intline)
	
	return(result)

def dict_to_int(dct):
	output = []
	output.append(dct["TITLE"])
	
	formats = ['{:4.0f}', ' {:7.0f}', ' {:13.4f}', ' {:4.0f}', ' {:4.0f}', ' {: 6.2f}', ' {: 6.2f}', ' {:13.4f}', ' {:13.4f}', ' {:4.0f}']
	
	values = [dct[key] for key in ['FLAGS', 'TAG', 'QROT', 'FBGN', 'FEND', 'STR0', 'STR1', 'FQLIM', 'TEMP', 'MAXV'] if key in dct]
	line = "".join([fs.format(x) for x, fs in zip(values, formats)])
	output.append(line)
	
	for param in dct['INTS']:
		output.append(f" {param[0]: d}  {param[1]:.2f}")
	
	output = "\n".join(output)
	return(output)

def erhamlines_to_df(fname, sort=True):
	noc = len(erham_dtypes)
	data = []
	tmp_file = open(fname, "r") if not isinstance(fname, io.StringIO) else fname
	with tmp_file as file:
		for line in file:
			if line.strip() == "" or line.startswith("#"):
				continue
			
			
			tmp = line.split(maxsplit=noc-1)
			if len(tmp) == noc-1:
				tmp.append("")
			
			data.append(tmp)
	
	column_names = list(erham_dtypes.keys())
	data = pd.DataFrame(data, columns=column_names).astype(erham_dtypes)
	
	data["qnu2"] = data["tauu"] // 2
	data["qnl2"] = data["taul"] // 2
	
	data["qnu3"] = data["qnu1"] - (data["tauu"] - 1) // 2
	data["qnl3"] = data["qnl1"] - (data["taul"] - 1) // 2
	
	data["qnu4"] = data["is1"]
	data["qnl4"] = data["is2"]
	
	data["qnu5"] = data["qnu6"] = data["qnl5"] = data["qnl6"] = SENTINEL
	
	data["filename"] = str(fname)
	
	return(data)


## SPFIT/SPCAT functions
def run_spfit(filename, parameterfile="", path=None, wd=None):
	if path:
		path = os.path.abspath(path)
	else:
		if SPFIT_PATH:
			path = SPFIT_PATH
		else:
			path = "spfit"
	
	command = [path, filename, parameterfile]
	return(run_subprocess(command, wd))

def run_spcat(filename, parameterfile="", path=None, wd=None):
	if path:
		path = os.path.abspath(path)
	else:
		if SPCAT_PATH:
			path = SPCAT_PATH
		else:
			path = "spcat"

	command = [path, filename, parameterfile]
	return(run_subprocess(command, wd))

def run_subprocess(command, wd=None):
	if wd is None:
		wd = os.getcwd()
	output = subprocess.check_output(command, cwd=wd)
	output = output.decode("utf-8")
	return(output)

def run_spfit_v(par_dict, lin_df, spfit_path=None):
	with tempfile.TemporaryDirectory(prefix='pyckett_') as tmp_dir:
		with open(os.path.join(tmp_dir, "tmp.par"), "w+") as par_file, open(os.path.join(tmp_dir, "tmp.lin"), "w+") as lin_file:
			lin_file.write(df_to_lin(lin_df))
			par_file.write(dict_to_parvar(par_dict))
		
		message = run_spfit("tmp", path=spfit_path, wd=tmp_dir)
		
		result = {
			"msg": message,
			"bak": parvar_to_dict(os.path.join(tmp_dir, "tmp.bak")),
			"par": parvar_to_dict(os.path.join(tmp_dir, "tmp.par")),
			"var": parvar_to_dict(os.path.join(tmp_dir, "tmp.var")),
		}
		
		
		for ext in ("fit", "bin"):
			tmp_filename = os.path.join(tmp_dir, f"tmp.{ext}")
			if os.path.isfile(tmp_filename):
				with open(tmp_filename, "r") as file:
					result[ext] = file.read()
	
	return(result)

def run_spcat_v(var_dict, int_dict, spcat_path=None):
	with tempfile.TemporaryDirectory(prefix='pyckett') as tmp_dir:
		with open(os.path.join(tmp_dir, "tmp.var"), "w+") as var_file, open(os.path.join(tmp_dir, "tmp.int"), "w+") as int_file:
			int_file.write(dict_to_int(int_dict))
			var_file.write(dict_to_parvar(var_dict))
		
		message = run_spcat("tmp", path=spcat_path, wd=tmp_dir)
		
		result = {
			"msg": message,
			"cat": cat_to_df(os.path.join(tmp_dir, "tmp.cat")),
			"egy": egy_to_df(os.path.join(tmp_dir, "tmp.egy")),
		}
		
		for ext in (".out", ".str"):
			tmp_filename = os.path.join(tmp_dir, f"tmp.{ext}")
			if os.path.isfile(tmp_filename):
				with open(tmp_filename, "r") as file:
					result[ext] = file.read()
	
	return(result)



## Main actions
def check_crossings(egy_df, states, kas, Jmax=60):
	output = []
	series_list = []
	for state in states:
		for ka in kas:
			qnsums = (0, 1) if ka != 0 else (0,)
			for qnsum in qnsums:
				tmp_df = egy_df.query(f"qn2 == {ka} and qn4 == {state} and qn1 + {qnsum} == qn2+qn3 and qn1 < {Jmax}").copy()
				xmin = tmp_df["qn1"].to_numpy().min() if len(tmp_df["qn1"].to_numpy()) != 0 else 0
				ys = tmp_df["egy"].to_numpy()
				
				series_list.append(((state, ka, qnsum), xmin, ys))
	
	crossings = []
	for i in range(len(series_list)):
		for j in range(i+1, len(series_list)):
			desc_1, xmin_1, ys_1 = series_list[i]
			desc_2, xmin_2, ys_2 = series_list[j]
			
			xdiff = xmin_1 - xmin_2
			xstart = max(xmin_1, xmin_2)
			
			if xdiff > 0:
				ys_2 = ys_2[xdiff:]
			elif xdiff < 0:
				ys_1 = ys_1[abs(xdiff):]
			
			ydiff = ys_1 - ys_2
			ytmp = [ydiff[k]*ydiff[k+1] for k in range(len(ydiff)-1)]
			
			for k in range(len(ytmp)):
				if ytmp[k] < 0:
					crossings.append((desc_1, desc_2, xstart+k))
	
	crossings = sorted(crossings, key = lambda x: (x[0][0], x[1][0]))
	
	output.append("Format is state1, state2 @ ka1, J-ka1-kc1 & ka2, J-ka2-kc2 @ Ji, Jf")
	for crossing in crossings:
		J = crossing[2]
		output.append(f"{crossing[0][0]:3d}, {crossing[1][0]:3d} @ {crossing[0][1]:3d}, {crossing[0][2]:1d} & {crossing[1][1]:3d}, {crossing[1][2]:1d} @ {J:3d}, {J+1:3d}")
	
	output.append(f"\nFound {len(crossings)} crossings in total.")
	output = "\n".join(output)
	
	return(output)

def mixing_coefficient(egy_df, query_string, save_fname=None):
	gs = matplotlib.gridspec.GridSpec(1, 3, width_ratios = [1,0.2, 0.1], hspace=0, wspace=0)
	fig = plt.figure()

	ax = fig.add_subplot(gs[0,0])
	eax = fig.add_subplot(gs[0,1])
	eax.axis("off")
	cbaxs = fig.add_subplot(gs[0,2])
	
	ax.set_xlabel("$J$")
	ax.set_ylabel("$K_{a}$")
	
	tmp_df = egy_df.query(query_string).copy()
	xs = tmp_df["qn1"].to_numpy()
	ys = tmp_df["qn2"].to_numpy()
	zs = tmp_df["pmix"].abs().to_numpy()
	
	df = pd.DataFrame({"x": xs, "y": ys, "z": zs})
	zmatrix = df.pivot_table(values="z", index="y", columns="x")
	zmatrix = zmatrix.to_numpy()

	if len(xs) == 0 or len(ys) == 0:
		print("No data found.")
		return()

	xs = [x-0.5 for x in sorted(list(set(xs)))]
	xs.append(max(xs)+1)
	ys = [y-0.5 for y in sorted(list(set(ys)))]
	ys.append(max(ys)+1)

	clim = (0.5,1)
	ax.pcolormesh(xs, ys, zmatrix)
	ax.set_xlim(min(xs), max(xs))
	ax.set_ylim(min(xs), max(ys))
	
	norm = matplotlib.colors.Normalize(vmin=0.5,vmax=1)
	sm = plt.cm.ScalarMappable(cmap="plasma_r", norm=norm)
	sm.set_array([])
	cb = fig.colorbar(sm, cax=cbaxs, orientation="vertical")
	cb.set_label('Mixing Coefficient', labelpad=10)
	
	plt.tight_layout()
	if save_fname == None:
		plt.show()
	elif type(save_fname) == str:
		plt.savefig(save_fname)
	
	plt.close()

def add_parameter(par_dict, lin_df, param_candidates, sort=True, spfit_path=None):
	runs = []
	
	def worker(i):
		params = param_candidates[i]
		if isinstance(params, (int, float, complex)):
			params = [[param, 1E-37, 1E+37]]
		else:
			params = list(params)
		ids = [x[0] for x in params]
		
		tmp_par_dict = par_dict.copy()
		tmp_par_dict["PARAMS"] = tmp_par_dict["PARAMS"] + params
		results = run_spfit_v(tmp_par_dict, lin_df, spfit_path)
		stats = parse_fit_result(results["msg"], results["var"])
		rms = stats["rms"]
		return({'id': ids, 'rms': rms, 'par': tmp_par_dict["PARAMS"].copy(), 'stats': stats})
	
	with ThreadPoolExecutor() as executor:
		futures = {i: executor.submit(worker, i) for i in range(len(param_candidates))}
		runs = [f.result() for f in futures.values()]
	
	if sort:
		runs = sorted(runs, key=lambda x: x['rms'])
	return(runs)

def omit_parameter(par_dict, lin_df, param_ids, sort=True, spfit_path=None):
	runs = []
	
	def worker(param_id):
		tmp_par_dict = par_dict.copy()
		tmp_par_dict["PARAMS"] = [x for x in tmp_par_dict["PARAMS"] if x[0] != param_id]
		results = run_spfit_v(tmp_par_dict, lin_df, spfit_path)
		stats = parse_fit_result(results["msg"], results["var"])
		rms = stats["rms"]
		return({'id': param_id, 'rms': rms, 'par': tmp_par_dict["PARAMS"].copy(), 'stats': stats})
	
	with ThreadPoolExecutor() as executor:
		futures = {param_id: executor.submit(worker, param_id) for param_id in param_ids}
		runs = [f.result() for f in futures.values()]
	
	if sort:
		runs = sorted(runs, key=lambda x: (x['stats']['rejected_lines'], x['rms']))
	return(runs)

def finalize(cat_df=pd.DataFrame(), lin_df=pd.DataFrame(), qn_tdict={}, qn=4):
	cat_df = cat_df.copy()
	lin_df = lin_df.copy()
	
	# Merge cat and lin file
	if len(lin_df) and len(cat_df):
		lin_qns, cat_qns = get_active_qns(lin_df), get_active_qns(cat_df)
		lin_qns = set([key for key, value in lin_qns.items() if value])
		cat_qns = set([key for key, value in cat_qns.items() if value])
		
		if lin_qns != cat_qns:
			raise Exception(f"The active quantum numbers of the lin and cat file do not match.\nQuantum numbers of the cat file: {cat_qns}\nQuantum numbers of the lin file: {lin_qns}")
		
		tmp_lin_df = lin_df.drop(set(lin_df.columns) - lin_qns - set(("x", "error")), axis=1)
		cat_df = pd.merge(cat_df, tmp_lin_df, how="left", on=list(cat_qns))
		
		mask = ~cat_df["x_y"].isna()
		cat_df.loc[mask, "x_x"] = cat_df.loc[mask, "x_y"]
		cat_df.loc[mask, "error_x"] = cat_df.loc[mask, "error_y"]
		cat_df.loc[mask, "tag"] = -abs(cat_df.loc[mask, "tag"])
		cat_df = cat_df.drop(["x_y", "error_y"], axis=1)
		cat_df = cat_df.rename({"x_x": "x", "error_x": "error"}, axis=1)
	
	
	# Sum up duplicate rows
	if len(cat_df):
		cat_df = cat_df.groupby(list(set(cat_df.columns) - set("y"))).sum().reset_index()
		cat_df = cat_df.sort_values("x").reset_index(drop=True)
	
	# Translate quantum numbers for the state
	if qn_tdict and qn:
		qnu, qnl = f"qnu{qn}", f"qnl{qn}"
		if len(cat_df):
			if qnu not in cat_qns or qnl not in cat_qns:
				raise Exception(f"The quantum numbers for the state translation, '{qnl}' and '{qnu}', are no active quantum numbers in the cat file.")
			cat_df["tmp"] = cat_df.apply(lambda row: qn_tdict[(row[qnu], row[qnl])], axis=1)
			cat_df[qnu] = cat_df[qnl] = cat_df["tmp"]
			cat_df.drop("tmp", axis=1)
	
		if len(lin_df):
			if qnu not in lin_qns or qnl not in lin_qns:
				raise Exception(f"The quantum numbers for the state translation, '{qnl}' and '{qnu}', are no active quantum numbers in the lin file.")
			lin_df["tmp"] = lin_df.apply(lambda row: qn_tdict[(row[qnu], row[qnl])], axis=1)
			lin_df[qnu] = lin_df[qnl] = lin_df["tmp"]
			lin_df.drop("tmp", axis=1)
	
	return(cat_df, lin_df)

def get_dr_candidates(df1, df2):
	qns_active1, qns_active2 = get_active_qns(df1), get_active_qns(df2)
	qns_upper = [f"qnu{i+1}" for i in range(6) if qns_active1[f"qnu{i+1}"] and qns_active2[f"qnu{i+1}"]]
	qns_lower = [f"qnl{i+1}" for i in range(6) if qns_active1[f"qnl{i+1}"] and qns_active2[f"qnl{i+1}"]]

	qns_inactive = [f"qn{ul}{i+1}" for i in range(6) for ul in ("u", "l") if not (qns_active1[f"qnu{i+1}"] and qns_active2[f"qnu{i+1}"])]

	schemes = {
		"pro_ul": (qns_upper, qns_lower),
		"pro_lu": (qns_lower, qns_upper),
		"reg_uu": (qns_upper, qns_upper),
		"reg_ll": (qns_lower, qns_lower)
	}
	
	results = []
	for label, (qns_left, qns_right) in schemes.items():
		tmp = pd.merge(df1.drop(columns=qns_inactive), df2.drop(columns=qns_inactive), how="inner", left_on=qns_left, right_on=qns_right)
		tmp["scheme"] = label
		results.append(tmp)
	
	results = pd.concat(results, ignore_index=True)
	results = results[results["x_x"] != results["x_y"]]
	
	for qn in qns_upper + qns_lower:
		mask = (results[qn+"_x"].isna() & results[qn+"_y"].isna())
		results.loc[mask, qn+"_x"] = results.loc[mask, qn+"_y"] = results.loc[mask, qn]
	results = results.drop(columns=qns_upper).drop(columns=qns_lower).reset_index(drop=True)
	
	return(results)

INITIAL_PARAMS_ROTATION = {100, 200, 300}

POSSIBLE_PARAMS_A = {
	100: ("A",        (2, 11, 20, 401, 410)),
	200: ("B",        (2, 11, 20, 401, 410)),
	300: ("C",        (2, 11, 20, 401, 410)),

	  2: ("-DeltaJ",  (3, 12, 402)),
	 11: ("-DeltaJK", (12, 21, 411)),
	 20: ("-DeltaK",  (21, 30, 420)),
	401: ("-deltaJ",  (402, 411)),
	410: ("-deltaK",  (411, 420)),

	  3: ("PhiJ",      (4, 13, 403)),
	 12: ("PhiJK",     (13, 22, 412)),
	 21: ("PhiKJ",     (22, 31, 421)),
	 30: ("PhiK",      (31, 40, 430)),
	402: ("phiJ",      (403, 412)),
	411: ("phiJK",     (412, 421)),
	420: ("phiK",      (421, 430)),

	  4: ("LJ",        (5, 14, 404)),
	 13: ("LJJK",      (14, 23, 413)),
	 22: ("LJK",       (23, 32, 422)),
	 31: ("LKKJ",      (32, 41, 431)),
	 40: ("LK",        (41, 50, 440)),
	403: ("lJ",        (404, 413)),
	412: ("lJK",       (413, 422)),
	421: ("lKJ",       (422, 431)),
	430: ("lK",        (431, 440)),
			          
	  5: ("PJ",        ()),
	 14: ("PJJK",      ()),
	 23: ("PJK",       ()),
	 32: ("PKJ",       ()),
	 41: ("PKKJ",      ()),
	 50: ("PK",        ()),
	404: ("pJ",        ()),
	413: ("pJJK",      ()),
	422: ("pJK",       ()),
	431: ("pKKJ",      ()),
	440: ("pK",        ()),
}

POSSIBLE_PARAMS_S = {
	100: ("A",    (2, 11, 20, 401, 500)),
	200: ("B",    (2, 11, 20, 401, 500)),
	300: ("C",    (2, 11, 20, 401, 500)),

	  2: ("-DJ",  (3, 12, 402) ),
	 11: ("-DJK", (12, 21)     ),
	 20: ("-DK",  (21, 30)     ),
	401: ("d1",   (402, 501)   ),
	500: ("d2",   (501, 600)   ),

	  3: ("HJ",   (4, 13, 403) ),
	 12: ("HJK",  (13, 22)     ),
	 21: ("HKJ",  (22, 31)     ),
	 30: ("HK",   (31, 40)     ),
	402: ("h1",   (403, 502)   ),
	501: ("h2",   (502, 601)   ),
	600: ("h3",   (601, 700)   ),

	  4: ("LJ",   (5, 14, 404) ),
	 13: ("LJJK", (14, 23)     ),
	 22: ("LJK",  (23, 32)     ),
	 31: ("LKKJ", (32, 41)     ),
	 40: ("LK",   (41, 50)     ),
	403: ("l1",   (404, 503)   ),
	502: ("l2",   (503, 602)   ),
	601: ("l3",   (602, 701)   ),
	700: ("l4",   (701, 800)   ),

	  5: ("PJ",   ()),
	 14: ("PJJK", ()),
	 23: ("PJK",  ()),
	 32: ("PKJ",  ()),
	 41: ("PKKJ", ()),
	 50: ("PK",   ()),
	404: ("p1",   ()),
	503: ("p2",   ()),
	602: ("p3",   ()),
	701: ("p4",   ()),
	800: ("p5",   ()),
}

POSSIBLE_PARAMS_LINEAR = {
	1: ("B",   (2,)),
	2: ("-D",  (3,)),
	3: ("H",   (4,)),
	4: ("L",   (5,)),
	5: ("P",   ()  ),
}


INITIAL_PARAMS_INTERACTION = {2000, 2100, 4000, 4100, 6000, 6100, 0, 400}

POSSIBLE_PARAMS_INTERACTION = {
	2000: ('Ga',    (2001, 2010, 2200)), 
	2001: ('GaJ',   ()), 
	2010: ('GaK',   ()), 
	2100: ('Fbc',   (2101, 2110, 2300)), 
	2101: ('FbcJ',  ()), 
	2110: ('FbcK',  ()), 
	2200: ('G2a',   (2201, 2210)), 
	2201: ('G2aJ',  ()), 
	2210: ('G2aK',  ()), 
	2300: ('F2bc',  (2301, 2310)), 
	2301: ('F2bcJ', ()), 
	2310: ('F2bcK', ()), 
	
	4000: ('Gb',    (4001, 4010, 4200)), 
	4001: ('GbJ',   ()), 
	4010: ('GbK',   ()), 
	4100: ('Fac',   (4101, 4110, 4300)), 
	4101: ('FacJ',  ()), 
	4110: ('FacK',  ()), 
	4200: ('G2b',   (4201, 4210)), 
	4201: ('G2bJ',  ()), 
	4210: ('G2bK',  ()), 
	4300: ('F2ac',  (4301, 4310)), 
	4301: ('F2acJ', ()), 
	4310: ('F2acK', ()), 
	
	6000: ('Gc',    (6001, 6010, 6200)), 
	6001: ('GcJ',   ()), 
	6010: ('GcK',   ()), 
	6100: ('Fab',   (6101, 6110, 6300)), 
	6101: ('FabJ',  ()), 
	6110: ('FabK',  ()), 
	6200: ('G2c',   (6201, 6210)), 
	6201: ('G2cJ',  ()), 
	6210: ('G2cK',  ()), 
	6300: ('F2ab',  (6301, 6310)), 
	6301: ('F2abJ', ()), 
	6310: ('F2abK', ()), 
	
	   0: ('F',     (1, 10)), 
	   1: ('FJ',    ()), 
	  10: ('FK',    ()), 
	 400: ('F2',    (401, 410)), 
	 401: ('F2J',   ()), 
	 410: ('F2K',   ()),
}

if __name__ == "__main__":
	pass
	
	# var_dict = parvar_to_dict(r"path/to/your/project/molecule.var")
	# par_dict = parvar_to_dict(r"path/to/your/project/molecule.par")
	# int_dict = int_to_dict(r"path/to/your/project/molecule.int")
	# lin_df = lin_to_df(r"path/to/your/project/molecule.lin")
	# cat_df = cat_to_df(r"path/to/your/project/molecule.cat")
	# egy_df = egy_to_df(r"path/to/your/project/molecule.egy")
	
	## Best Candidate to add to Fit
	# cands = [[140101, 0.0, 1e+37], [410101, 0.0, 1e+37]]
	# add_parameter(par_dict, lin_df, cands, r"SPFIT_SPCAT")
	
	## Best Candidate to neglect from Fit
	# cands = [320101, 230101]
	# omit_parameter(par_dict, lin_df, cands, r"SPFIT_SPCAT")
	
	## Check Crossings
	# check_crossings(egy_df, [1], range(10))
	
	## Plot Mixing Coefficients
	# mixing_coefficient(egy_df, "qn4 == 1 and qn2 < 20 and qn1 < 20 and qn1==qn2+qn3")
