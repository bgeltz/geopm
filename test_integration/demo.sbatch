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

# Capture stdout and stderr to log files
# exec > >(tee -i demo.log)
# exec 2> >(tee -i demoerr.out)

set -x

NUM_NODES=1
RANKS_PER_NODE=4
# export OMP_NUM_THREADS=5
export OMP_NUM_THREADS=10
# export FI_PROVIDER=tcp
export MPLBACKEND='Agg'

APP_EXECUTABLE=${GEOPM_SRC}/test_integration/.libs/test_ee_stream_dgemm_spin
APP_PARAMS=-v

APP_NAME=demo

MIN_FREQ=$(printf "%.0f" $(geopmread FREQUENCY_MIN board 0))
MAX_FREQ=$(printf "%.0f" $(geopmread FREQUENCY_MAX board 0))
STICKER_FREQ=$(printf "%.0f" $(geopmread FREQUENCY_STICKER board 0))
STEP_FREQ=$(printf "%.0f" $(geopmread FREQUENCY_STEP board 0))

ITERATIONS=0

for iter in $(seq 0 ${ITERATIONS}); do
    # Frequency sweep
    for freq in $(seq $MIN_FREQ $STEP_FREQ $STICKER_FREQ) ${MAX_FREQ}; do
        AGENT=frequency_map
        PROFILE=${APP_NAME}_freq_${freq}.0
        POLICY=${PROFILE}.json
        geopmagent -a ${AGENT} -p $freq,$freq > ${POLICY}
        geopmlaunch srun -n $(($RANKS_PER_NODE * $NUM_NODES)) -N $NUM_NODES \
            --geopm-agent=${AGENT} \
            --geopm-policy=${POLICY} \
            --geopm-profile=${PROFILE} \
            --geopm-report=${PROFILE}_${iter}.report \
            --geopm-trace=${PROFILE}_${iter}.trace \
            -- $APP_EXECUTABLE $APP_PARAMS
    done
done

for iter in $(seq 0 ${ITERATIONS}); do
    # Best-fit frequencies as determined by sweep
    AGENT=frequency_map
    PROFILE=${APP_NAME}_fm_best_fit
    POLICY=${PROFILE}.json
    geopmagent -a ${AGENT} -p nan,nan > ${POLICY}
    ../analyze.py --profile-name demo --verbose
    export GEOPM_FREQUENCY_MAP=$(../analyze.py --profile-name demo | tail -n1)
    geopmlaunch srun -n $(($RANKS_PER_NODE * $NUM_NODES)) -N $NUM_NODES \
        --geopm-agent=${AGENT} \
        --geopm-policy=${POLICY} \
        --geopm-profile=${PROFILE} \
        --geopm-report=${PROFILE}_${iter}.report \
        --geopm-trace=${PROFILE}_${iter}.trace \
        -- $APP_EXECUTABLE $APP_PARAMS
done

for iter in $(seq 0 ${ITERATIONS}); do
    # EE Agent
    AGENT=energy_efficient
    PROFILE=${APP_NAME}_ee
    POLICY=${PROFILE}.json
    geopmagent -a ${AGENT} -p nan,nan > ${POLICY}
    export TEST_ITERATIONS=200
    geopmlaunch srun -n $(($RANKS_PER_NODE * $NUM_NODES)) -N $NUM_NODES \
        --geopm-agent=${AGENT} \
        --geopm-policy=${POLICY} \
        --geopm-profile=${PROFILE} \
        --geopm-report=${PROFILE}_${iter}.report \
        --geopm-trace=${PROFILE}_${iter}.trace \
        --geopm-trace-signals=MSR::PERF_CTL:FREQ@package,REGION_HASH@package \
        -- $APP_EXECUTABLE $APP_PARAMS
done
