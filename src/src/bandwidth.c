/**
 *
 * Copyright (C) 2012  Heechul Yun <heechul@illinois.edu>
 *               2012  Zheng <zpwu@uwaterloo.ca>
 *
 * This file is distributed under the University of Illinois Open Source
 * License. See LICENSE.TXT for details.

 */

/* clang -S -mllvm --x86-asm-syntax=intel ./bandwidth.c */

/**************************************************************************
 * Conditional Compilation Options
 **************************************************************************/

/**************************************************************************
 * Included Files
 **************************************************************************/
#define _GNU_SOURCE             /* See feature_test_macros(7) */
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <inttypes.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/time.h>
#include <sys/resource.h>

#include <sys/ioctl.h>
#include <linux/perf_event.h>
#include <asm/unistd.h>

/* Import process address map parsing function into this file */
extern void pagetype(char* pid_s);
unsigned long long my_pid;
char pid_s[256];

/**************************************************************************
 * Public Definitions
 **************************************************************************/
#define CACHE_LINE_SIZE 64	   /* cache Line size is 64 byte */
#ifdef __arm__
#  define DEFAULT_ALLOC_SIZE_KB 4096
#else
#  define DEFAULT_ALLOC_SIZE_KB 16384
#endif

// Turn profiling on or off
#define PROFILE_CTL	0
#define PRINT_ON	0
#define MEM_CTL		1

/**************************************************************************
 * Public Types
 **************************************************************************/
enum access_type { READ, WRITE};

/**************************************************************************
 * Global Variables
 **************************************************************************/
int g_mem_size = DEFAULT_ALLOC_SIZE_KB * 1024;	   /* memory size */
int *g_mem_ptr = 0;		   /* pointer to allocated memory region */

volatile uint64_t g_nread = 0;	           /* number of bytes read */
volatile unsigned int g_start;		   /* starting time */
int cpuid = 0;

#if (PROFILE_CTL == 1)
int fd_a;
int fd_m;
#endif

void	*heap_ptr = NULL;

/**************************************************************************
 * Public Functions
 **************************************************************************/
unsigned int get_usecs()
{
	struct timeval         time;
	gettimeofday(&time, NULL);
	return (time.tv_sec * 1000000 +	time.tv_usec);
}

#if (PROFILE_CTL == 1)
static long perf_event_open (struct perf_event_attr *hw_event, pid_t pid,
		int cpu, int group_fd, unsigned long flags)
{
	int ret;
	pid = getpid();

	ret = syscall (__NR_perf_event_open, hw_event, pid, cpu, group_fd, flags);

	return ret;
}
#endif

void quit(int param)
{
	int		stack = 0;

#if (PRINT_ON == 1)
	float		dur_in_sec;
	float		bw, dur;
#endif

#if (PROFILE_CTL == 1)
	long long	count_a;
	long long	count_m;
	float		bw_llc;

	/* Stop the hardware counters */
	ioctl (fd_a, PERF_EVENT_IOC_DISABLE);
	ioctl (fd_m, PERF_EVENT_IOC_DISABLE);

	/* Read the final event values */
	bw	= read (fd_a, &count_a, sizeof(long long));
	bw_llc	= read (fd_m, &count_m, sizeof(long long));

	/* Close the counter file */
	close (fd_a);
	close (fd_m);
#endif

#if (PRINT_ON == 1)
	dur = get_usecs() - g_start;
	dur_in_sec = (float)dur / 1000000;
	printf("g_nread(bytes read) = %lld\n", (long long)g_nread);
	printf("elapsed = %.2f sec ( %.0f usec )\n", dur_in_sec, dur);
	bw = (float)g_nread / dur_in_sec / 1024 / 1024;
	printf("CPU%d: B/W = %.2f MB/s | ",cpuid, bw);
	printf("CPU%d: average = %.2f ns\n", cpuid, (dur*1000)/(g_nread/CACHE_LINE_SIZE));
#endif

#if (PROFILE_CTL == 1)
	bw = (float)count_m * 64 / dur_in_sec / 1024 / 1024;
	bw_llc = (float)count_a * 64 / dur_in_sec / 1024 / 1024;
	printf ("total llcache-events (accesses) : %lld\n", count_a);
	printf ("total llcache-events (misses)   : %lld\n", count_m);
	printf ("llcache-miss-rate               : %.2f%%\n", ((float)count_m / count_a) * 100);
	printf ("LLC B/W  = %.2f MB/s\n", bw_llc);
	printf ("DRAM B/W = %.2f MB/s\n", bw);
#endif

#if (MEM_CTL == 1)
	printf("\nStack \t\t\t : %p\n", &stack);
	printf("Heap \t\t\t : %p\n", g_mem_ptr);
	printf("BSS \t\t\t : %p\n", &g_mem_ptr);
	printf("Text \t\t\t : %p\n", quit);
#endif

	pagetype(pid_s);

	exit(0);
}

int64_t bench_read()
{
	int i;	
	int64_t sum = 0;
	for ( i = 0; i < g_mem_size/4; i+=(CACHE_LINE_SIZE/4) ) {
		sum += g_mem_ptr[i];
	}
	g_nread += g_mem_size;
	return sum;
}

int bench_write()
{
	register int i;	
	for ( i = 0; i < g_mem_size/4; i+=(CACHE_LINE_SIZE/4) ) {
		g_mem_ptr[i] = i;
	}
	g_nread += g_mem_size;
	return 1;
}

void usage(int argc, char *argv[])
{
	printf("Usage: $ %s [<option>]*\n\n", argv[0]);
	printf("-m: memory size in KB. deafult=8192\n");
	printf("-a: access type - read, write. default=read\n");
	printf("-n: addressing pattern - Seq, Row, Bank. default=Seq\n");
	printf("-t: time to run in sec. 0 means indefinite. default=5. \n");
	printf("-c: CPU to run.\n");
	printf("-i: iterations. 0 means intefinite. default=0\n");
	printf("-p: priority\n");
	printf("-l: log label. use together with -f\n");
	printf("-f: log file name\n");
	printf("-h: help\n");
	printf("\nExamples: \n$ bandwidth -m 8192 -a read -t 1 -c 2\n  <- 8MB read for 1 second on CPU 2\n");
	exit(1);
}

int main(int argc, char *argv[])
{
	int64_t sum = 0;
	unsigned finish = 5;
	int prio = 0;        
	int num_processors;
	int acc_type = READ;
	int opt;
	cpu_set_t cmask;
	int iterations = 0;
	int i;

	/* Create argument list to be passed to pagetype program */
	my_pid = getpid();
	// fprintf(stderr, "%d", (int)my_pid);
	sprintf(pid_s, "%llu", my_pid);

#if (PROFILE_CTL == 1)
	struct perf_event_attr pe_a;
	struct perf_event_attr pe_m;

	/* Initialize perf events */
	memset (&pe_a, 0, sizeof(struct perf_event_attr));
	memset (&pe_m, 0, sizeof(struct perf_event_attr));
	
	pe_a.type			= PERF_TYPE_RAW;
	pe_a.size			= sizeof(struct perf_event_attr);
	pe_a.config			= 0x50;
	pe_a.disabled			= 1;
	pe_a.exclude_kernel		= 1;
	pe_a.exclude_hv			= 1;

	pe_m.type			= PERF_TYPE_RAW;
	pe_m.size			= sizeof(struct perf_event_attr);
	pe_m.config			= 0x52;
	pe_m.disabled			= 1;
	pe_m.exclude_kernel		= 1;
	pe_m.exclude_hv			= 1;

	fd_a = perf_event_open(&pe_a, 0, -1, -1, 0);
	fd_m = perf_event_open(&pe_m, 0, -1, -1, 0);

	if (fd_a == -1 || fd_m == -1) {
		printf("Error opening leader a : %llx | m : %llx\n", pe_a.config, pe_m.config);
		exit(EXIT_FAILURE);
	}
#endif

	/* get command line options */
	while ((opt = getopt(argc, argv, "m:a:n:t:c:i:p:f:l:xh")) != -1) {
		switch (opt) {
		case 'm': /* set memory size */
			g_mem_size = 1024 * strtol(optarg, NULL, 0);
			break;
		case 'a': /* set access type */
			if (!strcmp(optarg, "read"))
				acc_type = READ;
			else if (!strcmp(optarg, "write"))
				acc_type = WRITE;
			else
				exit(1);
			break;
			
		case 't': /* set time in secs to run */
			finish = strtol(optarg, NULL, 0);
			break;
			
		case 'c': /* set CPU affinity */
			cpuid = strtol(optarg, NULL, 0);
			num_processors = sysconf(_SC_NPROCESSORS_CONF);
			CPU_ZERO(&cmask);
			CPU_SET(cpuid % num_processors, &cmask);
			if (sched_setaffinity(0, num_processors, &cmask) < 0)
				perror("error");
			else
				// fprintf(stderr, "assigned to cpu %d\n", cpuid);
			break;
			
		case 'p': /* set priority */
			prio = strtol(optarg, NULL, 0);
			if (setpriority(PRIO_PROCESS, 0, prio) < 0)
				perror("error");
			else
				printf("assigned priority %d\n", prio);
			break;
		case 'i': /* iterations */
			iterations = strtol(optarg, NULL, 0);
			break;
		case 'h': 
			usage(argc, argv);
			break;
		}
	}

	/* allocate contiguous region of memory */
	g_mem_ptr = (int *)malloc(g_mem_size);
	// printf("\n\n***** g_mem_ptr = %p\n\n", g_mem_ptr);

	// g_mem_ptr = (int *)mmap(0, g_mem_size, PROT_READ | PROT_WRITE, 
	//      		MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB, -1, 0);

	// /* Check if the allocation was successful */
	// if ((void *)g_mem_ptr == MAP_FAILED) {
	// 	perror("alloc failed");
	// 	exit(1);
	// }

	memset((char *)g_mem_ptr, 1, g_mem_size);
	heap_ptr = g_mem_ptr;

	for (i = 0; i < g_mem_size / sizeof(int); i++)
		g_mem_ptr[i] = i;

	/* print experiment info before starting */
#if (PRINT_ON == 1)
	printf("memsize=%d KB, type=%s, cpuid=%d\n",
	       g_mem_size/1024,
	       ((acc_type==READ) ?"read": "write"),
		cpuid);
	printf("stop at %d\n", finish);
#endif

	/* set signals to terminate once time has been reached */
	signal(SIGINT, &quit);
	if (finish > 0) {
		signal(SIGALRM, &quit);
		alarm(finish);
	}

#if (PROFILE_CTL == 1)
	/* actual memory access. start the performance counters */
	ioctl (fd_a, PERF_EVENT_IOC_RESET, 0);
	ioctl (fd_a, PERF_EVENT_IOC_ENABLE, 0);
	ioctl (fd_m, PERF_EVENT_IOC_RESET, 0);
	ioctl (fd_m, PERF_EVENT_IOC_ENABLE, 0);
#endif

	g_start = get_usecs();
	for (i=0;; i++) 
	{
		switch (acc_type) 
		{
			case READ:
				sum += bench_read();
				break;

			case WRITE:
				sum += bench_write();
				break;
		}

		if (iterations > 0 && i >= iterations)
			break;
	}

	printf("total sum = %ld\n", (long)sum);
	quit(0);
	return 0;
}

