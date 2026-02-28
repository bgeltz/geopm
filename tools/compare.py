#!/usr/bin/env python3
"""
Usage:
  ./compare.py \\
    --baseline /path/to/12459695_60 \\
    --capped /path/to/12459765_60_3500 /path/to/12459766_60_3000 /path/to/12459767_60_2500
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from geopmpy import io as geopm_io


TRIAL_RE = re.compile(r"-monitor_(?P<trial>\d+)\.report$")


def _parse_trial_from_report_file(filename: str) -> int:
    """Extract the trial number from a report filename string."""
    m = TRIAL_RE.search(filename)
    if not m:
        raise ValueError(
            f"Report filename does not match '*-monitor_<TRIAL>.report': {filename}"
        )
    return int(m.group("trial"))


def _add_trial_column(df: pd.DataFrame) -> pd.DataFrame:
    """Derive trial number from the report_file column."""
    if "report_file" not in df.columns:
        raise KeyError("Expected 'report_file' column in DataFrame")
    df = df.copy()
    df["trial"] = df["report_file"].apply(_parse_trial_from_report_file)
    return df


def load_report_data(dir_path: Path, cache_dir: Path) -> Dict[str, pd.DataFrame]:
    """Batch-load all report sections from all reports in *dir_path*.

    Returns a dict of DataFrames keyed by section name:
      - ``'totals'``  — Application Totals (one row per host per trial)
      - ``'<region>'`` — per-region data for each unique region name
    """
    report_files = sorted(dir_path.glob("*monitor_*.report"))
    if not report_files:
        raise FileNotFoundError(f"No *monitor_*.report files in {dir_path}")

    names = [rp.name for rp in report_files]
    rrc = geopm_io.RawReportCollection(
        names,
        dir_name=str(dir_path),
        dir_cache=str(cache_dir),
        verbose=False,
        do_cache=True,
    )

    result = {}  # type: Dict[str, pd.DataFrame]

    # Application Totals
    app_df = _add_trial_column(rrc.get_app_df())
    result["totals"] = app_df

    # Per-region data
    region_df = rrc.get_df()
    if region_df is not None and not region_df.empty:
        region_df = _add_trial_column(region_df)
        for region_name, rdf in region_df.groupby("region", sort=True):
            result[str(region_name)] = rdf.reset_index(drop=True)

    return result


def load_raw_host_data(
    dirs: List[Path], label: str, cache_root: Path
) -> Dict[str, pd.DataFrame]:
    """Load and tag raw host-level data for all reports in *dirs*.

    Returns a dict of DataFrames (same keys as :func:`load_report_data`)
    with ``label`` and ``directory`` columns added to each.
    """
    combined = {}  # type: Dict[str, List[pd.DataFrame]]
    for dir_path in dirs:
        cache_dir = cache_root / dir_path.name
        cache_dir.mkdir(parents=True, exist_ok=True)

        sections = load_report_data(dir_path, cache_dir)
        for key, df in sections.items():
            df = df.copy()
            df["label"] = label
            df["directory"] = dir_path.name
            combined.setdefault(key, []).append(df)

    return {
        key: pd.concat(dfs, ignore_index=True) for key, dfs in combined.items()
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--baseline", required=True,
        help="Path to the baseline (unconstrained) dataset directory",
    )
    p.add_argument(
        "--capped", nargs="+", required=True,
        help="Paths to one or more power-capped dataset directories",
    )
    p.add_argument(
        "--cache-dir", default=None,
        help="Directory for HDF5 caches (default: ./.compare_cache)",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    pd.set_option("display.float_format", "{:.4f}".format)

    args = parse_args(argv)

    baseline_dir = Path(args.baseline).expanduser().resolve()
    capped_dirs = [Path(d).expanduser().resolve() for d in args.capped]
    cache_root = (
        Path(args.cache_dir).expanduser().resolve()
        if args.cache_dir
        else Path(".compare_cache").resolve()
    )

    baseline_raw = load_raw_host_data([baseline_dir], "baseline", cache_root)
    capped_raw = load_raw_host_data(capped_dirs, "capped", cache_root)

    # Merge baseline and capped dicts into one dict of DataFrames.
    # Keys: 'totals', plus each unique region name (e.g. 'MPI_Init_thread').
    all_keys = set(baseline_raw) | set(capped_raw)
    raw = {}  # type: Dict[str, pd.DataFrame]
    for key in sorted(all_keys):
        parts = [d[key] for d in (baseline_raw, capped_raw) if key in d]
        raw[key] = pd.concat(parts, ignore_index=True)

    print(f"Available sections: {list(raw.keys())}")

    raw['totals']['sync_minus_mpi_time'] = (
        raw['totals']['sync-runtime (s)'] - raw['totals']['MPI startup (s)']
    )

    # Per-trial
    tdf = raw['totals'].groupby(['label', 'directory', 'trial'], sort=True)
    #  tdf['runtime (s)'].describe()
    #  b2 = df.get_group(('baseline', '12459695_60', 2))
    #  u1 = df.get_group(('capped', '12459765_60_3500', 1))

    # Speed up percentage
    # (b2['sync-runtime (s)'].mean() - u1['sync-runtime (s)'].mean()) / b2['sync-runtime (s)'].mean()
    # BOARD_POWER percentage
    # (b2['BOARD_POWER'].mean() - u1['BOARD_POWER'].mean()) / b2['BOARD_POWER'].mean()
    # BOARD_ENERGY percentage
    # (b2['BOARD_ENERGY'].mean() - u1['BOARD_ENERGY'].mean()) / b2['BOARD_ENERGY'].mean()

    # cols = ['sync-runtime (s)', 'BOARD_ENERGY', 'BOARD_POWER']

    # All trials
    adf = raw['totals'].groupby(['label', 'directory'], sort=True)
    base = adf.get_group(('baseline', '12459695_60'))
    cap_3500 = adf.get_group(('capped', '12459765_60_3500'))
    cap_3000 = adf.get_group(('capped', '12459766_60_3000'))
    cap_2500 = adf.get_group(('capped', '12459767_60_2500'))
    cap_210000 = adf.get_group(('capped', '12461211_60_210000'))
    cap_150000 = adf.get_group(('capped', '12461212_60_150000'))
    #  (base['sync-runtime (s)'].mean() - cap_3500['sync-runtime (s)'].mean()) / base['sync-runtime (s)'].mean()

    #  >>> (base['sync-runtime (s)'].mean() - cap_3500['sync-runtime (s)'].mean()) / base['sync-runtime (s)'].mean()
    #  -0.08564272398276769
    #  >>> (base['BOARD_ENERGY'].mean() - cap_3500['BOARD_ENERGY'].mean()) / base['BOARD_ENERGY'].mean()
    #  -0.05528310622693108
    #  >>> (base['BOARD_POWER'].mean() - cap_3500['BOARD_POWER'].mean()) / base['BOARD_POWER'].mean()
    #  0.024658783577226142

    import code
    code.interact(local=dict(globals(), **locals()))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
