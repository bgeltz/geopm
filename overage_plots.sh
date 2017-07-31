#!/bin/bash

JOBID=$(basename $(pwd))
NODEID=nid00011

START=${1}
END=${2}
STEP=${3}

# Make the initial plots
for i in $(seq ${START} -${STEP} ${END}); do
    pushd ${i}
    MPLBACKEND='Agg' analyze.py test_power_consumption.trace-${NODEID} ${i} power_test
    MPLBACKEND='Agg' geopmplotter --tgt_plugin static_policy --analyze -vcp freq --base_clock 1.3
    MPLBACKEND='Agg' geopmplotter --tgt_plugin static_policy --analyze -vcp freq --base_clock 1.3 --epoch_only
    popd
done

# Open plots in Chrome
for i in $(seq ${START} -${STEP} ${END}); do
    google-chrome http://kronos.ra.intel.com/~bgeltz/theta/${JOBID}/${i}/power_test_power_balanced_${i}W_5ms_${NODEID}_line.svg 2> /dev/null
done

# Print links for email
for i in $(seq ${START} -${STEP} ${END}); do
    echo "${i} W:"
    echo "http://kronos.ra.intel.com/~bgeltz/theta/${JOBID}/${i}/power_test_power_balanced_${i}W_5ms_${NODEID}_line.svg"
    echo "http://kronos.ra.intel.com/~bgeltz/theta/${JOBID}/${i}/figures/test_power_consumption_frequency_${i}_static_policy_socket_0_epoch_only.svg"
    echo "http://kronos.ra.intel.com/~bgeltz/theta/${JOBID}/${i}/figures/test_power_consumption_frequency_${i}_static_policy_socket_0_all_samples.svg"
    echo
done
