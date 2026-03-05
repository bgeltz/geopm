#!/usr/bin/env python3
"""
Usage:
  ./plot.py \\
    --baseline /path/to/12459695_60 \\
    --capped /path/to/12459765_60_3500 /path/to/12459766_60_3000 /path/to/12459767_60_2500 \\
    --output fom_boxplot.png

Produces vertical boxplots of Figure of Merit (FOM) grouped by
BOARD_POWER_LIMIT_CONTROL from the loaded report data.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Optional, List

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from compare import common_arg_parser, load_data, load_raw_host_data


# <JOBID>_<NODE_COUNT>_<POWER_CAP>
_DIR_RE = re.compile(r"^(?P<jobid>\d+)_(?P<nodes>\d+)_(?P<cap>\d+)$")


def _parse_dir_name(name: str) -> dict:
    """Extract job-id, node count, and power cap from a directory name.

    Directory format: ``<JOBID>_<NODE_COUNT>_<POWER_CAP>``
    """
    m = _DIR_RE.match(name)
    if not m:
        raise ValueError(
            f"Directory name does not match '<JOBID>_<NODES>_<CAP>': {name}"
        )
    return {
        "jobid": int(m.group("jobid")),
        "node_count": int(m.group("nodes")),
        "cap": int(m.group("cap")),
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        parents=[common_arg_parser()],
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--output", "-o", default=None,
        help="Save figure to this file (e.g. fom_boxplot.png). "
             "If omitted the plot is shown interactively.",
    )
    p.add_argument(
        "--title", default="Unknown App FOM Analysis",
        help="Plot title",
    )
    p.add_argument(
        "--uniform", nargs="+", default=None,
        help="Paths to one or more uniform power-cap dataset directories",
    )
    p.add_argument(
        "--nonuniform", nargs="+", default=None,
        help="Paths to one or more non-uniform (job-level) power-cap dataset directories",
    )
    return p.parse_args(argv)


def plot_fom_power_sweep_boxplot(
    df: pd.DataFrame,
    title: str = "FOM by Board Power Limit",
    output: Optional[str] = None,
) -> None:
    """Create a vertical boxplot of FOM grouped by BOARD_POWER_LIMIT_CONTROL.

    Parameters
    ----------
    df : pd.DataFrame
        The 'totals' DataFrame containing at least
        ``BOARD_POWER_LIMIT_CONTROL`` and ``FOM`` columns.
    title : str
        Plot title.
    output : str or None
        If provided, save figure to this path; otherwise display interactively.
    """
    col = "BOARD_POWER_LIMIT_CONTROL"
    metric = "FOM"

    for required in (col, metric):
        if required not in df.columns:
            raise KeyError(
                f"Column '{required}' not found in totals DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

    df = df.copy()
    df[col] = df[col].astype(int)
    fom_max = df[metric].max()
    df[metric] = df[metric] / fom_max

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(
        data=df,
        x=col,
        y=metric,
        ax=ax,
        order=sorted(df[col].dropna().unique()),
    )
    ax.set_title(title)
    ax.set_xlabel("Board Power Limit Control (W)")
    ax.set_ylabel("Normalized Figure of Merit")
    ax.yaxis.grid(True, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)
    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def plot_fom_cap_compare(
    df: pd.DataFrame,
    title: str = "Uniform vs Non-Uniform Power Cap FOM",
    output: Optional[str] = None,
) -> None:
    """Create a scatterplot comparing uniform vs non-uniform FOM.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``avg_power_per_node``, ``FOM``, and ``cap_type`` columns.
    title : str
        Plot title.
    output : str or None
        If provided, save figure to this path; otherwise display interactively.
    """
    metric = "FOM"
    x_col = "avg_power_per_node"
    hue_col = "cap_type"

    for required in (x_col, metric, hue_col):
        if required not in df.columns:
            raise KeyError(
                f"Column '{required}' not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

    sns.set_context("notebook", font_scale=0.8)

    df = df.copy()
    fom_max = df[metric].max()
    df[metric] = df[metric] / fom_max
    df[x_col] = df[x_col].astype(int)

    fig, ax = plt.subplots(figsize=(5, 4))
    sns.scatterplot(
        data=df,
        x=x_col,
        y=metric,
        hue=hue_col,
        style=hue_col,
        ax=ax,
        hue_order=["Uniform", "Non-Uniform"],
    )
    ax.set_title(title)
    ax.set_xlabel("Average Power Per Node (W)")
    ax.set_ylabel("Normalized Figure of Merit")
    ax.legend(title=None)
    ax.yaxis.grid(True, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)
    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def _load_cap_compare_data(
    uniform_dirs: List[str],
    nonuniform_dirs: List[str],
    cache_dir: Optional[str],
) -> pd.DataFrame:
    """Load uniform and non-uniform datasets, tag them, and compute avg power."""
    cache_root = (
        Path(cache_dir).expanduser().resolve()
        if cache_dir
        else Path(".compare_cache").resolve()
    )

    frames = []  # type: List[pd.DataFrame]

    for dir_str, cap_type in [
        *[(d, "Uniform") for d in uniform_dirs],
        *[(d, "Non-Uniform") for d in nonuniform_dirs],
    ]:
        dir_path = Path(dir_str).expanduser().resolve()
        info = _parse_dir_name(dir_path.name)
        if cap_type == "Uniform":
            avg_power = info["cap"]
        else:
            avg_power = info["cap"] / info["node_count"]

        sections = load_raw_host_data([dir_path], cap_type, cache_root)
        totals = sections.get("totals")
        if totals is not None and not totals.empty:
            totals = totals.copy()
            totals["cap_type"] = cap_type
            totals["avg_power_per_node"] = avg_power
            frames.append(totals)

    if not frames:
        raise RuntimeError("No totals data found in the supplied directories.")

    return pd.concat(frames, ignore_index=True)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.uniform and args.nonuniform:
        df = _load_cap_compare_data(
            args.uniform, args.nonuniform, args.cache_dir,
        )
        plot_fom_cap_compare(df, title=args.title, output=args.output)
    else:
        raw = load_data(args)
        if not raw:
            return 0
        plot_fom_power_sweep_boxplot(
            raw["totals"], title=args.title, output=args.output,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
