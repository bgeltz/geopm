#!/bin/bash

SRC_ROOT=$HOME/p3_power_management-geopm

#GEOPM_DEBUG_ATTACH=5 \
GEOPM_DEATH_TESTING=1 \
GEOPM_PMPI_CTL=process \
GEOPM_SHMKEY=/brg \
GEOPM_POLICY=${SRC_ROOT}/test/default_policy.json \
libtool --mode=execute \
srun -N1 -n2 \
test/geopm_mpi_test --gtest_filter=MPIControllerDeathTest.shm_clean_up
#test/geopm_mpi_test --gtest_filter=MPIControllerDeathTest.hello --gtest_death_test_style=fast
#test/geopm_mpi_test --gtest_filter=MPIProfileTest.*
#test/geopm_mpi_test --gtest_filter=MPISharedMemoryTest.hello
