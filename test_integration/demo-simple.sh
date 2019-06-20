#!/bin/bash

TIMESTAMP=$(date +%F_%H%M)
GEOPM_SRC=${HOME}/geopm
OUTDIR=${HOME}/output/test_app_${TIMESTAMP}
mkdir -p ${OUTDIR}
cd ${OUTDIR}

# Capture stdout and stderr to log files
exec > >(tee -i demo.log)
exec 2> >(tee -i demoerr.out)

set -x

NUM_NODES=1
RANKS_PER_NODE=4
export OMP_NUM_THREADS=5   # Use all physical cores but leave 2 cores free on each socket
export FI_PROVIDER=tcp     # Set default interconnect for IMPI

APP_EXECUTABLE=${GEOPM_SRC}/test_integration/.libs/test_ee_stream_dgemm_spin_demo
APP_PARAMS=

APP_NAME=demo

# EE Agent
AGENT=energy_efficient
PROFILE=${APP_NAME}_ee
POLICY=${PROFILE}.json
geopmagent -a ${AGENT} -p nan,nan > ${POLICY}
geopmlaunch impi -n $((${RANKS_PER_NODE} * ${NUM_NODES})) -ppn ${RANKS_PER_NODE} \
    --geopm-agent=${AGENT} \
    --geopm-policy=${POLICY} \
    --geopm-profile=${PROFILE} \
    --geopm-report=${PROFILE}.report \
    --geopm-trace=${PROFILE}.trace \
    --geopm-trace-signals=MSR::PERF_CTL:FREQ@package,REGION_HASH@package \
    -- ${APP_EXECUTABLE} ${APP_PARAMS}

