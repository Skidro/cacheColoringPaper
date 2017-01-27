##
# File
# 	mem_box.py
#
# Description
# 	This file contains python script for plotting the box-and-whisker plot
# 	for cache-miss rate and run-time statistics (over 100 iterations)
#
##

import re, sys
import numpy as np
import pylab as pl
from math import ceil

from generic_page import File

# Set to 1 for debugging
boxplot_miss_rate_debug = 0

# Global Data
plot_performance_data = {}
plot_performance_data["miss_rate"] = []
plot_performance_data["time"] = []

class mem_page(File):
	""" A subclass of file-type objects to process miss-rate in tegra
	    platform """

	def __init__(self, filename, platform = 'XE'):
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
				# Check the platform type to select appropriate regex
				if self.platform == 'XE':
					# Get the required lines
					refsLine = re.match('^\D*([\d,]+) cache-references.*$', line)
					missLine = re.match('^\D*([\d,]+) cache-misses.*$', line)
					timeLine = re.match('^\D*([\d.]+) seconds time.*$', line)
					inspLine = re.match('^.*#\D*([\d.]+)[^a-b]*insns per cycle.*$', line)

				if refsLine:
					accesses = int(re.sub('\D', '', refsLine.group(1)))

				if missLine:
					misses   = int(re.sub('\D', '', missLine.group(1)))

				if timeLine:
					try:
						time = float(timeLine.group(1))
					except:
						raise ValueError, 'Could not convert string (%s) to float' % (time.group(1))

				if inspLine:
					try:
						inspc    = float(inspLine.group(1))
					except:
						raise ValueError, 'Could not convert string (%s) to float' % (inspLine.group(1))
						sys.exit(-1)

		if accesses == 0 or misses == 0 or time == 0 or inspc == 0:
			print 'Unexpected File : %s' % (self.name)
			sys.exit(2)

		# Extract the file number
		file_number = (re.match("^.*/(\d+)", self.name)).group(1)

		# Insert the data in the hash
		plot_performance_data[file_number] = (accesses, misses, time, inspc)

		return

def performance_boxplots(figname, title, data_type, utilization, parsed_data, y_down, y_up, auto = True):
	""" This function can be used for drawing box plots """

	# Set uniform fontsize for all the captions
	pl_fontsize = 15

	# Create a figure to save all plots
	fig, ax1 = pl.subplots(figsize = (10, 8))

	# Calculate the extrema of parsed data
	maxs = [np.max(x) for x in parsed_data]
	mins = [np.min(x) for x in parsed_data]  

	bp = pl.boxplot(parsed_data, notch=0, sym='+', vert=1, whis=1.5)
	pl.setp(bp['boxes'], color='black')
	pl.setp(bp['whiskers'], color='black')
	pl.setp(bp['fliers'], color='red', marker='+')

	ax1.yaxis.grid(True, linestyle='-', which='major', color='lightgrey', alpha=0.5)

	ax1.set_axisbelow(True)
	ax1.set_title(title, fontsize = pl_fontsize)
	ax1.set_xlabel('Percentage Utilization', fontsize = pl_fontsize)

	if data_type == 'm':
		ax1.set_ylabel('Miss-Rate', fontsize = pl_fontsize)
		top = ceil(max(maxs)) + 5
		bottom = -2
	elif data_type == 't':
		ax1.set_ylabel('Time (ms)', fontsize = pl_fontsize)
		top = ceil(max(maxs)) + 0.5
		bottom = -0.2
	else:
		ax1.set_ylabel('IPC', fontsize = pl_fontsize)
		top = ceil(max(maxs)) + 0.5
		bottom = -0.2

	if not auto:
		top = y_up
		bottom = y_down

	ax1.set_xlim(0.5, len(utilization) + 0.5)
	ax1.set_ylim(bottom, top)

	xtickNames = pl.setp(ax1, xticklabels = utilization)
	pl.setp(xtickNames, rotation = 45, fontsize = pl_fontsize)

	numBoxes = len(utilization)
	boxColors = ['darkkhaki', 'darkkhaki']
	medians = list(range(numBoxes))
	for i in range(numBoxes):
	    box = bp['boxes'][i]
	    boxX = []
	    boxY = []
	    for j in range(5):
	        boxX.append(box.get_xdata()[j])
	        boxY.append(box.get_ydata()[j])
	    boxCoords = list(zip(boxX, boxY))

	    # Alternate between Dark Khaki and Royal Blue
	    k = i % 2
	    boxPolygon = pl.Polygon(boxCoords, facecolor=boxColors[k])
	    ax1.add_patch(boxPolygon)

	    # Now draw the median lines back over what we just filled in
	    med = bp['medians'][i]
	    medianX = []
	    medianY = []
	    for j in range(2):
	        medianX.append(med.get_xdata()[j])
	        medianY.append(med.get_ydata()[j])
	        pl.plot(medianX, medianY, 'k')
	        medians[i] = medianY[0]

	    # Finally, overplot the sample averages, with horizontal alignment
	    # in the center of each box
	    pl.plot([np.average(med.get_xdata())], [np.average(parsed_data[i])],
	             color='w', marker='*', markeredgecolor='k')  

	pos = np.arange(7) + 1
	boxColors = ['red', 'green']  
	upperLabels = [str(np.round(s, 2)) for s in maxs]
	bottomLabels = [str(np.round(s, 2)) for s in mins]
	weights = ['bold', 'semibold']

	for tick, label in zip(range(7), ax1.get_xticklabels()):
	    k = tick % 2
	    ax1.text(pos[tick], top - ((top - bottom)*0.05), upperLabels[tick],
	             horizontalalignment='center', size='small', weight=weights[k], color=boxColors[0])
	    ax1.text(pos[tick], bottom + ((top - bottom)*0.05), bottomLabels[tick],
	             horizontalalignment='center', size='small', weight=weights[k], color=boxColors[1])
       
	line_data = []
	for item in range(1, numBoxes + 1, 1):
		line_data.append(np.mean(parsed_data[item - 1]))
		pl.text(item - 0.2, line_data[item - 1], '%.2f' % line_data[item - 1], fontsize = pl_fontsize)

	pl.plot(range(1, numBoxes + 1, 1), line_data, 'r')

	# Save the figure
	fig.savefig(figname)

	# All done here
	return
	
# collate_performance_data
# Function to collate parsed data from the performance files
def collate_performance_data():

	mr_array   	= []
	time_array 	= []
	inspc_array 	= []

	for item in xrange(100):
		mr_array.append((float(plot_performance_data[str(item)][1])/plot_performance_data[str(item)][0]) * 100)
		time_array.append((plot_performance_data[str(item)][2]))
		inspc_array.append((plot_performance_data[str(item)][3]))
	
	# Push the miss-rate data into global hash
	plot_performance_data["miss_rate"].append(mr_array)
	plot_performance_data["time"].append(time_array)
	plot_performance_data["ipc"].append(inspc_array)

	return
	
def do_performance_boxplots(partition_type, algorithm):
	""" Helper function for making a single plot """

	# Create dimensions for the plot
	fig = pl.figure(1, figsize = (10, 8))

	# Reset the data hash for new experiment
	plot_performance_data["miss_rate"] = []
	plot_performance_data["time"] = []
	plot_performance_data["ipc"] = []

	# Specify the utilization range for this plot
	utilization = [37, 50, 63, 75, 87]
	utilization = [str(x) for x in utilization]

	fig_prefix = 'XE_%s_%s' % (partition_type.upper(), algorithm.upper())
	mrt_figname = fig_prefix + '_MRT.png'
	tme_figname = fig_prefix + '_TME.png'
	ipc_figname = fig_prefix + '_IPC.png'

	# Construct the parent directory path
	parent_dir = '../data/%s/%s/' % (partition_type, algorithm)

	# Parse the data in each file
	for util in utilization:
		for item in xrange(100):
			file_name = parent_dir + util + '/' + str(item) + '.perf'
			mem_page(file_name)
		
		# Collate the data collected so far
		collate_performance_data()

	# Perform the actual plotting
	title = algorithm.upper()
	
	choice = False

	# Create boxplot for time data
	performance_boxplots(tme_figname, title, 't', utilization, plot_performance_data["time"], -5, 30, auto = choice)

	# Create boxplot for miss-rate data
	performance_boxplots(mrt_figname, title, 'm', utilization, plot_performance_data["miss_rate"], -5, 50, auto = choice)

	# Create boxplot for ipc data
	performance_boxplots(ipc_figname, title, 'i', utilization, plot_performance_data["ipc"], 0, 2, auto = choice)

	return
	
def main():

	# Specify the partition type
	partition_type = "ways"

	# Specify the algorithms to plot for
	algorithm_list = ["buddy", "random", "rr", "bb"]

	# Plot the default data sets
	for algorithm in algorithm_list:
		do_performance_boxplots(partition_type, algorithm)

	return

# Desginate main as the entry point
if __name__ == "__main__":
	# Call the main function
	main()
