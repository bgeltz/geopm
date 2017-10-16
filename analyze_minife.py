#!/usr/bin/env python

# import geopmpy.plotter
import geopmpy.io
import code
import sys
import pandas
import matplotlib.pyplot as plt
import os
import code

_, os.environ['COLUMNS'] = os.popen('stty size', 'r').read().split() # Ensures COLUMNS is set so text wraps properly
pandas.set_option('display.width', int(os.environ['COLUMNS'])) # Same tweak for Pandas

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
simple_freq_df = report_df.loc[idx[:, :, :, :, 'simple_freq', :, :, 'epoch'], ]

power_governing_node_gp = power_governing_df.groupby(level=['iteration', 'node_name']).mean() # Mean here is a hack to display the groupby object
power_governing_iteration_gp = power_governing_df.groupby(level=['iteration']).mean()

with pandas.option_context('display.max_rows', None, 'display.max_columns', 99):
    print 'Power Governing leaf decider :\n{}\n'.format(power_governing_node_gp)
    print 'Power Governing leaf decider iteration means :\n{}\n'.format(power_governing_iteration_gp)

simple_freq_node_gp = simple_freq_df.groupby(level=['iteration', 'node_name']).mean() # Mean here is a hack to display the groupby object
simple_freq_iteration_gp = simple_freq_df.groupby(level=['iteration']).mean()

with pandas.option_context('display.max_rows', None, 'display.max_columns', 99):
    print 'Simple Freq leaf decider :\n{}\n'.format(simple_freq_node_gp)
    print 'Simple Freq leaf decider iteration means :\n{}\n'.format(simple_freq_iteration_gp)

energy_savings_per_node = (power_governing_node_gp['energy'] - simple_freq_node_gp['energy']) / power_governing_node_gp['energy']
energy_savings_per_iteration = (power_governing_iteration_gp['energy'] - simple_freq_iteration_gp['energy']) / power_governing_iteration_gp['energy']
runtime_savings_per_node = (power_governing_node_gp['runtime'] - simple_freq_node_gp['runtime']) / power_governing_node_gp['runtime']
runtime_savings_per_iteration = (power_governing_iteration_gp['runtime'] - simple_freq_iteration_gp['runtime']) / power_governing_iteration_gp['runtime']

with pandas.option_context('display.max_rows', None, 'display.max_columns', 99):
    print '_' * 60
    print 'Energy savings per node = \n{}'.format(energy_savings_per_node.groupby('node_name').describe())
    print '_' * 60
    print 'Energy savings  = \n{}'.format(energy_savings_per_node.describe())
    print '_' * 60
    print 'Runtime savings per node = \n{}'.format(runtime_savings_per_node.groupby('node_name').describe())
    print '_' * 60
    print 'Runtime savings  = \n{}'.format(runtime_savings_per_node.describe())
    print '_' * 60

print '=' * 60

if len(sys.argv) > 2:
    code.interact(local=dict(globals(), **locals()))

