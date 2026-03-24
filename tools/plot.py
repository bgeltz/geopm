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


# App-specific default FOM y-limits (lower, upper)
_FOM_YLIM_DEFAULTS = {
    "hacc": (6e6, 9e6),
    "nekbone": (2e6, 5.5e6),
}

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
    p.add_argument(
        "--sweep", nargs="+", default=None,
        help="Paths to one or more power-sweep dataset directories",
    )
    p.add_argument(
        "--raw-trials", action="store_true", default=False,
        help="Plot every trial as a separate data point instead of "
             "averaging trials per host before plotting",
    )
    p.add_argument(
        "--ylim", default=None,
        help="Y-axis limits as 'LOW,HIGH' (e.g. '6e6,9e6'). "
             "If omitted, defaults are chosen by app name in --title "
             f"(known apps: {', '.join(sorted(_FOM_YLIM_DEFAULTS))})",
    )
    p.add_argument(
        "--cache", nargs="?", const=".compare_cache", default=None,
        help="Load data directly from pre-built HDF5 cache files, "
             "skipping report parsing. Optionally accepts a path to the "
             "cache directory (default: .compare_cache).",
    )
    return p.parse_args(argv)


def plot_power_sweep_fom_boxplot(
    df: pd.DataFrame,
    title: str = "FOM by Board Power Limit",
    output: Optional[str] = None,
    average_trials: bool = True,
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

    if average_trials:
        group_cols = [c for c in ("host", col) if c in df.columns]
        if "host" in df.columns:
            df = df.groupby(group_cols, as_index=False)[metric].mean()

    fom_max = df[metric].max()
    #  df[metric] = df[metric] / fom_max
    df[metric] = df[metric] / 5305200.0
    print(f'FoM MAX = {fom_max}')

    order = sorted(df[col].dropna().unique())
    df[col] = df[col].astype(str)
    str_order = [str(v) for v in order]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(
        data=df,
        x=col,
        y=metric,
        hue=col,
        ax=ax,
        order=str_order,
        legend=False,
    )
    ax.set_title(title)
    ax.set_xlabel("Board Power Limit Control (W)")
    ax.set_ylabel("Normalized Figure of Merit")

    # Annotate each box with the spread (max / min) - 1 as a percentage
    for idx, power in enumerate(str_order):
        grp = df.loc[df[col] == power, metric]
        fom_min = grp.min()
        fom_max_val = grp.max()
        if fom_min > 0:
            spread_pct = (fom_max_val / fom_min - 1) * 100
        else:
            spread_pct = 0.0
        ax.annotate(
            f"{spread_pct:.1f}%",
            xy=(idx, fom_min),
            xytext=(0, -10),
            textcoords="offset points",
            ha="center", va="top",
            fontsize=8,
        )

    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def plot_power_sweep_uncore_freq_boxplot(
    df: pd.DataFrame,
    title: str = "Uncore Frequency by Board Power Limit",
    output: Optional[str] = None,
    average_trials: bool = True,
) -> None:
    """Create a vertical boxplot of achieved uncore frequency grouped by BOARD_POWER_LIMIT_CONTROL.

    Parameters
    ----------
    df : pd.DataFrame
        The 'totals' DataFrame containing at least
        ``BOARD_POWER_LIMIT_CONTROL`` and ``uncore-frequency (Hz)`` columns.
    title : str
        Plot title.
    output : str or None
        If provided, save figure to this path; otherwise display interactively.
    """
    col = "BOARD_POWER_LIMIT_CONTROL"
    metric = "uncore-frequency (Hz)"

    for required in (col, metric):
        if required not in df.columns:
            raise KeyError(
                f"Column '{required}' not found in totals DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

    df = df.copy()
    df[col] = df[col].astype(int)
    # Convert Hz to GHz for readability
    df[metric] = df[metric] / 1e9

    if average_trials:
        group_cols = [c for c in ("host", col) if c in df.columns]
        if "host" in df.columns:
            df = df.groupby(group_cols, as_index=False)[metric].mean()

    print(f"Max {metric}: {df[metric].max():.4f} GHz")

    order = sorted(df[col].dropna().unique())
    df[col] = df[col].astype(str)
    str_order = [str(v) for v in order]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(
        data=df,
        x=col,
        y=metric,
        hue=col,
        ax=ax,
        order=str_order,
        legend=False,
    )
    ax.set_title(title)
    ax.set_xlabel("Board Power Limit Control (W)")
    ax.set_ylabel("Uncore Frequency (GHz)")
    ax.set_ylim(bottom=1.3, top=2.4)

    # Annotate each box with the spread (max / min) - 1 as a percentage
    for idx, power in enumerate(str_order):
        grp = df.loc[df[col] == power, metric]
        freq_min = grp.min()
        freq_max = grp.max()
        if freq_min > 0:
            spread_pct = (freq_max / freq_min - 1) * 100
        else:
            spread_pct = 0.0
        ax.annotate(
            f"{spread_pct:.1f}%",
            xy=(idx, freq_min),
            xytext=(0, -10),
            textcoords="offset points",
            ha="center", va="top",
            fontsize=8,
        )

    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def plot_power_sweep_board_power_boxplot(
    df: pd.DataFrame,
    title: str = "Requested vs Achieved Board Power",
    output: Optional[str] = None,
    average_trials: bool = True,
) -> None:
    """Create a vertical boxplot of achieved BOARD_POWER grouped by requested limit.

    Parameters
    ----------
    df : pd.DataFrame
        The 'totals' DataFrame containing at least
        ``BOARD_POWER_LIMIT_CONTROL`` and ``BOARD_POWER`` columns.
    title : str
        Plot title.
    output : str or None
        If provided, save figure to this path; otherwise display interactively.
    """
    col = "BOARD_POWER_LIMIT_CONTROL"
    metric = "BOARD_POWER"

    for required in (col, metric):
        if required not in df.columns:
            raise KeyError(
                f"Column '{required}' not found in totals DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

    df = df.copy()
    df[col] = df[col].astype(int)

    if average_trials:
        group_cols = [c for c in ("host", col) if c in df.columns]
        if "host" in df.columns:
            df = df.groupby(group_cols, as_index=False)[metric].mean()

    fig, ax = plt.subplots(figsize=(10, 6))
    order = sorted(df[col].dropna().unique())
    df[col] = df[col].astype(str)
    str_order = [str(v) for v in order]
    sns.boxplot(
        data=df,
        x=col,
        y=metric,
        hue=col,
        ax=ax,
        order=str_order,
        legend=False,
    )
    # Reference line: achieved == requested
    ax.plot(
        range(len(order)), order,
        marker="_", color="red", linestyle="--", linewidth=1,
        label="Requested = Achieved",
    )
    ax.set_title(title)
    ax.set_xlabel("Board Power Limit Control (W)")
    ax.set_ylabel("Board Power (W)")
    ax.legend(frameon=True, framealpha=1.0, facecolor="white", edgecolor="black")
    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def plot_power_sweep_fom_violin(
    df: pd.DataFrame,
    title: str = "FOM by Board Power Limit",
    output: Optional[str] = None,
    ylim: Optional[tuple] = None,
    average_trials: bool = True,
) -> None:
    """Create a violin plot of FOM grouped by BOARD_POWER_LIMIT_CONTROL.

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

    if average_trials:
        group_cols = [c for c in ("host", col) if c in df.columns]
        df = df.groupby(group_cols, as_index=False)[metric].mean()

    order = sorted(df[col].dropna().unique())
    df[col] = df[col].astype(str)
    str_order = [str(v) for v in order]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.violinplot(
        data=df,
        x=col,
        y=metric,
        hue=col,
        ax=ax,
        order=str_order,
        legend=False,
        inner="box",
    )
    ax.set_title(title)
    ax.set_xlabel("Board Power Limit Control (W)")
    ax.set_ylabel("Figure of Merit")
    if ylim:
        ax.set_ylim(*ylim)
    ax.xaxis.grid(True)
    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def plot_power_sweep_fom_line(
    df: pd.DataFrame,
    title: str = "FOM by Board Power Limit",
    output: Optional[str] = None,
    ylim: Optional[tuple] = None,
    average_trials: bool = True,
) -> None:
    """Create a lineplot of FOM grouped by BOARD_POWER_LIMIT_CONTROL.

    Each host's trials are averaged so that every host contributes one
    point per power budget.  Individual host lines are drawn with a
    thicker line for the overall mean.

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

    if average_trials:
        group_cols = [c for c in ("host", col) if c in df.columns]
        df = df.groupby(group_cols, as_index=False)[metric].mean()

    fig, ax = plt.subplots(figsize=(10, 6))

    if "host" in df.columns:
        # Individual host lines (thin, translucent)
        for host, hdf in df.groupby("host"):
            hdf = hdf.sort_values(col)
            ax.plot(
                hdf[col], hdf[metric],
                marker=".", linewidth=0.8, alpha=1.0,
            )
    else:
        df = df.sort_values(col)
        ax.plot(df[col], df[metric], marker="o", linewidth=2)

    ax.set_title(title)
    ax.set_xlabel("Board Power Limit Control (W)")
    ax.set_ylabel("Figure of Merit")
    if ylim:
        ax.set_ylim(*ylim)
    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def plot_power_sweep_fom_lowess(
    df: pd.DataFrame,
    title: str = "FOM by Board Power Limit (LOWESS)",
    output: Optional[str] = None,
    ylim: Optional[tuple] = None,
    average_trials: bool = True,
) -> None:
    """Create a LOWESS regression plot of FOM vs BOARD_POWER_LIMIT_CONTROL.

    Each host's trials are averaged first, then a per-host LOWESS curve
    is drawn (thin, translucent) with a thicker overall LOWESS fit on
    the combined data.

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
    from statsmodels.nonparametric.smoothers_lowess import lowess as sm_lowess

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

    if average_trials:
        group_cols = [c for c in ("host", col) if c in df.columns]
        df = df.groupby(group_cols, as_index=False)[metric].mean()

    fig, ax = plt.subplots(figsize=(10, 6))
    hosts = sorted(df["host"].unique()) if "host" in df.columns else []

    if hosts:
        for host, hdf in df.groupby("host", sort=True):
            hdf = hdf.sort_values(col)
            smoothed = sm_lowess(hdf[metric].values, hdf[col].values, frac=0.3, it=3)
            ax.plot(
                smoothed[:, 0], smoothed[:, 1],
                linewidth=0.8, alpha=1.0,
            )

    ax.set_title(title)
    ax.set_xlabel("Board Power Limit Control (W)")
    ax.set_ylabel("Figure of Merit")
    if ylim:
        ax.set_ylim(*ylim)
    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def plot_power_sweep_fom_histogram(
    df: pd.DataFrame,
    title: str = "FOM Distribution",
    output: Optional[str] = None,
    ylim: Optional[tuple] = None,
    average_trials: bool = True,
) -> None:
    """Create one histogram of FOM per BOARD_POWER_LIMIT_CONTROL value.

    Each host's trials are averaged first so each host contributes one
    value per power limit.  A separate figure is saved/shown for each
    power limit.

    Parameters
    ----------
    df : pd.DataFrame
        The 'totals' DataFrame containing at least
        ``BOARD_POWER_LIMIT_CONTROL`` and ``FOM`` columns.
    title : str
        Base plot title (power limit value is appended).
    output : str or None
        If provided, the power limit is inserted into the filename
        (e.g. ``fom_hist_3000.png``); otherwise displayed interactively.
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

    if average_trials:
        group_cols = [c for c in ("host", col) if c in df.columns]
        df = df.groupby(group_cols, as_index=False)[metric].mean()

    for power_limit in sorted(df[col].unique()):
        subset = df.loc[df[col] == power_limit, metric]

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.histplot(subset, ax=ax)
        ax.set_title(f"{title} — {power_limit} W")
        ax.set_xlabel("Figure of Merit")
        ax.set_ylabel("Count")
        if ylim:
            ax.set_xlim(*ylim)
        plt.tight_layout()

        if output:
            base, ext = output.rsplit(".", 1)
            out_path = f"{base}_{power_limit}.{ext}"
            fig.savefig(out_path, dpi=150)
            print(f"Saved figure to {out_path}")
        else:
            plt.show()
        plt.close(fig)


def plot_fom_cap_compare(
    df: pd.DataFrame,
    title: str = "Uniform vs Non-Uniform Power Cap FOM",
    output: Optional[str] = None,
) -> None:
    """Create a pointplot comparing uniform vs non-uniform FOM.

    Shows mean with whiskers spanning the full min-to-max range.

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

    #  sns.set_context("notebook", font_scale=0.8)

    df = df.copy()
    fom_max = df[metric].max()
    df[metric] = df[metric] / fom_max
    df[x_col] = df[x_col].astype(int)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.pointplot(
        data=df,
        x=x_col,
        y=metric,
        hue=hue_col,
        ax=ax,
        order=sorted(df[x_col].dropna().unique()),
        hue_order=["Uniform", "Non-Uniform"],
        dodge=True,
        errorbar=("pi", 100),
        capsize=0.1,
        linestyle="none",
        markersize=4,
        linewidth=2,
    )
    ax.set_title(title)
    ax.set_xlabel("Average Power Per Node (W)")
    ax.set_ylabel("Normalized Figure of Merit")
    ax.legend(title=None, frameon=True, framealpha=1.0, facecolor="white", edgecolor="black")

    # Annotate each power cap with the percent difference between means
    means = (
        df.groupby([x_col, hue_col])[metric]
        .mean()
        .unstack(hue_col)
    )
    x_order = sorted(df[x_col].dropna().unique())
    for idx, power in enumerate(x_order):
        if power not in means.index:
            continue
        u_mean = means.loc[power, "Uniform"]
        nu_mean = means.loc[power, "Non-Uniform"]
        pct_diff = (nu_mean - u_mean) / u_mean * 100
        y_mid = (u_mean + nu_mean) / 2
        ax.annotate(
            f"{pct_diff:+.1f}%",
            xy=(idx, y_mid),
            xytext=(12, 0),
            textcoords="offset points",
            ha="left", va="center",
            fontsize=8,
        )

    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def plot_fom_baseline_compare(
    df: pd.DataFrame,
    title: str = "Before vs After Host Replacement FOM",
    output: Optional[str] = None,
) -> None:
    """Create a pointplot comparing FOM before and after a host replacement.

    Shows mean with whiskers spanning the full min-to-max range.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``BOARD_POWER_LIMIT_CONTROL``, ``FOM``, and
        ``baseline_label`` columns (values "Before" / "After").
    title : str
        Plot title.
    output : str or None
        If provided, save figure to this path; otherwise display interactively.
    """
    metric = "FOM"
    x_col = "BOARD_POWER_LIMIT_CONTROL"
    hue_col = "baseline_label"

    for required in (x_col, metric, hue_col):
        if required not in df.columns:
            raise KeyError(
                f"Column '{required}' not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

    df = df.copy()
    fom_max = df[metric].max()
    df[metric] = df[metric] / fom_max
    df[x_col] = df[x_col].astype(int)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.pointplot(
        data=df,
        x=x_col,
        y=metric,
        hue=hue_col,
        ax=ax,
        order=sorted(df[x_col].dropna().unique()),
        hue_order=["Before", "After"],
        dodge=True,
        errorbar=("pi", 100),
        capsize=0.1,
        linestyle="none",
        markersize=4,
        linewidth=2,
    )
    ax.set_title(title)
    ax.set_xlabel("Board Power Limit Control (W)")
    ax.set_ylabel("Normalized Figure of Merit")
    ax.legend(title=None, frameon=True, framealpha=1.0, facecolor="white", edgecolor="black")

    # Annotate each power level with the percent difference between means
    means = (
        df.groupby([x_col, hue_col])[metric]
        .mean()
        .unstack(hue_col)
    )
    x_order = sorted(df[x_col].dropna().unique())
    for idx, power in enumerate(x_order):
        if power not in means.index:
            continue
        before_mean = means.loc[power, "Before"]
        after_mean = means.loc[power, "After"]
        pct_diff = (after_mean - before_mean) / before_mean * 100
        y_mid = (before_mean + after_mean) / 2
        ax.annotate(
            f"{pct_diff:+.1f}%",
            xy=(idx, y_mid),
            xytext=(-3, -20),
            textcoords="offset points",
            ha="left", va="center",
            fontsize=8,
        )

    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def load_cached_data(cache_path: str) -> Dict[str, pd.DataFrame]:
    """Load pre-built HDF5 caches directly, skipping report parsing.

    Reads every ``cache_*.h5`` file under *cache_path* (including
    subdirectories) and concatenates the DataFrames keyed by section
    name (``'totals'``, region names, etc.).

    The HDF5 key mapping follows :class:`geopmpy.io.RawReportCollection`:

    * ``app_report`` -> ``totals``
    * ``report``     -> per-region data (split by ``region`` column)
    """
    root = Path(cache_path).expanduser().resolve()
    h5_files = sorted(root.rglob("cache_*.h5"))
    if not h5_files:
        raise FileNotFoundError(
            f"No cache_*.h5 files found under {root}"
        )

    combined: Dict[str, List[pd.DataFrame]] = {}
    for h5 in h5_files:
        # Application totals
        try:
            app_df = pd.read_hdf(h5, key="app_report")
            combined.setdefault("totals", []).append(app_df)
        except KeyError:
            pass

        # Per-region data
        try:
            region_df = pd.read_hdf(h5, key="report")
            if region_df is not None and not region_df.empty:
                for region_name, rdf in region_df.groupby("region", sort=True):
                    combined.setdefault(str(region_name), []).append(
                        rdf.reset_index(drop=True)
                    )
        except KeyError:
            pass

    return {
        key: pd.concat(dfs, ignore_index=True)
        for key, dfs in combined.items()
    }


def validate_sweep_dataset(
    df: pd.DataFrame,
    output_dir: Optional[str] = None,
) -> pd.DataFrame:
    """Check a sweep dataset for incomplete hosts and missing FOM values.

    Writes two files into *output_dir* (defaults to the current directory):

    * ``hosts_partial_power_limits.txt`` – hosts that do not have data for
      every ``BOARD_POWER_LIMIT_CONTROL`` value present in the full dataset.
    * ``hosts_missing_fom.txt`` – hosts whose ``FOM`` values are entirely
      missing (all NaN).

    After reporting, the problematic hosts are removed and the cleaned
    DataFrame is returned.

    Parameters
    ----------
    df : pd.DataFrame
        The 'totals' DataFrame expected to contain ``host``,
        ``BOARD_POWER_LIMIT_CONTROL``, and ``FOM`` columns.
    output_dir : str or None
        Directory in which to write the report files.  Defaults to ``"."``.

    Returns
    -------
    pd.DataFrame
        A copy of *df* with problematic hosts removed.
    """
    col = "BOARD_POWER_LIMIT_CONTROL"
    metric = "FOM"
    out = Path(output_dir) if output_dir else Path(".")
    out.mkdir(parents=True, exist_ok=True)

    hosts_to_drop: set = set()

    # --- Hosts with partial BOARD_POWER_LIMIT_CONTROL coverage ----------
    all_limits = set(df[col].dropna().unique())
    partial_hosts: List[str] = []
    has_report_file = "report_file" in df.columns
    if "host" in df.columns and all_limits:
        for host, hdf in df.groupby("host"):
            host_limits = set(hdf[col].dropna().unique())
            if host_limits != all_limits:
                missing = sorted(all_limits - host_limits)
                files = sorted(hdf["report_file"].unique()) if has_report_file else []
                entry = f"{host}  missing limits: {missing}"
                if files:
                    entry += f"  report_files: {files}"
                partial_hosts.append(entry)
                hosts_to_drop.add(host)

    partial_path = out / "hosts_partial_power_limits.txt"
    with open(partial_path, "w") as fh:
        if partial_hosts:
            fh.write("\n".join(sorted(partial_hosts)) + "\n")
            print(f"WARNING: {len(partial_hosts)} host(s) with partial "
                  f"power-limit data written to {partial_path}")
        else:
            fh.write("# All hosts have data for every BOARD_POWER_LIMIT_CONTROL value.\n")
            print(f"All hosts have complete power-limit coverage ({partial_path})")

    # --- Hosts missing FOM -----------------------------------------------
    missing_fom_hosts: List[str] = []
    if "host" in df.columns and metric in df.columns:
        for host, hdf in df.groupby("host"):
            if hdf[metric].dropna().empty:
                files = sorted(hdf["report_file"].unique()) if has_report_file else []
                entry = host
                if files:
                    entry += f"  report_files: {files}"
                missing_fom_hosts.append(entry)
                hosts_to_drop.add(host)

    fom_path = out / "hosts_missing_fom.txt"
    with open(fom_path, "w") as fh:
        if missing_fom_hosts:
            fh.write("\n".join(sorted(missing_fom_hosts)) + "\n")
            print(f"WARNING: {len(missing_fom_hosts)} host(s) missing FOM "
                  f"written to {fom_path}")
        else:
            fh.write("# All hosts have FOM data.\n")
            print(f"All hosts have FOM data ({fom_path})")

    # --- Remove problematic hosts ----------------------------------------
    if hosts_to_drop and "host" in df.columns:
        df = df[~df["host"].isin(hosts_to_drop)].reset_index(drop=True)
        print(f"Removed {len(hosts_to_drop)} host(s) from dataset: "
              f"{sorted(hosts_to_drop)}")

    if "host" in df.columns:
        print(f"Total unique hosts in cleaned dataset: {df['host'].nunique()}")

    return df


def _load_baseline_compare_data(
    baseline_dirs: List[List[str]],
    cache_dir: Optional[str],
) -> pd.DataFrame:
    """Load two sets of baseline directories tagged as Before / After."""
    cache_root = (
        Path(cache_dir).expanduser().resolve()
        if cache_dir
        else Path(".compare_cache").resolve()
    )

    labels = ["Before", "After"]
    frames: List[pd.DataFrame] = []

    for dir_list, label in zip(baseline_dirs, labels):
        paths = [Path(d).expanduser().resolve() for d in dir_list]
        sections = load_raw_host_data(paths, label, cache_root)
        totals = sections.get("totals")
        if totals is not None and not totals.empty:
            totals = totals.copy()
            totals["baseline_label"] = label
            frames.append(totals)

    if not frames:
        raise RuntimeError("No totals data found in the supplied directories.")

    return pd.concat(frames, ignore_index=True)


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
    plt.style.use('seaborn-v0_8-darkgrid')
    args = parse_args(argv)

    if args.sweep or (args.cache and not args.baseline and not (args.uniform and args.nonuniform)):
        if args.cache:
            sections = load_cached_data(args.cache)
        else:
            sweep_dirs = [Path(d).expanduser().resolve() for d in args.sweep]
            cache_root = (
                Path(args.cache_dir).expanduser().resolve()
                if args.cache_dir
                else Path(".compare_cache").resolve()
            )
            sections = load_raw_host_data(sweep_dirs, "sweep", cache_root)
        if "totals" not in sections or sections["totals"].empty:
            print("No totals data found in sweep directories.")
            return 0

        sections["totals"] = validate_sweep_dataset(
            sections["totals"],
            output_dir=str(Path(args.output).parent) if args.output else None,
        )

        # Resolve y-limits: explicit --ylim > app-name default > None
        if args.ylim:
            lo, hi = args.ylim.split(",")
            ylim = (float(lo), float(hi))
        else:
            ylim = None
            for app, limits in _FOM_YLIM_DEFAULTS.items():
                if app in args.title.lower():
                    ylim = limits
                    break

        avg = not args.raw_trials
        tag = "raw" if args.raw_trials else "average_trials"

        def _out(suffix: str) -> Optional[str]:
            if not args.output:
                return None
            base, ext = args.output.rsplit(".", 1)
            return f"{base}_{suffix}_{tag}.{ext}"

        plot_power_sweep_fom_violin(
            sections["totals"], title=args.title,
            output=_out("violin"),
            ylim=ylim, average_trials=avg,
        )
        plot_power_sweep_fom_line(
            sections["totals"], title=args.title,
            output=_out("line"),
            ylim=ylim, average_trials=avg,
        )
        plot_power_sweep_fom_lowess(
            sections["totals"], title=args.title,
            output=_out("lowess"),
            ylim=ylim, average_trials=avg,
        )
        plot_power_sweep_fom_histogram(
            sections["totals"], title=args.title,
            output=_out("hist"),
            ylim=ylim, average_trials=avg,
        )
        plot_power_sweep_fom_boxplot(
            sections["totals"], title=args.title + ' FoM Analysis - Host Means',
            output=_out("fom_boxplot_host_means"),
            average_trials=avg,
        )
        plot_power_sweep_board_power_boxplot(
            sections["totals"], title=args.title + ' Achieved Power Analysis',
            output=_out("board_power_boxplot"),
            average_trials=avg,
        )
        plot_power_sweep_uncore_freq_boxplot(
            sections["totals"], title=args.title + ' Uncore Frequency Analysis',
            output=_out("uncore_freq_boxplot"),
            average_trials=avg,
        )
    elif args.uniform and args.nonuniform:
        if args.cache:
            sections = load_cached_data(args.cache)
            df = sections.get("totals")
            if df is None or df.empty:
                raise RuntimeError("No totals data found in cached files.")
        else:
            df = _load_cap_compare_data(
                args.uniform, args.nonuniform, args.cache_dir,
            )
        plot_fom_cap_compare(df, title=args.title, output=args.output)
    elif args.baseline and len(args.baseline) > 1:
        if args.cache:
            sections = load_cached_data(args.cache)
            df = sections.get("totals")
            if df is None or df.empty:
                raise RuntimeError("No totals data found in cached files.")
        else:
            # Split baselines into two groups: first half = Before, second half = After
            mid = len(args.baseline) // 2
            before_dirs = args.baseline[:mid]
            after_dirs = args.baseline[mid:]
            df = _load_baseline_compare_data(
                [before_dirs, after_dirs], args.cache_dir,
            )
        plot_fom_baseline_compare(df, title=args.title, output=args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
