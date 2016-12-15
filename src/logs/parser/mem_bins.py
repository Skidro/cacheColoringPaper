import re
import numpy as np
import pylab as pl
import scipy.stats as stats

from generic_page import *
from helper_functions import *

# Set to 1 if debugging required
bins_histogram_debug = 0

# Global Data
plot_bins_data = {}
plot_performance_data = {}
ALLD_COLORS = 0x0FFFFFFF

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
		accesses = misses = time = 0

		# Open and parse the file
		with open(self.name, 'r') as fdi:
			for line in fdi:
				# Check the platform type to select appropriate regex
				if self.platform == 'XE':
					# Get the required lines
					refsLine = re.match('^\D*([\d,]+) cache-references.*$', line)
					missLine = re.match('^\D*([\d,]+) cache-misses.*$', line)
					timeLine = re.match('^\D*([\d.]+) seconds time.*$', line)
				elif self.platform == 'TG':
					# Get the required lines
					refsLine = re.match('^\D*([\d,]+) r50.*$', line)
					missLine = re.match('^\D*([\d,]+) r52.*$', line)
					timeLine = re.match('^\D*([\d.]+) seconds time.*$', line)

				if refsLine:
					accesses = int(re.sub('\D', '', refsLine.group(1)))

				if missLine:
					misses   = int(re.sub('\D', '', missLine.group(1)))

				if timeLine:
					try:
						time = float(timeLine.group(1))
					except:
						raise ValueError, 'Could not convert string (%s) to float' % (time.group(1))

		if accesses == 0 or misses == 0 or time == 0:
			print 'Unexpected File : %s' % (self.name)
			sys.exit(2)

		# Extract the file number
		file_number = (re.match("^.*/(\d+)", self.name)).group(1)

		# Insert the data in the hash
		plot_performance_data[file_number] = (accesses, misses, time)

		return

class mem_color(File, Helper):
	""" A subclass of file-type objects to process miss-rate in tegra
	    platform """

	def __init__(self, filename):
		# Invoke the super-class constructor method
		super(mem_color, self).__init__(filename)

		# Parse the file
		self.parse()

		return

	def parse(self):
		""" This is the primary function for extracting color distribution information
		    from pagetype data """

		# Get a bit-list of allowed color bins
		bit_list = self.bit_numbers(ALLD_COLORS)

		total_pages = alld_clr_pages = rest_clr_pages = 0
		pages = []
		alld_pages = []

		# Open and parse the file
		with open(self.name, 'r') as fdi:
			for line in fdi:
				# Get the required lines
				total_pages_line = re.match("^.*###\D*(\d+)", line)
				color_line = re.match("^.*Color.*:\D*(\d+)", line)

				if total_pages_line:
					total_pages = int(total_pages_line.group(1))

				if color_line:
					pages.append(int(color_line.group(1)))


		if total_pages == 0 or pages == []:
			print 'Unexpected File : %s' % (self.name)

		# Extract the file number
		file_number = (re.match("^.*/(\d+)$", self.name)).group(1)

		color = 0
		for page_items in pages:
			if color in bit_list:
				alld_clr_pages += pages[color]
				alld_pages.append(pages[color])
			else:
				rest_clr_pages += pages[color]

			color += 1

		# Sort the pages in allowed colors
		sorted_clr_pages = sorted(alld_pages)

		# Calculate the standard deviation of allowed color pages
		std_clr_pages = np.std(sorted_clr_pages)
		

		# Insert the data in the hash
		plot_bins_data[file_number] = (total_pages, alld_clr_pages, rest_clr_pages, std_clr_pages, alld_pages)

		return

# bins_histogram_plot
# Function to plot histogram using the data parsed from the target file
def bins_histogram_plot(target_hash, title):
	""" Function for plotting the collected data about page distribution """

	# Font size for plot titles
	pl_fontsize = 15
	pl_rows = 1
	pl_cols = 1
	top = 35
	right = 28

	pl.bar(range(28), plot_bins_data[target_hash["file"]][-1], 1, color = 'g')

	pl.xlim(0, right)
	pl.ylim(0, top)

	pl.xlabel('Cache Colors', fontsize = pl_fontsize)
	pl.ylabel('Page Count', fontsize = pl_fontsize)

	pl.text(0.5, top - 2, 'Miss-Rate = ' + '%.2f' % target_hash["miss_rate"] + '%', fontsize = pl_fontsize)
	pl.text(0.5, top - 4, 'Time = ' + '%.2f' % target_hash["time"] + ' sec', fontsize = pl_fontsize)
	pl.text(0.5, top - 6, r'$\sigma$ = ' + '%.2f' % plot_bins_data[target_hash["file"]][-2], fontsize = pl_fontsize)

	# Give the prescribed title to the plot
	pl.title(title)

	return

def do_cache_bins_histogram(parent_dir, target_hash, print_title):
	""" Helper function for plotting the histogram of a single experiment run """

	# Create a figure to save all plots
	fig = pl.figure(figsize = (15, 5))
	figname = ('_'.join(parent_dir.split('/')[2:]))[:-1] + '_' + target_hash["type"] + '.png'

	# Extract the platform name from the given path
	platform_name = str(re.match(r'^.*/data/([A-Z]+)/.*$', parent_dir).group(1))

	# Parse the data in the target file
	target_file = parent_dir + target_hash["file"]

	# Create the target performance file name corresponding to this color file
	target_perf_file = target_file.replace('CL', 'PF')
	mem_color(target_file)
	mem_page(target_perf_file, platform = platform_name)

	# Update the data in plot_bins_data hash as per the performance data
	target_hash["miss_rate"] = ((float(plot_performance_data[target_hash["file"]][1])/plot_performance_data[target_hash["file"]][0]) * 100)
	target_hash["time"] = plot_performance_data[target_hash["file"]][2]

	# Perform the actual plotting
	util  = str(re.match(r'^.*/(\d+)/$', parent_dir).group(1))
	corun = str(re.match(r'^.*/(\d+)/.*/$', parent_dir).group(1))

	if print_title:
		title = 'Corun : %s | Utilization : %s%%' % (corun, util)
	else:
		title = ''

	bins_histogram_plot(target_hash, title)

	# Save the figure
	fig.savefig('../figs/' + figname)

	return

def main():
	""" This is the primary entry point into the script """

	min_file = '262'
	max_file = '536'

	# The following data is only here for sanity checking
	min_rate = 3.99
	min_time = 1.17
	max_rate = 17.44
	max_time = 1.8

	# Designate a pre-set directory as parent
	parent_dir = '../data/TG/BW/UN/PL/CL/00/100/'

	data_hash = {}
	data_hash["file"] = max_file
	data_hash["type"] = "MX"

	# Make the histogram plot
	do_cache_bins_histogram(parent_dir, data_hash, False)

	return

# Desginate main as the entry point
if __name__ == "__main__":
	# Call the main function
	main()
