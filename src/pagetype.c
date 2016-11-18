/*
 * page-type : A replication of page-type program containing bare-bone
 *	       components required for parsing page-maps
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <limits.h>
#include <assert.h>
#include <sys/types.h>
#include <sys/errno.h>
#include <sys/fcntl.h>

/* Debug Control Macro */
#define DEBUG			4

/* Options for linking this program */
#define INTEGRATED		1

/* Macro Definitions */
#define MAX_VMAS		32
#define MAX_ADDR_RANGES		2
#define PROC_KPAGEFLAGS		"/proc/kpageflags"
#define PAGEMAP_BATCH		(64 << 10)
#define KPAGEFLAGS_BATCH	(64 << 10)

#define PM_PSHIFT_BITS		6
#define PM_STATUS_BITS		3
#define PM_STATUS_OFFSET	(64 - PM_STATUS_BITS)
#define PM_PSHIFT_OFFSET	(PM_STATUS_OFFSET - PM_PSHIFT_BITS)
#define PM_PFRAME_MASK		((1LL << PM_PSHIFT_OFFSET) - 1)
#define PM_PFRAME(x)		((x) & PM_PFRAME_MASK)

#define PM_STATUS_MASK		(((1LL << PM_STATUS_BITS) - 1) << PM_STATUS_OFFSET)
#define PM_STATUS(nr)		(((nr) << PM_STATUS_OFFSET) & PM_STATUS_MASK)
#define PM_PRESENT		PM_STATUS(4LL)

#define HASH_SHIFT		5
#define HASH_SIZE		(1 << HASH_SHIFT)

#define ARRAY_SIZE(x)		(sizeof(x) / sizeof((x)[0]))

#define for_each_set_bit(bit, addr, size)			\
	for ((bit) = find_first_bit((addr), (size));		\
	     (bit) < (size);					\
	     (bit) = find_next_bit((addr), (size), (bit) + 1))
#define find_first_bit(addr, size)				\
	find_next_bit((addr), (size), 0)

#ifdef __LP64
#define BITS_PER_LONG 		64
#else
#define BITS_PER_LONG 		32
#endif

#define BITOP_WORD(nr)		((nr) / BITS_PER_LONG)
#define PAGE_SHIFT		12

#define PALLOC_MASK		0x03000

/* Function Prototypes */
static void		show_summary(void);
static void 		parse_pid(char *pid);
static void 		walk_addr_ranges(void);
static void 		walk_vma(unsigned long index, unsigned long count);
static void 		walk_task(unsigned long index, unsigned long count);
static void 		add_addr_range(unsigned long offset, unsigned long size);
static void		add_page(unsigned long voffset, unsigned long offset, uint64_t flags);
static void		walk_pfn(unsigned long voffset, unsigned long index, unsigned long count);
static int		pfn_to_colors(uint64_t pfn);
static unsigned long 	pagemap_pfn(uint64_t val);
static unsigned long	pages2mb(unsigned long pages);
static unsigned long	find_next_bit(unsigned long *addr, unsigned long size, unsigned long offset);
static unsigned long	do_u64_read(int fd, char *name, uint64_t *buf, unsigned long index, unsigned long count);

#if (INTEGRATED == 1)

/* Function to be externed */
void 			pagetype(char *pid_s);

#endif

/* Global Data */
static pid_t		opt_pid;
static int		page_size;
static int		pagemap_fd;

static int		nr_vmas = 0;
static unsigned long	pg_start[MAX_VMAS];
static unsigned long	pg_end[MAX_VMAS];

static int		kpageflags_fd;
static int		nr_addr_ranges = 0;

static unsigned long	opt_offset[MAX_ADDR_RANGES];
static unsigned long	opt_size[MAX_ADDR_RANGES];

static unsigned long	total_pages = 0;
static unsigned long	nr_color_pages[HASH_SIZE];

static unsigned long	bits[32] =	{0x1, 		0x2, 		0x4, 		0x8, 
					0x10, 		0x20, 		0x40, 		0x80, 
					0x100, 		0x200, 		0x400, 		0x800, 
					0x1000, 	0x2000, 	0x4000, 	0x8000,
					0x10000, 	0x20000, 	0x40000, 	0x80000, 
					0x100000, 	0x200000, 	0x400000, 	0x800000,
					0x1000000, 	0x2000000, 	0x4000000, 	0x8000000,
					0x10000000, 	0x20000000, 	0x40000000, 	0x80000000};

#if (INTEGRATED == 1)

/*
 * pagetype
 * Function that can be externed by other programs for static linking
 * @pid_s : String of characters specifying the process id
 */
void pagetype(char *pid_s)
{

#else

/*
 * main
 * This is the primary entry point into this application
 * @argc : Number of arguments passed
 * @argv : Variable argument array. Should contain pid of the target process
 */
void main(int argc, char *argv[])
{
	char	*pid_s = argv[1];

#endif

	page_size = getpagesize();

	/* Parse the PID for page addresses */
	parse_pid(pid_s);

	/* Walk the address range */
	walk_addr_ranges();

	/* Show the page summary */
	show_summary();

	/* All done */
	return;
}

/*
 * parse_pid
 * Primary funciton for parsing the page-data against a PID
 * @pid : String of character specifying the PID
 */
static void parse_pid(char *pid_s)
{
	FILE	*file;
	char	buf[5000];

	/* Convert the page string to long long integer */
	opt_pid = strtoll(pid_s, NULL, 0);

	/* Create the address for pagemap file under /proc/ file-system */
	sprintf(buf, "/proc/%d/pagemap", opt_pid);

	/* Open the page-map file */
	pagemap_fd = open(buf, O_RDONLY);

	/* Verify that the file was correctly opened */
	if (pagemap_fd < 1) {
		perror(buf);
		exit(EXIT_FAILURE);
	}

	/* Open the memareas file */
	sprintf(buf, "/proc/%d/maps", opt_pid);
	file = fopen(buf, "r");

	/* Throw an error if the file can't be opened */
	if (!file) {
		perror(buf);
		exit(EXIT_FAILURE);
	}

	/* Parse the data in the memory map file */
	while (fgets(buf, sizeof(buf), file) != NULL) {
		unsigned long vm_start, vm_end;
		unsigned long long pgoff;
		int major, minor;
		char r, w, x, s;
		unsigned long ino;
		int n;

		n = sscanf(buf, "%lx-%lx %c%c%c%c %llx %x:%x %lu",
			   &vm_start, &vm_end,
			   &r, &w, &x, &s,
			   &pgoff,
			   &major, &minor,
			   &ino);

		/* Make sure that the correct number of arguments were read */
		if (n < 10) {
			printf("Unexpected line : %s\n", buf);
			continue;
		}

		/* Populate the memory areas */
		pg_start[nr_vmas] = vm_start / page_size;
		pg_end[nr_vmas]	  = vm_end / page_size;

#if (DEBUG == 1)
		printf("[VMA # %d] - Start : 0x%.12lx | End : 0x%.12lx\n", nr_vmas, pg_start[nr_vmas], pg_end[nr_vmas]);
#endif

		if (++nr_vmas >= MAX_VMAS) {
			printf("Too many VMAS\n");
			break;
		}
	}

	/* Close the memory area file */
	fclose(file);

	/* We are done here */
	return;	
}

/*
 * walk_addr_ranges
 * This function parses the address range of a process
 */
static void walk_addr_ranges(void)
{
	int i;

	/* Open the kernel page flags file */
	kpageflags_fd = open(PROC_KPAGEFLAGS, O_RDONLY);

	if (!nr_addr_ranges)
		/* Populate the address range if none has been added so far */
		add_addr_range(0, ULONG_MAX);

	/* Go through all address ranges */
	for (i = 0; i < nr_addr_ranges; i++)

#if (DEBUG == 2)
		printf("Parsing address range (#%d) | Offset : 0x%.8lx - Size : %lu\n", i, opt_offset[i], opt_size[i]);
#endif

		walk_task(opt_offset[i], opt_size[i]);

	/* Close the kernel page flags file */
	close(kpageflags_fd);

	/* We are done here */
	return;
}

/*
 * add_addr_range
 * This function adds an address range to global data
 * @offset : Offset of the address range
 * @size   : Size of the address range
 */
static void add_addr_range(unsigned long offset, unsigned long size)
{
	/* Make sure that there is still space left for adding memory range */
	if (nr_addr_ranges >= MAX_ADDR_RANGES) {
		printf("Too many address ranges!\n");
		exit(EXIT_FAILURE);
	}

	/* Store the range data in global variables */
	opt_offset[nr_addr_ranges] = offset;

	/* Make sure that the size is within accceptable bounds */
	opt_size[nr_addr_ranges]   = (size < (unsigned long)(ULONG_MAX - offset)) ? size : (unsigned long)(ULONG_MAX - offset);

	nr_addr_ranges++;

	/* We are done here */
	return;
}	

/*
 * walk_task
 * Function for parsing the memory foot-print of a single task
 * @index : Index of the task
 * @count : Count for the task
 */
static void walk_task(unsigned long index, unsigned long count)
{
	const unsigned long end = index + count;
	unsigned long start;
	int i = 0;

	while (index < end) {
		/* Make sure that the VMA region to be parsed for this
		   task specifies a valid memory range */
		while (pg_end[i] <= index)
			if (++i >= nr_vmas)
				return;

		if (pg_start[i] >= end)
			return;

		/* Sanity test have been passed. Proceed with parsing */
		start = (pg_start[i] > index) ? pg_start[i] : index;
		index = (pg_end[i] < end) ? pg_end[i] : end;

		/* Walk this VMA region */

#if (DEBUG == 1)
		printf("Walking VMA # %d | Start : 0x%.12lx - End : 0x%.12lx\n", i, start, index);
#endif

		walk_vma(start, index - start);

		/* Perform a basic sanity assertion */
		assert(start < index);
	}

	return;
}

/*
 * walk_vma
 * A  function for walking the virtual memory areas associated with a task
 * @index : Start address for the VMA region
 * @count : Size of the region to be parsed
 */
static void walk_vma(unsigned long index, unsigned long count)
{
	uint64_t	buf[PAGEMAP_BATCH];
	unsigned long	batch;
	unsigned long	pages;
	unsigned long	pfn;
	unsigned long	i;

	while (count) {
		/* Read pages in batch from the system */
		batch = (count < (unsigned long)PAGEMAP_BATCH) ? count : (unsigned long)PAGEMAP_BATCH;
		pages = do_u64_read(pagemap_fd, "/proc/pid/pagemap", buf, index, batch);

		if (pages == 0)
			/* No page frames could be read */
			break;

		for (i = 0; i < pages; i++) {
			/* Read the actual page frame numbers */
			pfn = pagemap_pfn(buf[i]);

			/* Make sure that pfn is valid */
			if (pfn)
				walk_pfn(index + i, pfn, 1);
		}

		/* Update index and count */
		index += pages;
		count -= pages;
	}

	return;
}

/*
 * pagemap_pfn
 * Verifies that the present bit is set in page and returns the page-frame number
 * @val : 64-bit page address
 */
static unsigned long pagemap_pfn(uint64_t val)
{
	unsigned long pfn;

	if (val & PM_PRESENT)
		/* Page is valid. Truncate the address from 64 bits to 55 bits */
		pfn = PM_PFRAME(val);
	else
		/* Page is not valid for our purposes */
		pfn = 0;

	return pfn;
}

/*
 * walk_pfn
 * Function to walk a page-frame range
 * @voffset : Virtual offset of the page in the VMA
 * @index   : Physical frame number of the page
 * @count   : Number of batched pages
 */
static void walk_pfn(unsigned long voffset, unsigned long index, unsigned long count)
{
	uint64_t	buf[KPAGEFLAGS_BATCH];
	unsigned long	batch;
	unsigned long	pages;
	unsigned long	i;

	/* Parse pages in batches */
	while (count) {
		batch = (count < (unsigned long)KPAGEFLAGS_BATCH) ? count : (unsigned long)KPAGEFLAGS_BATCH;

		/* Read the flags set against this page */
		pages = do_u64_read(kpageflags_fd, PROC_KPAGEFLAGS, buf, index, batch);

		if (pages == 0)
			break;

		for (i = 0; i < pages; i++)
			/* Add page-data to internal array */
			add_page(voffset + i, index + i, buf[i]);

		index += pages;
		count -= pages;
	}

	return;
}

/*
 * add_page
 * Funciton to add page to page-list array
 * @voffset : Virtual offset of the page in the VMA
 * @offset  : Physical page frame offset
 * @flags   : Kernel flags set against this page
 */
static void add_page(unsigned long voffset, unsigned long offset, uint64_t flags)
{
	/* Print page to output stream */
	// fprintf(stderr, "0x%.8lx : 0x%.12lx\n", voffset, offset);

	total_pages++;

	/* Keep track of page colors */
	nr_color_pages[pfn_to_colors(offset)]++;

	return;
}

/*
 * pfn_to_color
 * Parsed the page frame number to determine the page color
 * @pfn : Page frame number to parse
 */
static int pfn_to_colors(uint64_t pfn)
{
	unsigned long palloc_bitmask 	= (unsigned long)PALLOC_MASK;
	int color 			= 0;
	int idx   			= 0;
	int c;

	/* Parse the frame number one bit at a time */
	for_each_set_bit(c, &palloc_bitmask, sizeof(unsigned long) * 8) {

#if (DEBUG == 3)
		printf("Parsing Color # %.2d\n", c - PAGE_SHIFT);
#endif

		if ((pfn >> (c - PAGE_SHIFT)) & 0x1)
			color |= (1 << idx);

		idx++;
	}

	return color;
}

/*
 * do_u64_read
 * A simple helper function for doing a 64-bit read
 * @fd	  : File descriptor to read from
 * @name  : Character string to print in case of error
 * @buf   : Buffer to return data in
 * @index : File index at the end of read
 * @count : Number of bytes to read
 */
static unsigned long do_u64_read(int fd, char *name, uint64_t *buf, unsigned long index, unsigned long count)
{
	long bytes;

	/* Perform some preliminary error checks */
	if (index > ULONG_MAX / 8) {
		printf("Index overflow : %lu\n", index);
		exit(EXIT_FAILURE);
	}

	/* Advnace the seek in the passed in file */
	if (lseek(fd, index * 8, SEEK_SET) < 0) {
		perror(name);
		exit(EXIT_FAILURE);
	}

	bytes = read(fd, buf, count * 8);

	/* Make sure that the read was successful */
	if (bytes < 0) {
		perror(name);
		exit(EXIT_FAILURE);
	}

	if (bytes % 8) {
		printf("Partial read : %lu bytes\n", bytes);
		exit(EXIT_FAILURE);
	}

	return bytes / 8;
}

/*
 * show_summary
 * Shows the color distribution of pages for an application
 */
static void show_summary(void)
{
	int i;

	/* Show color distribution */
	printf("\n===========================================================\n");
	printf("\t Color Number \t : \t      Pages \t Size (MB)\n");
	printf("===========================================================\n");
	printf("\t    ### \t : \t %10lu %8lu\n", total_pages, pages2mb(total_pages));

	for (i = 0; i < ARRAY_SIZE(nr_color_pages); i++) {
		if (nr_color_pages[i])
			printf("\t Color[%.2d] \t : \t %10lu %8lu\n", i, nr_color_pages[i], pages2mb(nr_color_pages[i]));
	}

	/* Output an empty line at the end */
	printf("\n");

	return;
}

/*
 * pages2mb
 * Converts number of pages to byte size based on system page size
 * @pages : pages to convert to MB
 */
static unsigned long pages2mb(unsigned long pages)
{
	return (pages * page_size) >> 20;
}

/*
 * find_next_bit
 * Find the next bit in a bit-mask
 * @addr   : Address to parse
 * @size   : Size of the container
 * @offset : Offset of memory address
 */
static unsigned long find_next_bit(unsigned long *addr, unsigned long size, unsigned long offset)
{
	unsigned long value = *addr;
	int item;

	/* Zero out the value beyond the offset field */
	value &= ~((1UL << offset) - 1);

	/* Find the the least significant set bit */
	if (value) {
		value &= (~value + 1);

		for (item = 0; item < 32; item++) {
			if (bits[item] == value)
				return item;
		}
	}

	return size;
}
