#!/bin/bash

#set -e
#set -x

SRC_ROOT=${HOME}/p3_power_management-geopm
BIN_PATH=${HOME}/build/geopm/bin
NODES=2

# Save initial vals of all MSRs
srun -N${NODES} ${BIN_PATH}/geopmpolicy -s -f starting_msr_vals.conf
srun -N1 cp /tmp/starting_msr_vals.conf ${HOME}/tmp/initial_msr_vals/$(date +%F.%H:%M:%S).conf

# Create the policy config
#${BIN_PATH}/geopmpolicy -c -f ${SRC_ROOT}/brg_geopm_policy.conf -m dynamic -d power_budget:280,tree_decider:static_policy,leaf_decider:power_governing,platform:rapl
POLICY_PATH=${SRC_ROOT}/brg_test_policy.json
POLICY_STRING='{ "mode": "dynamic", "options": { "tree_decider": "static_policy", "leaf_decider": "power_governing", "platform": "rapl", "power_budget": 280 } }'

echo ${POLICY_STRING} >> ${POLICY_PATH}
# Override for testing
#POLICY_PATH=${SRC_ROOT}/test/default_policy.json

# DDT setup
#DDT='/opt/ohpc/pub/ddt/6.0.6/bin/ddt-client --ddtsessionfile /home/bgeltz/.allinea/session/mr-fusion0.prov-lab.net-1'
DDT=

# Run the program
#GEOPM_DEBUG_ATTACH=1 \
#GEOPM_REGION_BARRIER=true \
LD_LIBRARY_PATH=$HOME/build/geopm/lib:$LD_LIBRARY_PATH \
GEOPM_PMPI_CTL=process \
GEOPM_SHMKEY=/brg \
GEOPM_POLICY=${POLICY_PATH} \
GEOPM_TRACE="brg-nas-trace" \
GEOPM_REPORT="brg-nas-report" \
OMP_NUM_THREADS=8 \
\
srun -N${NODES} -n16 --cpu_bind=v,mask_cpu:0xFC,0xFF00,0xFF0000,0xFF000000,0xFF00000000,0xFF0000000000,0xFF000000000000,0xFF00000000000000,0xFF0000000000000000 ${DDT} ${SRC_ROOT}/examples/fft/.libs/nas_ft
#srun -N4 -n20 --cpu_bind=v,mask_cpu:0x100000000000000000000,0xFFFF,0xFFFF0000,0xFFFF00000000,0xFFFF000000000000	${SRC_ROOT}/examples/fft/.libs/nas_ft

# Restore initial vals of all MSRs
srun -N${NODES} ${BIN_PATH}/geopmpolicy -r -f /tmp/starting_msr_vals.conf
