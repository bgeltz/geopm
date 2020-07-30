#!/usr/bin/env python
#
#  Copyright (c) 2015, 2016, 2017, 2018, 2019, 2020, Intel Corporation
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#      * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#      * Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in
#        the documentation and/or other materials provided with the
#        distribution.
#
#      * Neither the name of Intel Corporation nor the names of its
#        contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY LOG OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import sys
import os
import time
import pandas
import math

import geopmpy.io

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from integration import util
from integration.experiment import common_args


def setup_power_bounds(min_power, max_power, step_power):
    sys_power = util.sys_power_avail()
    if min_power is None or min_power < sys_power['min_power']:
        # system minimum is actually too low; use 50% of TDP or min rounded up to nearest step, whichever is larger
        min_power = max(int(0.5 * sys_power['tdp_power']), sys_power['min_power'])
        min_power = int(step_power * math.ceil(float(min_power)/step_power))
        sys.stderr.write("Warning: <geopm> run_power_sweep: Invalid or unspecified min_power; using default minimum: {}.\n".format(min_power))
    if max_power is None or max_power > sys_power['max_power']:
        max_power = int(sys_power['tdp_power'])
        sys.stderr.write("Warning: <geopm> run_power_sweep: Invalid or unspecified max_power; using system TDP: {}.\n".format(max_power))
    return min_power, max_power


def launch_power_sweep(file_prefix, machine_config, output_dir, iterations,
                       min_power, max_power, step_power, agent_types,
                       num_node, num_rank, app_conf):
    """
    Runs the application under a range of socket power limits.  Used
    by other analysis types to run either the PowerGovernorAgent or
    the PowerBalancerAgent.
    """
    name = file_prefix + "_power_sweep"

    # create machine config
    util.save_machine_config(machine_config)

    # report extensions
    report_sig = ["CYCLES_THREAD@package", "CYCLES_REFERENCE@package",
                  "TIME@package", "ENERGY_PACKAGE@package"]
    # trace extensions
    trace_sig = ["MSR::PKG_POWER_LIMIT:PL1_POWER_LIMIT@package",
                 "EPOCH_RUNTIME@package",
                 "EPOCH_RUNTIME_NETWORK@package",
                 "EPOCH_RUNTIME_IGNORE@package",
                 "TEMPERATURE_PACKAGE@package"]

    for iteration in range(iterations):
        for power_cap in range(min_power, max_power+1, step_power):
            for agent in agent_types:
                options = {'power_budget': power_cap}
                # TODO: check for valid agent type; this should be reusable between all agent types

                config_file = os.path.join(output_dir, name + '_agent.config')
                agent_conf = geopmpy.io.AgentConf(path=config_file,
                                                  agent=agent,
                                                  options=options)
                agent_conf.write()

                uid = '{}_{}_{}_{}'.format(name, agent, power_cap, iteration)
                report_path = os.path.join(output_dir, '{}.report'.format(uid))
                trace_path = os.path.join(output_dir, '{}.trace'.format(uid))
                profile_name = 'iteration_{}'.format(iteration)

                # TODO: these are not passed to launcher create()
                # some are generic enough they could be, though
                run_args = ['--geopm-report', report_path,
                            '--geopm-trace', trace_path,
                            '--geopm-profile', profile_name,
                            '--geopm-report-signals=' + ','.join(report_sig),
                            '--geopm-trace-signals=' + ','.join(trace_sig)]
                # any arguments after run_args are passed directly to launcher
                util.try_launch(agent_conf, app_conf, run_args,
                                num_node=num_node, num_rank=num_rank)  # raw launcher factory args

                # rest to cool off between runs
                time.sleep(60)


def summary(parse_output):
    # rename some columns
    parse_output['power_limit'] = parse_output['POWER_PACKAGE_LIMIT_TOTAL']
    parse_output['runtime'] = parse_output['runtime (sec)']
    parse_output['network_time'] = parse_output['network-time (sec)']
    parse_output['energy_pkg'] = parse_output['package-energy (joules)']
    parse_output['energy_dram'] = parse_output['dram-energy (joules)']
    parse_output['frequency'] = parse_output['frequency (Hz)']
    parse_output['iteration'] = parse_output.apply(lambda row: row['Profile'].split('_')[-1],
                                                   axis=1)
    # set up index for grouping
    parse_output = parse_output.set_index(['Agent', 'host', 'power_limit'])
    summary = pandas.DataFrame()
    for col in ['count', 'runtime', 'network_time', 'energy_pkg', 'energy_dram', 'frequency']:
        summary[col] = parse_output[col].groupby(['Agent', 'power_limit']).mean()
    return summary


if __name__ == '__main__':
    aargs = common_args.ExperimentAnalysisArgs()
    output_dir = aargs.args

    output = geopmpy.io.RawReportCollection("*report", dir_name=output_dir)
    result = summary(output.get_epoch_df())

    sys.stdout.write('{}\n'.format(result))
