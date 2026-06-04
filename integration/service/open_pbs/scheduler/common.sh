#!/bin/bash
#  Copyright (c) 2015 - 2025 Intel Corporation
#  SPDX-License-Identifier: BSD-3-Clause
#
# Common configuration for MS427 PBS scheduling tests.
# Source this file from test drivers.

# PBS defaults
PBS_ACCOUNT="${PBS_ACCOUNT:-Intel-punchlist}"
PBS_QUEUE="${GEOPM_TEST_QUEUE:-geopm-test}"
PBS_WALLTIME="${PBS_WALLTIME:-00:10:00}"
PBS_FILESYSTEMS="${PBS_FILESYSTEMS:-home}"

# Power defaults (Sunspot)
MAX_NODE_POWER="${MAX_NODE_POWER:-4000}"
MIN_NODE_POWER="${MIN_NODE_POWER:-2400}"

# Timing — adjust if Sunspot job startup is slower/faster
# On Sunspot, jobs typically take 30-60s from qsub to Running state.
JOB_SLEEP="${JOB_SLEEP:-60}"         # How long test jobs sleep (must outlast observation window)
POLL_INTERVAL="${POLL_INTERVAL:-10}" # Seconds between qstat checks
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-120}" # Max wait for a job to reach R state

MS427_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_info() {
    echo "[MS427 $(date +%H:%M:%S)] $*"
}

log_pass() {
    echo "[MS427 PASS] $*"
}

log_fail() {
    echo "[MS427 FAIL] $*"
}

# Show GEOPM resources assigned to a job via qstat
show_geopm_job() {
    qstat -f -x "$1" 2>/dev/null | \
        awk '/Resource_List\.geopm/ { sub(/.*Resource_List\./, ""); gsub(/ = /, "="); print }'
}

# Get the assigned geopm-job-power-limit for a job from qstat
get_job_power_limit() {
    local job_id="$1"
    qstat -f "${job_id}" 2>/dev/null | \
        grep -oP 'geopm-job-power-limit=\K[0-9.]+'
}

# Get the current state of a job (Q, R, F, etc.)
get_job_state() {
    qstat -f "$1" 2>/dev/null | awk '/job_state/ {print $3}'
}

# Wait for a job to reach a target state (default: R).
# Returns 0 if the job reaches the target state, 1 on timeout.
wait_job_running() {
    local job_id="$1"
    local timeout="${2:-${STARTUP_TIMEOUT}}"
    local elapsed=0
    while (( elapsed < timeout )); do
        local state
        state=$(get_job_state "${job_id}")
        if [[ "${state}" == "R" ]]; then
            return 0
        elif [[ "${state}" == "F" || -z "${state}" ]]; then
            # Job already finished
            return 0
        fi
        sleep "${POLL_INTERVAL}"
        (( elapsed += POLL_INTERVAL ))
    done
    return 1
}

# Submit a job and return the job ID
# Automatically includes -l filesystems and a default walltime (if not
# specified by the caller).
submit_job() {
    # Check if caller already passed a walltime
    local has_walltime=false
    for arg in "$@"; do
        if [[ "${arg}" == *walltime* ]]; then
            has_walltime=true
            break
        fi
    done

    local wt_args=()
    if [[ "${has_walltime}" == "false" ]]; then
        wt_args=(-l "walltime=${PBS_WALLTIME}")
    fi

    local job_id
    job_id=$(qsub -A "${PBS_ACCOUNT}" -q "${PBS_QUEUE}" \
        -l "filesystems=${PBS_FILESYSTEMS}" "${wt_args[@]}" "$@")
    if [[ -z "${job_id}" ]]; then
        log_fail "qsub failed: $*"
        return 1
    fi
    echo "${job_id}"
}

# Maximum expected job duration before we suspect a hung job.
# JOB_SLEEP + reasonable startup overhead.
HUNG_JOB_THRESHOLD="${HUNG_JOB_THRESHOLD:-240}"  # seconds

# Wait until no test jobs remain in the queue (or timeout).
# Warns if a job stays in Running state longer than HUNG_JOB_THRESHOLD.
wait_queue_empty() {
    local timeout="${1:-300}"
    local elapsed=0
    local warned=false
    while (( elapsed < timeout )); do
        local count
        count=$(qstat 2>/dev/null | grep -c "ms427" || echo 0)
        if [[ "${count}" -eq 0 ]]; then
            return 0
        fi

        # Check for potentially hung jobs (R state past expected duration)
        if [[ "${warned}" == "false" && ${elapsed} -ge ${HUNG_JOB_THRESHOLD} ]]; then
            local hung_jobs
            hung_jobs=$(qstat 2>/dev/null | awk '/ms427/ && / R / {print $1}')
            if [[ -n "${hung_jobs}" ]]; then
                log_info "WARNING: Jobs still in R state after ${elapsed}s (may be hung at 'sent for execution'):"
                for jid in ${hung_jobs}; do
                    log_info "  ${jid}"
                done
                log_info "  If jobs are not producing output, the assigned node may be unresponsive."
                log_info "  Consider: qdel ${hung_jobs}"
                warned=true
            fi
        fi

        sleep "${POLL_INTERVAL}"
        (( elapsed += POLL_INTERVAL ))
    done
    log_fail "Timeout: jobs still in queue after ${timeout}s (possible hung jobs)"
    return 1
}

# Delete all ms427 test jobs
cleanup_jobs() {
    local jobs
    jobs=$(qstat 2>/dev/null | awk '/ms427/ {print $1}')
    if [[ -n "${jobs}" ]]; then
        echo "${jobs}" | xargs qdel 2>/dev/null || true
    fi
}

# Verify that power resources are configured on the test queue
check_power_resources() {
    local cap
    cap=$(qstat -Qf "${PBS_QUEUE}" 2>/dev/null | grep -oP 'geopm-job-power-limit = \K[0-9]+' || true)
    if [[ -z "${cap}" ]]; then
        # Fall back to checking server level
        cap=$(qstat -Bf 2>/dev/null | grep -oP 'geopm-job-power-limit = \K[0-9]+' || true)
    fi
    if [[ -z "${cap}" ]]; then
        log_fail "geopm-job-power-limit not set on queue '${PBS_QUEUE}' or server. Ask admin to run admin_setup.sh"
        return 1
    fi
    log_info "Power cap = ${cap} W (queue: ${PBS_QUEUE})"
}
