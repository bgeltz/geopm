#!/usr/bin/env python3
#  Copyright (c) 2015 - 2025 Intel Corporation
#  SPDX-License-Identifier: BSD-3-Clause
#

"""
GPU DRM Signal Integration Test (Python / PlatformIO batch interface)
=====================================================================

This test exercises the GEOPM service's PlatformIO (pio) batch interface
for GPU signals exposed through the DRM IOGroup.  It is designed for
systems with Intel discrete GPUs (Arc, Battlemage) that expose DRM sysfs
attributes.

The test covers:
    1. Signal domain type queries for all GPU signals.
    2. Batch reading of GPU frequency signals across all gpu_chip domains.
    3. Frequency ordering invariants (RPN <= RPE <= RPA <= RP0, MIN <= CUR <= MAX).
    4. Heterogeneous SKU detection (different RP0 / power critical limits).
    5. GPU power critical limit reading at the gpu domain.
    6. Control round-trip: write min/max frequency, read back, verify restore.
    7. Alias consistency: high-level aliases match raw DRM signals.

The test uses the geopmdpy.pio module directly, which connects to the
GEOPM service via D-Bus.  It requires that the GEOPM service is running
and that access lists have been populated:

    geopmaccess -a | sudo geopmaccess -w
    geopmaccess -a -c | sudo geopmaccess -w -c
"""

import unittest
import time
import os
import subprocess # nosec

from geopmdpy import pio, topo


def is_finite(value):
    """Return True if value is a finite number."""
    try:
        v = float(value)
        return abs(v) < 1e308
    except (ValueError, TypeError):
        return False


class TestGPUDRMSignals(unittest.TestCase):
    """Integration test for GPU DRM signals through the GEOPM service."""

    # Signals at the gpu_chip domain
    GPU_CHIP_SIGNALS = [
        'DRM::ACT_FREQ',
        'DRM::CUR_FREQ',
        'DRM::IDLE_RESIDENCY',
        'DRM::MAX_FREQ',
        'DRM::MIN_FREQ',
        'DRM::RP0_FREQ',
        'DRM::RPA_FREQ',
        'DRM::RPE_FREQ',
        'DRM::RPN_FREQ',
    ]

    # High-level aliases at the gpu_chip domain
    GPU_CHIP_ALIASES = {
        'GPU_CORE_FREQUENCY_STATUS': 'DRM::CUR_FREQ',
        'GPU_CORE_FREQUENCY_MAX_AVAIL': 'DRM::RP0_FREQ',
        'GPU_CORE_FREQUENCY_MIN_AVAIL': 'DRM::RPN_FREQ',
    }

    # Controls at the gpu_chip domain
    GPU_CHIP_CONTROLS = [
        'GPU_CORE_FREQUENCY_MAX_CONTROL',
        'GPU_CORE_FREQUENCY_MIN_CONTROL',
    ]

    # Signals at the gpu domain
    GPU_SIGNALS = [
        'DRM::HWMON::POWER1_CRIT',
    ]

    @classmethod
    def setUpClass(cls):
        cls.num_gpu = topo.num_domain('gpu')
        cls.num_gpu_chip = topo.num_domain('gpu_chip')
        assert cls.num_gpu > 0, "No GPUs detected by GEOPM topology"
        assert cls.num_gpu_chip > 0, "No gpu_chip domains detected by GEOPM topology"
        print(f"\n  GPUs: {cls.num_gpu}, gpu_chips: {cls.num_gpu_chip}")

    def _read_all_domains(self, signal_name, domain_name):
        """Read a signal across all domains of the given type using direct reads."""
        num = topo.num_domain(domain_name)
        values = []
        for i in range(num):
            values.append(pio.read_signal(signal_name, domain_name, i))
        return values

    def test_01_topology(self):
        """GEOPM detects the correct number of GPUs and gpu_chips."""
        # Count Intel GPU cards from /sys/class/drm
        drm_gpu_count = 0
        drm_dir = '/sys/class/drm'
        for entry in sorted(os.listdir(drm_dir)):
            if not entry.startswith('card') or not entry[4:].isdigit():
                continue
            vendor_path = os.path.join(drm_dir, entry, 'device', 'vendor')
            if not os.path.isfile(vendor_path):
                continue
            try:
                with open(vendor_path) as f:
                    vendor = f.read().strip()
                if vendor == '0x8086':
                    drm_gpu_count += 1
            except (OSError, IOError):
                pass

        self.assertEqual(self.num_gpu, drm_gpu_count,
                         f"GEOPM gpu count ({self.num_gpu}) != DRM Intel GPU count ({drm_gpu_count})")
        self.assertEqual(self.num_gpu_chip, self.num_gpu,
                         f"gpu_chip count ({self.num_gpu_chip}) != gpu count ({self.num_gpu}). "
                         "Expected 1 chip per GPU.")
        print(f"  OK: Topology matches ({self.num_gpu} GPU(s))")

    def test_02_signal_availability(self):
        """All expected DRM signals are available and return finite values."""
        for signal in self.GPU_CHIP_SIGNALS:
            domain_type = pio.signal_domain_type(signal)
            domain_name = topo.domain_name(domain_type)
            values = self._read_all_domains(signal, domain_name)
            self.assertEqual(len(values), self.num_gpu_chip,
                             f"{signal}: expected {self.num_gpu_chip} values, got {len(values)}")
            for i, v in enumerate(values):
                self.assertTrue(is_finite(v),
                                f"{signal} {domain_name} {i} returned non-finite value '{v}'")
            print(f"  OK: {signal} ({domain_name}) — finite on all {len(values)} domain(s)")

        for signal in self.GPU_SIGNALS:
            domain_type = pio.signal_domain_type(signal)
            domain_name = topo.domain_name(domain_type)
            values = self._read_all_domains(signal, domain_name)
            self.assertEqual(len(values), self.num_gpu,
                             f"{signal}: expected {self.num_gpu} values, got {len(values)}")
            for i, v in enumerate(values):
                self.assertTrue(is_finite(v),
                                f"{signal} {domain_name} {i} returned non-finite value '{v}'")
                self.assertGreater(v, 0,
                                   f"{signal} {domain_name} {i} is non-positive: {v}")
            print(f"  OK: {signal} ({domain_name}) — finite and positive on all {len(values)} domain(s)")

    def test_03_frequency_ordering(self):
        """Frequency ordering invariants hold on every gpu_chip."""
        for i in range(self.num_gpu_chip):
            rpn = pio.read_signal('DRM::RPN_FREQ', 'gpu_chip', i)
            rpe = pio.read_signal('DRM::RPE_FREQ', 'gpu_chip', i)
            rpa = pio.read_signal('DRM::RPA_FREQ', 'gpu_chip', i)
            rp0 = pio.read_signal('DRM::RP0_FREQ', 'gpu_chip', i)
            min_freq = pio.read_signal('DRM::MIN_FREQ', 'gpu_chip', i)
            cur_freq = pio.read_signal('DRM::CUR_FREQ', 'gpu_chip', i)
            max_freq = pio.read_signal('DRM::MAX_FREQ', 'gpu_chip', i)

            print(f"  gpu_chip {i}: cur={cur_freq:.0f} min={min_freq:.0f} max={max_freq:.0f} "
                  f"rpn={rpn:.0f} rpe={rpe:.0f} rpa={rpa:.0f} rp0={rp0:.0f}")

            self.assertLessEqual(rpn, rpe, f"gpu_chip {i}: RPN ({rpn}) > RPE ({rpe})")
            self.assertLessEqual(rpe, rpa, f"gpu_chip {i}: RPE ({rpe}) > RPA ({rpa})")
            self.assertLessEqual(rpa, rp0, f"gpu_chip {i}: RPA ({rpa}) > RP0 ({rp0})")
            self.assertLessEqual(min_freq, cur_freq, f"gpu_chip {i}: MIN ({min_freq}) > CUR ({cur_freq})")
            self.assertLessEqual(cur_freq, max_freq, f"gpu_chip {i}: CUR ({cur_freq}) > MAX ({max_freq})")
            self.assertLessEqual(rpn, min_freq, f"gpu_chip {i}: RPN ({rpn}) > MIN ({min_freq})")
            self.assertLessEqual(max_freq, rp0, f"gpu_chip {i}: MAX ({max_freq}) > RP0 ({rp0})")

        print(f"  OK: All frequency ordering constraints satisfied on {self.num_gpu_chip} gpu_chip(s)")

    def test_04_heterogeneous_sku_detection(self):
        """Detect and validate heterogeneous GPU SKUs."""
        rp0_values = [pio.read_signal('DRM::RP0_FREQ', 'gpu_chip', i)
                      for i in range(self.num_gpu_chip)]
        unique_rp0 = set(rp0_values)
        print(f"  RP0 frequencies: {rp0_values}")
        print(f"  Unique RP0 values: {len(unique_rp0)}")

        if len(unique_rp0) > 1:
            print(f"  INFO: Heterogeneous GPU SKUs detected ({len(unique_rp0)} distinct max frequencies)")

            # Verify power critical limits also differ
            power_values = [pio.read_signal('DRM::HWMON::POWER1_CRIT', 'gpu', i)
                            for i in range(self.num_gpu)]
            unique_power = set(power_values)
            print(f"  Power critical limits: {power_values}")
            print(f"  Unique power critical values: {len(unique_power)}")

            if len(unique_power) > 1:
                print(f"  OK: Heterogeneous power limits match heterogeneous frequency SKUs")
            else:
                print(f"  WARN: Heterogeneous frequency SKUs but homogeneous power limits")
        else:
            print(f"  OK: Homogeneous GPU SKUs (all RP0 frequencies identical)")

    def test_05_alias_consistency(self):
        """High-level aliases match their raw DRM counterparts."""
        for alias, raw in self.GPU_CHIP_ALIASES.items():
            for i in range(self.num_gpu_chip):
                alias_val = pio.read_signal(alias, 'gpu_chip', i)
                raw_val = pio.read_signal(raw, 'gpu_chip', i)
                self.assertAlmostEqual(alias_val, raw_val, delta=1,
                                       msg=f"{alias} ({alias_val}) != {raw} ({raw_val}) at gpu_chip {i}")
            print(f"  OK: {alias} matches {raw} on all {self.num_gpu_chip} gpu_chip(s)")

    def test_06_control_round_trip(self):
        """GPU frequency controls can be written and are restored after the session."""
        for control in self.GPU_CHIP_CONTROLS:
            domain_type = pio.control_domain_type(control)
            domain_name = topo.domain_name(domain_type)
            num = topo.num_domain(domain_name)

            for i in range(num):
                start = pio.read_signal(control, domain_name, i)
                self.assertTrue(is_finite(start),
                                f"{control} {domain_name} {i}: start value not finite")

                # Pick a target that differs from start by 100 MHz (1e8 Hz)
                target = start - 1e8 if 'MAX' in control else start + 1e8

                # Don't test if target would be out of range
                rpn = pio.read_signal('DRM::RPN_FREQ', 'gpu_chip', i)
                rp0 = pio.read_signal('DRM::RP0_FREQ', 'gpu_chip', i)
                if target < rpn or target > rp0:
                    print(f"  SKIP: {control} {domain_name} {i}: target {target:.0f} out of range "
                          f"[{rpn:.0f}, {rp0:.0f}]")
                    continue

                if abs(target - start) < 1:
                    print(f"  SKIP: {control} {domain_name} {i}: start already at target")
                    continue

                # Write the control
                pio.write_control(control, domain_name, i, target)

                # Read back the control value (controls can be read as signals)
                during = pio.read_signal(control, domain_name, i)
                self.assertNotAlmostEqual(during, start, delta=1e7,
                                          msg=f"{control} {domain_name} {i}: write had no effect "
                                          f"(start={start}, during={during}, target={target})")
                self.assertAlmostEqual(during, target, delta=1e7,
                                      msg=f"{control} {domain_name} {i}: value during write ({during}) "
                                      f"!= target ({target})")

                # Restore the original value
                pio.write_control(control, domain_name, i, start)

                # Verify restoration
                end = pio.read_signal(control, domain_name, i)
                self.assertAlmostEqual(end, start, delta=5e7,
                                       msg=f"{control} {domain_name} {i}: not restored "
                                       f"(start={start}, end={end})")

                print(f"  OK: {control} {domain_name} {i} round-trip "
                      f"start={start:.0f} during={during:.0f} restored={end:.0f}")

    def test_07_batch_read_all_gpu_signals(self):
        """Batch-read all GPU signals simultaneously and verify finiteness."""
        all_signals = self.GPU_CHIP_SIGNALS + list(self.GPU_CHIP_ALIASES.keys())
        indices = []
        for signal in all_signals:
            domain_type = pio.signal_domain_type(signal)
            domain_name = topo.domain_name(domain_type)
            num = topo.num_domain(domain_name)
            for i in range(num):
                idx = pio.push_signal(signal, domain_name, i)
                indices.append((signal, domain_name, i, idx))

        pio.read_batch()

        for signal, domain_name, i, idx in indices:
            value = pio.sample(idx)
            self.assertTrue(is_finite(value),
                            f"{signal} {domain_name} {i}: non-finite value '{value}' in batch read")

        # Reset PlatformIO to free all pushed signals
        pio.reset()

        print(f"  OK: Batch read {len(indices)} signal/domain combinations — all finite")

    def test_08_unknown_signal_rejection(self):
        """Unknown DRM signals are rejected by the PlatformIO interface."""
        with self.assertRaises(RuntimeError):
            pio.signal_domain_type('DRM::BOGUS_SIGNAL')
        print("  OK: Unknown DRM signal rejected by pio.signal_domain_type")

        with self.assertRaises(RuntimeError):
            pio.push_signal('DRM::BOGUS_SIGNAL', 'gpu_chip', 0)
        print("  OK: Unknown DRM signal rejected by pio.push_signal")


if __name__ == '__main__':
    unittest.main(verbosity=2)
