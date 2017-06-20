#!/bin/bash

SRC_ROOT=$HOME/p3_power_management-geopm

#GEOPM_DEBUG_ATTACH=0 \
#gdb --args \

GEOPM_PMPI_CTL=process \
GEOPM_SHMKEY=/brg \
GEOPM_POLICY=${SRC_ROOT}/test/default_policy.json \
GEOPM_TRACE="brg-example-trace" \
libtool --mode=execute \
srun -N1 -n4 \
${SRC_ROOT}/examples/timed_region

# Other progs:
#${SRC_ROOT}/examples/fft/nas_ft
