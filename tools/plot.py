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
import sys
from typing import Optional, List

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from compare import common_arg_parser, load_data


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
    return p.parse_args(argv)


def plot_fom_boxplot(
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
    ax.set_ylabel("Figure of Merit")
    ax.yaxis.grid(True, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)
    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved figure to {output}")
    else:
        plt.show()


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    raw = load_data(args)
    if not raw:
        return 0
    plot_fom_boxplot(raw["totals"], title=args.title, output=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
