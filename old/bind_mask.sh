#!/bin/bash

# MASK_STR="srun --cpu_bind=v,mask_cpu:0xFC,0xFFFF00,0xFFFF000000,0xFFFF0000000000,0xFFF00000000000000 -N2"
MASK_STR="srun --cpu_bind=v,mask_cpu:0x2,0x1FFFC,,0xFFFE0000,0x7FFF00000000,0x3FFF800000000000 -N2"

echo ${MASK_STR}
export MPIEXEC=${MASK_STR}
