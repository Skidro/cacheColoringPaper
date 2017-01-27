##
# File
# 	mem_page.py
#
# Description
# 	This file contains python script for plotting the probability density curve
# 	for cache-miss rate (over 100 iterations)
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
pl_rows = 1
pl_cols = 3


class mem_page(File):
	""" A subclass of file-type objects to process miss-rate in Xeon
	    platform """

	def __init__(self, filename, platform = 'Xeon'):
		# Invoke the super-class constructor method
		super(mem_page, self).__init__(filename)

		# Declare the platform type for this file object
		self.platform = platform

		# Parse the file
		self.parse()

		return

	def parse(self):
		""" This is the primary function for extracting miss-rate from a perf log file """
		accesses = misses = time = inspc = 0

		# Open and parse the file
		with open(self.name, 'r') as fdi:
			for line in fdi:
				# Get the required lines
				refsLine = re.match('^\D*([\d,]+) cache-references.*$', line)
				missLine = re.match('^\D*([\d,]+) cache-misses.*$', line)
				timeLine = re.match('^\D*([\d.]+) seconds time.*$', line)
				inspLine = re.match('^.*#\D*([\d.]+)[^a-b]*insns per cycle.*$', line)

				if refsLine:
					accesses = int(re.sub('\D', '', refsLine.group(1)))

				if missLine:
					misses   = int(re.sub('\D', '', missLine.group(1)))

				if inspLine:
					try:
						inspc    = float(inspLine.group(1))
					except:
						raise ValueError, 'Could not convert string (%s) to float' % (inspLine.group(1))
						sys.exit(-1)

				if timeLine:
					try:
						time = float(timeLine.group(1))
					except:
						raise ValueError, 'Could not convert string (%s) to float' % (timeLine.group(1))
						sys.exit(-1)

		if accesses == 0 or misses == 0 or time == 0 or inspc == 0:
			print 'Unexpected File : %s' % (self.name)
			sys.exit(-1)

		# Extract the file number
		try:
			file_number = (re.match("^.*1/\D*(\d+)\.log", self.name)).group(1)
		except:
			raise ValueError, 'File Number could not be extracted %s' % (self.name)
			sys.exit(-2)

		# Insert the data in the hash
		plot_data[file_number] = (accesses, misses, time, inspc)

		return

# plot_data
# Function to plot_data parsed from the files
def plotdata(position, title):
	""" Function for plotting the collected data about miss-rate """

	mr_array_usort = []
	time_array = []
	number = 0
	max_rate = 0.0
	min_rate = 100.0

	# Create arrays for histogram data
	ht_data = {}
	ht_data['time'] = []
	ht_data['miss'] = []
	ht_data['refs'] = []
	ht_data['rate'] = []
	ht_data['ipcs'] = []

	for item in plot_data.keys():
		references 	= plot_data[item][0]
		misses 		= plot_data[item][1]
		time 		= plot_data[item][2]
		instructions 	= plot_data[item][3]
		miss_rate 	= (float(misses)/references) * 100

		# Populate the histogram arrays
		ht_data['time'].append(time)
		ht_data['refs'].append(references)
		ht_data['miss'].append(misses)
		ht_data['rate'].append(miss_rate)
		ht_data['ipcs'].append(instructions)

	# Normalize the histogram statistics for all metrics w.r.t. the mean
	ht_tme_mean = np.mean(ht_data['time'])
	ht_ref_mean = np.mean(ht_data['refs'])
	ht_mis_mean = np.mean(ht_data['miss'])
	ht_mrt_mean = np.mean(ht_data['rate'])
	ht_ipc_mean = np.mean(ht_data['ipcs'])

	ht_data['time'] = [(x / ht_tme_mean) + 0 for x in ht_data['time']]
	ht_data['rate'] = [(x / ht_mrt_mean) + 2 for x in ht_data['rate']]
	ht_data['refs'] = [(x / ht_ref_mean) + 4 for x in ht_data['refs']]
	ht_data['miss'] = [(x / ht_mis_mean) + 6 for x in ht_data['miss']]
	ht_data['ipcs'] = [(x / ht_ipc_mean) + 8 for x in ht_data['ipcs']]

	# Create a subplot for timing bars
	mrate_pl = pl.subplot(pl_rows, pl_cols, position)

	# Plot the statistics data
	pl.plot(xrange(99), ht_data['time'], 'b', label = "Time")
	pl.plot([0, 99], [1, 1], 'b--')

	pl.plot(xrange(99), ht_data['rate'], 'r', label = "Miss-Rate")
	pl.plot([0, 99], [3, 3], 'r--')

	pl.plot(xrange(99), ht_data['refs'], 'g', label = "References")
	pl.plot([0, 99], [5, 5], 'g--')

	pl.plot(xrange(99), ht_data['miss'], 'y', label = "Misses")
	pl.plot([0, 99], [7, 7], 'y--')

	pl.plot(xrange(99), ht_data['ipcs'], 'k', label = "IPC")
	pl.plot([0, 99], [9, 9], 'k--')

	pl.xlabel('Test Run')
	pl.ylabel('Normalized Statistics')
	pl.tick_params(axis = 'y', left = 'off', right = 'off', labelleft = 'off')

	# Show legend on the plot
	pl.legend(loc = "upper center")

	# Set the y-axis limit
	pl.ylim(0, 11)

	pl.title(title.upper())

	return

def do_set(partition_type, algorithm, position):
	""" Helper function for plotting mutiple data sets """

	# Reset the global plot-data hash
	plot_data = {}

	# Set the parent directory path based on platform name
	parent_dir = '../1/'

	# Parse the data in each file
	for item in range(1, 100):
		file_path = parent_dir + partition_type + '/' + algorithm + '/' + str(item) + '.log'
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
	partition_type = 'sets'				# Type of paritioning
	partition_utilization = 0.95			# Fraction of partition which is filled by working set
	algorithms = ['random', 'rr', 'bb']		# Page placement algorithm used inside memory allocator

	partition_size = cache_utilization * cache_size
	working_set_size = partition_utilization * partition_size

	# Create a figure to save all plots
	fig = pl.figure(1, figsize = (35, 15))
	position = 1

	# Define the name to save the figure with
	figname = 'XE_BW_HIST_' + partition_type.upper() + '.png'

	# Place a title for these plots
	pl.suptitle('Xeon | BW-R | ' + str(partition_size) + ' | ' + str(working_set_size) + ' | ' + partition_type.upper(), fontsize = pl_sup_title_fontsize)

	for algorithm in algorithms:
		# Plot the data one set at a time
		do_set(partition_type, algorithm, position)

		# Update position for next iteration
		position += 1

		# Save the figure
		fig.savefig(figname)

	return

# Desginate main as the entry point
if __name__ == "__main__":
	# Call the main function
	main()
