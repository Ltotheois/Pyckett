#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : CLI tool for creating separate fits from global fit

import os
import argparse
import pyckett
from concurrent.futures import ThreadPoolExecutor


def separatefits():
	parser = argparse.ArgumentParser(prog='Separate Fits')
	
	parser.add_argument('linfile', type=str, help='Filename of the .lin file')
	parser.add_argument('parfile', type=str, nargs='?', help='Filename of the .par file')
	
	parser.add_argument('--parupdate', action='store_true', help='Reset .par parametes NPAR, NLINE, THRESH')
	parser.add_argument('--stateqn', default=4, type=int, help='Quantum number index for state')
	parser.add_argument('--forcesingles', action='store_true', help='Force single fits')
	parser.add_argument('--keepqns', action='store_true', help='Keep the original state qns')
	
	args = parser.parse_args()
	

	lin = pyckett.lin_to_df(args.linfile)
	par = pyckett.parvar_to_dict(args.parfile if args.parfile else args.linfile.replace(".lin", ".par"))
	
	VIB_DIGITS = pyckett.get_vib_digits(par)
	ALL_STATES = pyckett.get_all_states(VIB_DIGITS)
	
	if args.parupdate:
		par.update(pyckett.PARUPDATE)
	
	if not os.path.isdir('separatefits'):
		os.mkdir('separatefits')
	
	qnu, qnl = f'qnu{args.stateqn:1.0f}', f'qnl{args.stateqn:1.0f}'
	

	params = []
	states_sets = []	
	for param in par["PARAMS"]:
		parsed_id = pyckett.parse_param_id(param[0], VIB_DIGITS)
		v1, v2 = parsed_id['v1'], parsed_id['v2']
		if v1 == v2 == ALL_STATES:
			param[2] = pyckett.ZERO

		params.append([v1, v2, param])
		
		if v1 == v2:
			contains_v = [v1 in states for states in states_sets]			
			if not any(contains_v):
				states_sets.append(set((v1,)))
		elif not args.forcesingles:
			popped_sets = []
			
			for i, states in enumerate(states_sets):
				if v1 in states or v2 in states:
					popped_sets.append(i)
			
			popped_sets = [states_sets.pop(i) for i in popped_sets[::-1]]
			new_set = set((v1, v2)).union(*popped_sets)	
			
			states_sets.append(new_set)
					
	
	states_without_parameters = (set(lin[qnu].unique()) & set(lin[qnl].unique()))
	for v in states_without_parameters:
		if all([v not in states_set for states_set in states_sets]):
			states_sets.append(set((v,)))

	# @Luis: Think about states that are only in lin file
	
	
	def worker(i):
		states = sorted(states_sets[i])
		states_identifier = '_'.join([f'{state:03.0f}' for state in states])
		filename = f"State_{states_identifier}"
	
		tmp_lin = lin.query(f"{qnu} in @states and {qnl} in @states").copy()
	
		filter_states = lambda x: (x[0] in states and x[1] in states) or (x[0] == ALL_STATES and  x[1] == ALL_STATES) 
		tmp_params = [x[-1].copy() for x in params if filter_states(x)]
		tmp_par = par.copy()
		
		if not args.keepqns:
			sign_nvib = -1 if tmp_par['NVIB'] < 0 else 1
			tmp_par['NVIB'] = max(2, len(states)) * sign_nvib
			new_vib_digits = pyckett.get_vib_digits(tmp_par) 
			new_all_states = pyckett.get_all_states(new_vib_digits)
			
			translation_dict = {v: i for i, v in enumerate(states)}
			translation_dict[ALL_STATES] = new_all_states
			
			tmp_lin[qnu] = tmp_lin[qnu].replace(translation_dict)
			tmp_lin[qnl] = tmp_lin[qnl].replace(translation_dict)
			
			for param in tmp_params:
				parsed_id = pyckett.parse_param_id(param[0], VIB_DIGITS)
				parsed_id['v1'] = translation_dict[parsed_id['v1']]
				parsed_id['v2'] = translation_dict[parsed_id['v2']]
				param[0] = pyckett.format_param_id(parsed_id, new_vib_digits)
		tmp_par["PARAMS"] = tmp_params

		with open(os.path.join('separatefits', filename + ".lin"), "w+") as file:
			file.write(pyckett.df_to_lin(tmp_lin))
		
		with open(os.path.join('separatefits', filename + ".par"), "w+") as file:
			file.write(pyckett.dict_to_parvar(tmp_par))
		
		if len(tmp_lin):
			message = pyckett.run_spfit(filename, wd="separatefits")
			stats = pyckett.parse_fit_result(message, pyckett.parvar_to_dict(os.path.join('separatefits', filename + ".var")))
		else:
			stats = {}
		stats['states'] = states
		stats['total_lines'] = len(tmp_lin)
		
		return(stats)
	
	
	with ThreadPoolExecutor() as executor:
		futures = {i: executor.submit(worker, i) for i in range(len(states_sets))}
		runs = [f.result() for f in futures.values()]
	
	header = "States         |  RMS / kHz  |  Rejected  | Total Lines"
	print(header)
	print("-" * len(header))
	for results in sorted(runs, key=lambda x: x['states'][0]):
		states_identifier = '_'.join([f'{state:03.0f}' for state in results['states']])	
		if 'rms' in results:
			# print(f"States {states_identifier:15};   RMS {results['rms']*1000 :12.4f} kHz; Rejected lines {results['rejected_lines'] :7.0f} /{results['total_lines'] :7.0f}")
			print(f"{states_identifier:15}|{results['rms']*1000 :12.4f} |{results['rejected_lines'] :11.0f} |{results['total_lines'] :12.0f}")

