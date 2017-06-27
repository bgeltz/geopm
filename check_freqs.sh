#!/bin/bash

# START=${1}
# END=${2}
# STEP=${3}

START=135
END=190
STEP=5

# 4-node runs
# START_NODE=8
# END_NODE=11

# 12-node runs
START_NODE=1
END_NODE=12

echo "Unbalanced runs :"
echo "  (<THROTTLE_LINES> / <TOTAL_LINES>) "
for i in $(seq ${START} ${STEP} ${END}); do
    TOTAL_LINES=$(cat ${i}-*-unbalanced*trace* | wc -l)
    THROTTLE_LINES=$(awk -F '|' '{print $5}' ${i}*-unbalanced*trace* | grep "0\.5.*"| wc -l)
    echo "${i} - $(printf "%.3f %%" $(bc -l <<< "scale = 4; (${THROTTLE_LINES} / ${TOTAL_LINES}) * 10")) (${THROTTLE_LINES} / ${TOTAL_LINES})"

    for j in $(seq ${START_NODE} 1 ${END_NODE}); do
        TOTAL_LINES=$(cat ${i}-*-unbalanced*trace*mr-fusion${j} | wc -l)
        THROTTLE_LINES=$(awk -F '|' '{print $5}' ${i}*-unbalanced*trace*mr-fusion${j} | grep "0\.5.*"| wc -l)
        echo "    mr-fusion${j} - $(printf "%.3f %%" $(bc -l <<< "scale = 4; (${THROTTLE_LINES} / ${TOTAL_LINES}) * 10")) (${THROTTLE_LINES} / ${TOTAL_LINES})"
    done
done

echo "Balanced runs :"
for i in $(seq ${START} ${STEP} ${END}); do
    TOTAL_LINES=$(cat ${i}-*-balanced*trace* | wc -l)
    THROTTLE_LINES=$(awk -F '|' '{print $5}' ${i}*-balanced*trace* | grep "0\.5.*"| wc -l)
    echo "${i} - $(printf "%.3f %%" $(bc -l <<< "scale = 4; (${THROTTLE_LINES} / ${TOTAL_LINES}) * 10")) (${THROTTLE_LINES} / ${TOTAL_LINES})"

    for j in $(seq ${START_NODE} 1 ${END_NODE}); do
        TOTAL_LINES=$(cat ${i}-*-balanced*trace*mr-fusion${j} | wc -l)
        THROTTLE_LINES=$(awk -F '|' '{print $5}' ${i}*-balanced*trace*mr-fusion${j} | grep "0\.5.*"| wc -l)
        echo "    mr-fusion${j} - $(printf "%.3f %%" $(bc -l <<< "scale = 4; (${THROTTLE_LINES} / ${TOTAL_LINES}) * 10")) (${THROTTLE_LINES} / ${TOTAL_LINES})"
    done
done

# awk -F '|' '{print $5}' 120-1-balanced-fft-trace-it00.ftm.alcf.anl.gov | sort | uniq -c
