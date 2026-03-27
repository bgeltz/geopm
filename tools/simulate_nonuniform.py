#!/usr/bin/env python3
"""Monte Carlo simulation: non-uniform vs uniform power-capping improvement.

Samples random N-host subsets from a model host pool, computes the
worst-node slowdown improvement of non-uniform over uniform capping,
and plots the distribution as a violin plot across power budgets.

Usage:
  ./simulate_nonuniform.py \\
      models_2026-02-09_1612/426/nekbone_426.json \\
      model_hosts \\
      --outliers hosts_fom_outliers.txt \\
      --output nonuniform_projection.png
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest import mock

import numpy as np

# Add the PBS hook directory so geopm_power_limit_compute can be found
_hook_dir = str(Path(__file__).resolve().parent.parent
                / "integration" / "service" / "open_pbs")
if _hook_dir not in sys.path:
    sys.path.insert(0, _hook_dir)

# Mock PBS so we can import the compute module
_pbs_mock = mock.MagicMock()
_pbs_mock.hook_config_filename = None
mock.patch.dict("sys.modules", pbs=_pbs_mock).start()
import geopm_power_limit_compute as compute_hook

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Ensure geopmpy can be imported (plot.py / compare.py import it at module level).
try:
    import geopmpy  # noqa: F401
except ImportError:
    _geopmpy_mock = mock.MagicMock()
    sys.modules.setdefault("geopmpy", _geopmpy_mock)
    sys.modules.setdefault("geopmpy.io", _geopmpy_mock)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("model", help="Path to the model JSON file")
    p.add_argument("hosts", help="File listing all model hosts (one per line)")
    p.add_argument("--outliers", default=None,
                   help="File listing outlier hosts to exclude (one per line)")
    p.add_argument("--partial", default=None,
                   help="File listing hosts with partial power-limit data "
                        "to exclude (hosts_partial_power_limits.txt)")
    p.add_argument("--missing-fom", default=None,
                   help="File listing hosts missing FOM data "
                        "to exclude (hosts_missing_fom.txt)")
    p.add_argument("--job-type", default="nekbone",
                   help="Profile name in the model JSON (default: nekbone)")
    p.add_argument("--num-nodes", type=int, default=128,
                   help="Nodes to sample per iteration (default: 128)")
    p.add_argument("--iterations", type=int, default=1000,
                   help="Monte Carlo iterations per power budget (default: 1000)")
    p.add_argument("--power-min", type=int, default=2400,
                   help="Min per-node power budget in watts (default: 2400)")
    p.add_argument("--power-max", type=int, default=4000,
                   help="Max per-node power budget in watts (default: 4000)")
    p.add_argument("--power-step", type=int, default=200,
                   help="Power budget step in watts (default: 200)")
    p.add_argument("--output", "-o", required=True,
                   help="Output file for the violin plot")
    p.add_argument("--seed", type=int, default=None,
                   help="Random seed for reproducibility")
    p.add_argument("--title",
                   default="Projected Slowdown Improvement:\n"
                           "Non-Uniform vs Uniform Power Capping",
                   help="Plot title")
    p.add_argument("--real-data", action="store_true",
                   help="Use real power-sweep data (piecewise linear "
                        "interpolation) for both power allocation and "
                        "slowdown evaluation, replacing the quadratic "
                        "model entirely.")
    p.add_argument("--sweep", nargs="+", default=None,
                   help="(requires --real-data) Paths to power-sweep dataset "
                        "directories.  Parses reports and creates HDF5 caches. "
                        "If omitted, loads pre-built caches from --cache-dir.")
    p.add_argument("--cache-dir", default=".compare_cache",
                   help="(requires --real-data) Directory for HDF5 caches "
                        "(default: ./.compare_cache)")
    p.add_argument("--outliers-rules", nargs="+", default=None,
                   metavar="POWER,OP,THRESH",
                   help="(requires --real-data) FOM outlier rules "
                        "(same format as plot.py --outliers)")
    return p.parse_args(argv)


def load_model(model_path: str, job_type: str) -> tuple:
    """Load model JSON; return (max_power, {host: {x0,A,B,C}})."""
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


# ---------------------------------------------------------------------------
# Real-data helpers
# ---------------------------------------------------------------------------

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

    if args.outliers_rules:
        outlier_hosts = find_fom_outliers(df, args.outliers_rules)
        if outlier_hosts:
            df = df[~df["host"].isin(outlier_hosts)].reset_index(drop=True)
            print(f"Removed {len(outlier_hosts)} rule-based outlier host(s)")

    return df


def build_host_curves(
    df: pd.DataFrame,
) -> Tuple[Dict[str, Tuple[np.ndarray, np.ndarray]], List[int]]:
    """Build per-host FOM(power) lookup arrays from averaged sweep data.

    Returns
    -------
    host_curves : dict
        ``{hostname: (power_array, fom_array)}`` sorted by power ascending.
    measured_levels : list of int
        Sorted list of all measured BOARD_POWER_LIMIT_CONTROL values.
    """
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
        # Enforce monotonicity: dips are measurement noise
        fom_arr = np.maximum.accumulate(fom_arr)
        host_curves[str(host)] = (power_arr, fom_arr)

    return host_curves, measured_levels


def fom_at_power(power: float, curve: Tuple[np.ndarray, np.ndarray]) -> float:
    """Piecewise-linear interpolation of FOM at a given power level."""
    return float(np.interp(power, curve[0], curve[1]))


def power_at_fom(target_fom: float, curve: Tuple[np.ndarray, np.ndarray]) -> float:
    """Inverse piecewise-linear interpolation: minimum power to achieve target_fom.

    Curves are already monotonized at build time, so FOM is non-decreasing.
    When a host is saturated (FOM plateaus), returns the lowest power that
    reaches the target — no power is wasted on a saturated host.
    """
    powers, foms = curve
    if target_fom <= foms[0]:
        return float(powers[0])
    if target_fom >= foms[-1]:
        return float(powers[-1])
    idx = int(np.searchsorted(foms, target_fom, side="left"))
    idx = max(1, min(idx, len(foms) - 1))  # safety clamp
    f0, f1 = foms[idx - 1], foms[idx]
    p0, p1 = powers[idx - 1], powers[idx]
    if f1 == f0:
        return float(p0)  # flat (saturated) segment: minimum power
    t = (target_fom - f0) / (f1 - f0)
    return float(p0 + t * (p1 - p0))


def allocate_nonuniform(
    host_names: List[str],
    host_curves: Dict[str, Tuple[np.ndarray, np.ndarray]],
    avg_power: float,
) -> Tuple[float, List[float]]:
    """Bisect to find equal-FOM allocation for a total power budget.

    Returns (target_fom, power_by_host).
    """
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


def slowdown_from_fom(
    fom: float, fom_ref: float,
) -> float:
    """Convert FOM to a slowdown fraction comparable to the quadratic model.

    slowdown = (FOM_ref - FOM) / FOM_ref
    At max power (FOM ≈ FOM_ref), slowdown ≈ 0.
    At lower power (lower FOM), slowdown > 0.
    """
    if fom_ref <= 0:
        return 0.0
    return (fom_ref - fom) / fom_ref


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def simulate_one(
    host_names: List[str],
    host_models: dict,
    max_node_power: float,
    avg_power_per_node: int,
    host_curves: Optional[Dict[str, Tuple[np.ndarray, np.ndarray]]] = None,
    host_fom_ref: Optional[Dict[str, float]] = None,
) -> float:
    """Return the worst-node slowdown improvement for one random sample.

    When *host_curves* and *host_fom_ref* are provided, both the allocation
    and slowdown evaluation use piecewise-linear interpolation of real
    measured FOM data.  Otherwise the quadratic model is used throughout.
    """
    num_nodes = len(host_names)
    job_budget = num_nodes * avg_power_per_node

    if host_curves is not None and host_fom_ref is not None:
        # --- Real-data path: piecewise-linear model -----------------------
        curves = [host_curves[h] for h in host_names]

        # Non-uniform: bisection on FOM curves
        _target_fom, power_by_node = allocate_nonuniform(
            host_names, host_curves, float(avg_power_per_node),
        )
        slowdown_by_node_nu = [
            slowdown_from_fom(
                fom_at_power(p, host_curves[h]), host_fom_ref[h]
            )
            for h, p in zip(host_names, power_by_node)
        ]

        # Uniform: every host gets avg_power_per_node
        slowdown_by_node_uniform = [
            slowdown_from_fom(
                fom_at_power(avg_power_per_node, host_curves[h]),
                host_fom_ref[h],
            )
            for h in host_names
        ]
    else:
        # --- Quadratic-model path -----------------------------------------
        x0 = [host_models[h]["x0"] for h in host_names]
        A = [host_models[h]["A"] for h in host_names]
        B = [host_models[h]["B"] for h in host_names]
        C = [host_models[h]["C"] for h in host_names]

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

    # Job performance is gated by the worst (long-pole) node
    return (max(slowdown_by_node_uniform) - max(slowdown_by_node_nu)) * 100


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.seed is not None:
        random.seed(args.seed)

    # -- Load model --------------------------------------------------------
    max_power, host_models = load_model(args.model, args.job_type)
    print(f"Model: {args.model}  (max_power={max_power})")

    # -- Load real data (if requested) -------------------------------------
    host_curves = None
    host_fom_ref = None
    if args.real_data:
        df_real = load_real_data(args)
        host_curves, measured_levels = build_host_curves(df_real)
        print(f"Real data: {len(host_curves)} hosts at "
              f"{len(measured_levels)} power levels: {measured_levels}")
        # Reference FOM: FOM at max measured power level (uncapped baseline)
        host_fom_ref = {
            h: float(c[1][-1]) for h, c in host_curves.items()
        }

    # -- Load host pool ----------------------------------------------------
    with open(args.hosts) as f:
        all_hosts = [line.strip() for line in f if line.strip()]

    exclude_files = [
        (args.outliers, "outlier"),
        (args.partial, "partial-data"),
        (args.missing_fom, "missing-FOM"),
    ]
    for filepath, label in exclude_files:
        if filepath is None:
            continue
        with open(filepath) as f:
            exclude_set = {line.split()[0] for line in f
                           if line.strip() and not line.startswith("#")}
        before = len(all_hosts)
        all_hosts = [h for h in all_hosts if h not in exclude_set]
        print(f"Excluded {before - len(all_hosts)} {label} host(s) "
              f"via {filepath}, {len(all_hosts)} remaining")

    # Drop any host not present in the model
    missing = [h for h in all_hosts if h not in host_models]
    if missing:
        print(f"WARNING: {len(missing)} host(s) not in model, excluding them")
        all_hosts = [h for h in all_hosts if h in host_models]

    # If using real data, also drop hosts without measured curves
    if host_curves is not None:
        no_data = [h for h in all_hosts if h not in host_curves]
        if no_data:
            print(f"WARNING: {len(no_data)} host(s) in model but not in "
                  f"real data, excluding them")
            all_hosts = [h for h in all_hosts if h in host_curves]

    if len(all_hosts) < args.num_nodes:
        print(f"ERROR: only {len(all_hosts)} hosts available, "
              f"need {args.num_nodes}")
        return 1

    print(f"Host pool: {len(all_hosts)} hosts")
    print(f"Sampling {args.num_nodes} hosts × {args.iterations} iterations")
    print(f"Power range: {args.power_min}–{args.power_max} W "
          f"(step {args.power_step} W)\n")

    # -- Monte Carlo -------------------------------------------------------
    power_budgets = list(range(args.power_min,
                               args.power_max + 1,
                               args.power_step))
    records: list = []

    for power in power_budgets:
        print(f"  {power} W ...", end="", flush=True)
        for _ in range(args.iterations):
            sample = random.sample(all_hosts, args.num_nodes)
            improvement = simulate_one(
                sample, host_models, max_power, power,
                host_curves=host_curves, host_fom_ref=host_fom_ref,
            )
            records.append({
                "power_budget": power,
                "improvement": improvement,
            })
        print(" done")

    df = pd.DataFrame(records)

    # -- Plot --------------------------------------------------------------
    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(12, 6))

    order = [str(p) for p in power_budgets]
    df["power_budget"] = df["power_budget"].astype(str)

    sns.violinplot(
        data=df,
        x="power_budget",
        y="improvement",
        hue="power_budget",
        ax=ax,
        order=order,
        legend=False,
        inner="box",
    )

    ax.set_title(f"{args.title} | {args.num_nodes} nodes | {args.iterations} iterations | Profile: {args.job_type}")
    ax.set_xlabel("Per-Node Power Budget (W)")
    ax.set_ylabel("Worst-Node Slowdown Improvement (%)")
    plt.tight_layout()

    base, ext = args.output.rsplit(".", 1)
    output_path = f"{base}_{args.num_nodes}_{args.job_type}.{ext}"
    fig.savefig(output_path, dpi=150)
    print(f"\nSaved figure to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
