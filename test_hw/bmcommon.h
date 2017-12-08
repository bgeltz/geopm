#ifndef	BMCOMMON_H
#define	BMCOMMON_H

#if 0
#define TRACE_PRINT
#else
#define TRACE_PRINT fprintf
#endif

#ifndef __SSC_MARK
#define __SSC_MARK(mark) __asm__ __volatile__ ("movl %0, %%ebx; .byte 0x64, 0x67, 0x90 " ::"i"(mark):"%ebx")
#endif


#ifndef	__WINNT__
#include <sched.h>
#include <sys/mman.h>
#include <sys/sysinfo.h>
#include <pthread.h>
#include <fcntl.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#endif

#ifndef	PAGESIZE
//#define PAGESIZE	(2ULL << 20)
#define PAGESIZE	(4ULL << 10)
#endif

/* Redefinition for MPOL_PREFERRED */
#ifndef	MPOL_PREFERRED
#define	MPOL_PREFERRED	 1
#endif

/* Redefinition for MPOL_INTERLEAVE */
#ifndef	MPOL_INTERLEAVE
#define	MPOL_INTERLEAVE	 3
#endif

/* Redefinition for MADV_HUGEPAGE */
#ifndef	MADV_HUGEPAGE
#define	MADV_HUGEPAGE	14
#endif

/* Redefinition for MADV_NOHUGEPAGE */
#ifndef	MADV_NOHUGEPAGE
#define	MADV_NOHUGEPAGE	15
#endif

#ifndef MAP_HUGETLB
#define	MAP_HUGETLB     0x40000 
#endif

#define MSR_BASE	"/dev/cpu/%d/msr"
#define	MSR_ADDR_GLOBAL	0x38f
#define MSR_ADDR_CTRL	0x38d
#define MSR_ADDR_CTR0	0x309
#define MSR_ADDR_CTR1	0x30a
#define MSR_ADDR_CTR2	0x30b

#define MSR_USER_SEL0	0x186
#define MSR_USER_SEL1	0x187
#define MSR_USER_DAT0	0x0c1
#define MSR_USER_DAT1	0x0c2

#define MSR_USER_ID0_SET0	((0x4f << 8) | 0x2e) // L2_REQUESTS.REFERENCE
#define MSR_USER_ID1_SET0	((0x41 << 8) | 0x2e) // L2_REQUESTS.MISS

#define MSR_USER_ID0_SET1	((0x02 << 8) | 0x3e) // L2_PREFETCHER.ALLOC_L2Q
#define MSR_USER_ID1_SET1	((0x04 << 8) | 0x3e) // L2_PREFETCHER.ALLOC_XQ

#define MSR_USER_ID0_SET2   ((0x02 << 8) | 0x32) // L2_PREFETCHER_THROTTLE
#define MSR_USER_ID1_SET2   ((0x00 << 8) | 0x30) // L2_REQUESTS.REJECT

#define MSR_USER_ID0_SET3	((0x40 << 8) | 0x86) // FETCH_STALL.SNOOP
#define MSR_USER_ID1_SET3	((0x7f << 8) | 0x86) // FETCH_STALL.ANY

#define MSR_USER_ID0_SET4	((0x02 << 8) | 0x80) // ICACHE.MISS
#define MSR_USER_ID1_SET4	((0x04 << 8) | 0x86) // FETCH_STALL.ICACHE_FILL_PENDING

#define MSR_USER_ID0_SET5	((0x01 << 8) | 0x86) // FETCH_STALL.PFB_FULL
#define MSR_USER_ID1_SET5	((0x02 << 8) | 0x86) // FETCH_STALL.ITLB_MISS

#define	MSR_RAPL_POWER_UNIT	0x606
#define MSR_PKG_PERF_STATUS	0x613
#define	MSR_PKG_ENERGY_STATUS	0x611

#ifdef PRINT_TEMP_BUFS
#define MAX_THREAD_NUM 512
#define THREAD_PADD 8
long long mkl_atemp_pointers[MAX_THREAD_NUM*THREAD_PADD];
long long mkl_btemp_pointers[MAX_THREAD_NUM*THREAD_PADD];

static inline void print_mkl_temp_bufs() {
    int i;
    fprintf(stdout, "\n");
    fprintf(stdout, "Atemp buffers \n");
    for (i = 0; i < MAX_THREAD_NUM; ++i) { fprintf(stdout, "%p, ", mkl_atemp_pointers[i*THREAD_PADD]); }
    printf("\n");
    fprintf(stdout, "Btemp buffers \n");
    for (i = 0; i < MAX_THREAD_NUM; ++i) { fprintf(stdout, "%p, ", mkl_btemp_pointers[i*THREAD_PADD]); }
    fprintf(stdout, "\n");
}
#else
static inline void print_mkl_temp_bufs() {}
#endif


/* madvise system call */
static inline int my_madvise(void *addr, size_t len, int advice) {
  
  return syscall(__NR_madvise, addr, len, advice);
}

static inline int my_mbind(void *addr, unsigned long len, int mode,
			   unsigned long *nodemask, unsigned long maxnode,
			   unsigned flags) {

  return syscall(__NR_mbind, addr, len, mode, nodemask, maxnode, flags);

}

/* very basic interleaved mapping routine */

static size_t mcdram_size = (12ULL << 30);

static inline int my_xbind(void *addr, unsigned long len) {

  int curr, ret;
  unsigned long affinity[4] = {0,0,0,0};
  /* it has 2 : 1 mapping */
  int ratio[] = {2, 1};
  size_t actual, rest;


  if (len < mcdram_size || 1) {

    affinity[0] = 1;
  
    ret = my_mbind(addr, len, MPOL_PREFERRED, (unsigned long *)affinity, sizeof(affinity), 0);

  } else {

    rest = len - mcdram_size;

    //	printf("Rest ... %ld   mcdram ... %ld\n", rest, mcdram_size);

    if (rest > mcdram_size) {
      ratio[0] = rest / mcdram_size;
      ratio[1] = 1;
    } else {
      ratio[0] = 1;
      ratio[1] = mcdram_size / rest;
    }

    ratio[0] = 6; ratio[1] = 1;

    //    printf("Mapping Ratio = %d vs. %d\n", ratio[0], ratio[1]);

    curr = 0;
    ret  = 0;
    
    while (len > 0) {
      
      actual = PAGESIZE * ratio[curr];
      
      if (actual > len) actual = len;
      
      affinity[0] = (1UL << curr);
    
      ret |= my_mbind(addr, actual, MPOL_PREFERRED, (unsigned long *)affinity, sizeof(affinity), 0);
      
      addr += actual;
      len  -= actual;
      
      curr = 1 - curr;
    }
  }

  //  printf("Interleaved Mapping .... %d\n", ret);

  return ret;
}


static inline void *myalloc(size_t allocsize, int last) {

  void *buffer;

  allocsize = ((allocsize + PAGESIZE - 1) & ~(PAGESIZE - 1));

  buffer = mmap(NULL, allocsize + PAGESIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB, -1, 0);

  if ((long)buffer == -1) buffer = mmap(NULL, allocsize + PAGESIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  
  if ((long)buffer == -1) {
    TRACE_PRINT(stderr, "MMAP Error!!\n");
    exit(1);
  }

  //  if (last >= 0) my_xbind(buffer, allocsize + PAGESIZE);

  my_madvise(buffer, allocsize + PAGESIZE, MADV_HUGEPAGE);

  bzero(buffer, allocsize);

  mprotect(buffer + allocsize, PAGESIZE, PROT_NONE);

  if (last > 0) buffer += allocsize;

  return buffer;
}

static inline void myfree(void *buffer, size_t allocsize, int last) {

  allocsize = ((allocsize + PAGESIZE - 1) & ~(PAGESIZE - 1));

  if (last) buffer -= allocsize;

  munmap(buffer, allocsize + PAGESIZE);

}

static __inline__ FLOAT amax(FLOAT a, FLOAT b) {

  if (a < 0) a = -a;
  if (b < 0) b = -b;

  return (a >= b)? a : b;
}

static int get_nthreads(void) {

#if defined(USE_OMP)
  return omp_get_max_threads();
#else
  return 1;
#endif

}

#ifndef USE_DOUBLE
#define ERROR1	1.e-4
#define ERROR2	1.e-3
#else
#define ERROR1	1.e-4
#define ERROR2	1.e-5
#endif

#ifdef USE_INT
static __inline__ int diffs(FLOAT_OUT a, FLOAT_OUT b, int n) {
  return (a != b);
}
#else
static __inline__ int diffs(FLOAT_OUT a, FLOAT_OUT b, int n) {

  FLOAT sub;

  sub = a - b;
  if (sub < 0) sub = -sub;

  if (sub < ERROR1 * n) return 0;

  return ((sub / amax(a, b)) > ERROR2 * n);

}
#endif

static __inline__ double dsecond(void) {
  struct timeval tv;

  gettimeofday(&tv, NULL);

  return (double)tv.tv_sec + (double)tv.tv_usec * 1.e-6;
}

typedef struct {
  int core, fd;
  double eunits, punits;
  double cur_time, last_time;
  xlong cur_cycle, last_cycle;
  xlong cur_power, last_power;
  xlong cur_throttle, last_throttle;
  xlong cur_user0, last_user0;
  xlong cur_user1, last_user1;
  double user0_min;
  double user1_min;
  xlong cycle_min;
} perf_t;

static __inline__ void pmon_init(perf_t *perf, int pmon_set, int core) {

  char filename[256];
  xlong ret, msrdata, omsrdata;
  xlong MSR_USER_ID0, MSR_USER_ID1;

  if (pmon_set == 0) {
      MSR_USER_ID0 = MSR_USER_ID0_SET0;
      MSR_USER_ID1 = MSR_USER_ID1_SET0;
  } else if (pmon_set == 1) {
      MSR_USER_ID0 = MSR_USER_ID0_SET1;
      MSR_USER_ID1 = MSR_USER_ID1_SET1;
  } else if (pmon_set == 2) {
      MSR_USER_ID0 = MSR_USER_ID0_SET2;
      MSR_USER_ID1 = MSR_USER_ID1_SET2;
  } else if (pmon_set == 3) {
      MSR_USER_ID0 = MSR_USER_ID0_SET3;
      MSR_USER_ID1 = MSR_USER_ID1_SET3;
  } else if (pmon_set == 4) {
      MSR_USER_ID0 = MSR_USER_ID0_SET4;
      MSR_USER_ID1 = MSR_USER_ID1_SET4;
  } else if (pmon_set == 5) {
      MSR_USER_ID0 = MSR_USER_ID0_SET5;
      MSR_USER_ID1 = MSR_USER_ID1_SET5;
  } else {
      perf -> fd = -1;
      return;
  }

  if (core < 0) perf -> core = sched_getcpu();
  else perf -> core = core;

  sprintf(filename, MSR_BASE, perf -> core);
  
  perf -> fd = open(filename, O_RDWR);
  
 if (perf -> fd >= 0) {

    ret = pread(perf -> fd, &omsrdata, sizeof(omsrdata), MSR_ADDR_GLOBAL);
    
    if (ret == sizeof(omsrdata)) {
      
      msrdata = 0x00UL;
      
      ret = pwrite(perf -> fd, &msrdata, sizeof(msrdata), MSR_ADDR_GLOBAL);
      ret = pwrite(perf -> fd, &msrdata, sizeof(msrdata), MSR_ADDR_CTRL);
      ret = pwrite(perf -> fd, &msrdata, sizeof(msrdata), MSR_ADDR_CTR1);
      ret = pwrite(perf -> fd, &msrdata, sizeof(msrdata), MSR_USER_DAT0);
      ret = pwrite(perf -> fd, &msrdata, sizeof(msrdata), MSR_USER_DAT1);

      msrdata = 0x330;
      
      ret = pwrite(perf -> fd, &msrdata, sizeof(msrdata), MSR_ADDR_CTRL);
      
      if (ret != sizeof(msrdata)) perror("MSR failed ");

      msrdata = (1UL << 22) | (1UL << 16) | MSR_USER_ID0;

      ret = pwrite(perf -> fd, &msrdata, sizeof(msrdata), MSR_USER_SEL0);

      if (ret != sizeof(msrdata)) perror("MSR failed ");

      msrdata = (1UL << 22) | (1UL << 16) | MSR_USER_ID1;

      ret = pwrite(perf -> fd, &msrdata, sizeof(msrdata), MSR_USER_SEL1);

      if (ret != sizeof(msrdata)) perror("MSR failed ");

      msrdata = 0x700000003ULL;
      
      ret = pwrite(perf -> fd, &msrdata, sizeof(msrdata), MSR_ADDR_GLOBAL);

      if (ret != sizeof(msrdata)) perror("MSR failed ");
    }
    
    /* Get Power Unit */
    pread(perf -> fd, &msrdata, sizeof(msrdata), MSR_RAPL_POWER_UNIT);
    
    perf -> punits = pow(0.5, (double)( msrdata        &  0xf));
    perf -> eunits = pow(0.5, (double)((msrdata >>  8) & 0x1f));
  }

  perf -> last_time = dsecond();
  perf -> cur_time  = perf -> last_time;

  perf -> user0_min = -1;
  perf -> user1_min = -1;
  perf -> cycle_min = -1;
}

static __inline__ xlong pmon_cycle(perf_t *perf) {

  xlong data = 0;

  if (perf -> fd >= 0) {

    pread(perf -> fd, &data, sizeof(xlong), MSR_ADDR_CTR1);
    
    data &= 0x000000ffffffffffULL;

  }

  return data;
}

static __inline__ xlong pmon_power(perf_t *perf) {

  xlong data = 0;

  if (perf -> fd >= 0) {

    pread(perf -> fd, &data, sizeof(data), MSR_PKG_ENERGY_STATUS);
    
    data &= 0x00000000ffffffffULL;

  }

  return data;
}

static __inline__ xlong pmon_throttle(perf_t *perf) {

  xlong data = 0;

  if (perf -> fd >= 0) {

    pread(perf -> fd, &data, sizeof(data), MSR_PKG_PERF_STATUS);
    
    data &= 0x00000000ffffffffULL;
    
  }

  return data;
}

static __inline__ xlong pmon_user0(perf_t *perf) {

  xlong data = 0;

  if (perf -> fd >= 0) {

    pread(perf -> fd, &data, sizeof(xlong), MSR_USER_DAT0);
    
    data &= 0x000000ffffffffffULL;

  }

  return data;
}

static __inline__ xlong pmon_user1(perf_t *perf) {

  xlong data = 0;

  if (perf -> fd >= 0) {

    pread(perf -> fd, &data, sizeof(xlong), MSR_USER_DAT1);
    
    data &= 0x000000ffffffffffULL;

  }

  return data;
}

static __inline__ void pmon_quit(perf_t *perf) {

  if (perf -> fd >= 0) close(perf -> fd);
}

static __inline__ void pmon_get(perf_t *perf) {

  perf -> cur_cycle    = pmon_cycle(perf);
  perf -> cur_power    = pmon_power(perf);
  perf -> cur_throttle = pmon_throttle(perf);
  perf -> cur_user0    = pmon_user0(perf);
  perf -> cur_user1    = pmon_user1(perf);
  perf -> cur_time     = dsecond();
}

static __inline__ void pmon_sync(perf_t *perf) {

  perf -> last_cycle    = perf -> cur_cycle;
  perf -> last_power    = perf -> cur_power;
  perf -> last_throttle = perf -> cur_throttle;
  perf -> last_user0    = perf -> cur_user0;
  perf -> last_user1    = perf -> cur_user1;
  perf -> last_time     = perf -> cur_time;
}

static __inline__ void pmon_perf(perf_t *perf) {

  xlong cycle, power;
  double freq, watt, user0, user1;
  double diff_t = perf -> cur_time - perf -> last_time;

  if (perf -> fd < 0)  return;

  if (perf -> cur_cycle >= perf -> last_cycle) {
    cycle = perf -> cur_cycle - perf -> last_cycle;
  } else {
#if 0
    TRACE_PRINT(stderr,"Overflow Happned! \n");
    cycle = perf -> cur_cycle + 0x0ffffffffffULL - perf -> last_cycle;
#endif
  }
  
  power = perf -> cur_power - perf -> last_power;
  
  freq  = (double)cycle / diff_t * 1.e-9;
  watt  = (double)power / diff_t * perf -> eunits;
  user0 = (double)(perf -> cur_user0 - perf -> last_user0) / (double)cycle * 100.;
  user1 = (double)(perf -> cur_user1 - perf -> last_user1) / (double)cycle * 100.;
  
#if 0
  TRACE_PRINT(stderr," %6.3f GHz %6.2f Watt  PerfCtr0 : %6.2f%%  PerfCtr1 : %6.2f%% Cycle : %lld", freq, watt, user0, user1, cycle);
  TRACE_PRINT(stderr,"%lld, %6.3f, %6.2f, %6.2f, %6.2f, %lld,", perf -> core, freq, watt, user0, user1, cycle);

  if (perf -> cur_throttle > perf -> last_throttle) {
    TRACE_PRINT(stderr," TDP");
  } else {
    TRACE_PRINT(stderr,"    ");
  }
#endif
  TRACE_PRINT(stdout,"%6.3f, %6.2f, %6.2f, %lld, ", freq, user0, user1, cycle);

  if (perf -> cycle_min > cycle) {
      perf -> cycle_min = cycle;
      perf -> user0_min = user0;
      perf -> user1_min = user1;
  }
}


static __inline__ void pmon_init_cores(perf_t *perf, int pmon_set, int *cores, int ncores) {
    int i;
    if (perf[0].fd < 0) return;
    for (i=0; i<ncores; ++i) pmon_init(&perf[i], pmon_set, cores[i]);
}

static __inline__ void pmon_get_cores(perf_t *perf, int ncores) {
    int i;
    if (perf[0].fd < 0) return;
    for (i=0; i<ncores; ++i) pmon_get(&perf[i]);
}

static __inline__ void pmon_sync_cores(perf_t *perf, int ncores) {
    int i;
    for (i=0; i<ncores; ++i) pmon_sync(&perf[i]);
}

static __inline__ void pmon_perf_cores(perf_t *perf, int ncores) {
    int i;
    if (perf[0].fd < 0) return;
    TRACE_PRINT(stdout, "\n");
    for (i=0; i<ncores; ++i) {
        pmon_perf(&perf[i]);
        TRACE_PRINT(stdout, "\n");
    }
}

static __inline__ void pmon_quit_cores(perf_t *perf, int ncores) {
    int i;
    if (perf[0].fd < 0) return;
    for (i=0; i<ncores; ++i) pmon_quit(&perf[i]);
}

int matgen(int M, int nb, double *A, int LDA);

static struct { FLOAT *addr; size_t size; long num; long length; } memcheck_t;

static void set_zeros(FLOAT* addr, size_t size, float sparsity) {
    size_t i;
    for (i = 0; i < size; ++i) {
        float perc = (float) rand() / RAND_MAX;
        if (perc < sparsity) addr[i] = (FLOAT) 0.;
    }
}

static void count_zeros(FLOAT* addr, size_t size, size_t* num_zeros) {
    size_t i;
    *num_zeros=0;
    for (i = 0; i < size; ++i) {
        if (addr[i] == 0.) (*num_zeros)++;
    }
}
  
static void *random_thread(void *arg) {

  long pos = (long)arg;
  FLOAT *myaddr;
  size_t mysize, i;
  unsigned int x, y, z, w, t;
  cpu_set_t cpu_mask, cpu_omask;

  sched_getaffinity(0, sizeof(cpu_omask), &cpu_omask);

  CPU_ZERO(&cpu_mask);
  
  CPU_SET(pos, &cpu_mask);  

  sched_setaffinity(0, sizeof(cpu_mask), &cpu_mask);

  myaddr = memcheck_t.addr + pos * memcheck_t.length;
  mysize = memcheck_t.size - pos * memcheck_t.length;
  if (mysize > memcheck_t.length) mysize = memcheck_t.length;

  /* Xorshift random number generator. */
  /* http://www.jstatsoft.org/v08/i14/ */

  x=123456789;
  y=362436069;
  z=521288629;
  w= 88675123 + pos;

  for (i = 0; i < mysize; i ++) {

    t = (x ^ (x << 11));
    x = y;
    y = z;
    z = w;
    w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    
    myaddr[i] = (FLOAT)w / (FLOAT) RAND_MAX - .5;
  }

  sched_setaffinity(0, sizeof(cpu_omask), &cpu_omask);

  return NULL;
}

static void genrandom(FLOAT *addr, size_t size) {

  long i, numprocs;
  pthread_t *threads;

  numprocs = get_nprocs();

  threads = (pthread_t *)malloc(numprocs * sizeof(pthread_t));

  memcheck_t.addr   = addr;
  memcheck_t.size   = size;
  memcheck_t.num    = numprocs;
  memcheck_t.length = (size + numprocs - 1)/ numprocs;
  memcheck_t.length = (memcheck_t.length + 3) & ~3;
  
  for (i = 1; i < numprocs; i ++) pthread_create(&threads[i], NULL, random_thread, (void *)i);
  
  random_thread((void *)0);
  
  for (i = 1; i < numprocs; i ++) pthread_join(threads[i], NULL);
  
  free(threads);
}

static __inline__ void NanCheck(FLOAT *addr, size_t size) {

  long i;

  for (i = 0; i < size; i ++) {
    
    if (isnan(addr[i])) {
      TRACE_PRINT(stderr,"%4ld is NaN\n", i);
    }
  }
}

static __inline__ void *reset_fp(void *my) {

  unsigned int mode;

#ifdef _OPENMP
  long i = (long)my;
  cpu_set_t cpu_mask, cpu_omask;

  sched_getaffinity(0, sizeof(cpu_omask), &cpu_omask);

  CPU_ZERO(&cpu_mask);
  
  CPU_SET(i, &cpu_mask);  

  sched_setaffinity(0, sizeof(cpu_mask), &cpu_mask);

  sched_yield();
#endif

  __asm__ __volatile__ ("stmxcsr %0" : "=m" (mode) : );

  mode &= ~0x3f;

#if 1
  //  mode &= ~0x1000;  // Precision Mask
  mode &= ~0x0800;  // Undeflow  Mask
  mode &= ~0x0400;  // Overflow  Mask
  mode &= ~0x0200;  // Devide by zero Mask
  mode &= ~0x0100;  // Denormal Mask
  mode &= ~0x0080;  // Invalid operation Mask
#endif

  __asm__ __volatile__ ("ldmxcsr %0" : : "m" (mode) );

#ifdef _OPENMP
  sched_setaffinity(0, sizeof(cpu_omask), &cpu_omask);
#endif

  return NULL;
}

static __inline__ void *check_fp(void *my) {

  int mode;
  long i = (long)my;

#ifdef _OPENMP
  cpu_set_t cpu_mask, cpu_omask;

  sched_getaffinity(0, sizeof(cpu_omask), &cpu_omask);

  CPU_ZERO(&cpu_mask);
  
  CPU_SET(i, &cpu_mask);  

  sched_setaffinity(0, sizeof(cpu_mask), &cpu_mask);

  sched_yield();
#endif

  __asm__ __volatile__ ("stmxcsr %0" : "=m" (mode) : );

  if(mode & 0x0001) { TRACE_PRINT(stderr, "[cpu %3ld] Invalid Operation Happened.\n", i);}
  if(mode & 0x0002) { TRACE_PRINT(stderr, "[cpu %3ld] Denormal Happened.\n", i);}
  if(mode & 0x0004) { TRACE_PRINT(stderr, "[cpu %3ld] Divide-by-Zero Happened.\n", i);}
  if(mode & 0x0008) { TRACE_PRINT(stderr, "[cpu %3ld] Overflow Happened.\n", i);}
  if(mode & 0x0010) { TRACE_PRINT(stderr, "[cpu %3ld] Underflow Happened.\n", i);}

#if 0
  mode |= 0x1000;  // Precision Mask
  mode |= 0x0800;  // Undeflow  Mask
  mode |= 0x0400;  // Overflow  Mask
  mode |= 0x0200;  // Devide by zero Mask
  mode |= 0x0100;  // Denormal Mask
  mode |= 0x0080;  // Invalid operation Mask

  __asm__ __volatile__ ("ldmxcsr %0" : : "m" (mode) );
#endif

#ifdef _OPENMP
  sched_setaffinity(0, sizeof(cpu_omask), &cpu_omask);
#endif

  return NULL;
}

static __inline__ void reset_fp_all(void) {

#ifdef _OPENMP
  long i, numprocs;
  pthread_t *threads;

  numprocs = get_nprocs();

  threads = (pthread_t *)malloc(numprocs * sizeof(pthread_t));

  for (i = 0; i < numprocs; i ++) pthread_create(&threads[i], NULL, reset_fp, (void *)i);
  
  for (i = 0; i < numprocs; i ++) pthread_join(threads[i], NULL);

  free(threads);
#else
  reset_fp(NULL);
#endif
}

static __inline__ void check_fp_all(void) {

#ifdef _OPENMP
  long i, numprocs;
  pthread_t *threads;

  numprocs = get_nprocs();

  threads = (pthread_t *)malloc(numprocs * sizeof(pthread_t));

  for (i = 0; i < numprocs; i ++) pthread_create(&threads[i], NULL, check_fp, (void *)i);
  
  for (i = 0; i < numprocs; i ++) pthread_join(threads[i], NULL);
  
  free(threads);
#else
  check_fp(NULL);
#endif
}
#endif

typedef struct {
  int    MajorVersion;
  int    MinorVersion;
  int    UpdateVersion;
  char * ProductStatus;
  char * Build;
  char * Processor;
  char * Platform;
} MKLVersion;

static __inline__ void getmklver(void) {

  void MKL_Get_Version(MKLVersion *) __attribute__((weak));

  MKLVersion ver;

  if (MKL_Get_Version) {

    MKL_Get_Version(&ver);
    
    TRACE_PRINT(stderr,"Processor ... %s\n", ver.Processor);
    TRACE_PRINT(stderr,"MKL_DEBUG_CYP_TYPE : %s\n", getenv("MKL_DEBUG_CPU_TYPE"));
    fflush(stderr);
  }
}

static __inline__ int check_matrix(int m, int n, int k, FLOAT *a, int lda, FLOAT *b, int ldb) {

  int i, j, flag;

  flag = 0;

  for (j = 0; j < n; j ++) {
    for (i = 0; i < m; i ++) {
      //      printf("%d  %d\n", isnan(a[(i + j * lda) * 2 ]), isnan(b[(i + j * ldb) * 2]));

#ifndef USE_COMPLEX
      if (diffs(a[i + j * lda], b[i + j * ldb], k) || (isnan(a[i + j * lda]) != isnan(b[i + j * ldb]))) {
	if (flag == 0) TRACE_PRINT(stderr, "\n\n");
	
	TRACE_PRINT(stderr, "M = %4d  N = %4d  K = %4d [%4d, %4d] = %20.4f   %20.7f  Error = %e\n",
		m, n, k, i, j,
		(double)a[i + j * lda], (double)b[i + j * ldb], (double)a[i + j * lda] - (double)b[i + j * ldb]);
	
	flag = 1;
      }
#else
      if (diffs(a[(i + j * lda) * 2 + 0], b[(i + j * ldb) * 2 + 0], k) ||
	  diffs(a[(i + j * lda) * 2 + 1], b[(i + j * ldb) * 2 + 1], k) ||
	  (isnan(a[(i + j * lda) * 2 + 0]) != isnan(b[(i + j * ldb) * 2 + 0])) ||
	  (isnan(a[(i + j * lda) * 2 + 1]) != isnan(b[(i + j * ldb) * 2 + 1]))) {
	if (flag == 0) TRACE_PRINT(stderr, "\n\n");
	
	TRACE_PRINT(stderr, "M = %4d  N = %4d  K = %4d [%4d, %4d] = (%10.7f, %10.7f) (%10.7f, %10.7f)\n",
		m, n, k, i, j,
		(double)a[(i + j * lda) * 2 + 0], (double)a[(i + j * lda) * 2 + 1],
		(double)b[(i + j * ldb) * 2 + 0], (double)b[(i + j * ldb) * 2 + 1]);
	
	flag = 1;
      }
#endif
    }
  }

  return flag;
}

