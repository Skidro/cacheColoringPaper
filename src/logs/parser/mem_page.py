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
pl_rows = 2
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
			file_number = (re.match("^\D*(\d+)\.log", self.name)).group(1)
		except:
			raise ValueError, 'File Number could not be extracted'
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

	for item in plot_data.keys():
		mr_array_usort.append((float(plot_data[item][1])/plot_data[item][0]) * 100)

		time_array.append(plot_data[item][3])

		if mr_array_usort[number] > max_rate:
			max_rate = mr_array_usort[number]
			max_file = int(item)

		if mr_array_usort[number] < min_rate:
			min_rate = mr_array_usort[number]
			min_file = int(item)
			
		number += 1

	# Sort the data
	mr_array = sorted(mr_array_usort)
	time_array = sorted(time_array)

	# Calculate the mean and standard deviation
	mr_mean = np.mean(mr_array)
	mr_std  = np.std(mr_array)
	tm_mean = np.mean(time_array)
	tm_std  = np.std(time_array)
	tm_min  = time_array[0]
	tm_max  = time_array[-1]

	# Push the data regarding the plots in the global arrays
	avg_miss_rate.append(mr_mean)
	avg_time.append(tm_mean)
	extrema_files.append((min_file, max_file))
	extrema_miss_rate.append((min_rate, max_rate))
	extrema_time.append((tm_min, tm_max))

	# Fit a normal curve on the sorted data
	fit = stats.norm.pdf(mr_array, mr_mean, mr_std)

	# Create a sub-plot for all the plots
	pl.subplot(pl_rows, pl_cols, position)

	# Plot the normal curve
	pl.plot(mr_array, fit)

	# Plot the histogram along the curve
	pl.hist(mr_array, normed = True, bins = np.arange(min_rate, max_rate, (max_rate - min_rate)/10))

	# Plot vertical lines to indicate min-max values
	# pl.plot([max_rate, max_rate], [0, 1], '-r')
	# pl.plot([min_rate, min_rate], [0, 1], '-g')

	# State the x-label and y-label
	pl.xlabel('Miss-Rate', fontsize = pl_x_axis_fontsize)
	pl.ylabel('PDF', fontsize = pl_y_axis_fontsize)
	pl.tick_params(axis = 'y', left = 'off', right = 'off', labelleft = 'off')

	# Create a title for this plot
	pl.title('< ' + format(mr_mean, '0.2f') + '% > | [ ' + format(max_rate, '0.2f') + '% ] | ( ' + format(min_rate, '0.2f') + '% ) | ' + title.upper(), fontsize = pl_title_fontsize)

	# Set axes limits
	pl.xlim(0, 100)
	# pl.ylim(0, 1)

	# Create a subplot for timing bars
	mrate_pl = pl.subplot(pl_rows, pl_cols, position + pl_cols)

	# Fit a normal curve on sorted timing data
	fit = stats.norm.pdf(time_array, tm_mean, tm_std)

	# Plot the normal curve
	pl.plot(time_array, fit) 

	# Plot data histograms along the curve
	pl.hist(time_array, normed = True, bins = np.arange(tm_min, tm_max, (tm_max - tm_min)/10))

	# Plot vertical lines to indicate min-max values
	# pl.plot([tm_max, tm_max], [0, 7], '-r')
	# pl.plot([tm_min, tm_min], [0, 7], '-g')

	# Label the axis
	pl.xlabel('IPC', fontsize = pl_x_axis_fontsize)
	pl.ylabel('PDF', fontsize = pl_y_axis_fontsize)
	pl.tick_params(axis = 'y', left = 'off', right = 'off', labelleft = 'off')

	# Create a title for the plot
	pl.title('< ' + format(tm_mean, '0.3f') + ' > | [ ' + format(tm_max, '0.3f') + ' ] | ( ' + format(tm_min, '0.3f') + ' )', fontsize = pl_title_fontsize)

	# Set axes limits
	pl.xlim(0.5, 1.5)
	# pl.ylim(0, 1)

	return

def do_set(partition_type, algorithm, position):
	""" Helper function for plotting mutiple data sets """

	# Reset the global plot-data hash
	plot_data = {}

	# Set the parent directory path based on platform name
	parent_dir = ''

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
	partition_type = 'ways'				# Type of paritioning
	partition_utilization = 0.95			# Fraction of partition which is filled by working set
	algorithms = ['random', 'rr', 'bb']		# Page placement algorithm used inside memory allocator

	partition_size = cache_utilization * cache_size
	working_set_size = partition_utilization * partition_size

	# Create a figure to save all plots
	fig = pl.figure(1, figsize = (35, 15))
	position = 1

	# Define the name to save the figure with
	figname = 'XE_BW_' + partition_type.upper() + '.png'

	# Place a title for these plots
	pl.suptitle('Xeon | BW-R | ' + str(partition_size) + ' | ' + str(working_set_size) + ' | ' + partition_type.upper(), fontsize = pl_sup_title_fontsize)

	for algorithm in algorithms:
		# Plot the data one set at a time
		do_set(partition_type, algorithm, position)

		# Update position for next iteration
		position += 1

		# Save the figure
		fig.savefig(figname)

		# Print the global data
		# print '<Time>      : ', avg_time
		# print '<Miss Rate> : ', avg_miss_rate
		# print '[Time]      : ', extrema_time
		# print '[Miss-Rate] : ', extrema_miss_rate
		# print 'Files       : ', extrema_files

	return

# Desginate main as the entry point
if __name__ == "__main__":
	# Call the main function
	main()
