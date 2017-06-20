#!/bin/bash

SRC_ROOT=$HOME/p3_power_management-geopm

#GEOPM_DEBUG_ATTACH=5 \
LD_LIBRARY_PATH=$HOME/build/geopm/lib:$LD_LIBRARY_PATH \
GEOPM_PMPI_CTL=process \
GEOPM_SHMKEY=/brg \
GEOPM_POLICY=${SRC_ROOT}/test/default_policy.json \
GEOPM_REGION_BARRIER=true \
GEOPM_TRACE="brg-nas-trace" \
srun -N2 -n2 \
geopmctl
#srun -N4 -n4 \
