#!/usr/bin/env python3
# Simple tester for GEOPM PBS hook config performance model coefficients.
# Reads a JSON config (geopm_pbs_config.json-like) and attempts to invert
# slowdown values via power_at_slowdown() to detect negative discriminants.
# Exits non-zero if any models produce a ValueError.

import argparse
import json
import sys
from typing import List, Tuple, Optional

# Import the inversion routine from the compute hook implementation.
try:
    from geopm_power_limit_compute import power_at_slowdown
except ImportError as e:
    print(f"Error: Unable to import geopm_power_limit_compute.power_at_slowdown: {e}", file=sys.stderr)
    sys.exit(2)


def parse_args():
    p = argparse.ArgumentParser(description="Validate performance model coefficients by probing power_at_slowdown().")
    p.add_argument("config", help="Path to JSON config file formatted per geopm_pbs_hook_config.schema.json")
    p.add_argument("--max-slowdown", type=float, default=1.0, help="Maximum slowdown value to probe (default: 1.0)")
    p.add_argument("--include-below-min", action="store_true", help="Probe a slowdown just below the theoretical minimum (should raise ValueError)")
    p.add_argument("--quiet", action="store_true", help="Suppress successful model messages")
    return p.parse_args()


def compute_min_slowdown(A: float, B: float, C: float) -> Optional[float]:
    """Return minimum achievable slowdown if A>0, else None (flat/linear)."""
    if A <= 0:
        return None
    return C - B**2 / (4 * A)


def build_probe_values(min_slowdown: Optional[float], max_slowdown: float, include_below_min: bool) -> List[float]:
    samples = [0.0]
    if min_slowdown is not None and min_slowdown >= 0:
        # Add min and a point just above it.
        samples.append(min_slowdown)
        samples.append(min_slowdown + 1e-9)
        if include_below_min and min_slowdown > 0:
            samples.append(min_slowdown - 1e-9)
    # Add a coarse grid up to max_slowdown.
    grid = [0.05, 0.1, 0.2, 0.5, max_slowdown]
    for g in grid:
        if g <= max_slowdown and g not in samples:
            samples.append(g)
    # Deduplicate and sort.
    samples = sorted(set([s for s in samples if s >= 0]))
    return samples


def check_model(model: dict, profile_name: str, host_name: Optional[str], max_slowdown: float, include_below_min: bool) -> Tuple[List[Tuple[float, str]], List[float]]:
    try:
        x0 = float(model['x0'])
        A = float(model['A'])
        B = float(model['B'])
        C = float(model['C'])
    except Exception as e:
        return [(0.0, f"Coefficient parse error: {e}")], []

    min_slowdown = compute_min_slowdown(A, B, C)
    probes = build_probe_values(min_slowdown, max_slowdown, include_below_min)

    failures = []
    tol = 5e-9
    for s in probes:
        try:
            power_at_slowdown(s, [x0], [A], [B], [C])
        except ValueError as ve:
            # Suppress failures that are only due to tiny positive baseline slowdown within tolerance.
            if min_slowdown is not None and s == 0.0 and min_slowdown < tol:
                continue
            failures.append((s, str(ve)))
        except Exception as e:
            failures.append((s, f"Unexpected error: {e}"))
    return failures, probes


def main():
    args = parse_args()
    try:
        with open(args.config) as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"Error: Unable to load JSON config: {e}", file=sys.stderr)
        return 2

    profiles = cfg.get('profiles', {})
    if not profiles:
        print("Error: Config missing 'profiles' section", file=sys.stderr)
        return 2

    overall_failures = 0

    for profile_name, profile_data in profiles.items():
        # Profile may define host models or a single model.
        if 'hosts' in profile_data:
            for host_name, host_data in profile_data['hosts'].items():
                failures, probes = check_model(host_data['model'], profile_name, host_name, args.max_slowdown, args.include_below_min)
                if failures:
                    overall_failures += 1
                    print(f"FAIL: profile='{profile_name}' host='{host_name}'")
                    for slowdown_value, err in failures:
                        print(f"  slowdown={slowdown_value}: {err}")
                else:
                    if not args.quiet:
                        print(f"OK: profile='{profile_name}' host='{host_name}' probed {len(probes)} slowdown values")
        else:
            if 'model' not in profile_data:
                print(f"WARN: profile '{profile_name}' missing 'model' key; skipping")
                continue
            failures, probes = check_model(profile_data['model'], profile_name, None, args.max_slowdown, args.include_below_min)
            if failures:
                overall_failures += 1
                print(f"FAIL: profile='{profile_name}' (single model)")
                for slowdown_value, err in failures:
                    print(f"  slowdown={slowdown_value}: {err}")
            else:
                if not args.quiet:
                    print(f"OK: profile='{profile_name}' probed {len(probes)} slowdown values")

    if overall_failures:
        print(f"Summary: {overall_failures} model(s) produced errors.")
        return 1
    else:
        if not args.quiet:
            print("Summary: All models passed.")
        return 0


if __name__ == '__main__':
    sys.exit(main())
