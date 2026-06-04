#!/bin/bash
#  Copyright (c) 2015 - 2025 Intel Corporation
#  SPDX-License-Identifier: BSD-3-Clause
#
# MS427 PBS Scheduling Test Driver
#
# Implements TC1-TC7: validates that the GEOPM PBS hooks correctly interact
# with the PBS scheduler for power-budget-driven job admission.
#
# Usage:
#   ./test_scheduling.sh [TC1|TC2|TC3|TC4|TC5|TC6|TC7|phase1|phase2|phase3|phase4]
#
# Prerequisites:
#   - Admin has run admin_setup.sh to create the test queue and set resources
#     for the current phase.
#   - GEOPM_TEST_QUEUE is set (default: geopm-test)
#
# Phase grouping (tests grouped by required cluster cap):
#   Phase 1 (cap=100000): TC1, TC3, TC4  — cap not binding
#   Phase 2 (cap=8000):   TC6            — backfill with power headroom
#   Phase 3 (cap=6000):   TC2, TC7       — serializes 2-node jobs
#   Phase 4 (cap=4000):   TC5            — serializes 1-node jobs
#
# Note: Sleep times are tuned for Sunspot. Adjust JOB_SLEEP and POLL_INTERVAL
# in common.sh if needed.

set -e
source "$(dirname "$0")/common.sh"

TEST_ID="${1:-all}"

# Verify resources are set before running
check_power_resources || exit 1

# ---------------------------------------------------------------------------
# TC1: Jobs Execute Immediately Under No Power or Node Contention
# Phase 1 (cap=100000)
# ---------------------------------------------------------------------------
run_tc1() {
    log_info "=== TC1: Jobs Execute Immediately Under No Power or Node Contention ==="

    local job_id
    job_id=$(submit_job -N ms427_tc1 -koed -joe \
        -l "select=2" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "Submitted ${job_id}"

    if wait_job_running "${job_id}"; then
        local state
        state=$(get_job_state "${job_id}")
        log_pass "TC1: Job started (state=${state})"
    else
        local state
        state=$(get_job_state "${job_id}")
        log_fail "TC1: Job did not start within ${STARTUP_TIMEOUT}s (state=${state})"
    fi

    # Verify power assignment
    local power
    power=$(get_job_power_limit "${job_id}")
    log_info "TC1: assigned power = ${power:-none}"

    cleanup_jobs
    wait_queue_empty 60
}

# ---------------------------------------------------------------------------
# TC2: Default Job Power Limits are Limited by the System Budget
# Phase 3 (cap=6000)
# ---------------------------------------------------------------------------
run_tc2() {
    log_info "=== TC2: Default Job Power Limits are Limited by the System Budget ==="
    log_info "  Requires: admin_setup.sh phase3 (cap=6000)"

    # Cap = 6000 W. Two 2-node jobs would each want 8000 W (2×4000) but get
    # clamped to 6000 W. Since 6000+6000 > 6000, they must run in series.
    local job1 job2
    job1=$(submit_job -N ms427_tc2 -koed -joe \
        -l "select=2" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    job2=$(submit_job -N ms427_tc2 -koed -joe \
        -l "select=2" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "Submitted job1=${job1}, job2=${job2}"

    # Wait for job1 to start running
    if ! wait_job_running "${job1}"; then
        log_fail "TC2: job1 did not start within ${STARTUP_TIMEOUT}s"
        cleanup_jobs; wait_queue_empty 120; return
    fi

    # Give scheduler a cycle to potentially start job2
    sleep "${POLL_INTERVAL}"
    local s1 s2
    s1=$(get_job_state "${job1}")
    s2=$(get_job_state "${job2}")
    log_info "States: job1=${s1}, job2=${s2}"

    if [[ "${s1}" == "R" && "${s2}" == "Q" ]]; then
        log_pass "TC2: Jobs run in series (job1=R, job2=Q) — power cap enforced"
    elif [[ "${s1}" == "R" && "${s2}" == "R" ]]; then
        log_fail "TC2: Both jobs running concurrently — power cap NOT enforced"
    else
        log_info "TC2: job1=${s1}, job2=${s2} — may need more time"
    fi

    # Check assigned power
    local p1 p2
    p1=$(get_job_power_limit "${job1}")
    p2=$(get_job_power_limit "${job2}")
    log_info "TC2: job1 power=${p1:-?}, job2 power=${p2:-?}"
    if [[ "${p1}" == "6000" ]]; then
        log_pass "TC2: job1 power clamped to system budget (6000 W)"
    else
        log_fail "TC2: Expected job1 power=6000, got ${p1:-unset}"
    fi

    cleanup_jobs
    wait_queue_empty 120
}

# ---------------------------------------------------------------------------
# TC3: Default Job Power Caps are Limited by the Max Node Power
# Phase 1 (cap=100000)
# ---------------------------------------------------------------------------
run_tc3() {
    log_info "=== TC3: Default Job Power Caps are Limited by the Max Node Power ==="
    log_info "  Requires: admin_setup.sh phase1 (cap=100000)"

    # Cap = 100000 W (not binding). Each 2-node job should get 2×4000=8000 W.
    local job1 job2
    job1=$(submit_job -N ms427_tc3 -koed -joe \
        -l "select=2" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    job2=$(submit_job -N ms427_tc3 -koed -joe \
        -l "select=2" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "Submitted job1=${job1}, job2=${job2}"

    # Wait for at least one job to start
    if ! wait_job_running "${job1}"; then
        log_fail "TC3: job1 did not start within ${STARTUP_TIMEOUT}s"
        cleanup_jobs; wait_queue_empty 120; return
    fi

    # Give scheduler a cycle to start job2
    sleep "${POLL_INTERVAL}"
    local s1 s2
    s1=$(get_job_state "${job1}")
    s2=$(get_job_state "${job2}")
    log_info "States: job1=${s1}, job2=${s2}"

    if [[ "${s1}" == "R" && "${s2}" == "R" ]]; then
        log_pass "TC3: Both jobs run concurrently (cap not binding)"
    else
        log_fail "TC3: Expected both running; got job1=${s1}, job2=${s2}"
    fi

    # Check assigned power = 8000 (2 nodes × 4000)
    local p1 p2
    p1=$(get_job_power_limit "${job1}")
    p2=$(get_job_power_limit "${job2}")
    log_info "TC3: job1 power=${p1:-?}, job2 power=${p2:-?}"
    if [[ "${p1}" == "8000" ]]; then
        log_pass "TC3: job1 power = max_node × nodes (8000 W)"
    else
        log_fail "TC3: Expected job1 power=8000, got ${p1:-unset}"
    fi

    cleanup_jobs
    wait_queue_empty 120
}

# ---------------------------------------------------------------------------
# TC4: Single-node Jobs Run Concurrently When There is Enough Power
# Phase 1 (cap=100000)
# ---------------------------------------------------------------------------
run_tc4() {
    log_info "=== TC4: Single-node Jobs Run Concurrently When There is Enough Power ==="
    log_info "  Requires: admin_setup.sh phase1 (cap=100000)"

    # Cap = 100000 W. Two 1-node jobs at 4000 W each → both fit.
    local job1 job2
    job1=$(submit_job -N ms427_tc4 -koed -joe \
        -l "select=1" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    job2=$(submit_job -N ms427_tc4 -koed -joe \
        -l "select=1" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "Submitted job1=${job1}, job2=${job2}"

    # Wait for at least one job to start
    if ! wait_job_running "${job1}"; then
        log_fail "TC4: job1 did not start within ${STARTUP_TIMEOUT}s"
        cleanup_jobs; wait_queue_empty 120; return
    fi

    # Give scheduler a cycle to start job2
    sleep "${POLL_INTERVAL}"
    local s1 s2
    s1=$(get_job_state "${job1}")
    s2=$(get_job_state "${job2}")
    log_info "States: job1=${s1}, job2=${s2}"

    if [[ "${s1}" == "R" && "${s2}" == "R" ]]; then
        log_pass "TC4: Both single-node jobs run concurrently"
    else
        log_fail "TC4: Expected both running; got job1=${s1}, job2=${s2}"
    fi

    local p1 p2
    p1=$(get_job_power_limit "${job1}")
    p2=$(get_job_power_limit "${job2}")
    log_info "TC4: job1 power=${p1:-?}, job2 power=${p2:-?}"

    cleanup_jobs
    wait_queue_empty 120
}

# ---------------------------------------------------------------------------
# TC5: Single-node Jobs Run in Series When There is Not Enough Power
# Phase 4 (cap=4000)
# ---------------------------------------------------------------------------
run_tc5() {
    log_info "=== TC5: Single-node Jobs Run in Series When There is Not Enough Power ==="
    log_info "  Requires: admin_setup.sh phase4 (cap=4000)"

    # Cap = 4000 W. Each 1-node job gets 4000 W. Only one fits at a time.
    local job1 job2
    job1=$(submit_job -N ms427_tc5 -koed -joe \
        -l "select=1" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    job2=$(submit_job -N ms427_tc5 -koed -joe \
        -l "select=1" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "Submitted job1=${job1}, job2=${job2}"

    # Wait for job1 to start running
    if ! wait_job_running "${job1}"; then
        log_fail "TC5: job1 did not start within ${STARTUP_TIMEOUT}s"
        cleanup_jobs; wait_queue_empty 120; return
    fi

    # Give scheduler a cycle to potentially start job2
    sleep "${POLL_INTERVAL}"
    local s1 s2
    s1=$(get_job_state "${job1}")
    s2=$(get_job_state "${job2}")
    log_info "States: job1=${s1}, job2=${s2}"

    if [[ "${s1}" == "R" && "${s2}" == "Q" ]]; then
        log_pass "TC5: Jobs run in series (power cap limits concurrency)"
    elif [[ "${s1}" == "R" && "${s2}" == "R" ]]; then
        log_fail "TC5: Both running — power cap not constraining scheduler"
    else
        log_info "TC5: job1=${s1}, job2=${s2} — unexpected state"
    fi

    cleanup_jobs
    wait_queue_empty 120
}

# ---------------------------------------------------------------------------
# TC6: Backfiller is Not Disrupted by Automatic Power Cap Selection
# Phase 2 (cap=8000)
# ---------------------------------------------------------------------------
run_tc6() {
    log_info "=== TC6: Backfiller is Not Disrupted by Automatic Power Cap Selection ==="
    log_info "  Requires: admin_setup.sh phase2 (cap=8000)"
    log_info "  Requires: strict_ordering in scheduler config"

    # Cap = 8000 W. Enough for 2 single-node jobs (2×4000) simultaneously.

    # Job 1: 1-node, long walltime, starts ASAP (creates a scheduler hole)
    local job1
    job1=$(submit_job -N ms427_tc6_j1 -koed -joe -l walltime=5:00 \
        -l "select=1" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep 120")
    log_info "  Job1 (1-node, long): ${job1}"

    # Job 2: 2-node, high priority. Top job behind Job 1.
    local job2
    job2=$(submit_job -N ms427_tc6_j2 -koed -joe -p1000 -l walltime=1:00 \
        -l "select=2" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "  Job2 (2-node, high-pri): ${job2}"

    # Job 3: 1-node, low priority, walltime too long to backfill
    local job3
    job3=$(submit_job -N ms427_tc6_j3 -koed -joe -p0 -l walltime=5:30 \
        -l "select=1" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "  Job3 (1-node, long wt): ${job3}"

    # Job 4: 1-node, low priority, short walltime → backfill candidate
    local job4
    job4=$(submit_job -N ms427_tc6_j4 -koed -joe -p0 -l walltime=1:00 \
        -l "select=1" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "  Job4 (1-node, short wt): ${job4}"

    # Wait for Job1 to start, then allow time for backfill scheduling
    if ! wait_job_running "${job1}"; then
        log_fail "TC6: Job1 did not start within ${STARTUP_TIMEOUT}s"
        cleanup_jobs; wait_queue_empty 300; return
    fi
    sleep "${POLL_INTERVAL}"

    local s1 s2 s3 s4
    s1=$(get_job_state "${job1}")
    s2=$(get_job_state "${job2}")
    s3=$(get_job_state "${job3}")
    s4=$(get_job_state "${job4}")
    log_info "  States: j1=${s1} j2=${s2} j3=${s3} j4=${s4}"

    if [[ "${s1}" == "R" && "${s4}" == "R" && "${s2}" == "Q" && "${s3}" == "Q" ]]; then
        log_pass "TC6: Job4 backfilled alongside Job1; Jobs 2,3 queued"
    else
        log_info "TC6: j1=${s1} j2=${s2} j3=${s3} j4=${s4} — check manually"
    fi

    # Check power assignments
    local p1 p4
    p1=$(get_job_power_limit "${job1}")
    p4=$(get_job_power_limit "${job4}")
    log_info "  TC6: job1 power=${p1:-?}, job4 power=${p4:-?}"

    cleanup_jobs
    wait_queue_empty 300
}

# ---------------------------------------------------------------------------
# TC7: Backfiller Respects System Power Limits
# Phase 3 (cap=6000)
# ---------------------------------------------------------------------------
run_tc7() {
    log_info "=== TC7: Backfiller Respects System Power Limits ==="
    log_info "  Requires: admin_setup.sh phase3 (cap=6000)"
    log_info "  Requires: strict_ordering in scheduler config"

    # Cap = 6000 W. Job1 takes 4000 W, leaving 2000 W headroom.
    # A default 1-node job (4000 W) cannot backfill, but one with explicit
    # user-requested 2000 W limit can.

    # Job 1: 1-node, long walltime, starts ASAP (uses 4000 W)
    local job1
    job1=$(submit_job -N ms427_tc7_j1 -koed -joe -l walltime=5:00 \
        -l "select=1" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep 120")
    log_info "  Job1 (1-node, long): ${job1}"

    # Job 2: 2-node, high priority. Would get 6000 W (clamped). Can't co-run.
    local job2
    job2=$(submit_job -N ms427_tc7_j2 -koed -joe -p1000 -l walltime=1:00 \
        -l "select=2" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "  Job2 (2-node, high-pri): ${job2}"

    # Job 3: 1-node, low priority. Would get 4000 W. Cannot backfill (4000+4000>6000).
    local job3
    job3=$(submit_job -N ms427_tc7_j3 -koed -joe -p0 -l walltime=1:00 \
        -l "select=1" \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "  Job3 (1-node, default power): ${job3}"

    # Job 4: 1-node, low priority, explicit 2000 W. Can backfill (4000+2000≤6000).
    local job4
    job4=$(submit_job -N ms427_tc7_j4 -koed -joe -p0 -l walltime=1:00 \
        -l "select=1" -l geopm-job-power-limit=2000 \
        -- /usr/bin/sh -c "echo Hey \$(hostname) && sleep ${JOB_SLEEP}")
    log_info "  Job4 (1-node, user 2000W): ${job4}"

    # Wait for Job1 to start, then allow time for backfill scheduling
    if ! wait_job_running "${job1}"; then
        log_fail "TC7: Job1 did not start within ${STARTUP_TIMEOUT}s"
        cleanup_jobs; wait_queue_empty 300; return
    fi
    sleep "${POLL_INTERVAL}"

    local s1 s2 s3 s4
    s1=$(get_job_state "${job1}")
    s2=$(get_job_state "${job2}")
    s3=$(get_job_state "${job3}")
    s4=$(get_job_state "${job4}")
    log_info "  States: j1=${s1} j2=${s2} j3=${s3} j4=${s4}"

    if [[ "${s1}" == "R" && "${s4}" == "R" && "${s2}" == "Q" && "${s3}" == "Q" ]]; then
        log_pass "TC7: User-capped Job4 backfilled; default-power Job3 blocked by power budget"
    elif [[ "${s1}" == "R" && "${s3}" == "R" ]]; then
        log_fail "TC7: Job3 running — power budget NOT constraining backfill"
    else
        log_info "TC7: j1=${s1} j2=${s2} j3=${s3} j4=${s4} — check manually"
    fi

    # Check power assignments
    local p1 p2 p3 p4
    p1=$(get_job_power_limit "${job1}")
    p2=$(get_job_power_limit "${job2}")
    p3=$(get_job_power_limit "${job3}")
    p4=$(get_job_power_limit "${job4}")
    log_info "  TC7 powers: j1=${p1:-?} j2=${p2:-?} j3=${p3:-?} j4=${p4:-?}"
    log_info "  Expected: j1=4000, j2=6000, j3=4000, j4=2000"

    cleanup_jobs
    wait_queue_empty 300
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
case "${TEST_ID}" in
    TC1|tc1|1) run_tc1 ;;
    TC2|tc2|2) run_tc2 ;;
    TC3|tc3|3) run_tc3 ;;
    TC4|tc4|4) run_tc4 ;;
    TC5|tc5|5) run_tc5 ;;
    TC6|tc6|6) run_tc6 ;;
    TC7|tc7|7) run_tc7 ;;
    phase1)
        run_tc1
        echo ""
        run_tc3
        echo ""
        run_tc4
        ;;
    phase2)
        run_tc6
        ;;
    phase3)
        run_tc2
        echo ""
        run_tc7
        ;;
    phase4)
        run_tc5
        ;;
    all)
        log_info "Running all phases — admin must have set resources for each."
        log_info "Consider running phase1/phase2/phase3/phase4 individually instead."
        run_tc1; echo ""
        run_tc3; echo ""
        run_tc4; echo ""
        run_tc6; echo ""
        run_tc2; echo ""
        run_tc7; echo ""
        run_tc5
        ;;
    *) cat <<EOF
Usage: $0 <test_or_phase>

Individual tests:
  TC1  TC2  TC3  TC4  TC5  TC6  TC7

Phase groups (run after admin sets the corresponding phase):
  phase1   TC1, TC3, TC4  (admin_setup.sh phase1, cap=100000)
  phase2   TC6            (admin_setup.sh phase2, cap=8000)
  phase3   TC2, TC7       (admin_setup.sh phase3, cap=6000)
  phase4   TC5            (admin_setup.sh phase4, cap=4000)

  all      Runs all (assumes resources already set appropriately)
EOF
        exit 1 ;;
esac
