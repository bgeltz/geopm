#!/bin/bash

LD_LIBRARY_PATH=$HOME/build/geopm/lib:$LD_LIBRARY_PATH \
GEOPM_POLICY=$HOME/repos/geopm/test/default_policy.json \
GEOPM_TRACE="brg-controller-trace" \
srun -n 1 -ppn 1 geopmctl
