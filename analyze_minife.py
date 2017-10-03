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

app_output = geopmpy.io.AppOutput('*report', '*trace-*', file_path, True)
report_df = app_output.get_report_df()
trace_df = app_output.get_trace_df()
idx = pandas.IndexSlice

# Report file processing
power_governing_df = report_df.loc[idx[:, :, :, :, 'power_governing', :, :, 'epoch'], ]
simple_freq_df = report_df.loc[idx[:, :, :, :, 'simple_freq', :, :, 'epoch'], ]
power_governing_df = power_governing_df.reset_index(drop=True)
simple_freq_df = simple_freq_df.reset_index(drop=True)

print 'Power Governing leaf decider :\n{}\n'.format(power_governing_df.T)
print 'Simple Freq decider :\n{}\n'.format(simple_freq_df.T)

energy_savings = (power_governing_df['energy'] - simple_freq_df['energy']) / power_governing_df['energy']
runtime_savings = (power_governing_df['runtime'] - simple_freq_df['runtime']) / power_governing_df['runtime']

print 'Energy savings ratio = {}'.format(energy_savings.item())
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

