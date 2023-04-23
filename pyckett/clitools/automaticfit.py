#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : CLI tool for checking which parameter to add to fit

import json
import pyckett
from pyckett.clitools import addparameters_core, omitparameters_core
import argparse
from concurrent.futures import ThreadPoolExecutor

# @Luis: Provide option for symmetric, linear molecules
# @Luis: Maybe infer from Kmin and Kmax

def automaticfit():
	parser = argparse.ArgumentParser(prog='Automatic Fit')
	
	parser.add_argument('linfile', type=str, help='Filename of the .lin file')
	parser.add_argument('parfile', type=str, nargs='?', help='Filename of the .par file')
	
	parser.add_argument('--skipinterstate', action='store_true', help='Do not test interstate parameters')
	parser.add_argument('--skiprotational', action='store_true', help='Do not test pure rotational parameters')
	parser.add_argument('--skipfixed',  action='store_true', help='Do not test fixed parameters')
	parser.add_argument('--skipglobal', action='store_true', help='Do not test global parameters')
	
	parser.add_argument('--newinteraction', type=int, nargs='+', help='States to find new interactions for')
	parser.add_argument('--initialvalues', nargs='*', type=float, help='Initial values to test for parameters (default 1E-37)')
	parser.add_argument('--skipsavebest', action='store_true', help='Do not save the best run to "best.par"')
	parser.add_argument('--stateqn', default=4, type=int, help='Quantum number index for state')

	parser.add_argument('--areduction', dest='parameters', action='store_const', const='a_reduction', help='Use A-Reduction parameters')
	parser.add_argument('--sreduction', dest='parameters', action='store_const', const='s_reduction', help='Use S-Reduction parameters')
	parser.add_argument('--linear',     dest='parameters', action='store_const', const='linear',      help='Use linear parameters')
	
	parser.add_argument('--lin_qn', default='qnu2', type=str, help='Quantum number to filter dataset by')
	parser.add_argument('--skip_lin_qn', action='store_true', help='Use immediately the whole dataset')
	parser.add_argument('--min_lin_qn', default=0, type=int, help='Start value for lin_qn')

	args = parser.parse_args()


	lin = pyckett.lin_to_df(args.linfile)
	par = pyckett.parvar_to_dict(args.parfile if args.parfile else args.linfile.replace(".lin", ".par"))
	
	VIB_DIGITS = pyckett.get_vib_digits(par)
	ALL_STATES = pyckett.get_all_states(VIB_DIGITS)
	
	qnu, qnl = f'qnu{args.stateqn:1.0f}', f'qnl{args.stateqn:1.0f}'
	
	kwargs = {
		'skipglobal': args.skipglobal,
		'skipfixed': args.skipfixed,
		'skipinterstate': args.skipinterstate,
		'skiprotational': args.skiprotational,
		
		'qnu': qnu,
		'qnl': qnl,

		'parameters': args.parameters, 
		'newinteraction': args.newinteraction, 
		'skipsavebest': False, # @Luis: Change to true -> will be overwritten anyways
		'initialvalues': args.initialvalues,
	
		'lin_qn': args.lin_qn,
		'skip_lin_qn': args.skip_lin_qn,
		'min_lin_qn': args.min_lin_qn,
		
		'report': True, 
		'report_subprocesses': False, 
		
		'add_adoption': None, 
		'omit_adoption': None, 
	}
	
	par, log_data = automaticfit_core(par, lin, VIB_DIGITS, ALL_STATES, **kwargs)

	with open("automatedfit.par", "w+") as file:
		file.write(pyckett.dict_to_parvar(par))
	
	with open("automatedfit.log", "w+") as file:
		json.dump(log_data, file, indent=2)
	
def automatic_base_adoption_omit(runs):
	if len(runs) < 2:
		return(False)
	
	index_initial = [i for i, x in enumerate(runs) if x['id'] == 'INITIAL'][0]
	
	init_stats = runs.pop(index_initial)
	best_stats = runs[0]
	
	if init_stats['rms'] and best_stats['rms'] / init_stats['rms'] < 1.1 and best_stats["stats"]['rejected_lines'] <= init_stats["stats"]['rejected_lines'] and best_stats["stats"]['diverging'] != "LAST":
		return(True)
	return(False)

def automatic_base_adoption_add(init_stats, best_stats, results):
	if init_stats['rms'] and best_stats['rms'] / init_stats['rms'] < 0.9 and best_stats["stats"]['rejected_lines'] <= init_stats["stats"]['rejected_lines'] and best_stats["stats"]['diverging'] != "LAST":
		return(True)
	return(False)
	
def prit(condition, text=''):
	if condition:
		print(text)

def automaticfit_core(par, lin, VIB_DIGITS, ALL_STATES, lin_qn='qnu2', min_lin_qn=0, skip_lin_qn=False, qnu='qnu4', qnl='qnl4', parameters=None, skipsavebest=True, report=True, newinteraction=None, initialvalues=None, skipinterstate=False, skiprotational=False, skipfixed=False, skipglobal=False, omit_adoption=None, add_adoption=None, report_subprocesses=False):

	log_data = []
	if not omit_adoption:
		omit_adoption = automatic_base_adoption_omit
	
	if not add_adoption:
		add_adoption = automatic_base_adoption_add
	
	add_kwargs = {
		'VIB_DIGITS': VIB_DIGITS,
		'ALL_STATES': ALL_STATES,
		'skipglobal': skipglobal,
		'skipfixed': skipfixed,
		'skipinterstate': skipinterstate,
		'skiprotational': skiprotational,
		
		'qnu': qnu,
		'qnl': qnl,

		'parameters': parameters, 
		'newinteraction': newinteraction, 
		'skipsavebest': skipsavebest, 
		'initialvalues': initialvalues,
		
		'report': report_subprocesses,
	}
	
	omit_kwargs = {
		'VIB_DIGITS': VIB_DIGITS,
		'ALL_STATES': ALL_STATES,
		'skipglobal': skipglobal,
		'skipfixed': skipfixed,
		'skipinterstate': skipinterstate,
		'skiprotational': skiprotational,
		
		'report': report_subprocesses,
	}
	
	if skip_lin_qn:
		lin_qn = 'qnu1'
		lin_qn_max = lin[lin_qn].max()
		lin_qn_cur = lin_qn_max
	else:
		lin_qn_max = lin[lin_qn].max()
		lin_qn_cur = min(min_lin_qn, lin_qn_max)
	
	while lin_qn_cur <= lin_qn_max:
		lin_cur = lin.query(f'{lin_qn} <= {lin_qn_cur}')
		
		prit(report, f"Including all lines with {lin_qn} <= {lin_qn_cur}")
		lin_qn_cur += 1
		
		if not len(lin_cur):
			continue
		
		results = pyckett.run_spfit_v(par, lin_cur)
		stats = pyckett.parse_fit_result(results["msg"], results["var"])
		rms = stats["rms"]
		rl = stats["rejected_lines"]
		
		prit(report, f"RMS is currently {rms} with {rl} rejected lines.")
		prit(report, )
		
		log_data.append({"rms": float(rms), "rejected_lines": int(rl), "lin_qn_cur": int(lin_qn_cur), "added": [], "omitted": []})


		# check if any parameters can be omited
		while True:
			with open('test.par', 'w+') as file:
				file.write(pyckett.dict_to_parvar(par))
			
			with open('test.lin', 'w+') as file:
				file.write(pyckett.df_to_lin(lin_cur))
			
			par.update(pyckett.PARUPDATE)
			runs = omitparameters_core(par, lin_cur, **omit_kwargs)
			
			if not omit_adoption(runs):
				break
			
			id_to_omit = runs[0]['id']
			prit(report, f"Omitting {id_to_omit}")
			log_data[-1]["omitted"].append(int(id_to_omit))
			
			par["PARAMS"] = [x for x in par['PARAMS'] if x[0] != id_to_omit]
			par = pyckett.run_spfit_v(par, lin_cur)['par']
		
		# check if any parameters should be added
		while True:
			par.update(pyckett.PARUPDATE)
			init_stats, best_stats, results = addparameters_core(par, lin_cur, **add_kwargs)
		
			if not add_adoption(init_stats, best_stats, results):
				break
			
			id_to_add = best_stats['id'][0]
			
			prit(report, f"Adding {id_to_add}")
			log_data[-1]["added"].append(int(id_to_add))
			
			par["PARAMS"] = best_stats['par']
			par = pyckett.run_spfit_v(par, lin_cur)['par']
	
	par.update(pyckett.PARUPDATE)
	results = pyckett.run_spfit_v(par, lin_cur)
	stats = pyckett.parse_fit_result(results["msg"], results["var"])
	rms = stats["rms"]
	rl = stats["rejected_lines"]
	log_data.append({"rms": float(rms), "rejected_lines": int(rl), "lin_qn_cur": int(lin_qn_cur)})
	
	return(par, log_data)