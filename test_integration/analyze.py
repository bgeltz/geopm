#!/usr/bin/env python

# To import these, you may need to add $GEOPM_SOURCE/scripts to your PYTHONPATH
import geopmpy.analysis
import geopmpy.io
import sys 
import argparse
import os

# Note: this script assumes you have run a frequency sweep such that the
# report files are named with the following pattern:
#    ${PROFILE_NAME}_freq_${FREQ}.0_${ITERATION}.report
# An example script to generate these reports could look like:
#
# for iter in $(seq 0 $MAX_ITER); do
#     for freq in $(seq $MIN_FREQ $STEP_FREQ $STICKER_FREQ) $MAX_FREQ; do
#         geopmagent -a energy_efficient -p $freq,$freq > ${PROFILE_NAME}_freq_${freq}.json
#         geopmlaunch srun -N $NUM_NODES -n $(($RANKS_PER_NODE * $NUM_NODES)) \
#             --geopm-agent=energy_efficient \
#             --geopm-policy=${PROFILE_NAME}_freq_${freq}.json \
#             --geopm-profile=${PROFILE_NAME}_freq_${freq} \
#             --geopm-report=${PROFILE_NAME}_freq_${freq}.0_${iter}.report \
#             -- $APP_EXECUTABLE $APP_PARAMS
# done
#

parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
parser.add_argument('--profile-name', dest='profile_name', required=True)
parser.add_argument('--iterations', dest='iterations',
                    action='store', default=1, type=int)
parser.add_argument('--output-dir', dest='output_dir',
                    action='store', default='.')
parser.add_argument('--verbose', dest='verbose',
                    action='store_true', default=False)
parser.add_argument('--enable-turbo', dest='enable_turbo',
                    action='store_true', default=False)

args = parser.parse_args()

ctor_args = { 
    'profile_prefix': args.profile_name,
    'output_dir': args.output_dir,
    'verbose': args.verbose,
    'iterations': args.iterations,
    'min_freq': None,
    'max_freq': None,
    'enable_turbo': args.enable_turbo
}

analysis = geopmpy.analysis.FreqSweepAnalysis(**ctor_args)
analysis.find_files()
parse_output = analysis.parse()

# print out best fit frequencies from sweep
process_output = analysis.summary_process(parse_output)
if args.verbose:
    analysis.summary(process_output)
best_fit_freqs = analysis._region_freq_map(parse_output)
print str(best_fit_freqs).replace("'", '"') # Quotes hack to prevent bash from auto escaping single quotes
