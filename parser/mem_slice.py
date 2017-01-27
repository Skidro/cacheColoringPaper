##
# File
# 	mem_page.py
#
# Description
# 	This file contains python script for plotting the cache slice utilization
# 	hitstograms for Intel CAT enabled caches
#
##

import re, sys
import numpy as np
import pylab as pl
import scipy.stats as stats

from generic_page import *

# Global Data
plot_data = {}
avg_miss_rate = []
avg_time = []
extrema_miss_rate = []
extrema_time = []
extrema_files = []

# Specify plot characteristics
pl_sup_title_fontsize = 25
pl_title_fontsize = 20
pl_x_axis_fontsize = 20
pl_y_axis_fontsize = 20
pl_rows = 2
pl_cols = 1


class mem_page(File):
	""" A subclass of file-type objects to process miss-rate in Xeon
	    platform """

	def __init__(self, filename, platform = 'Xeon'):
		# Invoke the super-class constructor method
		super(mem_page, self).__init__(filename)

		# Declare the platform type for this file object
		self.platform = platform
		self.slice_count = 6

		# Parse the file
		self.parse()

		return

	def parse(self):
		""" This is the primary function for extracting slice utilization data from uncore counters """
		slice_references = [0 for x in xrange(self.slice_count)]

		# Open and parse the file
		with open(self.name, 'r') as fdi:
			for line in fdi:
				# Get the required lines
				slice_data = re.match('^slice-([\d]+) : ([\dabcdef]+)$', line)

				# Make sure that required data was extracted from the line
				try:
					slice_number 	= int(slice_data.group(1))
					ref_count	= int(slice_data.group(2), 16)

					# Store the data in array
					slice_references[slice_number] = ref_count
				except:
					raise ValueError, 'Unable to extract slice utilization data from line : %s' % (line)
					sys.exit(-1)

		# Extract the file number
		try:
			file_number = (re.match('^\D+/\d+/(\d+).uncore', self.name)).group(1)
		except:
			raise ValueError, 'Unable to extract file number from string : %s' % (self.name)
			sys.exit(-2)

		# Calculate the average value of slice references for this run
		avg_slice_refs = np.mean(slice_references)

		# Calculate the over / under utilization of each slice
		slice_utilization = [(((x - avg_slice_refs) / avg_slice_refs) * 100) for x in slice_references]

		# Insert the data in the hash
		plot_data[file_number] = slice_utilization
		print "File : %s | Utilization : %f" % (file_number, sum([abs(x) for x in slice_utilization]))

		return

# plot_data
# Function to plot_data parsed from the files
def plotdata(position, title):
	""" Function for plotting the collected data about miss-rate """

	# Plot the histograms for extrema files
	for file_number in plot_data.keys():
		# Create a subplot for this bar-graph
		pl.subplot(pl_rows, pl_cols, position)

		# Plot the bar graph
		x_axis = xrange(len(plot_data[file_number]))
		pl.bar(x_axis, plot_data[file_number], 1)

		# Place label on the axes
		pl.xlabel("Cache Slices")
		pl.ylabel("Normalized Slice Utilization")

		# Put limits to axes range
		pl.ylim(-5, 5)

		# Put a title on this plot
		pl.title('File : %s' % file_number)

		# Update the position for the next plot
		position += 1

	return

def do_set(partition_type, algorithm, partition_utilization, extrema_files, position):
	""" Helper function for plotting mutiple data sets """

	# Reset the global plot-data hash
	plot_data = {}

	# Set the parent directory path based on platform name
	parent_dir = '../data/'

	# Parse the data in each file
	for item in extrema_files:
		file_path = parent_dir + partition_type + '/' + algorithm + '/' + str(partition_utilization) + '/' + str(item) + '.uncore'
		mem_page(file_path)

	# Perform the actual plotting
	title = 'Algorithm : ' + algorithm
	plotdata(position, title)

	return

def main():
	""" This is the primary entry point into the script """

	# Set experiment parameters
	cache_size = 15360				# Xeon Haswell 2618v3L LLC Size
	cache_utilization = 0.25			# Fraction of total cache capacity dedicated to partition
	partition_type = 'ways'				# Type of paritioning
	partition_utilization = 87			# Percentage of partition which is filled by working set
	algorithms = ['bb']				# Page placement algorithm used inside memory allocator

	partition_size = cache_utilization * cache_size
	working_set_size = round(partition_utilization * partition_size / 100)

	# Specify the number of extrema files
	extrema_files = [26, 23]

	# Create a figure to save all plots
	fig = pl.figure(1, figsize = (35, 15))
	position = 1

	# Define the name to save the figure with
	figname = 'XE_BW_SL_EX_BB_' + partition_type.upper() + '_' + str(partition_utilization) + '.png'

	# Place a title for these plots
	pl.suptitle('Xeon | BW-R | SLICES | ' + str(partition_size) + ' | ' + str(working_set_size) + ' | ' + partition_type.upper(), fontsize = pl_sup_title_fontsize)

	for algorithm in algorithms:
		# Plot the data one set at a time
		do_set(partition_type, algorithm, partition_utilization, extrema_files, position)

		# Update position for next iteration
		position += 1

	# Save the figure
	fig.savefig(figname)

	return

# Desginate main as the entry point
if __name__ == "__main__":
	# Call the main function
	main()
