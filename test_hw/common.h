#ifndef COMMON_H
#define COMMON_H

#define	_GNU_SOURCE

#include <sys/time.h>
#include <stdio.h>
#include <asm/unistd.h>
#include <unistd.h>
#include <sched.h>
#include <stdint.h>
#ifdef _OPENMP
#include <omp.h>
#endif

#if !defined USE_FLOAT && !defined USE_DOUBLE && !defined USE_INT
#define USE_FLOAT
#endif

#ifdef	USE_FLOAT
#define	FLOAT_IN	float
#define	FLOAT_BUF	float
#define	FLOAT_OUT	float
#define	FLOAT		float
#endif

#ifdef	USE_DOUBLE
#define	FLOAT_IN	double
#define	FLOAT_BUF	double
#define	FLOAT_OUT	double
#define	FLOAT		double
#endif

#ifdef	USE_INT
#define	FLOAT_IN	uint8_t
#define	FLOAT_BUF	uint16_t
#define	FLOAT_OUT	int32_t
#define	FLOAT		int32_t
#endif

#ifdef __i386__
typedef int mkl_ker_int;
#else
typedef long long mkl_ker_int;
#endif

#ifndef USE_INTERNAL
typedef int  mkl_int;
#else
typedef long mkl_int;
#endif

typedef unsigned long long xlong;

#define	mkl_type	FLOAT

#define	BLAS_A_TRANS	 1
#define	BLAS_A_CONJ	 2
#define	BLAS_A_NONUNIT	 4
#define	BLAS_B_TRANS	 8
#define	BLAS_B_CONJ     16
#define	BLAS_B_NONUNIT  32

#define INSTRUCTION_SSE		1
#define INSTRUCTION_SSE2	2
#define INSTRUCTION_AVX		4
#define INSTRUCTION_AVX2	8
#define INSTRUCTION_AVX512     16
#define INSTRUCTION_KNC        32

#define	CPUARCH_NULL	0
#define	CPUARCH_WSM	1
#define	CPUARCH_SNB	2
#define	CPUARCH_HSW	3
#define	CPUARCH_SKL	4
#define	CPUARCH_SKX	5
#define	CPUARCH_KNL	6
#define	CPUARCH_ATM	7
#define	CPUARCH_BULL	8

static __inline__ xlong rdtsc(void) {
  unsigned int ax, dx;

  __asm__ __volatile__ ("rdtsc" : "=a"(ax), "=d"(dx));

  return ((((xlong)dx) << 32) | ax);
}

static __inline__ xlong rdtscp(void) {
  unsigned int ax, dx;

  __asm__ __volatile__ ("rdtscp" : "=a"(ax), "=d"(dx));

  return ((((xlong)dx) << 32) | ax);
}

static __inline__ void rawlock(__volatile__ unsigned long *addr){

  unsigned long ret;

  do {
    while (*addr) sched_yield();

    ret = __sync_lock_test_and_set(addr, 1);

  } while (ret);
}

static __inline__ void rawunlock(__volatile__ unsigned long *addr){

  __sync_lock_release(addr);

}

typedef struct {
  int cpuarch, instruction, cnr, dtlb;

  long offsetA, offsetB;

  int sunroll_m, sunroll_n, sblock_m, sblock_n, sblock_k;

  void (*sgemm_incopy)   (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*sgemm_itcopy)   (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*sgemm_oncopy)   (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*sgemm_otcopy)   (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*ssymm_iucopy)   (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*ssymm_ilcopy)   (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*ssymm_oucopy)   (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*ssymm_olcopy)   (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*sgemm_kernel)   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*sgemm_kernel_b0)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*strsm_kernel_lu)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*strsm_kernel_ll)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*strsm_kernel_ru)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*strsm_kernel_rl)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*strmm_kernel_lu)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*strmm_kernel_ll)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*strmm_kernel_ru)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*strmm_kernel_rl)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);

  void (*sgemm_kernelNoA)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, mkl_ker_int lda, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);

  int dunroll_m, dunroll_n, dblock_m, dblock_n, dblock_k;

  void (*dgemm_incopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*dgemm_itcopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*dgemm_oncopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*dgemm_otcopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*dsymm_iucopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*dsymm_ilcopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*dsymm_oucopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*dsymm_olcopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*dgemm_kernel)   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*dgemm_kernel_b0)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*dtrsm_kernel_lu)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*dtrsm_kernel_ll)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*dtrsm_kernel_ru)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*dtrsm_kernel_rl)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*dtrmm_kernel_lu)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*dtrmm_kernel_ll)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*dtrmm_kernel_ru)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*dtrmm_kernel_rl)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);

  void (*dgemm_kernelNoA)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, mkl_ker_int lda, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);

  int cunroll_m, cunroll_n, cblock_m, cblock_n, cblock_k;

  void (*cgemm_incopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*cgemm_itcopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*cgemm_oncopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*cgemm_otcopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*cgemm_cincopy)(mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*cgemm_citcopy)(mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*cgemm_concopy)(mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*cgemm_cotcopy)(mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*csymm_iucopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*csymm_ilcopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*csymm_oucopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*csymm_olcopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*chemm_iucopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*chemm_ilcopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*chemm_oucopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*chemm_olcopy) (mkl_ker_int *m, mkl_ker_int *n, float  *a, mkl_ker_int* lda, float  *alpha, float  *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*cgemm_kernel)   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*cgemm_kernel_b0)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ctrsm_kernel_lu)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ctrsm_kernel_ll)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ctrsm_kernel_ru)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ctrsm_kernel_rl)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ctrmm_kernel_lu)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ctrmm_kernel_ll)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ctrmm_kernel_ru)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ctrmm_kernel_rl)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);

  void (*cgemm_kernelNoA)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, mkl_ker_int lda, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);

  int zunroll_m, zunroll_n, zblock_m, zblock_n, zblock_k;

  void (*zgemm_incopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zgemm_itcopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zgemm_oncopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zgemm_otcopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*zgemm_cincopy)  (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zgemm_citcopy)  (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zgemm_concopy)  (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zgemm_cotcopy)  (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*zsymm_iucopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zsymm_ilcopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zsymm_oucopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zsymm_olcopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*zhemm_iucopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zhemm_ilcopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zhemm_oucopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*zhemm_olcopy)   (mkl_ker_int *m, mkl_ker_int *n, double *a, mkl_ker_int* lda, double *alpha, double *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*zgemm_kernel)   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*zgemm_kernel_b0)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ztrsm_kernel_lu)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ztrsm_kernel_ll)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ztrsm_kernel_ru)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ztrsm_kernel_rl)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ztrmm_kernel_lu)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ztrmm_kernel_ll)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ztrmm_kernel_ru)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*ztrmm_kernel_rl)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);

  void (*zgemm_kernelNoA)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, mkl_ker_int lda, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);

  int iunroll_m, iunroll_n, iblock_m, iblock_n, iblock_k;

  void (*igemm_incopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*igemm_itcopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*igemm_oncopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*igemm_otcopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*igemm_cincopy)  (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*igemm_citcopy)  (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*igemm_concopy)  (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*igemm_cotcopy)  (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*isymm_iucopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*isymm_ilcopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*isymm_oucopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*isymm_olcopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*ihemm_iucopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*ihemm_ilcopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*ihemm_oucopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*ihemm_olcopy)   (mkl_ker_int *m, mkl_ker_int *n, uint8_t *a, mkl_ker_int* lda, uint8_t *alpha, uint16_t *b, mkl_ker_int* ldb, mkl_ker_int* offt);

  void (*igemm_kernel)   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint16_t *a, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*igemm_kernel_b0)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint16_t *a, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*itrsm_kernel_lu)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint16_t *a, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*itrsm_kernel_ll)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint16_t *a, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*itrsm_kernel_ru)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint16_t *a, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*itrsm_kernel_rl)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint16_t *a, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*itrmm_kernel_lu)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint16_t *a, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*itrmm_kernel_ll)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint16_t *a, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*itrmm_kernel_ru)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint16_t *a, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*itrmm_kernel_rl)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint16_t *a, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);

  void (*igemm_kernelNoA)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint8_t *a, mkl_ker_int lda, uint16_t *b, int32_t *c, mkl_ker_int ldc, mkl_ker_int offt);

} archinfo_t;

typedef struct {
  int info;

  FLOAT_IN       *diag;
  mkl_ker_int  diag_inc;

  void (*copyA)    (mkl_ker_int *m, mkl_ker_int *n, FLOAT_IN  *a, mkl_ker_int* lda, FLOAT_IN  *alpha, FLOAT_BUF  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*copyB)    (mkl_ker_int *m, mkl_ker_int *n, FLOAT_IN  *a, mkl_ker_int* lda, FLOAT_IN  *alpha, FLOAT_BUF  *b, mkl_ker_int* ldb, mkl_ker_int* offt);
  void (*kernel)   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, FLOAT_BUF  *a, FLOAT_BUF  *b, FLOAT_OUT  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*tkernel)  (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, FLOAT_BUF  *a, FLOAT_BUF  *b, FLOAT_OUT  *c, mkl_ker_int ldc, mkl_ker_int offt);
  void (*kernelNoA)(mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, FLOAT_IN   *a, mkl_ker_int lda, FLOAT_BUF *b, FLOAT_OUT *c, mkl_ker_int ldc, mkl_ker_int offt);

} funcinfo_t;

extern archinfo_t archinfo;

#ifndef USE_COMPLEX
#define	COMPSIZE	1
#else
#define	COMPSIZE	2
#endif

#define BLASLONG	long

#if !defined(USE_COMPLEX) && defined(USE_FLOAT)
#define	UNROLL_M	archinfo.sunroll_m
#define	UNROLL_N	archinfo.sunroll_n
#define	BLOCK_M		archinfo.sblock_m
#define	BLOCK_N		archinfo.sblock_n
#define	BLOCK_K		archinfo.sblock_k
#define LEVEL3_DRIVER	slevel3_driver
#endif

#if !defined(USE_COMPLEX) && defined(USE_DOUBLE)
#define	UNROLL_M	archinfo.dunroll_m
#define	UNROLL_N	archinfo.dunroll_n
#define	BLOCK_M		archinfo.dblock_m
#define	BLOCK_N		archinfo.dblock_n
#define	BLOCK_K		archinfo.dblock_k
#define LEVEL3_DRIVER	dlevel3_driver
#endif

#if  defined(USE_COMPLEX) && defined(USE_FLOAT)
#define	UNROLL_M	archinfo.cunroll_m
#define	UNROLL_N	archinfo.cunroll_n
#define	BLOCK_M		archinfo.cblock_m
#define	BLOCK_N		archinfo.cblock_n
#define	BLOCK_K		archinfo.cblock_k
#define LEVEL3_DRIVER	clevel3_driver
#endif

#if  defined(USE_COMPLEX) && defined(USE_DOUBLE)
#define	UNROLL_M	archinfo.zunroll_m
#define	UNROLL_N	archinfo.zunroll_n
#define	BLOCK_M		archinfo.zblock_m
#define	BLOCK_N		archinfo.zblock_n
#define	BLOCK_K		archinfo.zblock_k
#define LEVEL3_DRIVER	zlevel3_driver
#endif

#if !defined(USE_COMPLEX) && defined(USE_INT)
#define	UNROLL_M	archinfo.iunroll_m
#define	UNROLL_N	archinfo.iunroll_n
#define	BLOCK_M		archinfo.iblock_m
#define	BLOCK_N		archinfo.iblock_n
#define	BLOCK_K		archinfo.iblock_k
#define LEVEL3_DRIVER	ilevel3_driver
#endif

#if defined USE_INT && defined IFPRATIO
#define FPRATIO		IFPRATIO
#endif

#ifdef USE_FLOAT
#define FPRATIO		SFPRATIO
#endif

#ifdef USE_DOUBLE
#define FPRATIO		DFPRATIO
#endif

#ifndef FPRATIO
#define FPRATIO		SFPRATIO
#endif

#define	BUFFER_SIZE	(32ULL << 20)

void gemm_sdiag_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, float  *, mkl_ker_int);
void gemm_ddiag_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, double *, mkl_ker_int);
void gemm_cdiag_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, float  *, mkl_ker_int);
void gemm_zdiag_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, double *, mkl_ker_int);

void gemm_sscale_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int, float  *);
void gemm_dscale_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int, double *);
void gemm_cscale_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int, float  *);
void gemm_zscale_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int, double *);

void trsm_sscale_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trsm_sscale_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trsm_dscale_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);
void trsm_dscale_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);
void trsm_cscale_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trsm_cscale_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trsm_zscale_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);
void trsm_zscale_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);

void trmm_sscale_upper_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trmm_sscale_lower_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trmm_sscale_upper_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trmm_sscale_lower_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trmm_dscale_upper_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);
void trmm_dscale_lower_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);
void trmm_dscale_upper_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);
void trmm_dscale_lower_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);

void trmm_cscale_upper_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trmm_cscale_lower_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trmm_cscale_upper_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trmm_cscale_lower_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, float  *, mkl_ker_int);
void trmm_zscale_upper_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);
void trmm_zscale_lower_unit_na   (mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);
void trmm_zscale_upper_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);
void trmm_zscale_lower_nonunit_na(mkl_ker_int, mkl_ker_int, mkl_ker_int, double *, mkl_ker_int);

/* This is a generic kernel and architecture suffix is not required */
void ssyrk_kernel_l     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void ssyrk_kernel_u     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void dsyrk_kernel_l     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void dsyrk_kernel_u     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void csyrk_kernel_l     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void csyrk_kernel_u     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void zsyrk_kernel_l     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void zsyrk_kernel_u     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void cherk_kernel_l     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void cherk_kernel_u     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void zherk_kernel_l     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void zherk_kernel_u     (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);

void ssyr2k_kernel1_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void ssyr2k_kernel2_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void ssyr2k_kernel1_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void ssyr2k_kernel2_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void dsyr2k_kernel1_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void dsyr2k_kernel2_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void dsyr2k_kernel1_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void dsyr2k_kernel2_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void csyr2k_kernel1_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void csyr2k_kernel2_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void csyr2k_kernel1_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void csyr2k_kernel2_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void zsyr2k_kernel1_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void zsyr2k_kernel2_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void zsyr2k_kernel1_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void zsyr2k_kernel2_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void cher2k_kernel1_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void cher2k_kernel2_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void cher2k_kernel1_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void cher2k_kernel2_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *a, float  *b, float  *c, mkl_ker_int ldc, mkl_ker_int offt);
void zher2k_kernel1_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void zher2k_kernel2_l   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void zher2k_kernel1_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);
void zher2k_kernel2_u   (mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *a, double *b, double *c, mkl_ker_int ldc, mkl_ker_int offt);

void *falloc(void);
void ffree(void *);
void archinfo_init();

void slevel3_driver(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *alpha, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *c, mkl_ker_int ldc, float * );
void dlevel3_driver(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *alpha, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *c, mkl_ker_int ldc, double *);
void clevel3_driver(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, float  *alpha, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *c, mkl_ker_int ldc, float * );
void zlevel3_driver(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, double *alpha, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *c, mkl_ker_int ldc, double *);
void ilevel3_driver(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, mkl_ker_int k, uint8_t *alpha, uint8_t *a, mkl_ker_int lda, uint8_t  *b, mkl_ker_int ldb, int32_t *c, mkl_ker_int ldc, uint16_t * );

void strsm_LL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void strsm_LU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void strsm_RL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void strsm_RU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);

void dtrsm_LL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void dtrsm_LU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void dtrsm_RL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void dtrsm_RU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);

void ctrsm_LL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void ctrsm_LU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void ctrsm_RL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void ctrsm_RU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);

void ztrsm_LL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void ztrsm_LU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void ztrsm_RL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void ztrsm_RU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);

void strmm_LL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void strmm_LU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void strmm_RL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void strmm_RU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);

void dtrmm_LL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void dtrmm_LU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void dtrmm_RL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void dtrmm_RU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);

void ctrmm_LL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void ctrmm_LU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void ctrmm_RL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);
void ctrmm_RU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, float  *a, mkl_ker_int lda, float  *b, mkl_ker_int ldb, float  *buffer);

void ztrmm_LL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void ztrmm_LU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void ztrmm_RL(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);
void ztrmm_RU(funcinfo_t *info, mkl_ker_int m, mkl_ker_int n, double *a, mkl_ker_int lda, double *b, mkl_ker_int ldb, double *buffer);

#if 0
void scopy_   (int *n, float  *x, int *incx, float  *y, int *incy);
void dcopy_   (int *n, double *x, int *incx, double *y, int *incy);
void ccopy_   (int *n, float  *x, int *incx, float  *y, int *incy);
void zcopy_   (int *n, double *x, int *incx, double *y, int *incy);

void scal_    (int *n, float  *alpha, float  *x, int *incx);
void dcal_    (int *n, double *alpha, double *x, int *incx);
void ccal_    (int *n, float  *alpha, float  *x, int *incx);
void zcal_    (int *n, double *alpha, double *x, int *incx);
#endif

int saxpy_(int *, float  *, float  *, int *, float  *, int *);
int daxpy_(int *, double *, double *, int *, double *, int *);
int caxpy_(int *, float  *, float  *, int *, float  *, int *);
int zaxpy_(int *, double *, double *, int *, double *, int *);

/* Fortran Interface */
float  snrm2_ (int *, float  *, int *);
double dnrm2_ (int *, double *, int *);
float  scnrm2_(int *, float  *, int *);
double dznrm2_(int *, double *, int *);

float  snrm2_fast     (int *, float  *, int *, float  *);
float  snrm2_scale    (int *, float  *, int *, float  *);
float  snrm2_accurate (int *, float  *, int *, float  *);

double dnrm2_fast     (int *, double *, int *, double *);
double dnrm2_scale    (int *, double *, int *, double *);
double dnrm2_accurate (int *, double *, int *, double *);

float  cnrm2_fast     (int *, float  *, int *, float  *);
float  cnrm2_scale    (int *, float  *, int *, float  *);
float  cnrm2_accurate (int *, float  *, int *, float  *);

double znrm2_fast     (int *, double *, int *, double *);
double znrm2_scale    (int *, double *, int *, double *);
double znrm2_accurate (int *, double *, int *, double *);

float  samax_(int *, float  *, int *);
double damax_(int *, double *, int *);
float  camax_(int *, float  *, int *);
double zamax_(int *, double *, int *);

int  isamax_(int *, float  *, int *);
int  idamax_(int *, double *, int *);
int  icamax_(int *, float  *, int *);
int  izamax_(int *, double *, int *);

int sger_  (int *, int *, float  *, float  *, int *, float  *, int *, float  *, int *);
int dger_  (int *, int *, double *, double *, int *, double *, int *, double *, int *);
int cgeru_ (int *, int *, float  *, float  *, int *, float  *, int *, float  *, int *);
int cgerc_ (int *, int *, float  *, float  *, int *, float  *, int *, float  *, int *);
int zgeru_ (int *, int *, double *, double *, int *, double *, int *, double *, int *);
int zgerc_ (int *, int *, double *, double *, int *, double *, int *, double *, int *);

int sgemv_ (char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dgemv_ (char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int cgemv_ (char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zgemv_ (char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int strmv_ (char *, char *, char *, int *, float  *, int *, float  *, int *);
int dtrmv_ (char *, char *, char *, int *, double *, int *, double *, int *);
int ctrmv_ (char *, char *, char *, int *, float  *, int *, float  *, int *);
int ztrmv_ (char *, char *, char *, int *, double *, int *, double *, int *);

int ssymv_ (char *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dsymv_ (char *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int csymv_ (char *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zsymv_ (char *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int sgemm_ (char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dgemm_ (char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int cgemm_ (char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zgemm_ (char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int igemm_ (char *, char *, int *, int *, int *, uint8_t *, uint8_t *, int *, uint8_t *, int *, int32_t *, int32_t *, int *);

int sgemsm_(char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dgemsm_(char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, int *, double *, double *, int *);
int cgemsm_(char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zgemsm_(char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, int *, double *, double *, int *);

int sgema_ (char *, int *, int *, float  *, float  *, int *, float  *, float  *, int *);
int dgema_ (char *, int *, int *, double *, double *, int *, double *, double *, int *);
int cgema_ (char *, int *, int *, float  *, float  *, int *, float  *, float  *, int *);
int zgema_ (char *, int *, int *, double *, double *, int *, double *, double *, int *);

int scgemm_ (char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dzgemm_ (char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int ssymm_ (char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dsymm_ (char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int csymm_ (char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zsymm_ (char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int chemm_ (char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zhemm_ (char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int ssyrk_ (char *, char *, int *, int *, float  *, float  *, int *, float  *, float  *, int *);
int dsyrk_ (char *, char *, int *, int *, double *, double *, int *, double *, double *, int *);
int csyrk_ (char *, char *, int *, int *, float  *, float  *, int *, float  *, float  *, int *);
int zsyrk_ (char *, char *, int *, int *, double *, double *, int *, double *, double *, int *);
int cherk_ (char *, char *, int *, int *, float  *, float  *, int *, float  *, float  *, int *);
int zherk_ (char *, char *, int *, int *, double *, double *, int *, double *, double *, int *);

int ssyrsk_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dsyrsk_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int csyrsk_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zsyrsk_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int ssyr2k_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dsyr2k_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int csyr2k_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zsyr2k_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int cher2k_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zher2k_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int shamm_(char *, char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dhamm_(char *, char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int chamm_(char *, char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zhamm_(char *, char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int strsm_ (char *, char *, char *, char *, int *, int *, float  *,  float  *, int *, float  *, int *);
int dtrsm_ (char *, char *, char *, char *, int *, int *, double *,  double *, int *, double *, int *);
int ctrsm_ (char *, char *, char *, char *, int *, int *, float  *,  float  *, int *, float  *, int *);
int ztrsm_ (char *, char *, char *, char *, int *, int *, double *,  double *, int *, double *, int *);

int strmm_ (char *, char *, char *, char *, int *, int *, float  *,  float  *, int *, float  *, int *);
int dtrmm_ (char *, char *, char *, char *, int *, int *, double *,  double *, int *, double *, int *);
int ctrmm_ (char *, char *, char *, char *, int *, int *, float  *,  float  *, int *, float  *, int *);
int ztrmm_ (char *, char *, char *, char *, int *, int *, double *,  double *, int *, double *, int *);

/* Reference BLAS */
float  snrm2f_ (int *, float  *, int *);
double dnrm2f_ (int *, double *, int *);
float  scnrm2f_(int *, float  *, int *);
double dznrm2f_(int *, double *, int *);

float  samaxf_(int *, float  *, int *);
double damaxf_(int *, double *, int *);
float  camaxf_(int *, float  *, int *);
double zamaxf_(int *, double *, int *);

int  isamaxf_(int *, float  *, int *);
int  idamaxf_(int *, double *, int *);
int  icamaxf_(int *, float  *, int *);
int  izamaxf_(int *, double *, int *);

int sgerf_ (int *, int *, float  *, float  *, int *, float  *, int *, float  *, int *);
int dgerf_ (int *, int *, double *, double *, int *, double *, int *, double *, int *);
int cgeruf_(int *, int *, float  *, float  *, int *, float  *, int *, float  *, int *);
int cgercf_(int *, int *, float  *, float  *, int *, float  *, int *, float  *, int *);
int zgeruf_(int *, int *, double *, double *, int *, double *, int *, double *, int *);
int zgercf_(int *, int *, double *, double *, int *, double *, int *, double *, int *);

int sgemvf_ (char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dgemvf_ (char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int cgemvf_ (char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zgemvf_ (char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int sgemmf_(char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dgemmf_(char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int cgemmf_(char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zgemmf_(char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int igemmf_(char *, char *, int *, int *, int *, uint8_t *, uint8_t *, int *, uint8_t *, int *, int32_t *, int32_t *, int *);

int ssymvf_ (char *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dsymvf_ (char *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int csymvf_ (char *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zsymvf_ (char *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int sgemsmf_(char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dgemsmf_(char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, int *, double *, double *, int *);
int cgemsmf_(char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zgemsmf_(char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, int *, double *, double *, int *);

int sgemaf_ (char *, int *, int *, float  *, float  *, int *, float  *, float  *, int *);
int dgemaf_ (char *, int *, int *, double *, double *, int *, double *, double *, int *);
int cgemaf_ (char *, int *, int *, float  *, float  *, int *, float  *, float  *, int *);
int zgemaf_ (char *, int *, int *, double *, double *, int *, double *, double *, int *);

int ssymmf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dsymmf_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int csymmf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zsymmf_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int chemmf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zhemmf_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int ssyrkf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, float  *, int *);
int dsyrkf_(char *, char *, int *, int *, double *, double *, int *, double *, double *, int *);
int csyrkf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, float  *, int *);
int zsyrkf_(char *, char *, int *, int *, double *, double *, int *, double *, double *, int *);
int cherkf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, float  *, int *);
int zherkf_(char *, char *, int *, int *, double *, double *, int *, double *, double *, int *);

int ssyrskf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dsyrskf_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int csyrskf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zsyrskf_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int ssyr2kf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dsyr2kf_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int csyr2kf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zsyr2kf_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int cher2kf_(char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zher2kf_(char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int shammf_(char *, char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dhammf_(char *, char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int chammf_(char *, char *, char *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zhammf_(char *, char *, char *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

int strsmf_ (char *, char *, char *, char *, int *, int *, float  *,  float  *, int *, float  *, int *);
int dtrsmf_ (char *, char *, char *, char *, int *, int *, double *,  double *, int *, double *, int *);
int ctrsmf_ (char *, char *, char *, char *, int *, int *, float  *,  float  *, int *, float  *, int *);
int ztrsmf_ (char *, char *, char *, char *, int *, int *, double *,  double *, int *, double *, int *);

int strmmf_ (char *, char *, char *, char *, int *, int *, float  *,  float  *, int *, float  *, int *);
int dtrmmf_ (char *, char *, char *, char *, int *, int *, double *,  double *, int *, double *, int *);
int ctrmmf_ (char *, char *, char *, char *, int *, int *, float  *,  float  *, int *, float  *, int *);
int ztrmmf_ (char *, char *, char *, char *, int *, int *, double *,  double *, int *, double *, int *);

int strmvf_ (char *, char *, char *, int *, float  *, int *, float  *, int *);
int dtrmvf_ (char *, char *, char *, int *, double *, int *, double *, int *);
int ctrmvf_ (char *, char *, char *, int *, float  *, int *, float  *, int *);
int ztrmvf_ (char *, char *, char *, int *, double *, int *, double *, int *);

int sgemm_nocopy_(char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int dgemm_nocopy_(char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);
int cgemm_nocopy_(char *, char *, int *, int *, int *, float  *, float  *, int *, float  *, int *, float  *, float  *, int *);
int zgemm_nocopy_(char *, char *, int *, int *, int *, double *, double *, int *, double *, int *, double *, double *, int *);

#endif
