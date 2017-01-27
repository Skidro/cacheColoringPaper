########################################################################################
#
# File 
# 	generic_parser.py
#
# Description
#	This file contains python classes for parsing different types of files
#
########################################################################################

import os
import collections

class File(object):
	""" A simple class for handling files """
	def __init__(self, filename = 'Nill'):
		if os.path.isfile(filename):
			self.name = filename
		else:
			raise ValueError, 'File (%s) does not exists!' % (filename)

		return

	def __str__(self):
		return self.name

	def parse(self):
		raise ValueError, 'Parser not implemented'

	def get_name(self):
		return self.name
