#!/bin/bash
#  Copyright (c) 2015 - 2024 Intel Corporation
#  SPDX-License-Identifier: BSD-3-Clause
#

mkdir -p ${TMPDIR}

INPUT_FILE=$(mktemp)
cat > ${INPUT_FILE} << "EOF"
{
    "loop-count": 50,
    "region": ["stream", "dgemm"],
    "big-o": [3.0, 30.0]
}
EOF

TEST_NAME=test_multi_app
export GEOPM_PROFILE=${TEST_NAME}
export GEOPM_PROGRAM_FILTER=geopmbench,stress-ng
export LD_PRELOAD=libgeopm.so.2.1.0

export SYSTEMD_BUS_TIMEOUT=600

GEOPM_REPORT=${TEST_NAME}_report.yaml \
GEOPM_REPORT_SIGNALS=TIME@package \
GEOPM_NUM_PROC=2 \
setsid geopmctl &

# Some of the initialization regions of geopmbench finish quickly. The
# test_multi_app.py test checks the execution time of all regions. This sleep
# ensures that geopmctl is started before starting geopmbench.
sleep 2

echo "$(hostname) starting..."
# geopmbench
export GEOPMBENCH_NO_MPI=1
/usr/bin/timeout -v -k 30s 18m numactl --cpunodebind=0 -- /usr/bin/timeout -v -k 30s 15m geopmbench ${INPUT_FILE} &

# stress-ng
export LD_PRELOAD=libgeopm.so.2.1.0
numactl --cpunodebind=1 -- stress-ng --cpu 1 --timeout 120 &

wait
rm ${INPUT_FILE}
echo "$(hostname) complete"
