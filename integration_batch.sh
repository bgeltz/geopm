#!/bin/bash
#SBATCH --mail-type=ALL
#SBATCH -N 4
#SBATCH --export=ALL
#SBATCH -t 01:00:00
set -e

LOG_FILE=test_output.log
GEOPM_PATH=${HOME}/geopm
PATH=${GEOPM_PATH}/.libs:${PATH}

module purge && module load gnu impi autotools

# Run integration tests

# FIXME - Requires pandas on compute nodes!
# pip install --user -I pandas matplotlib natsort numexpr bottleneck

pushd ${GEOPM_PATH}/test_integration
LD_PRELOAD=${GEOPM_PATH}/openmp/lib/libomp.so GEOPM_PLUGIN_PATH=${GEOPM_PATH}/.libs LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/5.3.0/lib64:${GEOPM_PATH}/.libs:${LD_LIBRARY_PATH} ./geopm_test_integration.py -v > >(tee -a integration_${LOG_FILE}) 2>&1
touch .tests_complete
popd

