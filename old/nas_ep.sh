#!/bin/bash

#libtool --mode=execute \
SRC_ROOT=$HOME/p3_power_management-geopm

#GEOPM_DEBUG_ATTACH=1 \
LD_LIBRARY_PATH=$HOME/build/geopm/lib:$LD_LIBRARY_PATH
GEOPM_PMPI_CTL=process \
GEOPM_SHMKEY=/brg \
GEOPM_POLICY=${SRC_ROOT}/test/default_policy.json \
GEOPM_REGION_BARRIER=true \
GEOPM_TRACE="brg-nas-trace" \
OMP_NUM_THREADS=16 \
\
srun -N4 -n20 \
     -w mr-fusion[4-7] \
     --cpu_bind=v,mask_cpu:0x100000000000000000000,0xFFFF,0xFFFF0000,0xFFFF00000000,0xFFFF000000000000 \
     examples/fft/.libs/nas_ft
