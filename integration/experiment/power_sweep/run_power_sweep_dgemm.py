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

'''
Example power sweep experiment using geopmbench.
'''

import sys
import os
import math
import pandas
import glob
import argparse

import geopmpy.io

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from integration.util import sys_power_avail
from integration.experiment import common_args, power_sweep


if __name__ == '__main__':
    largs = common_args.ExperimentLaunchArgs()
    if largs.do_help:
        sys.exit(0)

    skip_launch = largs.args.skip_launch
    output_dir = largs.args.output_dir
    num_nodes = largs.args.nodes
    machine_info = os.path.join(output_dir, largs.args.machine_config)

    if not skip_launch:
        # create output dir
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        # application parameters
        app_name = 'dgemm'
        app_conf = geopmpy.io.BenchConf(path=os.path.join(output_dir, 'dgemm.conf'))
        app_conf.append_region('dgemm', 8.0)
        app_conf.set_loop_count(500)
        app_conf.write()
        rank_per_node = 2

        # experiment parameters
        # TODO: can dynamically choose whole range with
        # setup_power_bounds(None, None), or add command line options
        step_power = 10
        min_power, max_power = power_sweep.setup_power_bounds(180, 190, step_power)
        iterations = 2
        power_sweep.launch_power_sweep(file_prefix=app_name,
                                       machine_config=machine_info,
                                       output_dir=output_dir,
                                       iterations=iterations,
                                       min_power=min_power,
                                       max_power=max_power,
                                       step_power=step_power,
                                       agent_types=['power_governor', 'power_balancer'],
                                       num_node=num_nodes,
                                       num_rank=num_nodes*rank_per_node,
                                       app_conf=app_conf)

    output = geopmpy.io.RawReportCollection("*report", dir_name=output_dir)
    result = power_sweep.summary(output.get_epoch_df())

    sys.stdout.write('{}\n'.format(result))
