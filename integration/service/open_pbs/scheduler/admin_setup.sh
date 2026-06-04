#!/bin/bash
#  Copyright (c) 2015 - 2025 Intel Corporation
#  SPDX-License-Identifier: BSD-3-Clause
#
# MS427 PBS Admin Setup Script
#
# This script is run by a PBS administrator to configure the server for
# MS427 scheduling tests. It creates an isolated 2-node test queue and
# sets the GEOPM power resources needed for each test phase.
#
# Usage:
#   ./admin_setup.sh create-queue <node1> <node2>   # One-time queue creation
#   ./admin_setup.sh phase1                          # TC1, TC3, TC4 (cap=100000)
#   ./admin_setup.sh phase2                          # TC6 (cap=8000)
#   ./admin_setup.sh phase3                          # TC2, TC7 (cap=6000)
#   ./admin_setup.sh phase4                          # TC5 (cap=4000)
#   ./admin_setup.sh teardown                        # Remove queue, unset resources
#
# The tester runs ./test_scheduling.sh for the matching test cases after
# the admin completes each phase setup.
#
# Power resources are set at the queue level only. Jobs in other queues
# (e.g., workq) are completely unaffected.

set -e

QUEUE_NAME="${GEOPM_TEST_QUEUE:-geopm-test}"
MIN_NODE_POWER="${MIN_NODE_POWER:-2400}"
MAX_NODE_POWER="${MAX_NODE_POWER:-4000}"

usage() {
    cat <<EOF
Usage: $0 <command> [args]

Commands:
  create-queue <node1> <node2>   Create isolated test queue with 2 nodes
  phase1                          Set cap=100000 (for TC1, TC3, TC4)
  phase2                          Set cap=8000  (for TC6)
  phase3                          Set cap=6000  (for TC2, TC7)
  phase4                          Set cap=4000  (for TC5)
  teardown                        Remove queue, unset resources, restore nodes

Environment:
  GEOPM_TEST_QUEUE   Queue name (default: geopm-test)
  MIN_NODE_POWER     Min node power in watts (default: 2400)
  MAX_NODE_POWER     Max node power in watts (default: 4000)

Test phase grouping (fewest admin changes):
  Phase 1: TC1, TC3, TC4  — cap not binding (high cap)
  Phase 2: TC6            — backfill with adequate power budget
  Phase 3: TC2, TC7       — moderate cap (serializes 2-node jobs)
  Phase 4: TC5            — tight cap (serializes 1-node jobs)
EOF
    exit 1
}

set_phase_resources() {
    local cap="$1"
    local phase_desc="$2"
    echo "Setting queue '${QUEUE_NAME}' power resources:"
    echo "  geopm-min-node-power-limit = ${MIN_NODE_POWER}"
    echo "  geopm-max-node-power-limit = ${MAX_NODE_POWER}"
    echo "  geopm-job-power-limit      = ${cap}  (${phase_desc})"
    qmgr -c "set queue ${QUEUE_NAME} resources_available.geopm-min-node-power-limit=${MIN_NODE_POWER}"
    qmgr -c "set queue ${QUEUE_NAME} resources_available.geopm-max-node-power-limit=${MAX_NODE_POWER}"
    qmgr -c "set queue ${QUEUE_NAME} resources_available.geopm-job-power-limit=${cap}"
    echo "Done. Tester can now run the corresponding test cases."
    echo ""
    echo "NOTE: These resources are set at the queue level only."
    echo "Jobs in other queues are unaffected."
}

cmd_create_queue() {
    local node1="${1:?Provide node1 hostname}"
    local node2="${2:?Provide node2 hostname}"

    echo "=== Creating test queue '${QUEUE_NAME}' with nodes: ${node1}, ${node2} ==="

    # Create the execution queue
    qmgr -c "create queue ${QUEUE_NAME} queue_type=execution"
    qmgr -c "set queue ${QUEUE_NAME} enabled=true"
    qmgr -c "set queue ${QUEUE_NAME} started=true"
    qmgr -c "set queue ${QUEUE_NAME} max_queued=20"

    # Assign the two nodes to this queue
    qmgr -c "set node ${node1} queue=${QUEUE_NAME}"
    qmgr -c "set node ${node2} queue=${QUEUE_NAME}"

    echo ""
    echo "Queue '${QUEUE_NAME}' created with nodes:"
    echo "  ${node1}"
    echo "  ${node2}"
    echo ""
    echo "These nodes are now dedicated to this queue and will not run workq jobs."
    echo ""
    echo "Tester should set: export GEOPM_TEST_QUEUE=${QUEUE_NAME}"
    echo "Then proceed with phase1."
}

cmd_phase1() {
    echo "=== Phase 1: TC1, TC3, TC4 (cap=100000, not binding) ==="
    set_phase_resources 100000 "not binding — tests that jobs run at full power"
    echo ""
    echo "Tester: run ./test_scheduling.sh TC1 && ./test_scheduling.sh TC3 && ./test_scheduling.sh TC4"
}

cmd_phase2() {
    echo "=== Phase 2: TC6 (cap=8000) ==="
    set_phase_resources 8000 "fits 2 single-node jobs — backfill test"
    echo ""
    echo "NOTE: TC6 requires strict_ordering in the scheduler config."
    echo "  Verify: grep strict_ordering \${PBS_HOME}/sched_priv/sched_config"
    echo "  If not set:"
    echo "    sed -i 's/^strict_ordering:.*$/strict_ordering: true ALL/' \${PBS_HOME}/sched_priv/sched_config"
    echo "    sed -i 's/^#job_sort_key:.*$/job_sort_key: \"job_priority HIGH\" ALL/' \${PBS_HOME}/sched_priv/sched_config"
    echo "    systemctl restart pbs  # or: /etc/init.d/pbs restart"
    echo ""
    echo "Tester: run ./test_scheduling.sh TC6"
}

cmd_phase3() {
    echo "=== Phase 3: TC2, TC7 (cap=6000) ==="
    set_phase_resources 6000 "serializes 2-node jobs, allows user-capped backfill"
    echo ""
    echo "Tester: run ./test_scheduling.sh TC2 && ./test_scheduling.sh TC7"
}

cmd_phase4() {
    echo "=== Phase 4: TC5 (cap=4000) ==="
    set_phase_resources 4000 "tight — serializes even 1-node jobs"
    echo ""
    echo "Tester: run ./test_scheduling.sh TC5"
}

cmd_teardown() {
    echo "=== Teardown: Removing test queue and unsetting resources ==="

    # Get nodes assigned to the test queue
    local nodes
    nodes=$(pbsnodes -a 2>/dev/null | awk -v q="${QUEUE_NAME}" '
        /^[^ ]/ { node=$1 }
        /queue = / && $3 == q { print node }
    ')

    # Move nodes back (unset queue assignment → goes back to default)
    if [[ -n "${nodes}" ]]; then
        echo "Releasing nodes from queue '${QUEUE_NAME}':"
        for node in ${nodes}; do
            echo "  ${node}"
            qmgr -c "unset node ${node} queue" 2>/dev/null || true
        done
    fi

    # Delete the queue
    qmgr -c "set queue ${QUEUE_NAME} enabled=false" 2>/dev/null || true
    qmgr -c "set queue ${QUEUE_NAME} started=false" 2>/dev/null || true
    qmgr -c "delete queue ${QUEUE_NAME}" 2>/dev/null || true

    echo "Teardown complete. Nodes returned to default queue."
}

# Main
case "${1:-}" in
    create-queue) shift; cmd_create_queue "$@" ;;
    phase1) cmd_phase1 ;;
    phase2) cmd_phase2 ;;
    phase3) cmd_phase3 ;;
    phase4) cmd_phase4 ;;
    teardown) cmd_teardown ;;
    *) usage ;;
esac
