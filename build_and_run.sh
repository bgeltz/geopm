#!/bin/bash

GEOPM_PATH=${HOME}/geopm

##############################
# Nightly integration test run
module purge && module load intel mvapich2 autotools

cd ${GEOPM_PATH}
git fetch --all
git reset --hard origin/dev
# FIXME Remove this when the patch is merged
git fetch https://review.gerrithub.io/geopm/geopm refs/changes/92/372592/1 && git cherry-pick FETCH_HEAD
git clean -fdx

# Intel Toolchain - Runs integration tests 10 times
${HOME}/bin/go -ic
make install

# Run the integration test SBATCH script
TIMESTAMP=$(date +\%F_\%H\%M)
TEST_DIR=${HOME}/public_html/cron_runs/${TIMESTAMP}

sbatch integration_batch.sh intel loop
echo "Integration tests launched via sbatch.  Sleeping..."
while [ ! -f ${GEOPM_PATH}/test_integration/.tests_complete ]; do
    sleep 5
done
echo "Integration tests complete."

# Move the files into the TEST_DIR
echo "Moving files to ${TEST_DIR}..."
mkdir -p ${TEST_DIR}
for f in $(git ls-files --others --exclude-standard);
do
    mv ${f} ${TEST_DIR}
done

# Send mail if there was a test failure.
if [ -f ${TEST_DIR}/.tests_failed ]; then
    ERR_MSG="The integration tests have failed.  Please see the output for more information:\nhttp://$(hostname -i)/~test/cron_runs/${TIMESTAMP}"

    echo -e ${ERR_MSG} | mail -r "do-not-reply" -s "Integration test failure : ${TIMESTAMP}" brad.geltz@intel.com,christopher.m.cantalupo@intel.com,steve.s.sylvester@intel.com,brandon.baker@intel.com

    echo "Email sent."
    exit 1
fi

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
export LD_LIBRARY_PATH=${GEOPM_PATH}/openmp/lib:${LD_LIBRARY_PATH}

cd ${GEOPM_PATH}
git fetch origin
git reset --hard origin/dev
git clean -fdx
export MPIEXEC="srun --cpu_bind=v,mask_cpu:0x2,0x1FFFC,0xFFFE0000,0x7FFF00000000,0x3FFF800000000000 -N4"

go -dc > >(tee -a build_${LOG_FILE}) 2>&1

# Initial / baseline lcov
lcov --capture --initial --directory src --directory plugin --directory test --output-file base_coverage.info --rc lcov_branch_coverage=1 --no-external > >(tee -a coverage_${LOG_FILE}) 2>&1

# Run integration tests
sbatch integration_batch.sh gnu once
echo "Integration tests launched via sbatch.  Sleeping..."
while [ ! -f ${GEOPM_PATH}/test_integration/.tests_complete ]; do
    sleep 5
done
echo "Integration tests complete."

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
