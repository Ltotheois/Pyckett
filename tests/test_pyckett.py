# -*- coding: utf-8 -*-
#!/usr/bin/env python3

# Author: Luis Bonah
# Description : Tests for Pyckett library

import unittest
import pyckett
import numpy as np


class TestLabels(unittest.TestCase):
	def test_QNLABELS(self):
		self.assertEqual(pyckett.qnlabels_from_quanta(), pyckett.QNLABELS)
		
	def test_QNLABELS_ENERGY(self):
		self.assertEqual(pyckett.qnlabels_energy_from_quanta(), pyckett.QNLABELS_ENERGY)

class TestCatFormat(unittest.TestCase):
	def test_cat_dtypes(self):
		self.assertEqual(pyckett.cat_dtypes_from_quanta(), pyckett.cat_dtypes)
		self.assertEqual(pyckett.cat_dtypes_from_quanta(), pyckett.cat_dtypes_from_quanta(6))
		
		self.assertEqual(pyckett.cat_dtypes_from_quanta(3), {
			'x': np.float64,
			'error': np.float64,
			'y': np.float64,
			'degfreed': pyckett.pickett_int,
			'elower': np.float64,
			'usd': pyckett.pickett_int,
			'tag': pyckett.pickett_int,
			'qnfmt': pyckett.pickett_int,
			**{f'qn{ul}{i+1}': pyckett.pickett_int for ul in ('u', 'l') for i in range(6)},

		})
		
		self.assertEqual(pyckett.cat_dtypes_from_quanta(6), {
			'x': np.float64,
			 'error': np.float64,
			 'y': np.float64,
			 'degfreed': pyckett.pickett_int,
			 'elower': np.float64,
			 'usd': pyckett.pickett_int,
			 'tag': pyckett.pickett_int,
			 'qnfmt': pyckett.pickett_int,
			**{f'qn{ul}{i+1}': pyckett.pickett_int for ul in ('u', 'l') for i in range(6)},

		})
		
		self.assertEqual(pyckett.cat_dtypes_from_quanta(8), {
			'x': np.float64,
			'error': np.float64,
			'y': np.float64,
			'degfreed': pyckett.pickett_int,
			'elower': np.float64,
			'usd': pyckett.pickett_int,
			'tag': pyckett.pickett_int,
			'qnfmt': pyckett.pickett_int,
			**{f'qn{ul}{i+1}': pyckett.pickett_int for ul in ('u', 'l') for i in range(8)},
		})

	def test_cat_widths(self):
		self.assertEqual(pyckett.cat_widths_from_quanta(), pyckett.cat_widths)
		self.assertEqual(pyckett.cat_widths_from_quanta(), pyckett.cat_widths_from_quanta(6))
		
		self.assertEqual(pyckett.cat_widths_from_quanta(3), {
			'x':		13,
			'error':	 8,
			'y':		 8,
			'degfreed':	 2,
			'elower':	10,
			'usd':		 3,
			'tag':		 7,
			'qnfmt':	 4,
			**{f'qn{ul}{i+1}': 2 for ul in ('u', 'l') for i in range(6)},
		})
		
		self.assertEqual(pyckett.cat_widths_from_quanta(6), {
			'x':		13,
			'error':	 8,
			'y':		 8,
			'degfreed':	 2,
			'elower':	10,
			'usd':		 3,
			'tag':		 7,
			'qnfmt':	 4,
			**{f'qn{ul}{i+1}': 2 for ul in ('u', 'l') for i in range(6)},
		})
		
		self.assertEqual(pyckett.cat_widths_from_quanta(8), {
			'x':		13,
			'error':	 8,
			'y':		 8,
			'degfreed':	 2,
			'elower':	10,
			'usd':		 3,
			'tag':		 7,
			'qnfmt':	 4,
			**{f'qn{ul}{i+1}': 2 for ul in ('u', 'l') for i in range(8)},
		})

class TestLinFormat(unittest.TestCase):
	def test_lin_dtypes(self):
		self.assertEqual(pyckett.lin_dtypes_from_quanta(), pyckett.lin_dtypes)
		self.assertEqual(pyckett.lin_dtypes_from_quanta(), pyckett.lin_dtypes_from_quanta(6))
		
		self.assertEqual(pyckett.lin_dtypes_from_quanta(3), {
			**{f'qn{ul}{i+1}': pyckett.pickett_int for ul in ('u', 'l') for i in range(6)},
			'x':		np.float64,
			'error':	np.float64,
			'weight':	np.float64,
			'comment':	str,
		})
		
		self.assertEqual(pyckett.lin_dtypes_from_quanta(6), {
			**{f'qn{ul}{i+1}': pyckett.pickett_int for ul in ('u', 'l') for i in range(6)},
			'x':		np.float64,
			'error':	np.float64,
			'weight':	np.float64,
			'comment':	str,
		})
		
		self.assertEqual(pyckett.lin_dtypes_from_quanta(8), {
			**{f'qn{ul}{i+1}': pyckett.pickett_int for ul in ('u', 'l') for i in range(8)},
			'x':		np.float64,
			'error':	np.float64,
			'weight':	np.float64,
			'comment':	str,
		})

class TestEgyFormat(unittest.TestCase):
	def test_egy_dtypes(self):
		self.assertEqual(pyckett.egy_dtypes_from_quanta(), pyckett.egy_dtypes)
		self.assertEqual(pyckett.egy_dtypes_from_quanta(), pyckett.egy_dtypes_from_quanta(6))
		
		self.assertEqual(pyckett.egy_dtypes_from_quanta(3), {
			'iblk':		np.int64,
			'indx':		np.int64,
			'egy':		np.float64,
			'err':		np.float64,
			'pmix':		np.float64,
			'we':		np.int64,
			':':		str,
			**{f'qn{i+1}': pyckett.pickett_int for i in range(6)},
		})
		
		self.assertEqual(pyckett.egy_dtypes_from_quanta(6), {
			'iblk':		np.int64,
			'indx':		np.int64,
			'egy':		np.float64,
			'err':		np.float64,
			'pmix':		np.float64,
			'we':		np.int64,
			':':		str,
			**{f'qn{i+1}': pyckett.pickett_int for i in range(6)},
		})
		
		self.assertEqual(pyckett.egy_dtypes_from_quanta(8), {
			'iblk':		np.int64,
			'indx':		np.int64,
			'egy':		np.float64,
			'err':		np.float64,
			'pmix':		np.float64,
			'we':		np.int64,
			':':		str,
			**{f'qn{i+1}': pyckett.pickett_int for i in range(8)},
		})

	def test_egy_widths(self):
		self.assertEqual(pyckett.egy_widths_from_quanta(), pyckett.egy_widths)
		self.assertEqual(pyckett.egy_widths_from_quanta(), pyckett.egy_widths_from_quanta(6))
		
		self.assertEqual(pyckett.egy_widths_from_quanta(3), {
			'iblk':		 6,
			'indx':		 5,
			'egy':		18,
			'err':		18,
			'pmix':		11,
			'we':		 5,
			':':		 1,
			**{f'qn{i+1}': 3 for i in range(6)},
		})
		
		self.assertEqual(pyckett.egy_widths_from_quanta(6), {
			'iblk':		 6,
			'indx':		 5,
			'egy':		18,
			'err':		18,
			'pmix':		11,
			'we':		 5,
			':':		 1,
			**{f'qn{i+1}': 3 for i in range(6)},
		})
		
		self.assertEqual(pyckett.egy_widths_from_quanta(8), {
			'iblk':		 6,
			'indx':		 5,
			'egy':		18,
			'err':		18,
			'pmix':		11,
			'we':		 5,
			':':		 1,
			**{f'qn{i+1}': 3 for i in range(8)},
		})


class TestFileFormats(unittest.TestCase):
	def test_mecn(self):
		lin = pyckett.lin_to_df('tests/resources/MeCN.lin', sort=False)
		par = pyckett.parvar_to_dict('tests/resources/MeCN.par')
		int = pyckett.int_to_dict('tests/resources/MeCN.int')
		
		active_qns = {'qnu1': True, 'qnu2': True, 'qnu3': True, 'qnu4': True, 'qnu5': False, 'qnu6': False, 'qnl1': True, 'qnl2': True, 'qnl3': True, 'qnl4': True, 'qnl5': False, 'qnl6': False}
		self.assertEqual(pyckett.get_active_qns(lin), active_qns)
		
		vib_digits = 1
		self.assertEqual(pyckett.get_vib_digits(par), vib_digits)
		
		all_states = 9
		self.assertEqual(pyckett.get_all_states(vib_digits), all_states)

		results = pyckett.run_spfit_v(par, lin)
		parsed_result = pyckett.parse_fit_result(results['msg'], results['var'])
		
		rms = 0.018262
		self.assertTrue(np.isclose(parsed_result['rms'], rms, rtol=1E-3))
		
		wrms = 0.89593
		self.assertTrue(np.isclose(float(parsed_result['wrms']), wrms, rtol=1E-3))

		rejected_lines = 0
		self.assertEqual(parsed_result['rejected_lines'], rejected_lines)

		diverging = 'NEVER'
		self.assertEqual(parsed_result['diverging'], diverging)
		
		var = results['var']
		results = pyckett.run_spcat_v(var, int)
		
		cat = results['cat']
		egy = results['egy']
		
		query = 'qnu1 == 1 and qnu2 == 0 and qnu3 == 0 and qnu4 == 1\
		and qnl1 == 0 and qnl2 == 0 and qnl3 == 0 and qnl4 == 0'
		view = cat.query(query)
		freq = view['x'].values[0]
		
		assert_freq = 18397.783
		self.assertTrue(np.isclose(freq, assert_freq))

		query = 'qn1 == 60 and qn2 == 1 and qn3 == 2 and qn4 == 60'
		view = egy.query(query)
		egy = view['egy'].values[0]
		
		assert_egy = 4.966675
		self.assertTrue(np.isclose(egy, assert_egy))

	def test_CH2O(self):
		lin = pyckett.lin_to_df('tests/resources/ch2o.lin', sort=False)
		par = pyckett.parvar_to_dict('tests/resources/ch2o.par')
		int = pyckett.int_to_dict('tests/resources/ch2o.int')
		
		active_qns = {'qnu1': True, 'qnu2': True, 'qnu3': True, 'qnu4': False, 'qnu5': False, 'qnu6': False, 'qnl1': True, 'qnl2': True, 'qnl3': True, 'qnl4': False, 'qnl5': False, 'qnl6': False}
		self.assertEqual(pyckett.get_active_qns(lin), active_qns)
		
		vib_digits = 1
		self.assertEqual(pyckett.get_vib_digits(par), vib_digits)
		
		all_states = 9
		self.assertEqual(pyckett.get_all_states(vib_digits), all_states)

		results = pyckett.run_spfit_v(par, lin)
		parsed_result = pyckett.parse_fit_result(results['msg'], results['var'])
		
		rms = 0.199064
		self.assertTrue(np.isclose(parsed_result['rms'], rms, rtol=1E-3))
		
		wrms = 0.56044
		self.assertTrue(np.isclose(float(parsed_result['wrms']), wrms, rtol=1E-3))

		rejected_lines = 0
		self.assertEqual(parsed_result['rejected_lines'], rejected_lines)

		diverging = 'NEVER'
		self.assertEqual(parsed_result['diverging'], diverging)
		
		var = results['var']
		results = pyckett.run_spcat_v(var, int)
		
		cat = results['cat']
		egy = results['egy']
		
		query = 'qnu1 == 37 and qnu2 == 7 and qnu3 == 30\
		and qnl1 == 37 and qnl2 == 7 and qnl3 == 31'
		view = cat.query(query)
		freq = view['x'].values[0]
		
		assert_freq = 138.7619
		self.assertTrue(np.isclose(freq, assert_freq))

		query = 'qn1 == 4 and qn2 == 0 and qn3 == 4'
		view = egy.query(query)
		egy = view['egy'].values[0]
		
		assert_egy =  24.259666
		self.assertTrue(np.isclose(egy, assert_egy))
	
	def test_CH2O_more_quanta(self):
		pyckett.QUANTA = 7
		try:

			lin = pyckett.lin_to_df('tests/resources/ch2o.lin', sort=False)
			par = pyckett.parvar_to_dict('tests/resources/ch2o.par')
			int = pyckett.int_to_dict('tests/resources/ch2o.int')
			
			par['SPIND'] = 3333
			par['NLINE'] = - abs(par['NLINE'])
			int['FEND'] = 5

			results = pyckett.run_spcat_v(par, int)

			cat = results['cat']
			lin = cat.query('y > 1E-6').copy()

			lin['error'] = 0.050
			lin['weight'] = 1
			lin['comment'] = ''

			np.random.seed(112)
			lin['x'] = lin['x'] + np.random.rand(len(lin)) * 0.1

			results_fit = pyckett.run_spfit_v(par, lin)
			parsed_result = pyckett.parse_fit_result(results_fit['msg'], results_fit['var'])

			results = pyckett.run_spfit_v(par, lin)
			parsed_result = pyckett.parse_fit_result(results['msg'], results['var'])
			
			rms = 0.061034
			self.assertTrue(np.isclose(parsed_result['rms'], rms, rtol=1E-3))
			
			wrms = 0.59024
			self.assertTrue(np.isclose(float(parsed_result['wrms']), wrms, rtol=1E-3))

			rejected_lines = 0
			self.assertEqual(parsed_result['rejected_lines'], rejected_lines)

			diverging = 'LAST'
			self.assertEqual(parsed_result['diverging'], diverging)
			
		except Exception as E:
			raise
		finally:
			pyckett.QUANTA = 6

	# @Luis: Ask Marie-Aline for some test data for a more than six quanta example





# - test add parameter
# - test omit parameter
# - test finalize
# - test get_dr_candidates
# - test CLI tools

# - think about running flake8 and black




# Run python -m unittest discover from main directory
if __name__ == '__main__':
	unittest.main()