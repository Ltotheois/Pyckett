#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : SPFIT/SPCAT wrapping Library


import os, io
import subprocess
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

## Miscellaneous
preset_colors = ['#000000e0', '#dbb243e0', '#2e42d3e0', '#e54fe3e0', '#f23434e0']
qnlabels = ['qnu1', 'qnu2', 'qnu3', 'qnu4', 'qnu5', 'qnu6', 'qnl1', 'qnl2', 'qnl3', 'qnl4', 'qnl5', 'qnl6']


cat_dtypes = {
  'x':			np.float64,
  'error':		np.float64,
  'y':			np.float64,
  'degfreed':	np.int64,
  'elower':		np.float64,
  'usd':		np.int64,
  'tag':		np.int64,
  'qnfmt':		np.int64,
  'qnu1':		np.int64,
  'qnu2':		np.int64,
  'qnu3':		np.int64,
  'qnu4':		np.int64,
  'qnu5':		np.int64,
  'qnu6':		np.int64,
  'qnl1':		np.int64,
  'qnl2':		np.int64,
  'qnl3':		np.int64,
  'qnl4':		np.int64,
  'qnl5':		np.int64,
  'qnl6':		np.int64,
}

lin_dtypes = {
  'qnu1':		np.int64,
  'qnu2':		np.int64,
  'qnu3':		np.int64,
  'qnu4':		np.int64,
  'qnu5':		np.int64,
  'qnu6':		np.int64,
  'qnl1':		np.int64,
  'qnl2':		np.int64,
  'qnl3':		np.int64,
  'qnl4':		np.int64,
  'qnl5':		np.int64,
  'qnl6':		np.int64,
  'x':			np.float64,
  'error':		np.float64,
  'weight':		np.float64,
  'comment':	str,
}

cat_widths = {
  'x':			13,
  'error':		 8,
  'y':			 8,
  'degfreed':	 2,
  'elower':		10,
  'usd':		 3,
  'tag':		 7,
  'qnfmt':		 4,
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

egy_dtypes = {
	'iblk':		np.int64,
	'indx':		np.int64,
	'egy':		np.float64,
	'err':		np.float64,
	'pmix':		np.float64,
	'we':		np.int64,
	':':		np.int64,
	'qn1':		np.int64,
	'qn2':		np.int64,
	'qn3':		np.int64,
	'qn4':		np.int64,
	'qn5':		np.int64,
	'qn6':		np.int64,
}


# Helper functions
def str_to_stream(string):
	return(io.StringIO(string))

def column_to_numeric(val, force_int=False):
	val = val.strip()
	if val == "" or val == ":" or val == len(val)*"*":
		if force_int:
			return(np.iinfo(np.int64).min)
		else:
			return(np.nan)
	elif val[0].isalpha():
		val = str(ord(val[0].upper())-55)+val[1:]

	if force_int:
		return(np.int64(val))
	else:
		return(np.float64(val))

def tmp_dir_name(dir):
	i = 0
	tmp_dir = os.path.join(dir, f"pyfit_pycat_temp_{i}")
	while os.path.isdir(tmp_dir):
		i += 1
		tmp_dir = os.path.join(dir, f"pyfit_pycat_temp_{i}")
	os.mkdir(tmp_dir)
	return(tmp_dir)

def rmdir(dir):
	for file in os.listdir(dir):
		os.remove(os.path.join(dir, file))
	os.rmdir(dir)

def minmax(value, min=None, max=None):
	if min and value < min:
		return(min)
	if max and value > max:
		return(max)
	return(value)

# Format functions
def cat_to_df(fname, sort=True):
	widths = cat_widths.values()
	columns = list(cat_dtypes.keys())
	
	converters = cat_dtypes.copy()
	converters.update({key: lambda x: column_to_numeric(x, True) for key in columns[5:20]})
	data = pd.read_fwf(fname, widths=widths, names=columns, converters=converters, skip_blank_lines=True, comment="#").astype(cat_dtypes)
	data["y"] = 10 ** data["y"]
	data["filename"] = str(fname)
	
	if sort:
		data.sort_values("x", inplace=True)
	return(data)

def lin_to_df(fname, sort=True):
	widths = range(0,37,3)
	column_names = list(lin_dtypes.keys())
	
	data = []
	tmp_file = open(fname, "r") if not isinstance(fname, io.StringIO) else fname
	with tmp_file as file:
		for line in file:
			if line.strip() == "" or line.startswith("#"):
				continue

			tmp = line[36:].split(maxsplit=3)
			if len(tmp) == 2:
				tmp.append("1.0000")

			tmp_line_content = [column_to_numeric(line[i:j], True) for i, j in zip(widths[:-1], widths[1:])] + [column_to_numeric(x) for x in tmp[:3]]
			if len(tmp) == 4:
				tmp_line_content.append(tmp[3].strip())
			else:
				tmp_line_content.append("")

			data.append(tmp_line_content)
	
	data = pd.DataFrame(data, columns=column_names).astype(lin_dtypes)
	data["filename"] = str(fname)
	
	## Set correct columns for data
	qns_labels = column_names[0:12]
	noq = len(qns_labels)
	for i in range(len(qns_labels)):
		if all(np.iinfo(np.int64).min == data[qns_labels[i]]):
			noq = i
			break
	noq = noq//2

	columns_qn = [f"qnu{i+1}" for i in range(noq)]+[f"qnl{i+1}" for i in range(noq)]+[f"qnu{i+1}" for i in range(noq, 6)]+[f"qnl{i+1}" for i in range(noq, 6)]
	data.columns = columns_qn + list(data.columns[12:])

	if sort:
		data.sort_values("x", inplace=True)
	return(data)

def df_to_cat(df):
	lines = []

	for index, row in df.iterrows():
		freq = minmax(row["x"], -9999999.9999, 99999999.9999)
		error = minmax(row["error"], -99.9999, 999.9999)
		intens = np.log10(row["y"]) if row["y"] > 0 else 0
		intens = minmax(intens, -99.999, 999.9999)

		qnsstring = ""
		for qnlabel in qnlabels:
			if row[qnlabel] == np.iinfo(np.int64).min:
				qnsstring += "  "
			else:
				qnsstring += f"{row[qnlabel]:2.0f}"

		lines.append(f"{freq:13.4f}{error:8.4f}{intens:8.4f}{row['degfreed']:2.0f}{row['elower']:10.4f}{row['usd']:3.0f}{row['tag']:7.0f}{row['qnfmt']:4.0f}{qnsstring}")
	lines.append("\n")
	
	return("\n".join(lines))

def df_to_lin(df):
	lines = []

	for index, row in df.iterrows():
		qnsstring = ""
		padstring = ""
		for qnlabel in qnlabels:
			if np.iinfo(np.int64).min == row[qnlabel]:
				padstring += "   "
			else:
				qnsstring += f"{min(row[qnlabel], 999):3.0f}"
		qnsstring = qnsstring + padstring
		comment = ""
		if row["comment"]:
			comment = row["comment"].strip()
			if comment[:2] in [r"\\", r"//"]:
				comment = comment[2:].strip()
			comment = r"  // "+comment
		
		freq = minmax(row["x"], -9999999.9999, 99999999.9999)
		error = minmax(row["error"], -99.9999, 999.9999)
		weight = minmax(row["weight"], -9999999.9999, 99999999.9999)
		lines.append(f"{qnsstring} {freq:13.4f} {error:8.4f} {weight:13.4f}{comment}")
	lines.append("")
	
	return("\n".join(lines))

def egy_to_df(fname, sort=True):
	widths = egy_widths.values()
	columns = list(egy_dtypes.keys())

	converters = egy_dtypes.copy()
	converters.update({key: lambda x: column_to_numeric(x, True) for key in columns[-6:]})
	data = pd.read_fwf(fname, widths=widths, names=columns, converters=converters, skip_blank_lines=True, comment="#").astype(egy_dtypes)
	
	data["filename"] = str(fname)
	
	if sort:
		data.sort_values("egy", inplace=True)
	return(data)

def parvar_to_dict(fname):
	result = {}
	tmp_file = open(fname, "r") if not isinstance(fname, io.StringIO) else fname
	with tmp_file as file:
		result["TITLE"] = file.readline().replace("\n", "")
		
		keys = ['NPAR', 'NLINE', 'NITR', 'NXPAR', 'THRESH ', 'ERRTST', 'FRAC', 'CAL']
		result.update({key: value for key, value in zip(keys, file.readline().split())})
		
		keys = ['CHR', 'SPIND', 'NVIB', 'KNMIN', 'KNMAX', 'IXX', 'IAX', 'WTPL', 'WTMN', 'VSYM', 'EWT', 'DIAG', 'XOPT']
		result.update({key: value for key, value in zip(keys, file.readline().split())})
		
		for key, value in result.items():
			if key not in ["TITLE", "CHR"]:
				value = np.float64(value)
				if value%1 == 0:
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
				keys = ["IDPAR", "PAR", "ERPAR", "LABEL"] #Only their in case list is changed to dict
				funcs = [int, np.float64, np.float64, lambda x: x.replace("/", "")]
				paramline = [func(value) for key, value, func in zip(keys, line.split(), funcs)]
			
				result['PARAMS'].append(paramline)
			except:
				break
			
	return(result)

def dict_to_parvar(dct):
	output = []
	output.append(dct["TITLE"])
	
	formats = ['{:4.0f}', ' {:7.0f}', ' {:5.0f}', ' {:4.0f}', '   {: .4e}', '   {: .4e}', '   {: .4e}', ' {:13.4f}']
	
	values = [dct[key] for key in ['NPAR', 'NLINE', 'NITR', 'NXPAR', 'THRESH ', 'ERRTST', 'FRAC', 'CAL'] if key in dct]
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

## Helper Functions
def run_spcat(filename, parameterfile="", path="", wd=None):
	command = f"{os.path.join(path, 'spcat')} {filename} {parameterfile}"
	return(run_subprocess(command, wd))

def run_spfit(filename, parameterfile="", path="", wd=None):
	command = f"{os.path.join(path, 'spfit')} {filename} {parameterfile}"
	return(run_subprocess(command, wd))

def run_subprocess(command, wd=os.getcwd()):
	output = subprocess.check_output(command, cwd=wd, shell=False)
	output = output.decode("utf-8")
	return(output)

def run_spfit_v(par_dict, lin_df, spfit_path):
	tmp_dir = tmp_dir_name(os.getcwd())
	
	with open(os.path.join(tmp_dir, "tmp.par"), "w+") as par_file, open(os.path.join(tmp_dir, "tmp.lin"), "w+") as lin_file:
		lin_file.write(df_to_lin(lin_df))
		par_file.write(dict_to_parvar(par_dict))
	
	message = run_spfit("tmp", path=spfit_path, wd=tmp_dir)
	
	result = {"message": message}
	for ext in (".bak", ".par", ".var", ".fit", ".bin"):
		tmp_filename = os.path.join(tmp_dir, f"tmp{ext}")
		if os.path.isfile(tmp_filename):
			with open(tmp_filename, "r") as file:
				result[ext] = file.read()
	
	rmdir(tmp_dir)
	return(result)

def run_spcat_v(var_dict, int_dict, spcat_path):
	tmp_dir = tmp_dir_name(os.getcwd())
	
	with open(os.path.join(tmp_dir, "tmp.var"), "w+") as var_file, open(os.path.join(tmp_dir, "tmp.int"), "w+") as int_file:
		int_file.write(dict_to_int(int_dict))
		var_file.write(dict_to_parvar(var_dict))
	
	message = run_spcat("tmp", path=spcat_path, wd=tmp_dir)
	
	result = {"message": message}
	for ext in (".out", ".cat", ".str", ".egy"):
		tmp_filename = os.path.join(tmp_dir, f"tmp{ext}")
		if os.path.isfile(tmp_filename):
			with open(tmp_filename, "r") as file:
				result[ext] = file.read()
	
	rmdir(tmp_dir)
	return(result)

def parse_fit_result(msg):
	results = {}
	
	i_0 = msg.rfind("MICROWAVE RMS")
	i_1 = msg.find(",", i_0)
	RMS = msg[i_0:i_1].split("=")[1].split()[0]
	RMS = np.float64(RMS)
	results["RMS"] = RMS
	
	i_0 = msg.rfind("RMS ERROR=")
	i_1 = msg.find("\n", i_0)
	WRMS = msg[i_0:i_1].split()[-1]
	results["WRMS"] = WRMS
	
	return(results)

def plot_bars(ys, xlabels, title="", xlabel="", ylabel=""):
	fig, ax = plt.subplots()
	plt.title(title)
	plt.ylabel(xlabel)
	plt.xlabel(ylabel)
	
	xs = np.arange(len(ys))
	colors = preset_colors[:len(ys)]
	
	plt.bar(xs, ys, align="center", color=colors)
	plt.xticks(rotation=45, ha='right')

	ax.set_xticks(xs)
	ax.set_xticklabels(xlabels)
	
	return(fig)

## Main Actions
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

def add_parameter(par_dict, lin_df, param_candidates, spfit_path=None, save_fname=None):
	runs = []
	orig_par_dict = par_dict.copy()
	
	param_candidates.insert(0, ["Initial", 0, 0])
	
	for i, param in enumerate(param_candidates):
		par_dict =  orig_par_dict.copy()
		if param[0] != "Initial":
			par_dict["PARAMS"].append(param)
		
		results = run_spfit_v(par_dict, lin_df, spfit_path)
		RMS = parse_fit_result(results["message"])["RMS"]
		runs.append([i, RMS, par_dict["PARAMS"].copy()])
	
	runs = sorted(runs, key=lambda x: x[1])
	print(f"Best RMS is {runs[0][1]} for run {runs[0][0]}.")
	
	plot_bars([x[1] for x in runs], [c[0] for c in param_candidates], "Add Parameter", "Parameter", "RMS")
	plt.tight_layout()
	if save_fname == None:
		plt.show()
	elif type(save_fname) == str:
		plt.savefig(save_fname)
	
	plt.close()
	
	return(runs)

def ommit_parameter(par_dict, lin_df, param_candidates, spfit_path=None, save_fname=None):
	runs = []
	orig_par_dict = par_dict.copy()
	
	param_candidates.insert(0, "Initial")

	
	for i, param in enumerate(param_candidates):
		par_dict =  orig_par_dict.copy()
		for j, cparam in enumerate(par_dict["PARAMS"]):
			if cparam[0] == param:
				del par_dict["PARAMS"][j]
				break
		
		results = run_spfit_v(par_dict, lin_df, spfit_path)
		RMS = parse_fit_result(results["message"])["RMS"]
		runs.append([i, RMS, par_dict["PARAMS"].copy()])

	runs = sorted(runs, key=lambda x: x[1])
	print(f"Best RMS is {runs[0][1]} for run {runs[0][0]}.")
	
	plot_bars([x[1] for x in runs], param_candidates, "Neglect Parameter", "Parameter", "RMS")
	plt.tight_layout()
	if save_fname == None:
		plt.show()
	elif type(save_fname) == str:
		plt.savefig(save_fname)
	
	plt.close()
	
	return(runs)


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
	# ommit_parameter(par_dict, lin_df, cands, r"SPFIT_SPCAT")
	
	## Check Crossings
	# check_crossings(egy_df, [1], range(10))
	
	## Plot Mixing Coefficients
	# mixing_coefficient(egy_df, "qn4 == 1 and qn2 < 20 and qn1 < 20 and qn1==qn2+qn3")
