#!/usr/bin/env python

# import geopmpy.plotter
import geopmpy.io
import code
import sys
import pandas
import matplotlib.pyplot as plt
import code

print '=' * 60
file_path = sys.argv[1]
print 'Parsing data in {}...'.format(file_path)

#  app_output = geopmpy.io.AppOutput('*report', '*trace-*', file_path, True)
app_output = geopmpy.io.AppOutput('*report', None, file_path, True)
report_df = app_output.get_report_df()
trace_df = app_output.get_trace_df()
idx = pandas.IndexSlice

# Report file processing
power_governing_df = report_df.loc[idx[:, :, :, :, 'power_governing', :, :, 'epoch'], ]
power_governing_df = power_governing_df.reset_index(drop=True)
print 'Power Governing leaf decider :\n{}\n'.format(power_governing_df.T)

simple_freq_df = report_df.loc[idx[:, :, :, :, 'simple_freq', :, :, 'epoch'], ]
for (_, name, _, tree_decider, leaf_decider), df in \
    simple_freq_df.groupby(level=['version', 'name', 'power_budget', 'tree_decider', 'leaf_decider']):

    print '-' * 60
    df = df.reset_index(drop=True)
    print 'Simple Freq decider ({}):\n{}\n'.format(name, df.T)

    energy_savings = (power_governing_df['energy'] - df['energy']) / power_governing_df['energy']
    runtime_savings = (power_governing_df['runtime'] - df['runtime']) / power_governing_df['runtime']

    print 'Energy savings ratio  = {}'.format(energy_savings.item())
    print 'Runtime savings ratio = {}'.format(runtime_savings.item())

#Trace file processing
# power_governing_trace_df = trace_df.loc[idx[:, :, :, :, 'power_governing', :, :], ]
# simple_freq_trace_df = trace_df.loc[idx[:, :, :, :, 'simple_freq', :, :], ]
# power_governing_trace_df = power_governing_trace_df.reset_index(drop=True)
# simple_freq_trace_df = simple_freq_trace_df.reset_index(drop=True)

# power_governing_trace_df[['region_id', 'frequency-0']].plot.hist()
# simple_freq_trace_df[['region_id', 'frequency-0']].plot.hist()

print '=' * 60

if len(sys.argv) > 2:
    code.interact(local=dict(globals(), **locals()))

