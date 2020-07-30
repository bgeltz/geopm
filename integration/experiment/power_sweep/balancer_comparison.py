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
from integration import util
from integration.experiment import common_args


def plot_process(self, parse_output):
    parse_output.extract_index_from_profile(inplace=True)
    df = pandas.DataFrame()
    reference = 'power_governor'
    target = 'power_balancer'
    # TODO: have a separate power analysis?
    ref_epoch_data = parse_output.get_report_data(profile=(self._min_power, self._max_power),
                                                  agent=reference,
                                                  region='epoch')
    if self._metric == 'power':
        rge = ref_epoch_data['energy_pkg']
        rgr = ref_epoch_data['runtime']
        reference_g = (rge / rgr).groupby(level='name')
    else:
        reference_g = ref_epoch_data[self._metric].groupby(level='name')

    df['reference_mean'] = reference_g.mean()
    df['reference_max'] = reference_g.max()
    df['reference_min'] = reference_g.min()

    tar_epoch_data = parse_output.get_report_data(profile=(self._min_power, self._max_power),
                                                  agent=target,
                                                  region='epoch')
    if self._metric == 'power':
        tge = tar_epoch_data['energy_pkg']
        tgr = tar_epoch_data['runtime']
        target_g = (tge / tgr).groupby(level='name')
    else:
        target_g = tar_epoch_data[self._metric].groupby(level='name')

    df['target_mean'] = target_g.mean()
    df['target_max'] = target_g.max()
    df['target_min'] = target_g.min()

    if self._normalize and not self._speedup:  # Normalize the data against the rightmost reference bar
        df /= df['reference_mean'].iloc[-1]

    if self._speedup:  # Plot the inverse of the target data to show speedup as a positive change
        df = df.div(df['reference_mean'], axis='rows')
        df['target_mean'] = 1 / df['target_mean']
        df['target_max'] = 1 / df['target_max']
        df['target_min'] = 1 / df['target_min']

    # Convert the maxes and mins to be deltas from the mean; required for the errorbar API
    df['reference_max_delta'] = df['reference_max'] - df['reference_mean']
    df['reference_min_delta'] = df['reference_mean'] - df['reference_min']
    df['target_max_delta'] = df['target_max'] - df['target_mean']
    df['target_min_delta'] = df['target_mean'] - df['target_min']

    return df

def plot(self, process_output):
    config = geopmpy.plotter.ReportConfig(output_dir=os.path.join(self._output_dir, 'figures'))
    config.output_types = ['png']
    config.verbose = True
    config.datatype = self._metric
    config.speedup = self._speedup
    config.normalize = self._normalize
    config.profile_name = self._name
    config.tgt_plugin = 'power_balancer'
    config.ref_plugin = 'power_governor'
    geopmpy.plotter.generate_bar_plot_comparison(process_output, config)


# TODO: fix me
def print_power_data(app_name, agent, report_path, trace_path, show_details=False):
    for agent in self._agent_list:
        run_name = '{}_{}_{}'.format(self._test_name, agent, app_name)
        report_path = '{}.report'.format(run_name)
        trace_path = '{}.trace'.format(run_name)

        self.print_power_data(app_name, agent, report_path, trace_path)
    ##########################
    new_output = geopmpy.io.RawReport(report_path)
    output = geopmpy.io.AppOutput('', trace_path + '*')

    node_names = new_output.host_names()
    power_budget = new_output.meta_data()['Policy']['POWER_PACKAGE_LIMIT_TOTAL']
    # Total power consumed will be Socket(s) + DRAM
    for nn in node_names:
        tt = output.get_trace_data(node_name=nn)
        # TODO: pass if dataframe
        first_epoch_index = tt.loc[tt['EPOCH_COUNT'] == 0][:1].index[0]
        epoch_dropped_data = tt[first_epoch_index:]  # Drop all startup data

        power_data = epoch_dropped_data[['TIME', 'ENERGY_PACKAGE', 'ENERGY_DRAM']]
        power_data = power_data.diff().dropna()
        power_data.rename(columns={'TIME': 'ELAPSED_TIME'}, inplace=True)
        power_data = power_data.loc[(power_data != 0).all(axis=1)]  # Will drop any row that is all 0's

        pkg_energy_cols = [s for s in power_data.keys() if 'ENERGY_PACKAGE' in s]
        dram_energy_cols = [s for s in power_data.keys() if 'ENERGY_DRAM' in s]
        power_data['SOCKET_POWER'] = power_data[pkg_energy_cols].sum(axis=1) / power_data['ELAPSED_TIME']
        power_data['DRAM_POWER'] = power_data[dram_energy_cols].sum(axis=1) / power_data['ELAPSED_TIME']
        power_data['COMBINED_POWER'] = power_data['SOCKET_POWER'] + power_data['DRAM_POWER']

        pandas.set_option('display.width', 100)
        power_stats = '\nPower stats from {} {} :\n{}\n'.format(agent, nn, power_data.describe())
        sys.stdout.write(power_stats)


def balancer_comparison(report_epoch_data, detailed=False):
    margin_factor = 0.25
    power_caps = report_epoch_data['POWER_PACKAGE_LIMIT_TOTAL'].unique()

    result = pandas.DataFrame(columns=['max_runtime_gov', 'max_runtime_bal', 'margin', 'runtime_pct'])
    for cap in power_caps:
        #edf = report_epoch_data.loc[report_epoch_data['POWER_PACKAGE_LIMIT_TOTAL'] == cap]
        edf = report_epoch_data
        edf = edf.set_index(['Agent', 'POWER_PACKAGE_LIMIT_TOTAL', 'Profile', 'host'])
        if detailed:
            sys.stdout.write('{}\n'.format(edf.xs(['power_governor', cap])))
        mean_runtime_gov = edf.xs(['power_governor', cap])['sync-runtime (sec)'].mean()
        max_runtime_gov = edf.xs(['power_governor', cap])['sync-runtime (sec)'].max()
        max_runtime_bal = edf.xs(['power_balancer', cap])['sync-runtime (sec)'].max()
        margin = margin_factor * (max_runtime_gov - mean_runtime_gov)
        runtime_pct = (max_runtime_gov - max_runtime_bal) / max_runtime_bal

        result.loc[cap] = [max_runtime_gov, max_runtime_bal, margin, runtime_pct]
    return result


def print_summary(df):
    sys.stdout.write('{}\n'.format(df))
    # for cap in power_caps:
    #        sys.stdout.write("\nPower limit {}:\n".format(cap))

    # sys.stdout.write("\nAverage runtime stats:\n")
    # sys.stdout.write("governor runtime: {}, balancer runtime: {}, margin: {}\n".format(
    #     df['max_runtime_gov'], max_runtime_bal, margin))
    # sys.stdout.write('\nBalancer runtime percent improvement: {}\n\n'.format(runtime_pct))


if __name__ == '__main__':
    aargs = common_args.ExperimentAnalysisArgs()
    output_dir = aargs.args.output_dir
    detailed = aargs.args.show_details

    # TODO: throw if data is missing; mention that user needs to run a power sweep

    output = geopmpy.io.RawReportCollection("*report", dir_name=output_dir)
    result = balancer_comparison(output.get_epoch_df(), detailed=detailed)
    print_summary(result)

    # if detailed:
    # trace_data = geopmpy.io.AppOutput('', trace_path + '*')
    # if show_details:
    #    print_power_data()
    # sys.stdout.write('{}\n'.format(result))
