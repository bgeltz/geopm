#!/bin/bash
#SBATCH -N 1
#SBATCH -J demo
#SBATCH -t 24:00:00
#SBATCH -o %j_demo.out

TIMESTAMP=$(date +%F_%H%M)
GEOPM_SRC=${HOME}/geopm
OUTDIR=${HOME}/output/test_app_${TIMESTAMP}
mkdir -p ${OUTDIR}
cd ${OUTDIR}

set -x

NUM_NODES=1
RANKS_PER_NODE=4
# export OMP_NUM_THREADS=5
export OMP_NUM_THREADS=10
# export FI_PROVIDER=tcp
export MPLBACKEND='Agg'

APP_EXECUTABLE=${GEOPM_SRC}/test_integration/.libs/test_ee_stream_dgemm_spin_demo
APP_PARAMS=

APP_NAME=demo

# EE Agent
AGENT=energy_efficient
PROFILE=${APP_NAME}_ee
POLICY=${PROFILE}.json
geopmagent -a ${AGENT} -p nan,nan > ${POLICY}
geopmlaunch srun -n $((${RANKS_PER_NODE} * ${NUM_NODES})) -N ${NUM_NODES} \
    --geopm-agent=${AGENT} \
    --geopm-policy=${POLICY} \
    --geopm-profile=${PROFILE} \
    --geopm-report=${PROFILE}.report \
    --geopm-trace=${PROFILE}.trace \
    --geopm-trace-signals=MSR::PERF_CTL:FREQ@package,REGION_HASH@package \
    -- ${APP_EXECUTABLE} ${APP_PARAMS}

