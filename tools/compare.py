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
from typing import List, Optional

import pandas as pd

from geopmpy import io as geopm_io


TRIAL_RE = re.compile(r"-monitor_(?P<trial>\d+)\.report$")


def parse_trial_from_filename(report_path: Path) -> int:
    m = TRIAL_RE.search(report_path.name)
    if not m:
        raise ValueError(
            f"Report filename does not match '*-monitor_<TRIAL>.report': {report_path.name}"
        )
    return int(m.group("trial"))


def extract_start_time(report_path: Path) -> str:
    rr = geopm_io.RawReport(str(report_path))
    return str(rr.meta_data()["Start Time"])


def _normalize_str(val) -> str:
    if isinstance(val, bytes):
        return val.decode(errors="replace")
    return str(val)


def load_app_totals(dir_path: Path, cache_dir: Path) -> pd.DataFrame:
    """Batch-load Application Totals from all reports in *dir_path*."""
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
    df = rrc.get_app_df().copy()

    # Build Start Time -> trial mapping
    st_to_trial = {}
    for rp in report_files:
        trial = parse_trial_from_filename(rp)
        st = extract_start_time(rp)
        st_to_trial[st] = trial

    if "Start Time" not in df.columns:
        raise KeyError("Expected 'Start Time' column in Application Totals DataFrame")

    df["trial"] = df["Start Time"].map(_normalize_str).map(st_to_trial)
    if df["trial"].isna().any():
        missing = df[df["trial"].isna()]["Start Time"].unique().tolist()
        raise KeyError(f"Unable to map Start Time values to trials: {missing}")

    return df


def load_raw_host_data(dirs: List[Path], label: str, cache_root: Path) -> pd.DataFrame:
    """Load and tag raw host-level Application Totals for all reports in *dirs*."""
    raw_dfs = []
    for dir_path in dirs:
        cache_dir = cache_root / dir_path.name
        cache_dir.mkdir(parents=True, exist_ok=True)

        df = load_app_totals(dir_path, cache_dir)
        df["label"] = label
        df["directory"] = dir_path.name
        raw_dfs.append(df)

    return pd.concat(raw_dfs, ignore_index=True) if raw_dfs else pd.DataFrame()


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

    raw_df = pd.concat([baseline_raw, capped_raw], ignore_index=True)
    raw_df['sync_minus_mpi_time'] = raw_df['sync-runtime (s)'] - raw_df['MPI startup (s)']

    # Per-trial
    tdf = raw_df.groupby(['label', 'directory', 'trial'], sort=True)
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
    adf = raw_df.groupby(['label', 'directory'], sort=True)
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
