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
    """
    metric = "FOM"
    if metric not in df.columns:
        raise KeyError(f"Column '{metric}' not in DataFrame.")

    fom_values = df[metric].dropna()
    if fom_values.empty:
        print(f"No FOM data at {power_limit} W — skipping.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # Resolve highlight host FOM before plotting
    host_fom = None
    host_stats = None
    if highlight_host and "host" in df.columns:
        host_rows = df.loc[df["host"] == highlight_host, metric].dropna()
        if host_rows.empty:
            print(f"WARNING: host '{highlight_host}' not found at "
                  f"{power_limit} W")
        else:
            from scipy import stats as sp_stats
            host_fom = host_rows.mean()
            fom_mean = fom_values.mean()
            fom_std = fom_values.std()
            host_stats = {
                "Power (W)": power_limit,
                "Host FOM": host_fom,
                "Percentile": sp_stats.percentileofscore(fom_values, host_fom, kind="rank"),
                "N": fom_values.shape[0],
                "Mean FOM": fom_mean,
                "Median FOM": fom_values.median(),
                "Std Dev": fom_std,
                "Z-score": (host_fom - fom_mean) / fom_std if fom_std > 0 else float("nan"),
            }

    # Draw histogram with seaborn
    sns.histplot(fom_values, bins=bins, ax=ax)

    # Highlight the bin containing the target host
    if host_fom is not None:
        counts, bin_edges = np.histogram(fom_values, bins=bins)
        highlight_idx = int(np.searchsorted(bin_edges[1:], host_fom, side="left"))
        highlight_idx = min(highlight_idx, len(counts) - 1)
        # Recolor the highlighted bar
        for idx, patch in enumerate(ax.patches):
            if idx == highlight_idx:
                patch.set_facecolor("#DD8452")
        ax.axvline(host_fom, color="#DD8452", linestyle="--", linewidth=1.5,
                    label=f"{highlight_host} (FOM={host_fom:.2e})", zorder=5)
        ax.legend(frameon=True, framealpha=1.0, facecolor="white",
                  edgecolor="black")

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


def _print_stats_table(rows: List[dict], host: str) -> None:
    """Print a formatted table of per-power-limit statistics."""
    if not rows:
        return
    headers = ["Power (W)", "Host FOM", "Percentile", "N",
               "Mean FOM", "Median FOM", "Std Dev", "Z-score"]
    fmt = {
        "Power (W)": lambda v: f"{v:>9d}",
        "Host FOM": lambda v: f"{v:>12.4e}",
        "Percentile": lambda v: f"{v:>10.1f}th",
        "N": lambda v: f"{v:>5d}",
        "Mean FOM": lambda v: f"{v:>12.4e}",
        "Median FOM": lambda v: f"{v:>12.4e}",
        "Std Dev": lambda v: f"{v:>12.4e}",
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


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if not args.baseline:
        print("ERROR: --baseline is required.", file=sys.stderr)
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
    baseline_dirs = [Path(d).expanduser().resolve() for d in args.baseline]
    cache_root = (
        Path(args.cache_dir).expanduser().resolve()
        if args.cache_dir
        else Path(".compare_cache").resolve()
    )
    sections = load_raw_host_data(baseline_dirs, "baseline", cache_root)

    totals = sections.get("totals")
    if totals is None or totals.empty:
        print("No totals data found in baseline directories.")
        return 1

    col = "BOARD_POWER_LIMIT_CONTROL"
    if col not in totals.columns:
        raise KeyError(f"Column '{col}' not found. "
                       f"Available: {list(totals.columns)}")

    totals[col] = totals[col].astype(int)

    xlim = None
    if args.ylim:
        lo, hi = args.ylim.split(",")
        xlim = (float(lo), float(hi))

    stats_rows = []
    for power_limit in sorted(totals[col].unique()):
        subset = totals[totals[col] == power_limit]
        row_stats = plot_fom_histogram(
            subset,
            power_limit=power_limit,
            title=args.title,
            output=args.output,
            highlight_host=args.highlight_host,
            bins=args.bins,
            publication=args.publication,
            xlim=xlim,
        )
        if row_stats is not None:
            stats_rows.append(row_stats)

    if stats_rows:
        _print_stats_table(stats_rows, args.highlight_host)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
