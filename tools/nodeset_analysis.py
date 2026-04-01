#!/usr/bin/env python3
"""Nodeset analysis: compute or find node sets for non-uniform power capping.

Subcommands
-----------
compute  Given a node-set file and power budget, report the expected
         worst-node FOM improvement (non-uniform vs uniform).
find     Given a target improvement %, Monte-Carlo sample from a host pool
         and return the node set closest to that target.

Examples
--------
  # Compute improvement for a specific node set (quadratic model)
  ./nodeset_analysis.py compute \\
      models/426/nekbone_426.json \\
      my_nodeset.txt \\
      --power 3000

  # Same, but using real sweep data instead of the model
  ./nodeset_analysis.py compute \\
      models/426/nekbone_426.json \\
      my_nodeset.txt \\
      --power 3000 \\
      --real-data --cache-dir .compare_cache

  # Find a node set that yields ~2.5 % improvement (quadratic model)
  ./nodeset_analysis.py find \\
      models/426/nekbone_426.json \\
      model_hosts \\
      --power 3000 \\
      --target-improvement 2.5 \\
      --output best_nodeset.txt

  # Same, but using real sweep data instead of the model
  ./nodeset_analysis.py find \\
      models/426/nekbone_426.json \\
      model_hosts \\
      --power 3000 \\
      --target-improvement 2.5 \\
      --output best_nodeset.txt \\
      --real-data --cache-dir .compare_cache
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest import mock

import numpy as np

# ---------------------------------------------------------------------------
# Bootstrap: make geopm_power_limit_compute importable
# ---------------------------------------------------------------------------
_hook_dir = str(Path(__file__).resolve().parent.parent
                / "integration" / "service" / "open_pbs")
if _hook_dir not in sys.path:
    sys.path.insert(0, _hook_dir)

_pbs_mock = mock.MagicMock()
_pbs_mock.hook_config_filename = None
mock.patch.dict("sys.modules", pbs=_pbs_mock).start()
import geopm_power_limit_compute as compute_hook  # noqa: E402

# Ensure geopmpy can be imported (plot.py / compare.py import it at module level).
try:
    import geopmpy  # noqa: F401
except ImportError:
    _geopmpy_mock = mock.MagicMock()
    sys.modules.setdefault("geopmpy", _geopmpy_mock)
    sys.modules.setdefault("geopmpy.io", _geopmpy_mock)


# ---------------------------------------------------------------------------
# Model helpers (shared with simulate_nonuniform.py)
# ---------------------------------------------------------------------------

def load_model(model_path: str, job_type: str) -> tuple:
    """Load model JSON; return (max_power, {host: {x0, A, B, C}})."""
    with open(model_path) as f:
        config = json.load(f)
    max_power = config["max_power"]
    profile = config["profiles"][job_type]
    hosts = {}
    for host_name, host_data in profile["hosts"].items():
        m = host_data["model"]
        hosts[host_name] = {
            "x0": float(m["x0"]),
            "A": float(m["A"]),
            "B": float(m["B"]),
            "C": float(m["C"]),
        }
    return max_power, hosts


def load_hosts(path: str) -> List[str]:
    """Read a one-hostname-per-line file."""
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def exclude_hosts(all_hosts: List[str], filepath: str, label: str) -> List[str]:
    """Remove hosts listed in *filepath* from *all_hosts*."""
    with open(filepath) as f:
        exclude_set = {line.split()[0] for line in f
                       if line.strip() and not line.startswith("#")}
    before = len(all_hosts)
    result = [h for h in all_hosts if h not in exclude_set]
    print(f"Excluded {before - len(result)} {label} host(s) "
          f"via {filepath}, {len(result)} remaining")
    return result


# ---------------------------------------------------------------------------
# Real-data helpers (piecewise-linear interpolation)
# ---------------------------------------------------------------------------

import pandas as pd  # noqa: E402


def load_real_data(args: argparse.Namespace) -> pd.DataFrame:
    """Load sweep data from --sweep dirs or pre-built HDF5 caches."""
    from plot import load_cached_data, validate_sweep_dataset, find_fom_outliers

    cache_root = Path(args.cache_dir).expanduser().resolve()
    if args.sweep:
        from compare import load_raw_host_data
        sweep_dirs = [Path(d).expanduser().resolve() for d in args.sweep]
        sections = load_raw_host_data(sweep_dirs, "sweep", cache_root)
    else:
        sections = load_cached_data(str(cache_root))

    if "totals" not in sections or sections["totals"].empty:
        raise RuntimeError("No totals data found.")

    df = validate_sweep_dataset(sections["totals"])

    if getattr(args, "outliers_rules", None):
        outlier_hosts = find_fom_outliers(df, args.outliers_rules)
        if outlier_hosts:
            df = df[~df["host"].isin(outlier_hosts)].reset_index(drop=True)
            print(f"Removed {len(outlier_hosts)} rule-based outlier host(s)")

    return df


def build_host_curves(
    df: pd.DataFrame,
) -> Tuple[Dict[str, Tuple[np.ndarray, np.ndarray]], List[int]]:
    """Build per-host FOM(power) lookup arrays from averaged sweep data."""
    col = "BOARD_POWER_LIMIT_CONTROL"
    metric = "FOM"

    df = df.copy()
    df[col] = df[col].astype(int)
    df = df.dropna(subset=[metric])
    avg = df.groupby(["host", col], as_index=False)[metric].mean()

    measured_levels = sorted(avg[col].unique())
    host_curves: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}

    for host, hdf in avg.groupby("host"):
        hdf = hdf.sort_values(col)
        power_arr = hdf[col].values.astype(float)
        fom_arr = hdf[metric].values.astype(float)
        if np.any(np.isnan(fom_arr)):
            continue
        fom_arr = np.maximum.accumulate(fom_arr)
        host_curves[str(host)] = (power_arr, fom_arr)

    return host_curves, measured_levels


def fom_at_power(power: float, curve: Tuple[np.ndarray, np.ndarray]) -> float:
    """Piecewise-linear interpolation of FOM at a given power level."""
    return float(np.interp(power, curve[0], curve[1]))


def power_at_fom(target_fom: float, curve: Tuple[np.ndarray, np.ndarray]) -> float:
    """Inverse piecewise-linear interpolation: minimum power to achieve target_fom."""
    powers, foms = curve
    if target_fom <= foms[0]:
        return float(powers[0])
    if target_fom >= foms[-1]:
        return float(powers[-1])
    idx = int(np.searchsorted(foms, target_fom, side="left"))
    idx = max(1, min(idx, len(foms) - 1))
    f0, f1 = foms[idx - 1], foms[idx]
    p0, p1 = powers[idx - 1], powers[idx]
    if f1 == f0:
        return float(p0)
    t = (target_fom - f0) / (f1 - f0)
    return float(p0 + t * (p1 - p0))


def allocate_nonuniform(
    host_names: List[str],
    host_curves: Dict[str, Tuple[np.ndarray, np.ndarray]],
    avg_power: float,
) -> Tuple[float, List[float]]:
    """Bisect to find equal-FOM allocation for a total power budget."""
    num_nodes = len(host_names)
    total_budget = num_nodes * avg_power
    curves = [host_curves[h] for h in host_names]

    peak_fom = [float(c[1].max()) for c in curves]
    min_fom = [float(c[1].min()) for c in curves]

    fom_upper = min(peak_fom)
    fom_lower = min(min_fom)

    for _ in range(60):
        mid = (fom_lower + fom_upper) / 2.0
        powers = [power_at_fom(mid, c) for c in curves]
        total = sum(powers)
        if total > total_budget + 0.1:
            fom_upper = mid
        elif total < total_budget - 0.1:
            fom_lower = mid
        else:
            break

    target_fom = (fom_lower + fom_upper) / 2.0
    power_by_host = [power_at_fom(target_fom, c) for c in curves]
    return target_fom, power_by_host


# ---------------------------------------------------------------------------
# compute subcommand
# ---------------------------------------------------------------------------

def compute_improvement(
    host_names: List[str],
    host_models: dict,
    max_node_power: float,
    avg_power_per_node: int,
    host_curves: Optional[Dict[str, Tuple[np.ndarray, np.ndarray]]] = None,
) -> dict:
    """Compute non-uniform vs uniform improvement for a fixed node set.

    Returns a dict with summary and per-node details.
    """
    num_nodes = len(host_names)
    job_budget = num_nodes * avg_power_per_node

    if host_curves is not None:
        # --- Real-data path -----------------------------------------------
        target_fom, power_by_node = allocate_nonuniform(
            host_names, host_curves, float(avg_power_per_node),
        )
        fom_nu = [fom_at_power(p, host_curves[h])
                  for h, p in zip(host_names, power_by_node)]
        fom_uniform = [fom_at_power(avg_power_per_node, host_curves[h])
                       for h in host_names]

        worst_nu = min(fom_nu)
        worst_uniform = min(fom_uniform)
        improvement = ((worst_nu - worst_uniform) / worst_uniform * 100
                       if worst_uniform > 0 else 0.0)

        worst_nu_idx = fom_nu.index(worst_nu)
        worst_uni_idx = fom_uniform.index(worst_uniform)

        per_node = []
        for i, h in enumerate(host_names):
            per_node.append({
                "host": h,
                "power_nonuniform": power_by_node[i],
                "fom_nonuniform": fom_nu[i],
                "fom_uniform": fom_uniform[i],
            })

        return {
            "method": "real-data (piecewise-linear)",
            "num_nodes": num_nodes,
            "power_budget_per_node": avg_power_per_node,
            "job_budget": job_budget,
            "target_fom_nonuniform": target_fom,
            "worst_fom_nonuniform": worst_nu,
            "worst_host_nonuniform": host_names[worst_nu_idx],
            "worst_fom_uniform": worst_uniform,
            "worst_host_uniform": host_names[worst_uni_idx],
            "improvement_pct": improvement,
            "per_node": per_node,
        }
    else:
        # --- Quadratic-model path -----------------------------------------
        x0 = [host_models[h]["x0"] for h in host_names]
        A = [host_models[h]["A"] for h in host_names]
        B = [host_models[h]["B"] for h in host_names]
        C = [host_models[h]["C"] for h in host_names]

        slowdown_nu, power_by_node = compute_hook.allocate_budget_to_nodes(
            job_budget, max_node_power, x0, A, B, C,
        )
        normalized_power = [p / max_node_power for p in power_by_node]
        slowdown_by_node_nu = [
            An * (x0n - pn) ** 2 + Bn * (x0n - pn) + Cn
            for x0n, An, Bn, Cn, pn in zip(x0, A, B, C, normalized_power)
        ]

        norm_uniform = avg_power_per_node / max_node_power
        slowdown_by_node_uniform = [
            An * (x0n - norm_uniform) ** 2 + Bn * (x0n - norm_uniform) + Cn
            for x0n, An, Bn, Cn in zip(x0, A, B, C)
        ]

        worst_nu_idx = slowdown_by_node_nu.index(max(slowdown_by_node_nu))
        worst_uni_idx = slowdown_by_node_uniform.index(max(slowdown_by_node_uniform))
        improvement = (max(slowdown_by_node_uniform) - max(slowdown_by_node_nu)) * 100

        per_node = []
        for i, h in enumerate(host_names):
            per_node.append({
                "host": h,
                "power_nonuniform": power_by_node[i],
                "slowdown_nonuniform": slowdown_by_node_nu[i],
                "slowdown_uniform": slowdown_by_node_uniform[i],
            })

        return {
            "method": "quadratic model",
            "num_nodes": num_nodes,
            "power_budget_per_node": avg_power_per_node,
            "job_budget": job_budget,
            "max_node_power": max_node_power,
            "worst_slowdown_nonuniform": max(slowdown_by_node_nu),
            "worst_host_nonuniform": host_names[worst_nu_idx],
            "worst_slowdown_uniform": max(slowdown_by_node_uniform),
            "worst_host_uniform": host_names[worst_uni_idx],
            "improvement_pct": improvement,
            "per_node": per_node,
        }


def print_compute_result(result: dict) -> None:
    """Pretty-print a compute result."""
    print(f"\n{'='*70}")
    print(f"  Method: {result['method']}")
    print(f"  Nodes: {result['num_nodes']}")
    print(f"  Power budget per node: {result['power_budget_per_node']} W")
    print(f"  Total job budget: {result['job_budget']} W")
    print(f"{'='*70}")

    if "target_fom_nonuniform" in result:
        # Real-data results
        print(f"\n  Non-uniform target FOM:  {result['target_fom_nonuniform']:.2f}")
        print(f"  Worst FOM (non-uniform): {result['worst_fom_nonuniform']:.2f}  "
              f"({result['worst_host_nonuniform']})")
        print(f"  Worst FOM (uniform):     {result['worst_fom_uniform']:.2f}  "
              f"({result['worst_host_uniform']})")
    else:
        # Quadratic model results
        print(f"\n  Max node power: {result['max_node_power']} W")
        print(f"  Worst slowdown (non-uniform): {result['worst_slowdown_nonuniform']:.6f}  "
              f"({result['worst_host_nonuniform']})")
        print(f"  Worst slowdown (uniform):     {result['worst_slowdown_uniform']:.6f}  "
              f"({result['worst_host_uniform']})")

    print(f"\n  >>> Improvement: {result['improvement_pct']:.4f} %")
    print()

    # Per-node table
    per_node = result["per_node"]
    if "fom_nonuniform" in per_node[0]:
        print(f"  {'Host':<25s} {'Power(NU)':>10s} {'FOM(NU)':>12s} {'FOM(Uni)':>12s}")
        print(f"  {'-'*25} {'-'*10} {'-'*12} {'-'*12}")
        for n in per_node:
            print(f"  {n['host']:<25s} {n['power_nonuniform']:>10.1f} "
                  f"{n['fom_nonuniform']:>12.1f} {n['fom_uniform']:>12.1f}")
    else:
        print(f"  {'Host':<25s} {'Power(NU)':>10s} {'Slow(NU)':>12s} {'Slow(Uni)':>12s}")
        print(f"  {'-'*25} {'-'*10} {'-'*12} {'-'*12}")
        for n in per_node:
            print(f"  {n['host']:<25s} {n['power_nonuniform']:>10.1f} "
                  f"{n['slowdown_nonuniform']:>12.6f} {n['slowdown_uniform']:>12.6f}")


# ---------------------------------------------------------------------------
# find subcommand
# ---------------------------------------------------------------------------

def find_nodeset(
    all_hosts: List[str],
    host_models: dict,
    max_node_power: float,
    avg_power_per_node: int,
    target_improvement: float,
    num_nodes: int,
    iterations: int,
    seed: Optional[int] = None,
    host_curves: Optional[Dict[str, Tuple[np.ndarray, np.ndarray]]] = None,
) -> dict:
    """Monte-Carlo search for a node set matching a target improvement.

    When *host_curves* is provided, uses piecewise-linear interpolation
    of real sweep data.  Otherwise uses the quadratic model.

    Returns the best match including the node list and improvement.
    """
    if seed is not None:
        random.seed(seed)

    best = None
    best_diff = float("inf")

    for i in range(iterations):
        sample = random.sample(all_hosts, num_nodes)

        if host_curves is not None:
            # --- Real-data path -------------------------------------------
            _target_fom, power_by_node = allocate_nonuniform(
                sample, host_curves, float(avg_power_per_node),
            )
            fom_nu = [fom_at_power(p, host_curves[h])
                      for h, p in zip(sample, power_by_node)]
            fom_uniform = [fom_at_power(avg_power_per_node, host_curves[h])
                           for h in sample]
            worst_nu = min(fom_nu)
            worst_uniform = min(fom_uniform)
            if worst_uniform <= 0:
                improvement = 0.0
            else:
                improvement = (worst_nu - worst_uniform) / worst_uniform * 100
        else:
            # --- Quadratic-model path -------------------------------------
            job_budget = num_nodes * avg_power_per_node
            x0 = [host_models[h]["x0"] for h in sample]
            A = [host_models[h]["A"] for h in sample]
            B = [host_models[h]["B"] for h in sample]
            C = [host_models[h]["C"] for h in sample]

            _slowdown_nu, power_by_node = compute_hook.allocate_budget_to_nodes(
                job_budget, max_node_power, x0, A, B, C,
            )
            normalized_power = [p / max_node_power for p in power_by_node]
            slowdown_by_node_nu = [
                An * (x0n - pn) ** 2 + Bn * (x0n - pn) + Cn
                for x0n, An, Bn, Cn, pn in zip(x0, A, B, C, normalized_power)
            ]
            norm_uniform = avg_power_per_node / max_node_power
            slowdown_by_node_uniform = [
                An * (x0n - norm_uniform) ** 2 + Bn * (x0n - norm_uniform) + Cn
                for x0n, An, Bn, Cn in zip(x0, A, B, C)
            ]
            improvement = (max(slowdown_by_node_uniform) - max(slowdown_by_node_nu)) * 100

        diff = abs(improvement - target_improvement)

        if diff < best_diff:
            best_diff = diff
            best = {
                "hosts": list(sample),
                "improvement_pct": improvement,
                "diff_from_target": diff,
                "iteration": i,
            }

        if (i + 1) % 1000 == 0:
            print(f"  {i + 1}/{iterations} iterations, "
                  f"best so far: {best['improvement_pct']:.4f}% "
                  f"(diff={best['diff_from_target']:.4f})")

    return best


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def add_common_args(p: argparse.ArgumentParser) -> None:
    """Add arguments shared between subcommands."""
    p.add_argument("model", help="Path to the model JSON file")
    p.add_argument("--job-type", default="nekbone",
                   help="Profile name in the model JSON (default: nekbone)")
    p.add_argument("--power", type=int, required=True,
                   help="Per-node power budget in watts")
    p.add_argument("--outliers", default=None,
                   help="File listing outlier hosts to exclude")
    p.add_argument("--partial", default=None,
                   help="File listing hosts with partial power-limit data to exclude")
    p.add_argument("--missing-fom", default=None,
                   help="File listing hosts missing FOM data to exclude")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    # -- compute -----------------------------------------------------------
    p_compute = sub.add_parser(
        "compute",
        help="Compute improvement for a given node set",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_args(p_compute)
    p_compute.add_argument("nodeset",
                           help="File listing the node set (one host per line)")
    p_compute.add_argument("--real-data", action="store_true",
                           help="Use real power-sweep data instead of the "
                                "quadratic model")
    p_compute.add_argument("--sweep", nargs="+", default=None,
                           help="(requires --real-data) Paths to power-sweep "
                                "dataset directories")
    p_compute.add_argument("--cache-dir", default=".compare_cache",
                           help="(requires --real-data) Directory for HDF5 "
                                "caches (default: ./.compare_cache)")
    p_compute.add_argument("--outliers-rules", nargs="+", default=None,
                           metavar="POWER,OP,THRESH",
                           help="(requires --real-data) FOM outlier rules")

    # -- find --------------------------------------------------------------
    p_find = sub.add_parser(
        "find",
        help="Find a node set matching a target improvement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_args(p_find)
    p_find.add_argument("hosts",
                        help="File listing the full host pool (one per line)")
    p_find.add_argument("--target-improvement", type=float, required=True,
                        help="Target FOM improvement percentage")
    p_find.add_argument("--num-nodes", type=int, default=128,
                        help="Nodes per sample (default: 128)")
    p_find.add_argument("--iterations", type=int, default=10000,
                        help="Monte Carlo iterations (default: 10000)")
    p_find.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    p_find.add_argument("--output", "-o", required=True,
                        help="Output file for the best node set")
    p_find.add_argument("--real-data", action="store_true",
                        help="Use real power-sweep data instead of the "
                             "quadratic model")
    p_find.add_argument("--sweep", nargs="+", default=None,
                        help="(requires --real-data) Paths to power-sweep "
                             "dataset directories")
    p_find.add_argument("--cache-dir", default=".compare_cache",
                        help="(requires --real-data) Directory for HDF5 "
                             "caches (default: ./.compare_cache)")
    p_find.add_argument("--outliers-rules", nargs="+", default=None,
                        metavar="POWER,OP,THRESH",
                        help="(requires --real-data) FOM outlier rules")

    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    # Load model (needed for both subcommands)
    max_power, host_models = load_model(args.model, args.job_type)
    print(f"Model: {args.model}  (max_power={max_power})")

    if args.command == "compute":
        nodeset = load_hosts(args.nodeset)

        # Apply exclusions
        if args.outliers:
            nodeset = exclude_hosts(nodeset, args.outliers, "outlier")
        if args.partial:
            nodeset = exclude_hosts(nodeset, args.partial, "partial-data")
        if args.missing_fom:
            nodeset = exclude_hosts(nodeset, args.missing_fom, "missing-FOM")

        # Check hosts exist in model
        missing = [h for h in nodeset if h not in host_models]
        if missing:
            print(f"WARNING: {len(missing)} host(s) not in model, excluding")
            nodeset = [h for h in nodeset if h in host_models]

        if not nodeset:
            print("ERROR: no hosts remaining after filtering")
            return 1

        # Load real data if requested
        host_curves = None
        if args.real_data:
            df_real = load_real_data(args)
            host_curves, measured_levels = build_host_curves(df_real)
            print(f"Real data: {len(host_curves)} hosts at "
                  f"{len(measured_levels)} power levels: {measured_levels}")

            no_data = [h for h in nodeset if h not in host_curves]
            if no_data:
                print(f"WARNING: {len(no_data)} host(s) not in real data, "
                      f"excluding")
                nodeset = [h for h in nodeset if h in host_curves]

            if not nodeset:
                print("ERROR: no hosts remaining after real-data filtering")
                return 1

        print(f"Computing improvement for {len(nodeset)} nodes "
              f"at {args.power} W per node ...")

        result = compute_improvement(
            nodeset, host_models, max_power, args.power,
            host_curves=host_curves,
        )
        print_compute_result(result)

    elif args.command == "find":
        all_hosts = load_hosts(args.hosts)

        # Apply exclusions
        if args.outliers:
            all_hosts = exclude_hosts(all_hosts, args.outliers, "outlier")
        if args.partial:
            all_hosts = exclude_hosts(all_hosts, args.partial, "partial-data")
        if args.missing_fom:
            all_hosts = exclude_hosts(all_hosts, args.missing_fom, "missing-FOM")

        # Drop hosts not in model
        missing = [h for h in all_hosts if h not in host_models]
        if missing:
            print(f"WARNING: {len(missing)} host(s) not in model, excluding")
            all_hosts = [h for h in all_hosts if h in host_models]

        # Load real data if requested
        host_curves = None
        if args.real_data:
            df_real = load_real_data(args)
            host_curves, measured_levels = build_host_curves(df_real)
            print(f"Real data: {len(host_curves)} hosts at "
                  f"{len(measured_levels)} power levels: {measured_levels}")

            no_data = [h for h in all_hosts if h not in host_curves]
            if no_data:
                print(f"WARNING: {len(no_data)} host(s) not in real data, "
                      f"excluding")
                all_hosts = [h for h in all_hosts if h in host_curves]

        if len(all_hosts) < args.num_nodes:
            print(f"ERROR: only {len(all_hosts)} hosts available, "
                  f"need {args.num_nodes}")
            return 1

        method = "real-data" if host_curves else "quadratic model"
        print(f"Host pool: {len(all_hosts)} hosts")
        print(f"Method: {method}")
        print(f"Target improvement: {args.target_improvement:.4f}%")
        print(f"Sampling {args.num_nodes} nodes × {args.iterations} "
              f"iterations at {args.power} W per node ...\n")

        result = find_nodeset(
            all_hosts, host_models, max_power, args.power,
            target_improvement=args.target_improvement,
            num_nodes=args.num_nodes,
            iterations=args.iterations,
            seed=args.seed,
            host_curves=host_curves,
        )

        print(f"\n{'='*70}")
        print(f"  Best match: {result['improvement_pct']:.4f}% "
              f"(target: {args.target_improvement:.4f}%, "
              f"diff: {result['diff_from_target']:.4f}%)")
        print(f"  Found at iteration {result['iteration']}")
        print(f"{'='*70}\n")

        # Write node set
        with open(args.output, "w") as f:
            for h in sorted(result["hosts"]):
                f.write(h + "\n")
        print(f"Wrote {len(result['hosts'])} hosts to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
