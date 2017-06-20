#!/bin/bash

#libtool --mode=execute \
SRC_ROOT=$HOME/p3_power_management-geopm

LD_LIBRARY_PATH=$HOME/build/geopm/lib:$LD_LIBRARY_PATH
OMP_NUM_THREADS=8 \
GEOPM_ERROR_AFFINITY_IGNORE=true \
srun -N2 -n8 \
${SRC_ROOT}/examples/fft/.libs/nas_ft
#OMP_NUM_THREADS=16 \
#srun -N4 -n16 \
