#!/bin/bash

set -e

min_power=$(rdmsr --decimal --bitfield 30:16 0x614)
max_power=$(rdmsr --decimal --bitfield 46:32 0x614)
tdp_power=$(rdmsr --decimal --bitfield 14:0 0x614)

min_power=$((${min_power} / 8))
max_power=$((${max_power} / 8))
tdp_power=$((${tdp_power} / 8))

echo "Min power = ${min_power} W"
echo "Max power = ${max_power} W"
echo "TDP power = ${tdp_power} W"
