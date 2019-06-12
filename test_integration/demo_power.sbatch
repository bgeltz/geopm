#!/bin/bash
#SBATCH -N 2
#SBATCH -J demo_balancer
#SBATCH -t 24:00:00
#SBATCH -o %j_dgemm.out

TIMESTAMP=$(date +%F_%H%M)
GEOPM_SRC=${HOME}/geopm
OUTDIR=./test_app_${SLURM_JOB_ID}_${TIMESTAMP}
mkdir -p ${OUTDIR}
cd ${OUTDIR}

set -x

NUM_NODES=2
RANKS_PER_NODE=4  #TODO hardcoded imbalance in source code depends on this value
export OMP_NUM_THREADS=10
export MPLBACKEND='Agg'

APP_EXECUTABLE=${GEOPM_SRC}/test_integration/.libs/test_ee_stream_dgemm_spin_demo
APP_PARAMS="--imbalance"

APP_NAME=demo
export TEST_ITERATIONS=200

for iter in $(seq 0 0); do
    POWER_CAP=170

    AGENT=power_governor
    PROFILE=${APP_NAME}_gov_${POWER_CAP}.0
    POLICY=${PROFILE}.json
    geopmagent -a power_governor -p $POWER_CAP > ${POLICY}
    geopmlaunch srun -n $(($RANKS_PER_NODE * $NUM_NODES)) -N $NUM_NODES \
        --geopm-agent=${AGENT} \
        --geopm-policy=${POLICY} \
        --geopm-profile=${PROFILE} \
        --geopm-report=${PROFILE}_${iter}.report \
        --geopm-trace=${PROFILE}_${iter}.trace \
        -- $APP_EXECUTABLE $APP_PARAMS

    AGENT=power_balancer
    PROFILE=${APP_NAME}_bal_${POWER_CAP}.0
    POLICY=${PROFILE}.json
    geopmagent -a power_balancer -p $POWER_CAP,NAN,NAN,NAN > ${POLICY}
    geopmlaunch srun -n $(($RANKS_PER_NODE * $NUM_NODES)) -N $NUM_NODES \
        --geopm-agent=${AGENT} \
        --geopm-policy=${POLICY} \
        --geopm-profile=${PROFILE} \
        --geopm-report=${PROFILE}_${iter}.report \
        --geopm-trace=${PROFILE}_${iter}.trace \
        -- $APP_EXECUTABLE $APP_PARAMS

done
