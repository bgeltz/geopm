#!/bin/bash
#COBALT -d
#COBALT -t 120
#COBALT -n 1
#COBALT -q it
#COBALT -O logs/$jobid
#COBALT --jobname geopm_coverage
#COBALT --env JOBID=$jobid

set -x

export TZ="/usr/share/zoneinfo/US/Pacific"
export PATH="${HOME}/bin:${HOME}/build/python/bin:${HOME}/build/cmake/bin:${HOME}/build/lcov/bin:${HOME}/perl5/bin:${PATH}"
export PYTHONPATH=${HOME}/build/geopm/lib/python2.7/site-packages:${HOME}/build/python/lib/python2.7/site-packages:${PYTHONPATH}
export PERL5LIB=${HOME}/perl5/lib/perl5:${PERL5LIB}
export http_proxy=http://proxy:3128
export https_proxy=http://proxy:3128
export ftp_proxy=http://proxy:3128

#GEOPM_PATH=${HOME}/geopm
GEOPM_PATH=/tmp/bgeltz/geopm

pushd ${HOME}/bin
source ./compilervars.sh intel64
./whitelist.sh
popd

##############################
# Nightly integration test run
#module purge && module load intel mvapich2 autotools

#cd ${GEOPM_PATH}
#git fetch --all
#git reset --hard origin/dev
#git clean -fdx

## Intel Toolchain - Runs integration tests 10 times
#${HOME}/bin/go -ic
#make install
#cd test_integration
#./geopm_test_loop.sh
# End integration test run
#############################

####################################
# Nightly coverage report generation
TIMESTAMP=$(date +\%F_\%H\%M)
TEST_DIR=${HOME}/public_html/coverage_runs/${TIMESTAMP}
LOG_FILE=test_output.log
# The integration tests require that the GEOPM binaries are in the path
PATH=${GEOPM_PATH}/.libs:${PATH}

mkdir -p ${TEST_DIR}
rm -fr ${GEOPM_PATH}
mkdir -p ${GEOPM_PATH}

# GNU Toolchain - Runs unit tests, then integration tests, then generates coverage report
export LD_LIBRARY_PATH=${GEOPM_PATH}/openmp/lib:${LD_LIBRARY_PATH}

cd ${GEOPM_PATH}/..
cp -r ${HOME}/geopm .
#git clone https://github.com/geopm/geopm.git
cd geopm
#git fetch origin
#git reset --hard origin/dev
git clean -fdx

go -dc > >(tee -a build_${LOG_FILE}) 2>&1

# Initial / baseline lcov
lcov --capture --initial --directory src --directory plugin --directory test --output-file base_coverage.info --rc lcov_branch_coverage=1 --no-external > >(tee -a coverage_${LOG_FILE}) 2>&1

# Run integration tests
#pushd ${GEOPM_PATH}/test_integration
#LD_PRELOAD=${GEOPM_PATH}/openmp/lib/libomp.so GEOPM_PLUGIN_PATH=${GEOPM_PATH}/.libs LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/5.3.0/lib64:${GEOPM_PATH}/.libs:${LD_LIBRARY_PATH} ./geopm_test_integration.py -v > >(tee -a integration_${LOG_FILE}) 2>&1
#popd

# Run unit tests
make check > >(tee -a check_${LOG_FILE}) 2>&1
# make coverage > >(tee -a check_${LOG_FILE}) 2>&1 # Target does lcov and genhtml calls

lcov --no-external --capture --directory src --directory plugin --directory test --output-file coverage.info --rc lcov_branch_coverage=1 > >(tee -a coverage_${LOG_FILE}) 2>&1

lcov --rc lcov_branch_coverage=1 -a base_coverage.info -a coverage.info -o combined_coverage.info > >(tee -a coverage_${LOG_FILE}) 2>&1

lcov --rc lcov_branch_coverage=1 --remove combined_coverage.info "$(pwd)/test*" "$(pwd)/src/geopm_pmpi_fortran.c" "$(pwd)/gmock*" "/opt*" "/usr*" "5.3.0*" -o filtered_coverage.info > >(tee -a coverage_${LOG_FILE}) 2>&1

#genhtml filtered_coverage.info --output-directory coverage --rc lcov_branch_coverage=1 --legend -t $(git describe) -f > >(tee -a coverage_${LOG_FILE}) 2>&1

# Copy coverage html to date stamped public_html dir
#cp -rp coverage ${TEST_DIR}

# Copy unit and integration test outputs to dir
cp -rp test/gtest_links ${TEST_DIR}
cp -rp scripts/test/pytest_links ${TEST_DIR}

for f in $(git ls-files --others --exclude-standard);
do
    cp -p --parents ${f} ${TEST_DIR}
done

# End nightly coverage report generation
########################################
