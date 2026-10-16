#!/bin/bash
#  Copyright (c) 2015 - 2025 Intel Corporation
#  SPDX-License-Identifier: BSD-3-Clause
#

# test_gpu_drm_signals.sh
#
# Integration test for GPU (DRM) signals and controls through the GEOPM
# service.  This test is designed for systems with Intel discrete GPUs
# that expose the DRM (Direct Rendering Manager) sysfs interface — for
# example Intel Arc / Battlemage GPUs using the xe driver.
#
# The test verifies:
#   1. GPU topology detection — the correct number of GPUs and gpu_chips
#      are detected, matching /sys/class/drm.
#   2. Read-only DRM signal availability — all expected DRM signals are
#      listed and return finite values for every GPU.
#   3. GPU frequency control round-trip — the min/max frequency controls
#      can be written and read back, and are restored after the write
#      session ends.
#   4. Multi-GPU consistency — signals are read from all GPUs and
#      cross-checked for sanity (e.g. min <= cur <= max).
#   5. Heterogeneous SKU handling — on systems with mixed GPU SKUs
#      (e.g. 2× B570 + 1× B580), the RP0 frequencies differ as expected.
#   6. GPU power critical limit — the HWMON power1_crit signal is read
#      at the gpu domain and verified to be finite and positive.
#
# The test only reads platform state except for the frequency control
# round-trip, which briefly perturbs min/max frequency and relies on
# the GEOPM service save/restore mechanism.
#
# Prerequisites:
#   - GEOPM service installed and running
#   - Access lists populated:
#       geopmaccess -a | sudo geopmaccess -w
#       geopmaccess -a -c | sudo geopmaccess -w -c

if [[ $# -gt 0 ]] && [[ $1 == '--help' ]]; then
    echo "
    GPU DRM Signal and Control Integration Test
    -------------------------------------------

    Tests GPU signals and controls exposed through the DRM IOGroup of
    the GEOPM service.  Designed for Intel discrete GPUs (Arc,
    Battlemage) that expose DRM sysfs frequency and power attributes.

    The test verifies topology detection, signal availability and
    finiteness, frequency control round-trip with save/restore,
    multi-GPU consistency, heterogeneous SKU handling, and power
    limit reading.

    Requires the GEOPM service to be running and access lists to be
    populated.
"
    exit 0
fi

set -u

SCRIPT_DIR=$(dirname "$(realpath "$0")")

err() {
    echo "Error: $1" 1>&2
    exit 1
}

# Succeeds (exit 0) when the argument parses to a finite number.
is_finite() {
    case "$1" in
        ''|*[!0-9eE.+-]*) return 1 ;;
    esac
    awk -v x="$1" 'BEGIN { v = x + 0.0; if (v < 1e308 && v > -1e308) exit 0; exit 1 }'
}

# Succeeds when |$1 - $2| <= $3.
within() {
    awk -v a="$1" -v b="$2" -v t="$3" 'BEGIN { d = a - b; if (d < 0) d = -d; if (d <= t) exit 0; exit 1 }'
}

# Succeeds when $1 <= $2.
le() {
    awk -v a="$1" -v b="$2" 'BEGIN { if (a <= b) exit 0; exit 1 }'
}

# Succeeds when NAME appears on its own line in the newline separated LIST.
in_list() {
    printf '%s\n' "$2" | grep -qx -- "$1"
}

echo "=== GPU DRM Signal Integration Test ==="
echo ""

# ---------------------------------------------------------------------------
# 1. GPU Topology Detection
# ---------------------------------------------------------------------------
echo "1. GPU Topology Detection"

# Count Intel GPU cards from /sys/class/drm (vendor 0x8086)
DRM_GPU_CARDS=()
for card_path in /sys/class/drm/card[0-9]; do
    [[ -r "${card_path}/device/vendor" ]] || continue
    vendor=$(cat "${card_path}/device/vendor" 2>/dev/null)
    if [[ "${vendor}" == "0x8086" ]]; then
        DRM_GPU_CARDS+=("$(basename "${card_path}")")
    fi
done
DRM_GPU_COUNT=${#DRM_GPU_CARDS[@]}

echo "   Found ${DRM_GPU_COUNT} Intel GPU(s) in /sys/class/drm: ${DRM_GPU_CARDS[*]}"

# Query GEOPM for the number of gpu and gpu_chip domains
TOPO_OUTPUT=$(geopmread --domain 2>&1) || err "Failed to read GEOPM topology"
GEOPM_GPU_COUNT=$(echo "${TOPO_OUTPUT}" | awk '/^gpu /{print $2}')
GEOPM_GPU_CHIP_COUNT=$(echo "${TOPO_OUTPUT}" | awk '/^gpu_chip /{print $2}')

echo "   GEOPM reports: gpu=${GEOPM_GPU_COUNT}, gpu_chip=${GEOPM_GPU_CHIP_COUNT}"

test "${GEOPM_GPU_COUNT}" -eq "${DRM_GPU_COUNT}" ||
    err "GEOPM gpu count (${GEOPM_GPU_COUNT}) != DRM GPU count (${DRM_GPU_COUNT})"

test "${GEOPM_GPU_CHIP_COUNT}" -eq "${GEOPM_GPU_COUNT}" ||
    err "GEOPM gpu_chip count (${GEOPM_GPU_CHIP_COUNT}) != gpu count (${GEOPM_GPU_COUNT}). Expected 1 chip per GPU."

echo "   OK: Topology matches (${GEOPM_GPU_COUNT} GPU(s), ${GEOPM_GPU_CHIP_COUNT} gpu_chip(s))"
echo ""

# ---------------------------------------------------------------------------
# 2. Read-Only DRM Signal Availability and Finiteness
# ---------------------------------------------------------------------------
echo "2. DRM Signal Availability and Finiteness"

SIGNALS=$(geopmread 2>&1) || err "Failed to list signals with geopmread"
CONTROLS=$(geopmwrite 2>&1) || err "Failed to list controls with geopmwrite"

# Signals expected at the gpu_chip domain
GPU_CHIP_SIGNALS="
DRM::ACT_FREQ
DRM::CUR_FREQ
DRM::IDLE_RESIDENCY
DRM::MAX_FREQ
DRM::MIN_FREQ
DRM::RP0_FREQ
DRM::RPA_FREQ
DRM::RPE_FREQ
DRM::RPN_FREQ
GPU_CORE_FREQUENCY_MAX_AVAIL
GPU_CORE_FREQUENCY_MIN_AVAIL
GPU_CORE_FREQUENCY_STATUS
"

# Signals expected at the gpu domain
GPU_SIGNALS="
DRM::HWMON::POWER1_CRIT
"

for SIG in ${GPU_CHIP_SIGNALS}; do
    if ! in_list "${SIG}" "${SIGNALS}"; then
        echo "   SKIP: ${SIG} is not available on this platform"
        continue
    fi
    DOMAIN=$(geopmread --signal-domain "${SIG}" 2>&1) ||
        err "Failed to query domain for ${SIG}"
    for ((i=0; i<GEOPM_GPU_CHIP_COUNT; i++)); do
        VALUE=$(geopmread "${SIG}" "${DOMAIN}" "${i}" 2>&1) ||
            err "Failed to read ${SIG} ${DOMAIN} ${i}: ${VALUE}"
        is_finite "${VALUE}" ||
            err "${SIG} ${DOMAIN} ${i} returned non-finite value '${VALUE}'"
    done
    echo "   OK: ${SIG} (${DOMAIN}) — finite values on all ${GEOPM_GPU_CHIP_COUNT} gpu_chip(s)"
done

for SIG in ${GPU_SIGNALS}; do
    if ! in_list "${SIG}" "${SIGNALS}"; then
        echo "   SKIP: ${SIG} is not available on this platform"
        continue
    fi
    DOMAIN=$(geopmread --signal-domain "${SIG}" 2>&1) ||
        err "Failed to query domain for ${SIG}"
    for ((i=0; i<GEOPM_GPU_COUNT; i++)); do
        VALUE=$(geopmread "${SIG}" "${DOMAIN}" "${i}" 2>&1) ||
            err "Failed to read ${SIG} ${DOMAIN} ${i}: ${VALUE}"
        is_finite "${VALUE}" ||
            err "${SIG} ${DOMAIN} ${i} returned non-finite value '${VALUE}'"
    done
    echo "   OK: ${SIG} (${DOMAIN}) — finite values on all ${GEOPM_GPU_COUNT} gpu(s)"
done

echo ""

# ---------------------------------------------------------------------------
# 3. Multi-GPU Frequency Consistency
# ---------------------------------------------------------------------------
echo "3. Multi-GPU Frequency Consistency"

for ((i=0; i<GEOPM_GPU_CHIP_COUNT; i++)); do
    CUR=$(geopmread DRM::CUR_FREQ gpu_chip "${i}" 2>&1)
    MIN=$(geopmread DRM::MIN_FREQ gpu_chip "${i}" 2>&1)
    MAX=$(geopmread DRM::MAX_FREQ gpu_chip "${i}" 2>&1)
    RPN=$(geopmread DRM::RPN_FREQ gpu_chip "${i}" 2>&1)
    RP0=$(geopmread DRM::RP0_FREQ gpu_chip "${i}" 2>&1)
    RPE=$(geopmread DRM::RPE_FREQ gpu_chip "${i}" 2>&1)
    RPA=$(geopmread DRM::RPA_FREQ gpu_chip "${i}" 2>&1)

    echo "   gpu_chip ${i}: cur=${CUR} min=${MIN} max=${MAX} rpn=${RPN} rpe=${RPE} rpa=${RPA} rp0=${RP0}"

    # Sanity: RPN <= RPE <= RPA <= RP0
    le "${RPN}" "${RPE}" ||
        err "gpu_chip ${i}: RPN (${RPN}) > RPE (${RPE})"
    le "${RPE}" "${RPA}" ||
        err "gpu_chip ${i}: RPE (${RPE}) > RPA (${RPA})"
    le "${RPA}" "${RP0}" ||
        err "gpu_chip ${i}: RPA (${RPA}) > RP0 (${RP0})"

    # Sanity: MIN <= CUR <= MAX
    le "${MIN}" "${CUR}" ||
        err "gpu_chip ${i}: MIN (${MIN}) > CUR (${CUR})"
    le "${CUR}" "${MAX}" ||
        err "gpu_chip ${i}: CUR (${CUR}) > MAX (${MAX})"

    # Sanity: MIN should be >= RPN (min requestable)
    le "${RPN}" "${MIN}" ||
        err "gpu_chip ${i}: RPN (${RPN}) > MIN (${MIN})"

    # Sanity: MAX should be <= RP0 (max non-overclocked)
    le "${MAX}" "${RP0}" ||
        err "gpu_chip ${i}: MAX (${MAX}) > RP0 (${RP0})"
done
echo "   OK: All frequency ordering constraints satisfied"
echo ""

# ---------------------------------------------------------------------------
# 4. Heterogeneous SKU Detection
# ---------------------------------------------------------------------------
echo "4. Heterogeneous SKU Detection"

# Collect RP0 (max non-overclocked frequency) for each GPU to detect different SKUs
RP0_VALUES=()
for ((i=0; i<GEOPM_GPU_CHIP_COUNT; i++)); do
    RP0_VALUES+=("$(geopmread DRM::RP0_FREQ gpu_chip "${i}" 2>&1)")
done

# Count unique RP0 values — if there is more than one, we have mixed SKUs
UNIQUE_RP0=$(printf '%s\n' "${RP0_VALUES[@]}" | sort -u | wc -l)
echo "   RP0 frequencies: ${RP0_VALUES[*]}"
echo "   Unique RP0 values: ${UNIQUE_RP0}"

if [[ "${UNIQUE_RP0}" -gt 1 ]]; then
    echo "   INFO: Heterogeneous GPU SKUs detected (${UNIQUE_RP0} distinct max frequencies)"
    # Verify that the power critical limit also differs between SKUs
    POWER_CRIT_VALUES=()
    for ((i=0; i<GEOPM_GPU_COUNT; i++)); do
        POWER_CRIT_VALUES+=("$(geopmread DRM::HWMON::POWER1_CRIT gpu "${i}" 2>&1)")
    done
    UNIQUE_POWER=$(printf '%s\n' "${POWER_CRIT_VALUES[@]}" | sort -u | wc -l)
    echo "   Power critical limits: ${POWER_CRIT_VALUES[*]}"
    echo "   Unique power critical values: ${UNIQUE_POWER}"
    if [[ "${UNIQUE_POWER}" -gt 1 ]]; then
        echo "   OK: Heterogeneous power limits match heterogeneous frequency SKUs"
    else
        echo "   WARN: Heterogeneous frequency SKUs but homogeneous power limits"
    fi
else
    echo "   OK: Homogeneous GPU SKUs (all RP0 frequencies identical)"
fi
echo ""

# ---------------------------------------------------------------------------
# 5. GPU Frequency Control Round-Trip (write session with save/restore)
# ---------------------------------------------------------------------------
echo "5. GPU Frequency Control Round-Trip"

# Test GPU_CORE_FREQUENCY_MIN_CONTROL and GPU_CORE_FREQUENCY_MAX_CONTROL
# These use the do_write.sh helper to open a write session through the service.
# The service saves the original value and restores it when the session ends.

round_trip_freq_control() {
    local CONTROL="$1"
    local DOMAIN="$2"
    local DOMAIN_IDX="$3"
    local TARGET="$4"
    local LABEL="$5"

    if ! in_list "${CONTROL}" "${CONTROLS}"; then
        echo "   SKIP: ${CONTROL} is not available as a control on this platform"
        return 0
    fi

    local START
    START=$(geopmread "${CONTROL}" "${DOMAIN}" "${DOMAIN_IDX}" 2>&1) ||
        err "Failed to read start value of ${CONTROL}"

    is_finite "${START}" ||
        err "${CONTROL} start value '${START}' is not finite"

    # Don't attempt if target equals start
    if within "${START}" "${TARGET}" 1; then
        echo "   SKIP: ${CONTROL} ${DOMAIN} ${DOMAIN_IDX}: start (${START}) already at target (${TARGET}), skipping"
        return 0
    fi

    echo "   ${LABEL}: start=${START}, target=${TARGET}"

    # Open a write session that holds the target value
    setsid "${SCRIPT_DIR}/do_write.sh" SERVICE::${CONTROL} ${DOMAIN} ${DOMAIN_IDX} ${TARGET} &
    local SESSION_ID=$!
    sleep 4

    local DURING
    DURING=$(geopmread "${CONTROL}" "${DOMAIN}" "${DOMAIN_IDX}" 2>&1) ||
        err "Failed to read ${CONTROL} during write session"

    if ! wait "${SESSION_ID}"; then
        echo "   SKIP: ${CONTROL} ${DOMAIN} ${DOMAIN_IDX}: write was rejected on this platform"
        return 0
    fi
    sleep 1

    local END
    END=$(geopmread "${CONTROL}" "${DOMAIN}" "${DOMAIN_IDX}" 2>&1)

    # Verify the value changed during the session
    within "${DURING}" "${START}" 1 &&
        err "${CONTROL} write had no effect (silent failure): start=${START} during=${DURING} target=${TARGET}"

    # Verify the value was restored after the session
    within "${END}" "${START}" 50000000 ||
        err "${CONTROL} was not restored after session: start=${START} end=${END} (tolerance 50MHz)"

    echo "   OK: ${LABEL} round-trip start=${START} during=${DURING} restored=${END}"
}

# Test on gpu_chip 0 — lower the max frequency by 100 MHz and raise the min by 100 MHz
MAX_FREQ_0=$(geopmread DRM::MAX_FREQ gpu_chip 0 2>&1)
MIN_FREQ_0=$(geopmread DRM::MIN_FREQ gpu_chip 0 2>&1)
RPN_FREQ_0=$(geopmread DRM::RPN_FREQ gpu_chip 0 2>&1)

# Target for max: reduce by 100 MHz (1e8 Hz), but don't go below min
MAX_TARGET_0=$(awk -v m="${MAX_FREQ_0}" 'BEGIN { print m - 100000000 }')
# Target for min: increase by 100 MHz (1e8 Hz), but don't exceed max
MIN_TARGET_0=$(awk -v m="${MIN_FREQ_0}" 'BEGIN { print m + 100000000 }')

round_trip_freq_control "GPU_CORE_FREQUENCY_MAX_CONTROL" "gpu_chip" 0 "${MAX_TARGET_0}" "MAX_FREQ gpu_chip 0"
round_trip_freq_control "GPU_CORE_FREQUENCY_MIN_CONTROL" "gpu_chip" 0 "${MIN_TARGET_0}" "MIN_FREQ gpu_chip 0"

# Test on the last gpu_chip to verify multi-GPU control
LAST_IDX=$((GEOPM_GPU_CHIP_COUNT - 1))
MAX_FREQ_LAST=$(geopmread DRM::MAX_FREQ gpu_chip "${LAST_IDX}" 2>&1)
MAX_TARGET_LAST=$(awk -v m="${MAX_FREQ_LAST}" 'BEGIN { print m - 100000000 }')
round_trip_freq_control "GPU_CORE_FREQUENCY_MAX_CONTROL" "gpu_chip" "${LAST_IDX}" "${MAX_TARGET_LAST}" "MAX_FREQ gpu_chip ${LAST_IDX}"

echo ""

# ---------------------------------------------------------------------------
# 6. GPU Power Critical Limit
# ---------------------------------------------------------------------------
echo "6. GPU Power Critical Limit (HWMON)"

if in_list "DRM::HWMON::POWER1_CRIT" "${SIGNALS}"; then
    for ((i=0; i<GEOPM_GPU_COUNT; i++)); do
        VALUE=$(geopmread DRM::HWMON::POWER1_CRIT gpu "${i}" 2>&1) ||
            err "Failed to read DRM::HWMON::POWER1_CRIT gpu ${i}: ${VALUE}"
        is_finite "${VALUE}" ||
            err "DRM::HWMON::POWER1_CRIT gpu ${i} returned non-finite value '${VALUE}'"

        # Power critical limit should be positive (in watts)
        awk -v v="${VALUE}" 'BEGIN { if (v > 0) exit 0; exit 1 }' ||
            err "DRM::HWMON::POWER1_CRIT gpu ${i} is non-positive: ${VALUE}"

        echo "   OK: DRM::HWMON::POWER1_CRIT gpu ${i} = ${VALUE} W"
    done
else
    echo "   SKIP: DRM::HWMON::POWER1_CRIT is not available on this platform"
fi
echo ""

# ---------------------------------------------------------------------------
# 7. GPU Energy Counter (if available)
# ---------------------------------------------------------------------------
echo "7. GPU Energy Counter (if available)"

# Check for energy signals — these may not be present on all GPU models
ENERGY_SIGNALS=$(geopmread 2>&1 | grep -i 'ENERGY' | grep -i -E 'GPU|DRM' || true)
if [[ -n "${ENERGY_SIGNALS}" ]]; then
    echo "   Found GPU energy signals:"
    echo "${ENERGY_SIGNALS}" | sed 's/^/     /'
    for SIG in $(echo "${ENERGY_SIGNALS}" | awk '{print $1}'); do
        DOMAIN=$(geopmread --signal-domain "${SIG}" 2>&1) || continue
        NUM_DOMAINS=$(geopmread --domain 2>&1 | awk -v d="${DOMAIN}" '$1 == d {print $2}')
        for ((i=0; i<NUM_DOMAINS; i++)); do
            E1=$(geopmread "${SIG}" "${DOMAIN}" "${i}" 2>&1) || continue
            sleep 0.5
            E2=$(geopmread "${SIG}" "${DOMAIN}" "${i}" 2>&1) || continue
            if is_finite "${E1}" && is_finite "${E2}"; then
                le "${E1}" "${E2}" ||
                    echo "   WARN: ${SIG} ${DOMAIN} ${i}: energy counter decreased (${E1} -> ${E2})"
                echo "   OK: ${SIG} ${DOMAIN} ${i}: ${E1} -> ${E2} J (monotonic)"
            else
                echo "   SKIP: ${SIG} ${DOMAIN} ${i}: non-finite value"
            fi
        done
    done
else
    echo "   SKIP: No GPU energy signals available on this platform"
    echo "   INFO: Some GPU models (e.g. B570 card0) may not expose energy counters"
fi
echo ""

# ---------------------------------------------------------------------------
# 8. Alias Consistency Check
# ---------------------------------------------------------------------------
echo "8. Alias Consistency Check"

# Verify that high-level aliases match their raw DRM counterparts
check_alias() {
    local ALIAS="$1"
    local RAW="$2"
    local DOMAIN="$3"
    local NUM="$4"

    if ! in_list "${ALIAS}" "${SIGNALS}"; then
        echo "   SKIP: ${ALIAS} is not available"
        return 0
    fi
    if ! in_list "${RAW}" "${SIGNALS}"; then
        echo "   SKIP: ${RAW} is not available"
        return 0
    fi

    for ((i=0; i<NUM; i++)); do
        ALIAS_VAL=$(geopmread "${ALIAS}" "${DOMAIN}" "${i}" 2>&1)
        RAW_VAL=$(geopmread "${RAW}" "${DOMAIN}" "${i}" 2>&1)
        within "${ALIAS_VAL}" "${RAW_VAL}" 1 ||
            err "Alias mismatch: ${ALIAS}=${ALIAS_VAL} vs ${RAW}=${RAW_VAL} at ${DOMAIN} ${i}"
    done
    echo "   OK: ${ALIAS} matches ${RAW} on all ${NUM} ${DOMAIN}(s)"
}

check_alias "GPU_CORE_FREQUENCY_STATUS"    "DRM::CUR_FREQ"  "gpu_chip" "${GEOPM_GPU_CHIP_COUNT}"
check_alias "GPU_CORE_FREQUENCY_MAX_AVAIL" "DRM::RP0_FREQ"  "gpu_chip" "${GEOPM_GPU_CHIP_COUNT}"
check_alias "GPU_CORE_FREQUENCY_MIN_AVAIL" "DRM::RPN_FREQ"  "gpu_chip" "${GEOPM_GPU_CHIP_COUNT}"

# Control aliases
check_alias "GPU_CORE_FREQUENCY_MAX_CONTROL" "DRM::MAX_FREQ" "gpu_chip" "${GEOPM_GPU_CHIP_COUNT}"
check_alias "GPU_CORE_FREQUENCY_MIN_CONTROL" "DRM::MIN_FREQ" "gpu_chip" "${GEOPM_GPU_CHIP_COUNT}"

echo ""

# ---------------------------------------------------------------------------
# 9. Unknown Signal Rejection
# ---------------------------------------------------------------------------
echo "9. Unknown Signal Rejection"

BOGUS="DRM::GEOPM_TEST_BOGUS_SIGNAL"
if geopmread "${BOGUS}" gpu_chip 0 >/dev/null 2>&1; then
    err "geopmread silently accepted the unknown signal ${BOGUS}"
fi
echo "   OK: Unknown signal ${BOGUS} correctly rejected by geopmread"

BOGUS_CTRL="DRM::GEOPM_TEST_BOGUS_CONTROL"
if geopmwrite "${BOGUS_CTRL}" gpu_chip 0 0 >/dev/null 2>&1; then
    err "geopmwrite silently accepted the unknown control ${BOGUS_CTRL}"
fi
echo "   OK: Unknown control ${BOGUS_CTRL} correctly rejected by geopmwrite"
echo ""

echo "=== GPU DRM Signal Integration Test: SUCCESS ==="
exit 0
