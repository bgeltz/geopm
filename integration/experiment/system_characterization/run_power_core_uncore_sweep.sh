#!/bin/bash
set -ex

source ~/.geopmrc
RUN_DIR=${RUN_DIR?-Set RUN_DIR to the location of run_mpiexec.sh}
GEOPM_SOURCE=${GEOPM_SOURCE?-Set GEOPM_SOURCE to the location of geopm source code}
source ${GEOPM_SOURCE}/integration/config/run_env.sh

NUM_NODE=$(wc -l ${PBS_NODEFILE} | cut -d\  -f1)
PROFILE_NAME=nekbone
EXPERIMENT_NAME=${PROFILE_NAME}-geopm-power-core-uncore-sweep
TRIAL_COUNT=${TRIAL_COUNT:-5}
MIN_POWER=${MIN_POWER:-2400}
MAX_POWER=${MAX_POWER:-4000}
POWER_STEP=${POWER_STEP:-100}
SWEEP_OUTPUT_DIR=${SWEEP_OUTPUT_DIR:-${RUN_DIR}/power_cpu_core_uncore_sweep}

# CPU frequency sweep params (core and uncore)
CORE_MIN_FREQ=$(geopmread CPU_FREQUENCY_MIN_AVAIL board 0)
CORE_MAX_FREQ=$(geopmread CPU_FREQUENCY_MAX_AVAIL board 0)
CORE_FREQ_STEP=$(geopmread CPU_FREQUENCY_STEP board 0)
UNCORE_MIN_FREQ=$(geopmread CPU_UNCORE_FREQUENCY_MIN_CONTROL board 0)
UNCORE_MAX_FREQ=$(geopmread CPU_UNCORE_FREQUENCY_MAX_CONTROL board 0)
UNCORE_FREQ_STEP=$(geopmread CPU_FREQUENCY_STEP board 0)

# GPU frequency sweep params
GPU_CORE_MIN_FREQ=$(geopmread GPU_CORE_FREQUENCY_MIN_AVAIL board 0)
GPU_CORE_MAX_FREQ=$(geopmread GPU_CORE_FREQUENCY_MAX_AVAIL board 0)
GPU_CORE_FREQ_STEP=$(geopmread GPU_CORE_FREQUENCY_STEP board 0)

cd ${RUN_DIR}
mkdir -p ${SWEEP_OUTPUT_DIR}
echo "Writing logs and reports to ${SWEEP_OUTPUT_DIR}"
for ((p=${MIN_POWER}; p<=${MAX_POWER}; p=p+${POWER_STEP})); do
    for ((c=${CORE_MIN_FREQ}; c<=${CORE_MAX_FREQ}; c=c+${CORE_FREQ_STEP})); do
        for ((u=${UNCORE_MIN_FREQ}; u<=${UNCORE_MAX_FREQ}; u=u+${UNCORE_FREQ_STEP})); do
            for ((t=0; t<${TRIAL_COUNT}; t++)); do

                echo "================= Trial $t, $p W power cap , $c CPU core freq, $u CPU uncore freq ================="

                # TODO Move all the init control manipulation to here
                TMPFILE=/tmp/sweep_controls_${p}.txt
                echo "MSR::PLATFORM_POWER_LIMIT:PL1_POWER_LIMIT board 0 ${p}" > ${TMPFILE}
                echo "MSR::PLATFORM_POWER_LIMIT:PL1_TIME_WINDOW board 0 0.013" >> ${TMPFILE}
                echo "MSR::PLATFORM_POWER_LIMIT:PL1_LIMIT_ENABLE board 0 1" >> ${TMPFILE}
                echo "MSR::PLATFORM_POWER_LIMIT:PL1_CLAMP_ENABLE board 0 1" >> ${TMPFILE}

                # MEM B/W Monitoring
                echo "MSR::PQR_ASSOC:RMID board 0 0" >> ${TMPFILE}
                echo "MSR::QM_EVTSEL:RMID board 0 0" >> ${TMPFILE}
                echo "MSR::QM_EVTSEL:EVENT_ID board 0 2" >> ${TMPFILE}

                echo "CPU_FREQUENCY_MIN_CONTROL board 0 ${c}" >> ${TMPFILE}
                echo "CPU_FREQUENCY_MAX_CONTROL board 0 ${c}" >> ${TMPFILE}
                echo "CPU_UNCORE_FREQUENCY_MIN_CONTROL board 0 ${u}" >> ${TMPFILE}
                echo "CPU_UNCORE_FREQUENCY_MAX_CONTROL board 0 ${u}" >> ${TMPFILE}


                EXTRA_SIGNALS="BOARD_POWER@board,BOARD_POWER_LIMIT_CONTROL@board,BOARD_ENERGY@board"
                # CPU sweep extra signals
                EXTRA_SIGNALS+=",MSR::QM_CTR_SCALED_RATE@package,CPU_UNCORE_FREQUENCY_STATUS@package,MSR::CPU_SCALABILITY_RATIO@package,CPU_FREQUENCY_MIN_CONTROL@package,CPU_UNCORE_FREQUENCY_MIN_CONTROL@package"
                # GPU sweep extra signals
                EXTRA_SIGNALS+=",GPU_CORE_FREQUENCY_STATUS@board,GPU_CORE_FREQUENCY_MIN_CONTROL@board"

                OUTPUT_BASENAME=${EXPERIMENT_NAME}_p${p}_c${c}_u${u}_t${t}

                export GEOPM_PROFILE=${PROFILE_NAME}
                export GEOPM_PROGRAM_FILTER=nekbone
                export GEOPM_NUM_PROC=12
                export GEOPM_REPORT=${SWEEP_OUTPUT_DIR}/${OUTPUT_BASENAME}.report
                export GEOPM_REPORT_SIGNALS=${EXTRA_SIGNALS}
                export GEOPM_INIT_CONTROL=/tmp/sweep_controls_${p}.txt
                mpiexec -n ${NUM_NODE} -ppn 1 geopmctl &

                # geopmlaunch pals \
                #     -n 1 -ppn 1 \
                #     --geopm-init-control=/tmp/sweep_controls_${p}.txt \
                #     --geopm-ctl=application \
                #     --geopm-preload \
                #     --geopm-profile=${PROFILE_NAME} \
                #     --geopm-report=${SWEEP_OUTPUT_DIR}/${OUTPUT_BASENAME}.report \
                #     --geopm-report-signals=${EXTRA_SIGNALS} \
                #     --geopm-program-filter=nekbone \
                #     -- ./run_mpiexec.sh -n=${NUM_NODE} -rpn=12 --ranks_per_socket=6 2>&1 \
                #     > ${SWEEP_OUTPUT_DIR}/${OUTPUT_BASENAME}.log

                export LD_PRELOAD=libgeopm.so.2.2.0
                ./run_mpiexec.sh -n=${NUM_NODE} -rpn=12 --ranks_per_socket=6 2>&1 \
                    > ${SWEEP_OUTPUT_DIR}/${OUTPUT_BASENAME}.log
                unset LD_PRELOAD

                sleep 5

                # Extract the figure of merit from the app log into the GEOPM report
                # For solve time:
                awk '/Solve Time/{sum+=$NF} END{printf "Figure of Merit: %f\n", sum}' \
                    ${SWEEP_OUTPUT_DIR}/${OUTPUT_BASENAME}.log \
                    >> "${SWEEP_OUTPUT_DIR}/${OUTPUT_BASENAME}.report"

                # For Av MFlops:
                # awk '/^Av MFlops = / {print "Figure of Merit: " $4}' \
                #     ${SWEEP_OUTPUT_DIR}/${OUTPUT_BASENAME}.log \
                #     >> ${SWEEP_OUTPUT_DIR}/${OUTPUT_BASENAME}.report

                sleep 45
            done
        done
    done
done
