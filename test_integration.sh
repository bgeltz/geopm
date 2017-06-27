#!/bin/bash
#COBALT -t 60 
#COBALT -n 4
#COBALT -A intel
#COBALT -O logs/$jobid
#COBALT -q backfill-cache-quad
#COBALT --jobname pwr_test
#COBALT --env JOBID=$jobid
##COBALT --notify brad.geltz@intel.com

# Export vars that would be overwritten by module loading
export PYTHONPATH=/lus-projects/intel/geopm-home/bgeltz/lib/python:${PYTHONPATH}
export TZ="/usr/share/zoneinfo/US/Pacific"

SRC_ROOT=/lus-projects/intel/geopm-home/bgeltz/geopm

cd ${SRC_ROOT}/test_integration
git clean -fd .

# Run the test once
GEOPM_RUN_LONG_TESTS=true ./geopm_test_integration.py -v TestIntegration.${1}

mkdir -p ~/logs/${JOBID}
for f in $(git ls-files --others --exclude-standard);
do
    mv ${f} ~/logs/${JOBID}
done

rm ~/last_job
ln -sf ~/logs/${JOBID} ~/last_job

###########################################################################################################

# DDT=/soft/debuggers/ddt/bin/ddt --connect
# DDT=

# LD_LIBRARY_PATH=/opt/intel/compilers_and_libraries_2017.1.132/linux/compiler/lib/intel64:$LD_LIBRARY_PATH ./geopm_test_integration.py --verbose TestReport.test_scaling

# cp ~/tmp/*config .
# KMP_AFFINITY=disabled OMP_NUM_THREADS=62 GEOPM_POLICY=test_scaling_ctl.config LD_DYNAMIC_WEAK=true GEOPM_REPORT=test_scaling.report GEOPM_PMPI_CTL=process ${DDT} aprun -N 2 -n 128 -cc 1:2-63 .libs/geopm_test_integration --verbose test_scaling_app.config

#
# Trying to background the controller, sleep (with hopefully enough time to connect DDT remotely), and then launch the app
#
# GEOPM_POLICY=test_scaling_ctl.config LD_DYNAMIC_WEAK=true GEOPM_REPORT=test_scaling.report /soft/debuggers/ddt/bin/ddt --connect aprun -N 1 -n 64 -cc 1 ~/build/geopm/bin/geopmctl &
# sleep 120
# KMP_AFFINITY=disabled OMP_NUM_THREADS=62 LD_DYNAMIC_WEAK=true aprun -N 1 -n 64 -cc 2-63 .libs/geopm_test_integration --verbose test_scaling_app.config

#COBALT -M 8044821851@msg.fi.google.com
#COBALT -M christopher.m.cantalupo@intel.com
