#!/bin/bash
#SBATCH -N 1
#SBATCH -J dgemm
#SBATCH -t 24:00:00
#SBATCH -o %j_dgemm.out
#SBATCH --reservation test_ee

set -x

OUTDIR=$HOME/output/${SLURM_JOB_ID}_dgemm
mkdir -p $OUTDIR
cd $OUTDIR

NUM_NODES=$SLURM_NNODES
RANKS_PER_NODE=4
export OMP_NUM_THREADS=10
# RANKS_PER_NODE=2
# export OMP_NUM_THREADS=21

# echo "{\"loop-count\":500, \"region\": [\"dgemm\"], \"big-o\": [38.0]}" > dgemm.config
echo "{\"loop-count\":100, \"region\": [\"dgemm\"], \"big-o\": [18.0]}" > dgemm.config
APP_EXECUTABLE=geopmbench
APP_PARAMS=dgemm.config

export MPLBACKEND='Agg'

APP_NAME=dgemm
PROFILE_NAME=$APP_NAME

MIN_FREQ=$(printf "%.0f" $(geopmread FREQUENCY_MIN board 0))
MAX_FREQ=$(printf "%.0f" $(geopmread FREQUENCY_MAX board 0))
STICKER_FREQ=$(printf "%.0f" $(geopmread FREQUENCY_STICKER board 0))
STEP_FREQ=$(printf "%.0f" $(geopmread FREQUENCY_STEP board 0))

for iter in $(seq 0 0); do
for freq in $(seq $MIN_FREQ $STEP_FREQ $STICKER_FREQ) ${MAX_FREQ}; do
    AGENT=frequency_map
    PROFILE=${PROFILE_NAME}_freq_${freq}.0
    POLICY=${PROFILE}.json
    geopmagent -a ${AGENT} -p $freq,$freq > ${POLICY}
    # GEOPM_FREQUENCY_MAP='{"stream":2100000000, "dgemm": 3700000000}'\
    geopmlaunch srun -N $NUM_NODES -n $(($RANKS_PER_NODE * $NUM_NODES)) \
    --geopm-agent=${AGENT} \
    --geopm-policy=${POLICY} \
    --geopm-profile=${PROFILE} \
    --geopm-report=${PROFILE}_${iter}.report \
    --geopm-trace=${PROFILE}_${iter}.trace \
    -- $APP_EXECUTABLE $APP_PARAMS
done

AGENT=energy_efficient
PROFILE=${PROFILE_NAME}
POLICY=${PROFILE}.json
geopmagent -a ${AGENT} -p nan,nan > ${POLICY}
geopmlaunch srun -N $NUM_NODES -n $(($RANKS_PER_NODE * $NUM_NODES)) \
--geopm-agent=${AGENT} \
--geopm-policy=${POLICY} \
--geopm-profile=${PROFILE} \
--geopm-report=${PROFILE}_${iter}.report \
--geopm-trace=${PROFILE}_${iter}.trace \
-- $APP_EXECUTABLE $APP_PARAMS

done

