#!/bin/bash
#SBATCH -J nekbone
#SBATCH -o %j.nekbone.out
#SBATCH -N 1
#SBATCH -t 1:00:00

source ${HOME}/.geopmrc
source ${GEOPM_SRC}/integration/env_run.sh

OUTPUT_DIR=${GEOPM_WORKDIR}/output/${SLURM_JOB_NAME}_${SLURM_JOBID}
EXP_DIR=monitor
EXP_TYPE=monitor
APP=nekbone

./${EXP_DIR}/run_${EXP_TYPE}_${APP}.py \
    --nodes=$SLURM_NNODES \
    --output-dir=${OUTPUT_DIR} \
    # end

