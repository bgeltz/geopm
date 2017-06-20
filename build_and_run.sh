#!/bin/bash

GEOPM_PATH=${HOME}/geopm

##############################
# Nightly integration test run
module purge && module load intel mvapich2 autotools

cd ${GEOPM_PATH}
git fetch --all
git reset --hard origin/dev
git clean -fdx

# Intel Toolchain - Runs integration tests 10 times
${HOME}/bin/go -ic
make install
cd test_integration
./geopm_test_loop.sh
# End integration test run
#############################

####################################
# Nightly coverage report generation
TIMESTAMP=$(date +\%F_\%H\%M)
TEST_DIR=${HOME}/public_html/coverage_runs/${TIMESTAMP}
LOG_FILE=test_output.log

mkdir -p ${TEST_DIR}

# GNU Toolchain - Runs unit tests, then integration tests, then generates coverage report
module purge && module load gnu impi autotools

cd ${GEOPM_PATH}
git fetch origin
git reset --hard origin/dev
git clean -fdx
export MPIEXEC="srun --cpu_bind=v,mask_cpu:0x2,0x1FFFC,0xFFFE0000,0x7FFF00000000,0x3FFF800000000000 -N4"

go -dc > >(tee -a build_${LOG_FILE}) 2>&1

# Initial / baseline lcov
lcov --capture --initial --directory src --directory plugin --directory test --output-file base_coverage.info --rc lcov_branch_coverage=1 --no-external > >(tee -a coverage_${LOG_FILE}) 2>&1

# Run integration tests
pushd test_integration
GEOPM_PLUGIN_PATH=${HOME}/geopm/.libs LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/5.3.0/lib64:${HOME}/geopm/.libs:${LD_LIBRARY_PATH} ./geopm_test_integration.py -v > >(tee -a integration_${LOG_FILE}) 2>&1
popd

# Run unit tests
make check > >(tee -a check_${LOG_FILE}) 2>&1
# make coverage > >(tee -a check_${LOG_FILE}) 2>&1 # Target does lcov and genhtml calls

lcov --no-external --capture --directory src --directory plugin --directory test --output-file coverage.info --rc lcov_branch_coverage=1 > >(tee -a coverage_${LOG_FILE}) 2>&1

lcov --rc lcov_branch_coverage=1 -a base_coverage.info -a coverage.info -o combined_coverage.info > >(tee -a coverage_${LOG_FILE}) 2>&1

lcov --rc lcov_branch_coverage=1 --remove combined_coverage.info "$(pwd)/test*" "$(pwd)/src/geopm_pmpi_fortran.c" "$(pwd)/gmock*" "/opt*" "/usr*" "5.3.0*" -o filtered_coverage.info > >(tee -a coverage_${LOG_FILE}) 2>&1

genhtml filtered_coverage.info --output-directory coverage --rc lcov_branch_coverage=1 --legend -t $(git describe) -f > >(tee -a coverage_${LOG_FILE}) 2>&1

# Copy coverage html to date stamped public_html dir
cp -rp coverage ${TEST_DIR}

# Copy unit and integration test outputs to dir
cp -rp --parents test/gtest_links ${TEST_DIR}
cp -rp --parents test/fortran/fortran_links ${TEST_DIR}

for f in $(git ls-files --others --exclude-standard);
do
    cp -p --parents ${f} ${TEST_DIR}
done

# End nightly coverage report generation
########################################
