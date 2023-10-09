#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : CLI tool for checking which parameter to omit from fit

import argparse
import pyckett

def omitparameters():
	parser = argparse.ArgumentParser(prog='Omit Parameters')
	
	parser.add_argument('linfile', type=str, help='Filename of the .lin file')
	parser.add_argument('parfile', type=str, nargs='?', help='Filename of the .par file')
	
	parser.add_argument('--skipinterstate', action='store_true', help='Do not test interstate parameters')
	parser.add_argument('--skiprotational', action='store_true', help='Do not test pure rotational parameters')
	parser.add_argument('--skipfixed',  action='store_true', help='Do not test fixed parameters')
	parser.add_argument('--skipglobal', action='store_true', help='Do not test global parameters')
	
	parser.add_argument('--skipparupdate',  action='store_true', help='Do not reset .par parametes NPAR, NLINE, THRESH')

	args = parser.parse_args()


	lin = pyckett.lin_to_df(args.linfile)
	par = pyckett.parvar_to_dict(args.parfile if args.parfile else args.linfile.replace(".lin", ".par"))
	
	VIB_DIGITS = pyckett.get_vib_digits(par)
	ALL_STATES = pyckett.get_all_states(VIB_DIGITS)
	
	if not args.skipparupdate:
		par.update(pyckett.PARUPDATE)

	kwargs = {
		'VIB_DIGITS': VIB_DIGITS,
		'ALL_STATES': ALL_STATES,
		'skipglobal': args.skipglobal,
		'skipfixed': args.skipfixed,
		'skipinterstate': args.skipinterstate,
		'skiprotational': args.skiprotational,
	}

	omitparameters_core(par, lin, **kwargs)

def omitparameters_core(par, lin, VIB_DIGITS=1, ALL_STATES=9, skipglobal=False, skipfixed=True, skipinterstate=True, skiprotational=True, report=True):
	candidates = ['INITIAL']
	
	for param in par['PARAMS']:
		id = param[0]
		parsed_id = pyckett.parse_param_id(id, VIB_DIGITS)
		
		isinterstate = (parsed_id['v1'] != parsed_id['v2'])
		isrotational = (parsed_id['v1'] == parsed_id['v2'])
		isglobal     = (parsed_id['v1'] == parsed_id['v2'] == ALL_STATES)
		isfixed      = (abs(param[2]) < pyckett.ZEROTHRESHOLD)
		
		if skipfixed and isfixed:
			continue
		
		if skipglobal and isglobal:
			continue
		
		if skipinterstate and isinterstate:
			continue
		
		if skiprotational and isrotational:
			continue
		
		candidates.append(id)

	runs = pyckett.omit_parameter(par, lin, candidates)
	
	if report:
		for results in runs:
			if results["rms"] is None:
				print(f"ID {results['id']:8}; FAILED! This parameter could be essential.")
			else:
				print(f"ID {results['id']:8}; RMS of {results['rms']*1000 :10.2f} kHz; Rejected lines {results['stats']['rejected_lines']:8}; Diverging {results['stats']['diverging']:8};")

	return(runs)

