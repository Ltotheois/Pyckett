#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Luis Bonah
# Description : CLI tool for checking which parameter to add to fit

import os
import subprocess
import argparse

def runfit():
	parser = argparse.ArgumentParser(prog='Run SPFIT')
	parser.add_argument('linfile', type=str, help='Filename of the .lin file')
	parser.add_argument('parfile', type=str, nargs='?', help='Filename of the .par file')
	args = parser.parse_args()

	linfile = args.linfile
	root, ext = os.path.splitext(linfile)
	if not ext:
		linfile = linfile + ".lin"
	
	parfile = args.parfile if args.parfile else linfile.replace(".lin", ".par")
	
	path = os.environ.get("PYCKETT_SPFIT_PATH", "spfit")
	command = [path, linfile, parfile]
	
	with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
		while process.poll() is None:
			text = process.stdout.read1().decode("utf-8")
			print(text, end="", flush=True)

		text = process.stdout.read().decode("utf-8")
		print(text)

def runpredictions():
	parser = argparse.ArgumentParser(prog='Run SPCAT')
	parser.add_argument('intfile', type=str, help='Filename of the .int file')
	parser.add_argument('varfile', type=str, nargs='?', help='Filename of the .var file')
	args = parser.parse_args()
	
	intfile = args.intfile
	root, ext = os.path.splitext(intfile)
	if not ext:
		intfile = intfile + ".int"
	
	varfile = args.varfile if args.varfile else intfile.replace(".int", ".var")
	
	path = os.environ.get("PYCKETT_SPCAT_PATH", "spcat")
	command = [path, intfile, varfile]
	
	with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
		while process.poll() is None:
			text = process.stdout.read1().decode("utf-8")
			print(text, end="", flush=True)
		
		text = process.stdout.read().decode("utf-8")
		print(text)