## geopm/integration/experiment/README
#########################

GEOPM EXPERIMENT SCRIPTS
------------------------

The scripts in this directory are intended to be used as a starting
point for various types of experiments using GEOPM.  An experiment
consists of a run step, containing application launches with GEOPM,
and an analysis step, in which the reports and traces produced by the
run step are processed, interpreted, and summarized.  Analysis scripts
may also produce plots.

Scripts are grouped into subfolders based on the type of experiment,
such as a sweep across power limits or processor frequency settings.
In general, analysis of one type may be difficult to apply to results
from another, so run scripts for the appropriate type should be used.


NOTE ON APPLICATIONS
--------------------

In general, the current model for run scripts is to have a different
script for each application.  This is because applications have
specific runtime requirements and are scaled to different node and
rank counts.


EXPERIMENT TYPES
----------------

Experiments are organized into the following subdirectories:

- power_sweep: experiments based on running agents with power limit policies

- frequency_sweep: experiments based on running agents with maximum frequency policies

#######
Glossary of terms
-----------------
application -

experiment - a run step followed by one or more analysis steps in
    order to answer a question about application behavior or GEOPM
    agent performance

run step - a sequence of job launches of an application

analysis step - post-process, summarize, and interpret data from GEOPM reports and traces

report/trace - output files from the GEOPM runtime.  Refer to the geopmlaunch(1) man page for more information.





### do_everything.slurm ##

# does launch step
./experiment/power_sweep/run_dgemm.py --nodes=4 --output-dir=test7 --machine-config=mcfly.machine
./run_dgemm.py
./run_dgemm_imbalance.py



# alternative
./run.py --app=dgemm_imbalance --nodes=8


./experiment/power_sweep/node_efficiency.py





######################



#####

1. integration/experiment/power_sweep.py
2. integration/experiment/power_sweep/__init__.py

from integration.experiment import power_sweep, balancer_comparison
import integration.experiment.power_sweep as power_sweep
power_sweep.launch()


from integration.experiment.power_sweep import launch_power_sweep

launch_power_sweep()
####



FREQUENCY SWEEP-BASED EXPERIMENTS
---------------------------------
Coming soon.
