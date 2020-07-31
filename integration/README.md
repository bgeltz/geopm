GEOPM INTEGRATION SCRIPTS
-------------------------

Welcome to GEOPM integration.

This directory contains scripts for running GEOPM for performance and
integration testing.  Refer to the README.md files in each
subdirectory for more information.

The directory structure is organized as follows:

- apps:

    The apps directory is where information about applications is
    located.  Each application supported has its own subdirectory
    within the apps directory.  Each application directory contains
    scripts that encapsulate the required setup, run configuration,
    and command line arguments for executing the application.  There
    may be more than one script for an application to support
    different workloads or scenarios.  For some applications, there
    are dedicated subdirectories containing more information on how to
    download and build the application, and sometimes GEOPM-related
    patches to be applied on top of publically-available source code.

- experiment:

    The scripts in this directory are intended to be used as a
    starting point for various types of experiments using GEOPM.  An
    experiment consists of a run step, containing application launches
    with GEOPM, and an analysis step, in which the reports and traces
    produced by the run step are processed, interpreted, and
    summarized.  Analysis scripts may also produce plots.

    Scripts are grouped into subfolders based on the type of
    experiment, such as a sweep across power limits or processor
    frequency settings.  In general, analysis of one type may be
    difficult to apply to results from another, so run scripts for the
    appropriate type should be used.

    In general, the current model is to have a different run script
    for each application.  This is because applications have specific
    runtime requirements and are scaled to different node and rank
    counts.

- test:
    The test directory contains the integration tests of the GEOPM
    runtime.  These tests may use functions from the experiment
    scripts to assist in launch and analysis, but they also perform
    assertions on the results.


##### NOTES BELOW HERE #####


TODO
----
- documentation in some cases doesn't match current file structure.  document intent and fix files later.
- should these files be README.md? - Chris: Yes, that way we get good formatting on github
- every __init__.py should have a docstring
- instead of required arg for `--machine-config`, perhaps can autodetect?
- by default, machine config is saved in output-dir and searched for in that dir.  a little confusing, maybe this should just be CWD or full path.
- remove _power_sweep_ being added to name of all power sweep files.  use provided file prefix only.
- node_efficiency should add an argument for target region



EXPERIMENT TYPES
----------------

Experiments are organized into the following subdirectories:

- power_sweep: experiments based on running agents with power limit policies

- frequency_sweep: experiments based on running agents with maximum frequency policies


Glossary of terms
-----------------
application -

experiment - a run step followed by one or more analysis steps in
    order to answer a question about application behavior or GEOPM
    agent performance

run step - a sequence of job launches of an application

analysis step - post-process, summarize, and interpret data from GEOPM reports and traces

report/trace - output files from the GEOPM runtime.  Refer to the geopmlaunch(1) man page for more information.


Example directory structure:

integration/
 L experiment/
   L __init__.py  (docs only)
   L monitor/   (baseline runs)
     L run_dgemm.py
   L power_sweep/
     L __init__.py  ()
     L run_dgemm.py
     L run_minife.py
     L node_efficiency.py  ( achieved_freq_histogram() )
     L launch.py  ( generic launch function
   L freq_sweep/
     L __init__.py  ()
     L run_dgemm.py
     L run_minife.py
     L runtime_energy_scaling.py  ( plots runtime and energy vs. frequency )

 L apps
   L dgemm.py  ( name of exe, config file for big-o, ranks per node )
   L dgemm_4rank.py
   L dgemm_imbalance.py
   L minife
     L minife.py    ( AppConf(num_node)  )
     L minife_imbalance.py  ( AppConf)
     L calculate_size.py
     L intel.patch
     L download_and_build.sh
     L miniFE_openmp-2.0-rc3  (downloaded source)
   L nekbone
     L go.py
     L go1.py
   L hacc
     L conf.py
     L conf_4rank_16th.py
