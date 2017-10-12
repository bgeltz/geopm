#!/bin/bash

# set -x
# set -e

NODE_LIST=it00,it06,it07,it12
NUM_NODE=4

APP_RANKS_PER_NODE=2
NUM_CORE=43 # App CPU's per rank : APP_RANKS_PER_NODE * NUM_CORE <= Total number of available cores - 1

# APP_RANKS_PER_NODE=1
# NUM_CORE=86 # App CPU's per rank : APP_RANKS_PER_NODE * NUM_CORE <= Total number of available cores - 1

NUM_RANK=$((${NUM_NODE} * ${APP_RANKS_PER_NODE})) # Total ranks!! Will be evenly split between nodes.

SRC_DIR=${HOME}/apps/miniFE_openmp-2.0-rc3/src
PROFILE_NAME=${1:-BDX_TEST_RUN}
OUTPUT_DIR=minife-${NUM_NODE}-node-${PROFILE_NAME}-$(date +%F_%H%M)
MSR_FILE=.$(hostname -s).$(date +%F_%H%M).msrs

if [ ! -d "${OUTPUT_DIR}" ]; then
    mkdir ${OUTPUT_DIR}
fi

pushd ${OUTPUT_DIR}

# Redirect stdout and stderr to an output file
exec > >(tee -i stdouterr.txt)
exec 2>&1

echo "Output will be saved in ${OUTPUT_DIR}/."

create_policy(){
    NAME=${1:-"generic"}
    TREE_DECIDER=${2:-"static_policy"}
    LEAF_DECIDER=${3:-"power_governing"}
    PWR_LIMIT=290

    if [ ! -f ${NAME}_policy.json ]; then
        echo -ne "Making ${NAME}_policy.json..."
        echo {\"mode\": \"dynamic\",\
              \"options\": {\
                  \"tree_decider\": \"${TREE_DECIDER}\",\
                  \"leaf_decider\": \"${LEAF_DECIDER}\",\
                  \"platform\": \"rapl\",\
                  \"power_budget\": ${PWR_LIMIT} }\
              } > ${NAME}_policy.json
        echo -ne " Done.\n"
    fi
}

print_hr(){
    printf "%.0s${1}" {1..80} && echo
}

init(){
    msrsave ${MSR_FILE}

    # Use rdmsr to examine IA32_PERF_CTL 0x199
    print_hr !
    echo "init() - Unique frequency values from IA32_PERF_CTL - 0x199:"
    pdsh -w ${NODE_LIST} "${HOME}/build/msr-tools/bin/rdmsr 0x199 -af 15:0 | cut -f2 -d':' | sort -u | uniq"
    print_hr !

    # Force parts to max non-turbo (sticker)
    pdsh -w ${NODE_LIST} "${HOME}/build/msr-tools/bin/wrmsr -a 0x199 0x1600"
    # Force these parts into the turbo range before the run.
    # pdsh -w ${NODE_LIST} "${HOME}/build/msr-tools/bin/wrmsr -a 0x199 0x1700"
}

cleanup(){
    print_hr !
    echo "cleanup() before restore - Unique frequency values from IA32_PERF_CTL - 0x199:"
    pdsh -w ${NODE_LIST} "${HOME}/build/msr-tools/bin/rdmsr 0x199 -af 15:0 | cut -f2 -d':' | sort -u | uniq"
    print_hr !

    msrsave -r ${MSR_FILE} > /dev/null

    print_hr !
    echo "cleanup() after restore - Unique frequency values from IA32_PERF_CTL - 0x199:"
    pdsh -w ${NODE_LIST} "${HOME}/build/msr-tools/bin/rdmsr 0x199 -af 15:0 | cut -f2 -d':' | sort -u | uniq"
    print_hr !
}

run_app(){

    init

    PPN=$(( NUM_RANK / NUM_NODE + 1)) # FIXME +1 HACK to workaround launcher bug
    CONFIG=${1:-"baseline"}
    NX=${2:-264}
    NY=${3:-256}
    NZ=${4:-256}
    MIN_FREQ=${5:-1300000000}
    # MAX_FREQ=${6:-2300000000} # Turbo range
    MAX_FREQ=${6:-2200000000} # Max non-turbo

    print_hr -
    echo "Running ${CONFIG} config..."
    print_hr -

    GEOPM_SIMPLE_FREQ_MIN=${MIN_FREQ} \
    GEOPM_SIMPLE_FREQ_MAX=${MAX_FREQ} \
    LD_LIBRARY_PATH=${HOME}/build/geopm/lib:${LD_LIBRARY_PATH} \
    GEOPM_REGION_BARRIER=true \
    OMP_NUM_THREADS=${NUM_CORE} \
    GEOPM_RM="IMPI" \
    ${HOME}/build/geopm/bin/geopmsrun \
    --geopm-ctl=process \
    --geopm-policy=${CONFIG}_policy.json \
    --geopm-report=${CONFIG}-minife.report \
    --geopm-trace=${CONFIG}-minife-trace \
    --geopm-profile=${PROFILE_NAME}-${MIN_FREQ} \
    -n ${NUM_RANK} \
    -ppn ${PPN} \
    --hosts ${NODE_LIST} \
    ${SRC_DIR}/miniFE.x nx=${NX} ny=${NY} nz=${NZ}
    # ${SRC_DIR}/miniFE.x nx=${NX} ny=${NY} nz=${NZ} verify_solution=1

    cleanup
}

# Source the startup script to set the path to the Intel toolchain and
# set up the whitelist.
source ${HOME}/startup

# Setup baseline config
create_policy baseline

# Setup SimpleFreq config
create_policy ee static_policy simple_freq

# Small problem size per the MiniFE Summary v2.0 PDF on the CORAL workloads site
# NX=264
# NY=256
# NZ=256

# NX=462
# NY=448
# NZ=448

NX=528 # Runs OK on 4 nodes.
NY=512
NZ=512

# run_app baseline 693 672 672 # Way too big!  Crashes node.
# run_app baseline 660 640 640 # Takes 10-20 minutes per run, sometimes hangs for a long time

# Do the runs
run_app baseline ${NX} ${NY} ${NZ}
run_app ee ${NX} ${NY} ${NZ}

popd

# Analyze the output data
./analyze_minife.py ${OUTPUT_DIR} | tee -a ${OUTPUT_DIR}/stats.txt
# Remove DOS line endings
awk 'BEGIN{RS="^$";ORS="";getline;gsub("\r","");print>ARGV[1]}' ${OUTPUT_DIR}/stats.txt
