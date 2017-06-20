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
srun -w mr-fusion[4-7] -N4 -n20 --cpu_bind=v,mask_cpu:0x100000000000000000000,0xFFFF,0xFFFF0000,0xFFFF00000000,0xFFFF000000000000 \
examples/fft/.libs/nas_ft
#${SRC_ROOT}/examples/fft/nas_ft

#OMP_NUM_THREADS=16 \
#srun -N4 -n20 --cpu_bind=v,mask_cpu:0x100000000000000000000,0xFFFF,0xFFFF0000,0xFFFF00000000,0xFFFF000000000000 \

#OMP_NUM_THREADS=8 \
#srun -N2 -n10 --cpu_bind=v,mask_cpu:0x100000000000000000000,0xFFFF,0xFFFF0000,0xFFFF00000000,0xFFFF000000000000 \

#gdb --args \
#test/geopm_mpi_test --gtest_filter=MPIControllerDeathTest.shm_clean_up
#test/geopm_mpi_test --gtest_filter=MPIControllerDeathTest.hello --gtest_death_test_style=fast
#test/geopm_mpi_test --gtest_filter=MPIProfileTest.*
#test/geopm_mpi_test --gtest_filter=MPISharedMemoryTest.hello
