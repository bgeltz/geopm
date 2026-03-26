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
from typing import List, Optional
from unittest import mock

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


def simulate_one(
    host_names: List[str],
    host_models: dict,
    max_node_power: float,
    avg_power_per_node: int,
) -> float:
    """Return the worst-node slowdown improvement for one random sample."""
    num_nodes = len(host_names)
    job_budget = num_nodes * avg_power_per_node

    x0 = [host_models[h]["x0"] for h in host_names]
    A = [host_models[h]["A"] for h in host_names]
    B = [host_models[h]["B"] for h in host_names]
    C = [host_models[h]["C"] for h in host_names]

    # --- Non-uniform (balanced) allocation --------------------------------
    _slowdown_nu, power_by_node = compute_hook.allocate_budget_to_nodes(
        job_budget, max_node_power, x0, A, B, C,
    )
    normalized_power = [p / max_node_power for p in power_by_node]
    slowdown_by_node_nu = [
        An * (x0n - pn) ** 2 + Bn * (x0n - pn) + Cn
        for x0n, An, Bn, Cn, pn in zip(x0, A, B, C, normalized_power)
    ]

    # --- Uniform allocation -----------------------------------------------
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
            improvement = simulate_one(sample, host_models, max_power, power)
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
