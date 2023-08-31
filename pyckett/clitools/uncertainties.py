#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : CLI tool for showing parameter uncertainties

import argparse
import pyckett

def uncertainties():
	parser = argparse.ArgumentParser(prog='Show Uncertainties')
	
	parser.add_argument('varfile', type=str, help='Filename of the .var file')
	parser.add_argument('--unordered', action='store_true', help='Do not sort by relative uncertainty')
	parser.add_argument('--interstate', action='store_true', help='Only test interstate parameters')
	parser.add_argument('--rotational', action='store_true', help='Only test pure rotational parameters')
	parser.add_argument('--skipfixed',  action='store_true', help='Do not test fixed parameters')
	parser.add_argument('--skipglobal', action='store_true', help='Do not test global parameters')
	
	args = parser.parse_args()


	var = pyckett.parvar_to_dict(args.varfile)
	VIB_DIGITS = pyckett.get_vib_digits(var)
	ALL_STATES = pyckett.get_all_states(VIB_DIGITS)
	
	params = {}
	for param in var['PARAMS']:
		id_, value, unc = param[:3]
		rel_unc = abs(unc / value) if value else 0
		params[id_] = {'id': id_, 'value': value, 'unc': unc, 'rel_unc': rel_unc}
	
	output = []
	for id_, param in params.items():
		_, rel_unc, value, unc = param['id'], param['rel_unc'], param['value'], param['unc']
		parsed_id = pyckett.parse_param_id(id_, VIB_DIGITS)
		
		isinterstate = (parsed_id['v1'] != parsed_id['v2'])
		isrotational = (parsed_id['v1'] == parsed_id['v2'])
		isglobal     = (parsed_id['v1'] == parsed_id['v2'] == ALL_STATES)
		isfixed      = (abs(unc) < pyckett.ZEROTHRESHOLD)
		
		if args.skipfixed and isfixed:
			continue
		
		if args.skipglobal and isglobal:
			continue
		
		if args.interstate and not isinterstate:
			continue
		
		if args.rotational and not isrotational:
			continue
		
		global_id = pyckett.format_param_id({**parsed_id, **{'v1': ALL_STATES, 'v2': ALL_STATES}}, VIB_DIGITS)
		global_param = params.get(global_id)
		rel_global = param['value'] / global_param['value'] if global_param and global_param['value'] else 0
		
		output.append((rel_unc, f"ID {id_:8}; REL UNC {rel_unc:10.4f};   VALUE {value: .2e};   ABS UNC {unc: .2e};   GLOB REL {rel_global:10.4f}"))
	
	if not args.unordered:
		output.sort(key=lambda x: x[0], reverse=True)
	
	print("\n".join([x[1] for x in output]))

