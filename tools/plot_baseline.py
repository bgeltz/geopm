#!/usr/bin/env python3
"""
Usage:
  ./plot_baseline.py \\
    --baseline /path/to/12459695_60 /path/to/12459766_60_3000 \\
    --output fom_hist.png \\
    --highlight-host x4218c7s0b0n0

Produces one FOM histogram per BOARD_POWER_LIMIT_CONTROL value.
Optionally highlights the bin containing a specific node.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from compare import common_arg_parser, load_raw_host_data
from select_uniform_nodes import (
    apply_outlier_filter,
    load_cached_data,
    load_host_filter,
    load_report_dirs,
    validate_dataset,
)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        parents=[common_arg_parser()],
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--output", "-o", default=None,
        help="Save figures to this path (power limit value is inserted "
             "into the filename).  If omitted, plots are shown interactively.",
    )
    p.add_argument(
        "--title", default="FOM Distribution",
        help="Base plot title (power limit is appended).",
    )
    p.add_argument(
        "--highlight-host", default=None,
        help="Hostname to highlight in the histogram.  The bin "
             "containing that host's FOM is drawn in a different color.",
    )
    p.add_argument(
        "--bins", type=int, default=30,
        help="Number of histogram bins (default: 30).",
    )
    p.add_argument(
        "--publication", action="store_true", default=False,
        help="Publication mode: remove titles, minimize margins, use "
             "white background with gray gridlines, and increase font sizes.",
    )
    p.add_argument(
        "--ylim", default=None,
        help="FOM axis limits as 'LOW,HIGH' (e.g. '6e6,9e6').",
    )
    p.add_argument(
        "--cache", nargs="?", const=".compare_cache", default=None,
        help="Load data from pre-built HDF5 cache files (cache_*.h5), "
             "skipping report parsing. Optionally accepts a path to the "
             "cache directory (default: .compare_cache).",
    )
    p.add_argument(
        "--filter-hosts", metavar="FILE", default=None,
        help="Path to a file containing hostnames (one per line) "
             "to exclude from the dataset.",
    )
    p.add_argument(
        "--outliers", nargs="+", default=None,
        metavar="POWER,OP,THRESH",
        help="FOM outlier rules. Each rule is "
             "'POWER,OPERATOR,THRESHOLD' where OPERATOR is "
             "'lt' or 'gt'. Any host with a trial violating a "
             "rule is removed from the dataset.",
    )
    p.add_argument(
        "--validate", action="store_true", default=False,
        help="Run dataset validation (remove hosts with incomplete "
             "sweeps or insufficient trials).",
    )
    p.add_argument(
        "--focus-node-dir", default=None,
        help="Directory containing GEOPM report files for a single node. "
             "The node's trials are overlaid on the population histogram "
             "(from --cache/--baseline) without contributing to the "
             "distribution. Hostname is extracted automatically.",
    )
    return p.parse_args(argv)


def plot_fom_histogram(
    df: pd.DataFrame,
    power_limit: int,
    title: str = "FOM Distribution",
    output: Optional[str] = None,
    highlight_host: Optional[str] = None,
    bins: int = 30,
    publication: bool = False,
    xlim: Optional[tuple] = None,
    highlight_fom_override: Optional[pd.Series] = None,
) -> None:
    """Create a single FOM histogram for one BOARD_POWER_LIMIT_CONTROL value.

    Parameters
    ----------
    df : pd.DataFrame
        Rows for a single power limit, must contain ``FOM`` and ``host``.
    power_limit : int
        The power limit value (used in title/filename).
    highlight_host : str or None
        If given, the bin containing this host's FOM is colored differently.
    highlight_fom_override : pd.Series or None
        If provided, use these FOM values for highlighting instead of
        looking up *highlight_host* in *df*.  The values are overlaid on
        the population histogram without contributing to the distribution.
    """
    metric = "FOM"
    if metric not in df.columns:
        raise KeyError(f"Column '{metric}' not in DataFrame.")

    fom_values = df[metric].dropna()
    if fom_values.empty:
        print(f"No FOM data at {power_limit} W — skipping.")
        return

    fig, ax = plt.subplots(figsize=(3.5, 2.5))

    # Resolve highlight host FOM before plotting
    host_fom = None
    host_stats = []
    if highlight_fom_override is not None and not highlight_fom_override.empty:
        host_rows = highlight_fom_override.dropna()
        from scipy import stats as sp_stats
        host_fom = host_rows.mean()
        fom_mean = fom_values.mean()
        fom_std = fom_values.std()
        for trial_num, trial_fom in enumerate(host_rows.values, start=1):
            host_stats.append({
                "Power (W)": power_limit,
                "Trial": trial_num,
                "Trial FOM": trial_fom,
                "Percentile": sp_stats.percentileofscore(fom_values, trial_fom, kind="rank"),
                "N": fom_values.shape[0],
                "Dist Mean": fom_mean,
                "Dist Median": fom_values.median(),
                "Dist Std": fom_std,
                "Z-score": (trial_fom - fom_mean) / fom_std if fom_std > 0 else float("nan"),
            })
    elif highlight_host and "host" in df.columns:
        host_rows = df.loc[df["host"] == highlight_host, metric].dropna()
        if host_rows.empty:
            print(f"WARNING: host '{highlight_host}' not found at "
                  f"{power_limit} W")
        else:
            from scipy import stats as sp_stats
            host_fom = host_rows.mean()
            fom_mean = fom_values.mean()
            fom_std = fom_values.std()
            for trial_num, trial_fom in enumerate(host_rows.values, start=1):
                host_stats.append({
                    "Power (W)": power_limit,
                    "Trial": trial_num,
                    "Trial FOM": trial_fom,
                    "Percentile": sp_stats.percentileofscore(fom_values, trial_fom, kind="rank"),
                    "N": fom_values.shape[0],
                    "Dist Mean": fom_mean,
                    "Dist Median": fom_values.median(),
                    "Dist Std": fom_std,
                    "Z-score": (trial_fom - fom_mean) / fom_std if fom_std > 0 else float("nan"),
                })

    # Draw histogram with seaborn
    sns.histplot(fom_values, bins=bins, ax=ax)

    # Highlight the bins containing the target host's trials
    if host_fom is not None:
        counts, bin_edges = np.histogram(fom_values, bins=bins)
        # Find all bins that contain at least one trial from this host
        if highlight_fom_override is not None and not highlight_fom_override.empty:
            host_trial_values = highlight_fom_override.dropna()
        else:
            host_trial_values = df.loc[df["host"] == highlight_host, metric].dropna()
        highlight_indices = set()
        for trial_val in host_trial_values:
            idx = int(np.searchsorted(bin_edges[1:], trial_val, side="left"))
            idx = min(idx, len(counts) - 1)
            highlight_indices.add(idx)
        # Recolor all bins containing a trial
        for idx, patch in enumerate(ax.patches):
            if idx in highlight_indices:
                patch.set_facecolor("#DD8452")
        # Draw vertical lines for each individual trial
        for i, trial_val in enumerate(sorted(host_trial_values)):
            ax.axvline(trial_val, color="#DD8452", linestyle=":", linewidth=1.0,
                        alpha=0.7, zorder=4,
                        label=f"Trial {i+1} (FOM={trial_val:.2e})")
        # Draw the mean as a thicker dashed line
        ax.axvline(host_fom, color="#C44E52", linestyle="--", linewidth=2.0,
                    label=f"{highlight_host} mean (FOM={host_fom:.2e})", zorder=5)
        ax.legend(frameon=True, framealpha=1.0, facecolor="white",
                  edgecolor="black", fontsize=8)

    if not publication:
        host_tag = f" [{highlight_host}]" if highlight_host else ""
        ax.set_title(f"{title} — {power_limit} W{host_tag}")
    ax.set_xlabel("Figure of Merit")
    ax.set_ylabel("Count")
    if xlim:
        ax.set_xlim(*xlim)

    if publication:
        ax.margins(x=0)
    plt.tight_layout()

    if output:
        base, ext = output.rsplit(".", 1)
        host_suffix = f"_{highlight_host}" if highlight_host else ""
        out_path = f"{base}_{power_limit}{host_suffix}.{ext}"
        fig.savefig(out_path, dpi=150)
        print(f"Saved figure to {out_path}")
    else:
        plt.show()
    plt.close(fig)
    return host_stats


def _print_stats_table(rows: List[dict], host: str, output_path: Optional[str] = None) -> None:
    """Print a formatted table of per-trial statistics and optionally write to file."""
    if not rows:
        return
    headers = ["Power (W)", "Trial", "Trial FOM", "Percentile", "N",
               "Dist Mean", "Dist Median", "Dist Std", "Z-score"]
    fmt = {
        "Power (W)": lambda v: f"{v:>9d}",
        "Trial": lambda v: f"{v:>5d}",
        "Trial FOM": lambda v: f"{v:>12.4e}",
        "Percentile": lambda v: f"{v:>10.1f}th",
        "N": lambda v: f"{v:>5d}",
        "Dist Mean": lambda v: f"{v:>12.4e}",
        "Dist Median": lambda v: f"{v:>12.4e}",
        "Dist Std": lambda v: f"{v:>12.4e}",
        "Z-score": lambda v: f"{v:>8.2f}" if not np.isnan(v) else f"{'N/A':>8s}",
    }
    col_widths = {}
    formatted_rows = []
    for row in rows:
        frow = {h: fmt[h](row[h]) for h in headers}
        formatted_rows.append(frow)
    for h in headers:
        col_widths[h] = max(len(h), *(len(fr[h]) for fr in formatted_rows))

    header_line = "  ".join(h.rjust(col_widths[h]) for h in headers)
    sep_line = "  ".join("-" * col_widths[h] for h in headers)

    print(f"\n=== Highlight Host: {host} ===")
    print(header_line)
    print(sep_line)
    for fr in formatted_rows:
        print("  ".join(fr[h].rjust(col_widths[h]) for h in headers))
    print()

    if output_path:
        with open(output_path, "w") as fh:
            fh.write(f"=== Highlight Host: {host} (Per-Trial) ===\n")
            fh.write(header_line + "\n")
            fh.write(sep_line + "\n")
            for fr in formatted_rows:
                fh.write("  ".join(fr[h].rjust(col_widths[h]) for h in headers) + "\n")
        print(f"Saved per-trial stats table to {output_path}")


def _build_summary_rows(trial_rows: List[dict]) -> List[dict]:
    """Average per-trial rows into one row per power limit."""
    from collections import defaultdict
    by_power: dict = defaultdict(list)
    for r in trial_rows:
        by_power[r["Power (W)"]].append(r)
    summary = []
    for power in sorted(by_power):
        rows = by_power[power]
        n_trials = len(rows)
        mean_fom = np.mean([r["Trial FOM"] for r in rows])
        mean_pct = np.mean([r["Percentile"] for r in rows])
        mean_z = np.mean([r["Z-score"] for r in rows])
        summary.append({
            "Power (W)": power,
            "Trials": n_trials,
            "Mean Host FOM": mean_fom,
            "Mean Percentile": mean_pct,
            "N": rows[0]["N"],
            "Dist Mean": rows[0]["Dist Mean"],
            "Dist Median": rows[0]["Dist Median"],
            "Dist Std": rows[0]["Dist Std"],
            "Mean Z-score": mean_z,
        })
    return summary


def _print_summary_table(trial_rows: List[dict], host: str, output_path: Optional[str] = None) -> None:
    """Print a summary table averaging trials per power limit."""
    rows = _build_summary_rows(trial_rows)
    if not rows:
        return
    headers = ["Power (W)", "Trials", "Mean Host FOM", "Mean Percentile", "N",
               "Dist Mean", "Dist Median", "Dist Std", "Mean Z-score"]
    fmt = {
        "Power (W)": lambda v: f"{v:>9d}",
        "Trials": lambda v: f"{v:>6d}",
        "Mean Host FOM": lambda v: f"{v:>14.4e}",
        "Mean Percentile": lambda v: f"{v:>15.1f}th",
        "N": lambda v: f"{v:>5d}",
        "Dist Mean": lambda v: f"{v:>12.4e}",
        "Dist Median": lambda v: f"{v:>12.4e}",
        "Dist Std": lambda v: f"{v:>12.4e}",
        "Mean Z-score": lambda v: f"{v:>12.2f}" if not np.isnan(v) else f"{'N/A':>12s}",
    }
    col_widths = {}
    formatted_rows = []
    for row in rows:
        frow = {h: fmt[h](row[h]) for h in headers}
        formatted_rows.append(frow)
    for h in headers:
        col_widths[h] = max(len(h), *(len(fr[h]) for fr in formatted_rows))

    header_line = "  ".join(h.rjust(col_widths[h]) for h in headers)
    sep_line = "  ".join("-" * col_widths[h] for h in headers)

    print(f"\n=== Highlight Host: {host} (Trial Averages) ===")
    print(header_line)
    print(sep_line)
    for fr in formatted_rows:
        print("  ".join(fr[h].rjust(col_widths[h]) for h in headers))
    print()

    if output_path:
        with open(output_path, "a") as fh:
            fh.write(f"\n=== Highlight Host: {host} (Trial Averages) ===\n")
            fh.write(header_line + "\n")
            fh.write(sep_line + "\n")
            for fr in formatted_rows:
                fh.write("  ".join(fr[h].rjust(col_widths[h]) for h in headers) + "\n")
        print(f"Appended summary stats to {output_path}")


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if not args.baseline and not args.cache:
        print("ERROR: --baseline or --cache is required.", file=sys.stderr)
        return 1

    if args.publication:
        plt.style.use("seaborn-v0_8-whitegrid")
        plt.rcParams.update({
            "font.size": 14,
            "axes.labelsize": 16,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "legend.fontsize": 12,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
        })
    else:
        plt.style.use("seaborn-v0_8-darkgrid")

    # Load data
    if args.cache:
        totals = load_cached_data(args.cache, verbose=True)
    else:
        baseline_dirs = [Path(d).expanduser().resolve() for d in args.baseline]
        cache_root = (
            Path(args.cache_dir).expanduser().resolve()
            if args.cache_dir
            else Path(".compare_cache").resolve()
        )
        sections = load_raw_host_data(baseline_dirs, "baseline", cache_root)
        totals = sections.get("totals")

    if totals is None or totals.empty:
        print("No totals data found.")
        return 1

    # Apply hostname filter
    if args.filter_hosts:
        excluded = load_host_filter(args.filter_hosts)
        if excluded and "host" in totals.columns:
            before = len(totals)
            totals = totals[~totals["host"].isin(excluded)].reset_index(drop=True)
            removed = before - len(totals)
            if removed:
                print(f"Filtered {len(excluded)} host(s) from "
                      f"{args.filter_hosts} ({removed} rows removed)",
                      file=sys.stderr)

    # Apply outlier filtering
    if args.outliers:
        totals = apply_outlier_filter(totals, args.outliers)

    # Validate dataset
    if args.validate:
        totals = validate_dataset(totals, verbose=True)

    col = "BOARD_POWER_LIMIT_CONTROL"
    if col not in totals.columns:
        raise KeyError(f"Column '{col}' not found. "
                       f"Available: {list(totals.columns)}")

    totals[col] = totals[col].astype(int)

    # Load focus node data (overlay only — not part of population)
    focus_node_data = None
    focus_host = args.highlight_host
    if args.focus_node_dir:
        focus_df = load_report_dirs([args.focus_node_dir], verbose=True)
        if col not in focus_df.columns:
            print(f"ERROR: focus node reports missing '{col}' column.",
                  file=sys.stderr)
            return 1
        focus_df[col] = focus_df[col].astype(int)
        # Extract hostname automatically
        focus_hosts = focus_df["host"].unique()
        if len(focus_hosts) == 1:
            focus_host = focus_hosts[0]
        elif focus_host and focus_host in focus_hosts:
            focus_df = focus_df[focus_df["host"] == focus_host]
        else:
            focus_host = focus_hosts[0]
            print(f"WARNING: multiple hosts in --focus-node-dir: "
                  f"{list(focus_hosts)}; using '{focus_host}'",
                  file=sys.stderr)
            focus_df = focus_df[focus_df["host"] == focus_host]
        focus_node_data = focus_df
        print(f"Focus node: {focus_host} "
              f"({len(focus_df)} trials from --focus-node-dir)",
              file=sys.stderr)

    xlim = None
    if args.ylim:
        lo, hi = args.ylim.split(",")
        xlim = (float(lo), float(hi))

    stats_rows = []
    for power_limit in sorted(totals[col].unique()):
        subset = totals[totals[col] == power_limit]
        # Get focus node FOM values at this power level (if any)
        fom_override = None
        if focus_node_data is not None:
            focus_at_power = focus_node_data[
                focus_node_data[col] == power_limit
            ]
            if not focus_at_power.empty:
                fom_override = focus_at_power["FOM"].reset_index(drop=True)
        row_stats = plot_fom_histogram(
            subset,
            power_limit=power_limit,
            title=args.title,
            output=args.output,
            highlight_host=focus_host,
            bins=args.bins,
            publication=args.publication,
            xlim=xlim,
            highlight_fom_override=fom_override,
        )
        if row_stats:
            stats_rows.extend(row_stats)

    if stats_rows:
        stats_path = None
        if args.output:
            base, ext = args.output.rsplit(".", 1)
            host_suffix = f"_{focus_host}" if focus_host else ""
            stats_path = f"{base}{host_suffix}_stats.txt"
        _print_stats_table(stats_rows, focus_host, output_path=stats_path)
        _print_summary_table(stats_rows, focus_host, output_path=stats_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
