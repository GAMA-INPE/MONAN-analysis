#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
precipitation_analysis_period_aggregate.py

Aggregate precipitation verification results across a period of forecast
initialization cycles for one or more MONAN experiments.

For each experiment, observational reference, and forecast lead, this script
generates:

1. Period-mean Bias field, using CDO ensmean
2. Period-mean MAE field, using CDO ensmean
3. Period RMSE field = sqrt(period-mean squared error), with the squared-error
   mean computed using CDO ensmean
4. Period-summed categorical contingency fields H, M, F, C and VALID, using
   CDO enssum, followed by spatially weighted skill scores
5. CSV summaries

Important methodological convention
------------------------------------
The aggregation period is defined by FORECAST INITIALIZATION CYCLES.
For example, start=2026010100 and end=2026011000 uses the ten cycles
2026010100 ... 2026011000 for every lead.

Therefore, the verification valid dates differ with lead:
024 h verifies valid times 2026010200 ... 2026011100
120 h verifies valid times 2026010600 ... 2026011500

Categorical scores are NOT averaged across cycles. The 2-D H, M, F, and C
fields are first summed across cycles. The period scores are then recomputed
from the temporally aggregated contingency fields after spatial aggregation
with cos(latitude) weights.

The unweighted raw totals are also stored for audit/checking, but the reported
period categorical scores use latitude weighting.

Usage
-----
python precipitation_analysis_period_aggregate.py \
    --start-cycle 2026010100 \
    --end-cycle 2026011000 \
    --experiments MONAN_CTL_AMS_CAR MONAN_NEW_AMS_CAR

Optional:
    --allow-missing
    --base-dir /path/to/analyses/precipitation
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

import numpy as np
import xarray as xr


PRECIP_VAR_NAME = "prec"
SKILL_FIELD_NAMES = ("H", "M", "F", "C", "VALID")

DEFAULT_EXPERIMENTS = [
    "MONAN_CTL_AMS_CAR",
    "MONAN_NEW_AMS_CAR",
]

DEFAULT_REFERENCES = ["GPM", "GSMAP", "MSWEP"]
DEFAULT_LEADS = [24, 48, 72, 96, 120]
DEFAULT_THRESHOLDS = [1, 2, 5, 10, 20, 50]
DEFAULT_DOMAIN = "REG"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate precipitation verification over forecast cycles."
    )
    parser.add_argument(
        "--start-cycle",
        required=True,
        help="First initialization cycle, YYYYMMDDHH.",
    )
    parser.add_argument(
        "--end-cycle",
        required=True,
        help="Last initialization cycle, YYYYMMDDHH, inclusive.",
    )
    parser.add_argument(
        "--experiments",
        nargs="+",
        default=DEFAULT_EXPERIMENTS,
        help="Experiment directory names.",
    )
    parser.add_argument(
        "--references",
        nargs="+",
        default=DEFAULT_REFERENCES,
        help="Observational references.",
    )
    parser.add_argument(
        "--leads",
        nargs="+",
        type=int,
        default=DEFAULT_LEADS,
        help="Forecast leads in hours.",
    )
    parser.add_argument(
        "--thresholds",
        nargs="+",
        type=float,
        default=DEFAULT_THRESHOLDS,
        help="Categorical precipitation thresholds in mm/24 h.",
    )
    parser.add_argument(
        "--domain",
        default=DEFAULT_DOMAIN,
        help="Domain label used in output names. Current experiment uses REG.",
    )
    parser.add_argument(
        "--cycle-step-h",
        type=int,
        default=24,
        help="Initialization-cycle interval in hours.",
    )
    parser.add_argument(
        "--base-dir",
        default=str(Path(__file__).resolve().parent),
        help="analyses/precipitation directory.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help=(
            "Allow missing cycles/files. Default is strict: every expected "
            "cycle must be available for every product."
        ),
    )
    return parser.parse_args()


def parse_cycle(cycle: str) -> datetime:
    try:
        return datetime.strptime(cycle, "%Y%m%d%H")
    except ValueError as exc:
        raise ValueError(
            f"Invalid cycle '{cycle}'. Expected YYYYMMDDHH."
        ) from exc


def build_cycles(start_cycle: str, end_cycle: str, step_h: int) -> list[str]:
    start = parse_cycle(start_cycle)
    end = parse_cycle(end_cycle)

    if end < start:
        raise ValueError("end-cycle must be >= start-cycle.")
    if step_h <= 0:
        raise ValueError("cycle-step-h must be > 0.")

    cycles = []
    current = start
    step = timedelta(hours=step_h)

    while current <= end:
        cycles.append(current.strftime("%Y%m%d%H"))
        current += step

    if parse_cycle(cycles[-1]) != end:
        raise ValueError(
            "The requested end-cycle is not aligned with cycle-step-h."
        )

    return cycles


def yearmonth(cycle: str) -> str:
    return cycle[:6]


def threshold_label(threshold: float) -> str:
    if float(threshold).is_integer():
        return str(int(threshold))
    return f"{threshold:g}".replace(".", "p")


def daily_metric_path(
    base_dir: Path,
    experiment: str,
    metric_dir: str,
    metric_prefix: str,
    reference: str,
    cycle: str,
    lead: int,
) -> Path:
    return (
        base_dir
        / "output"
        / experiment
        / "data"
        / metric_dir
        / yearmonth(cycle)
        / cycle
        / f"{metric_prefix}_{reference}_{cycle}_{lead:03d}h.nc"
    )


def daily_skill_path(
    base_dir: Path,
    experiment: str,
    reference: str,
    domain: str,
    cycle: str,
    lead: int,
    threshold: float,
) -> Path:
    return (
        base_dir
        / "output"
        / experiment
        / "data"
        / "Skill"
        / yearmonth(cycle)
        / cycle
        / (
            f"skill_{reference}_{domain}_{cycle}_{lead:03d}h_"
            f"thr{threshold_label(threshold)}mm.nc"
        )
    )


def collect_existing_paths(
    paths: list[Path],
    expected_count: int,
    allow_missing: bool,
    description: str,
) -> list[Path]:
    existing = [path for path in paths if path.exists()]
    missing = [path for path in paths if not path.exists()]

    if missing and not allow_missing:
        message = "\n".join(str(path) for path in missing)
        raise FileNotFoundError(
            f"Missing {len(missing)} required file(s) for {description}:\n"
            f"{message}"
        )

    if not existing:
        raise FileNotFoundError(
            f"No input files found for {description}."
        )

    if len(existing) != expected_count:
        print(
            f"WARNING: {description}: found {len(existing)} of "
            f"{expected_count} expected cases."
        )

    return existing


def _run_cdo_command(command: list[str]) -> None:
    """Run CDO directly, or load the JACI CDO module if needed."""
    print("CDO:", " ".join(shlex.quote(part) for part in command))

    if shutil.which(command[0]) is not None:
        subprocess.run(command, check=True)
        return

    shell_command = "module load cdo && " + " ".join(
        shlex.quote(part) for part in command
    )
    subprocess.run(
        ["bash", "-l", "-c", shell_command],
        check=True,
    )


def cdo_ensmean(paths: list[Path], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "cdo",
        "-O",
        "-f",
        "nc4c",
        "ensmean",
        *[str(path) for path in paths],
        str(output_path),
    ]
    _run_cdo_command(command)


def cdo_enssum_skill(paths: list[Path], output_path: Path) -> None:
    """Sum only H/M/F/C/VALID across cycles, ignoring daily scalar scores."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "cdo",
        "-O",
        "-f",
        "nc4c",
        "-enssum",
        *[str(path) for path in paths],
        str(output_path),
    ]
    _run_cdo_command(command)


def load_precip(path: Path) -> xr.DataArray:
    with xr.open_dataset(path) as ds:
        if PRECIP_VAR_NAME not in ds:
            raise KeyError(
                f"Variable '{PRECIP_VAR_NAME}' not found in {path}"
            )
        da = ds[PRECIP_VAR_NAME].load()

    if "latitude" in da.dims or "latitude" in da.coords:
        da = da.rename({"latitude": "lat"})
    if "longitude" in da.dims or "longitude" in da.coords:
        da = da.rename({"longitude": "lon"})

    return da


def normalize_lat_lon_dataset(ds: xr.Dataset) -> xr.Dataset:
    rename = {}
    if "latitude" in ds.dims or "latitude" in ds.coords:
        rename["latitude"] = "lat"
    if "longitude" in ds.dims or "longitude" in ds.coords:
        rename["longitude"] = "lon"
    if rename:
        ds = ds.rename(rename)
    return ds


def assert_exact_grid(
    reference: xr.DataArray,
    candidate: xr.DataArray,
    path: Path,
) -> None:
    try:
        xr.align(reference, candidate, join="exact", copy=False)
    except ValueError as exc:
        raise ValueError(
            f"Grid mismatch detected in {path}. "
            "Aggregation aborted to avoid silently mixing grids."
        ) from exc


def count_valid_cases(paths: list[Path]) -> xr.DataArray:
    """
    Count finite values at each grid point without holding all cases in memory.

    This preserves an explicit audit field for missing-value handling while CDO
    performs the actual ensemble mean.
    """
    first = load_precip(paths[0])
    count = xr.where(np.isfinite(first), 1, 0).astype("int16")

    for path in paths[1:]:
        da = load_precip(path)
        assert_exact_grid(first, da, path)
        count = count + np.isfinite(da).astype("int16")

    count.name = "n_valid_cases"
    count.attrs["long_name"] = "number of finite cases used at each grid point"
    return count


def validate_skill_grids(paths: list[Path]) -> None:
    with xr.open_dataset(paths[0]) as ds:
        ds = normalize_lat_lon_dataset(ds)
        first = ds["H"].load()

    for path in paths[1:]:
        with xr.open_dataset(path) as ds:
            ds = normalize_lat_lon_dataset(ds)
            candidate = ds["H"].load()
        assert_exact_grid(first, candidate, path)


def weighted_spatial_mean(da: xr.DataArray) -> float:
    if "lat" not in da.coords:
        return float(da.mean(skipna=True).item())

    weights = xr.DataArray(
        np.cos(np.deg2rad(da["lat"])),
        coords={"lat": da["lat"]},
        dims=["lat"],
    )
    return float(da.weighted(weights).mean(skipna=True).item())


def weighted_sum(da: xr.DataArray) -> float:
    """Area-weighted spatial sum for a regular latitude/longitude grid."""
    if "lat" not in da.coords:
        return float(da.fillna(0.0).sum().item())

    weights = xr.DataArray(
        np.cos(np.deg2rad(da["lat"])),
        coords={"lat": da["lat"]},
        dims=["lat"],
    )
    return float((da.fillna(0.0) * weights).sum().item())


def skill_scores(
    h: float,
    m: float,
    f: float,
    c: float,
) -> dict[str, float]:
    total = h + m + f + c

    return {
        "ACC": (h + c) / total if total else np.nan,
        "POD": h / (h + m) if (h + m) else np.nan,
        "POFD": f / (f + c) if (f + c) else np.nan,
        "FAR": f / (h + f) if (h + f) else np.nan,
        "CSI": h / (h + m + f) if (h + m + f) else np.nan,
        "F1": 2 * h / (2 * h + f + m) if (2 * h + f + m) else np.nan,
    }


def set_grads_coordinate_attrs(ds: xr.Dataset) -> xr.Dataset:
    if "lat" in ds.coords:
        ds["lat"].attrs.update(
            {
                "standard_name": "latitude",
                "units": "degrees_north",
                "axis": "Y",
            }
        )
    if "lon" in ds.coords:
        ds["lon"].attrs.update(
            {
                "standard_name": "longitude",
                "units": "degrees_east",
                "axis": "X",
            }
        )
    return ds


def save_continuous_dataset(
    field: xr.DataArray,
    n_valid_cases: xr.DataArray,
    output_path: Path,
    metric: str,
    experiment: str,
    reference: str,
    lead: int,
    period: str,
    cycles: list[str],
    n_cases_found: int,
    extra_vars: dict[str, xr.DataArray] | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ds = xr.Dataset(
        {
            PRECIP_VAR_NAME: field.astype("float32"),
            "n_valid_cases": n_valid_cases.astype("int16"),
        }
    )

    if extra_vars:
        for name, da in extra_vars.items():
            ds[name] = da

    ds = set_grads_coordinate_attrs(ds)

    ds.attrs.update(
        {
            "description": f"{metric} aggregated across forecast initialization cycles",
            "metric": metric,
            "experiment": experiment,
            "reference": reference,
            "lead_time_h": np.int32(lead),
            "aggregation_period": period,
            "period_definition": "forecast initialization cycles",
            "first_cycle": cycles[0],
            "last_cycle": cycles[-1],
            "n_cases_expected": np.int32(len(cycles)),
            "n_cases_found": np.int32(n_cases_found),
            "temporal_aggregation": "CDO ensmean",
            "missing_value_treatment": (
                "CDO ensemble mean over input metric fields; n_valid_cases "
                "stores the local finite-input count for audit"
            ),
        }
    )

    encoding = {
        PRECIP_VAR_NAME: {"zlib": True, "complevel": 1},
        "n_valid_cases": {"zlib": True, "complevel": 1},
    }
    if extra_vars:
        for name in extra_vars:
            encoding[name] = {"zlib": True, "complevel": 1}

    ds.to_netcdf(
        output_path,
        engine="netcdf4",
        encoding=encoding,
    )


def aggregate_continuous_with_cdo(
    paths: list[Path],
    expected_count: int,
    allow_missing: bool,
    description: str,
) -> tuple[xr.DataArray, xr.DataArray, int]:
    existing = collect_existing_paths(
        paths,
        expected_count,
        allow_missing,
        description,
    )

    n_valid_cases = count_valid_cases(existing)

    with tempfile.TemporaryDirectory(prefix="precip_agg_") as tmpdir:
        tmp_path = Path(tmpdir) / "ensmean.nc"
        cdo_ensmean(existing, tmp_path)
        mean_field = load_precip(tmp_path).astype("float32")

    assert_exact_grid(n_valid_cases, mean_field, Path("CDO ensmean output"))

    return mean_field, n_valid_cases, len(existing)


def aggregate_skill_with_cdo(
    paths: list[Path],
    expected_count: int,
    allow_missing: bool,
    description: str,
) -> tuple[
    xr.Dataset,
    dict[str, int],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    int,
]:
    existing = collect_existing_paths(
        paths,
        expected_count,
        allow_missing,
        description,
    )

    validate_skill_grids(existing)

    with tempfile.TemporaryDirectory(prefix="skill_agg_") as tmpdir:
        tmp_path = Path(tmpdir) / "enssum_skill.nc"
        cdo_enssum_skill(existing, tmp_path)
        with xr.open_dataset(tmp_path) as ds:
            ds = normalize_lat_lon_dataset(ds)
            aggregated = ds[list(SKILL_FIELD_NAMES)].load()

    for name in SKILL_FIELD_NAMES:
        aggregated[name] = aggregated[name].astype("int32")

    # Strong internal consistency check: each valid gridpoint-case must belong
    # to exactly one contingency category.
    category_sum = (
        aggregated["H"]
        + aggregated["M"]
        + aggregated["F"]
        + aggregated["C"]
    )
    if not bool((category_sum == aggregated["VALID"]).all().item()):
        max_diff = int(
            np.abs(category_sum - aggregated["VALID"]).max().item()
        )
        raise ValueError(
            "Aggregated contingency consistency check failed: "
            "H+M+F+C != VALID. "
            f"Maximum absolute difference = {max_diff}."
        )

    raw_counts = {
        name: int(aggregated[name].sum().item())
        for name in ("H", "M", "F", "C")
    }
    raw_counts["N"] = sum(raw_counts.values())

    weighted_counts = {
        name: weighted_sum(aggregated[name])
        for name in ("H", "M", "F", "C")
    }
    weighted_counts["N"] = sum(weighted_counts.values())

    weighted_valid = weighted_sum(aggregated["VALID"])
    if not np.isclose(
        weighted_counts["N"],
        weighted_valid,
        rtol=1.0e-12,
        atol=1.0e-6,
    ):
        raise ValueError(
            "Weighted contingency consistency check failed: "
            "weighted H+M+F+C != weighted VALID."
        )

    raw_scores = skill_scores(
        raw_counts["H"],
        raw_counts["M"],
        raw_counts["F"],
        raw_counts["C"],
    )

    scores = skill_scores(
        weighted_counts["H"],
        weighted_counts["M"],
        weighted_counts["F"],
        weighted_counts["C"],
    )

    return (
        aggregated,
        raw_counts,
        weighted_counts,
        raw_scores,
        scores,
        len(existing),
    )


def save_skill_dataset(
    output_path: Path,
    fields: xr.Dataset,
    raw_counts: dict[str, float],
    weighted_counts: dict[str, float],
    raw_scores: dict[str, float],
    scores: dict[str, float],
    n_cases: int,
    experiment: str,
    reference: str,
    domain: str,
    lead: int,
    threshold: float,
    period: str,
    cycles: list[str],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ds = fields.copy()

    ds["H_total"] = xr.DataArray(np.int64(raw_counts["H"]))
    ds["M_total"] = xr.DataArray(np.int64(raw_counts["M"]))
    ds["F_total"] = xr.DataArray(np.int64(raw_counts["F"]))
    ds["C_total"] = xr.DataArray(np.int64(raw_counts["C"]))
    ds["N_total"] = xr.DataArray(np.int64(raw_counts["N"]))

    ds["H_weighted"] = xr.DataArray(np.float64(weighted_counts["H"]))
    ds["M_weighted"] = xr.DataArray(np.float64(weighted_counts["M"]))
    ds["F_weighted"] = xr.DataArray(np.float64(weighted_counts["F"]))
    ds["C_weighted"] = xr.DataArray(np.float64(weighted_counts["C"]))
    ds["N_weighted"] = xr.DataArray(np.float64(weighted_counts["N"]))

    for name, value in raw_scores.items():
        ds[f"{name}_raw"] = xr.DataArray(np.float64(value))

    for name, value in scores.items():
        ds[name] = xr.DataArray(np.float64(value))

    ds["n_cases"] = xr.DataArray(np.int32(n_cases))

    ds = set_grads_coordinate_attrs(ds)

    ds["H"].attrs["long_name"] = "period-summed hits"
    ds["M"].attrs["long_name"] = "period-summed misses"
    ds["F"].attrs["long_name"] = "period-summed false alarms"
    ds["C"].attrs["long_name"] = "period-summed correct negatives"
    ds["VALID"].attrs["long_name"] = "number of valid forecast-observation pairs in period"

    ds.attrs.update(
        {
            "description": (
                "Categorical precipitation verification aggregated across "
                "forecast initialization cycles"
            ),
            "experiment": experiment,
            "reference": reference,
            "domain": domain,
            "lead_time_h": np.int32(lead),
            "threshold_mm_24h": np.float32(threshold),
            "aggregation_period": period,
            "period_definition": "forecast initialization cycles",
            "first_cycle": cycles[0],
            "last_cycle": cycles[-1],
            "n_cases_expected": np.int32(len(cycles)),
            "n_cases_found": np.int32(n_cases),
            "temporal_aggregation": "CDO enssum of H, M, F, C, VALID",
            "spatial_weighting": "cos(latitude)",
            "score_definition": (
                "ACC/POD/POFD/FAR/CSI/F1 recomputed from temporally summed "
                "H/M/F/C after cos(latitude) spatial weighting"
            ),
            "raw_score_definition": (
                "Variables with suffix _raw are recomputed from unweighted "
                "H_total/M_total/F_total/C_total for audit and comparison "
                "with the daily unweighted-score convention"
            ),
            "raw_total_definition": (
                "H_total/M_total/F_total/C_total/N_total are unweighted sums "
                "of gridpoint-case counts and are stored for audit"
            ),
            "missing_data_handling": (
                "Daily invalid forecast-observation pairs have H=M=F=C=0 "
                "and VALID=0; VALID is summed across cycles"
            ),
        }
    )

    encoding = {
        name: {
            "dtype": "int32",
            "zlib": True,
            "complevel": 1,
        }
        for name in SKILL_FIELD_NAMES
    }

    ds.to_netcdf(
        output_path,
        engine="netcdf4",
        encoding=encoding,
    )


def validate_experiment_grids(
    base_dir: Path,
    experiments: list[str],
    cycles: list[str],
    reference: str,
    lead: int,
) -> None:
    if len(experiments) < 2:
        return

    ref_path = daily_metric_path(
        base_dir,
        experiments[0],
        "Bias",
        "bias",
        reference,
        cycles[0],
        lead,
    )
    if not ref_path.exists():
        raise FileNotFoundError(ref_path)

    ref_da = load_precip(ref_path)

    for experiment in experiments[1:]:
        path = daily_metric_path(
            base_dir,
            experiment,
            "Bias",
            "bias",
            reference,
            cycles[0],
            lead,
        )
        if not path.exists():
            raise FileNotFoundError(path)

        da = load_precip(path)
        assert_exact_grid(ref_da, da, path)

    print(
        "Grid validation: experiments use identical coordinates "
        f"for cycle {cycles[0]} and lead {lead:03d} h."
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        return

    with path.open("w", newline="", encoding="utf-8") as fobj:
        writer = csv.DictWriter(
            fobj,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    base_dir = Path(args.base_dir).resolve()
    cycles = build_cycles(
        args.start_cycle,
        args.end_cycle,
        args.cycle_step_h,
    )
    period = f"{cycles[0]}_{cycles[-1]}"
    allow_missing = args.allow_missing

    print("=" * 80)
    print("Precipitation verification period aggregation")
    print(f"Base directory: {base_dir}")
    print("Period definition: forecast initialization cycles")
    print(f"First cycle: {cycles[0]}")
    print(f"Last cycle:  {cycles[-1]}")
    print(f"Expected cycles: {len(cycles)}")
    print(f"Experiments: {args.experiments}")
    print(f"References: {args.references}")
    print(f"Leads: {args.leads}")
    print(f"Thresholds: {args.thresholds}")
    print(f"Allow missing: {allow_missing}")
    print("Continuous temporal aggregation: CDO ensmean")
    print("Categorical temporal aggregation: CDO enssum")
    print("Categorical spatial weighting: cos(latitude)")
    print("=" * 80)

    validate_experiment_grids(
        base_dir,
        args.experiments,
        cycles,
        args.references[0],
        args.leads[0],
    )

    continuous_summary_rows: list[dict] = []
    skill_summary_rows: list[dict] = []

    for experiment in args.experiments:
        print()
        print("#" * 80)
        print(f"Experiment: {experiment}")
        print("#" * 80)

        aggregate_root = (
            base_dir
            / "output"
            / experiment
            / "aggregated"
            / period
        )

        for reference in args.references:
            for lead in args.leads:
                print(
                    f"Continuous metrics: {reference}, "
                    f"lead {lead:03d} h"
                )

                bias_paths = [
                    daily_metric_path(
                        base_dir,
                        experiment,
                        "Bias",
                        "bias",
                        reference,
                        cycle,
                        lead,
                    )
                    for cycle in cycles
                ]
                mae_paths = [
                    daily_metric_path(
                        base_dir,
                        experiment,
                        "MAE",
                        "mae",
                        reference,
                        cycle,
                        lead,
                    )
                    for cycle in cycles
                ]
                sqerr_paths = [
                    daily_metric_path(
                        base_dir,
                        experiment,
                        "SQERR",
                        "sqerr",
                        reference,
                        cycle,
                        lead,
                    )
                    for cycle in cycles
                ]

                bias_mean, bias_nvalid, n_bias = aggregate_continuous_with_cdo(
                    bias_paths,
                    len(cycles),
                    allow_missing,
                    f"Bias {experiment} {reference} {lead:03d} h",
                )
                mae_mean, mae_nvalid, n_mae = aggregate_continuous_with_cdo(
                    mae_paths,
                    len(cycles),
                    allow_missing,
                    f"MAE {experiment} {reference} {lead:03d} h",
                )
                sqerr_mean, sqerr_nvalid, n_sqerr = aggregate_continuous_with_cdo(
                    sqerr_paths,
                    len(cycles),
                    allow_missing,
                    f"SQERR {experiment} {reference} {lead:03d} h",
                )

                rmse = np.sqrt(sqerr_mean).astype("float32")

                if not (n_bias == n_mae == n_sqerr):
                    raise RuntimeError(
                        "Bias, MAE, and SQERR have different numbers of cases."
                    )

                bias_out = (
                    aggregate_root
                    / "data"
                    / "Bias"
                    / (
                        f"bias_{reference}_{args.domain}_{period}"
                        f"_mean_{lead:03d}h.nc"
                    )
                )
                mae_out = (
                    aggregate_root
                    / "data"
                    / "MAE"
                    / (
                        f"mae_{reference}_{args.domain}_{period}"
                        f"_mean_{lead:03d}h.nc"
                    )
                )
                rmse_out = (
                    aggregate_root
                    / "data"
                    / "RMSE"
                    / (
                        f"rmse_{reference}_{args.domain}_{period}"
                        f"_{lead:03d}h.nc"
                    )
                )

                save_continuous_dataset(
                    bias_mean,
                    bias_nvalid,
                    bias_out,
                    "Bias",
                    experiment,
                    reference,
                    lead,
                    period,
                    cycles,
                    n_bias,
                )
                save_continuous_dataset(
                    mae_mean,
                    mae_nvalid,
                    mae_out,
                    "MAE",
                    experiment,
                    reference,
                    lead,
                    period,
                    cycles,
                    n_mae,
                )
                save_continuous_dataset(
                    rmse,
                    sqerr_nvalid,
                    rmse_out,
                    "RMSE",
                    experiment,
                    reference,
                    lead,
                    period,
                    cycles,
                    n_sqerr,
                    extra_vars={
                        "mean_sqerr": sqerr_mean.astype("float32")
                    },
                )

                continuous_summary_rows.append(
                    {
                        "experiment": experiment,
                        "reference": reference,
                        "domain": args.domain,
                        "lead_h": lead,
                        "n_cases": n_bias,
                        "bias_area_mean_mm": weighted_spatial_mean(
                            bias_mean
                        ),
                        "mae_area_mean_mm": weighted_spatial_mean(
                            mae_mean
                        ),
                        "rmse_field_area_mean_mm": weighted_spatial_mean(
                            rmse
                        ),
                    }
                )

                for threshold in args.thresholds:
                    skill_paths = [
                        daily_skill_path(
                            base_dir,
                            experiment,
                            reference,
                            args.domain,
                            cycle,
                            lead,
                            threshold,
                        )
                        for cycle in cycles
                    ]

                    (
                        skill_fields,
                        raw_counts,
                        weighted_counts,
                        raw_scores,
                        scores,
                        n_skill,
                    ) = aggregate_skill_with_cdo(
                        skill_paths,
                        len(cycles),
                        allow_missing,
                        (
                            f"Skill {experiment} {reference} "
                            f"{lead:03d} h {threshold:g} mm"
                        ),
                    )

                    thr_label = threshold_label(threshold)

                    skill_out = (
                        aggregate_root
                        / "data"
                        / "Skill"
                        / (
                            f"skill_{reference}_{args.domain}_{period}"
                            f"_{lead:03d}h_thr{thr_label}mm.nc"
                        )
                    )

                    save_skill_dataset(
                        skill_out,
                        skill_fields,
                        raw_counts,
                        weighted_counts,
                        raw_scores,
                        scores,
                        n_skill,
                        experiment,
                        reference,
                        args.domain,
                        lead,
                        threshold,
                        period,
                        cycles,
                    )

                    skill_summary_rows.append(
                        {
                            "experiment": experiment,
                            "reference": reference,
                            "domain": args.domain,
                            "lead_h": lead,
                            "threshold_mm": threshold,
                            "n_cases": n_skill,
                            "H_total_raw": int(raw_counts["H"]),
                            "M_total_raw": int(raw_counts["M"]),
                            "F_total_raw": int(raw_counts["F"]),
                            "C_total_raw": int(raw_counts["C"]),
                            "N_total_raw": int(raw_counts["N"]),
                            "H_weighted": weighted_counts["H"],
                            "M_weighted": weighted_counts["M"],
                            "F_weighted": weighted_counts["F"],
                            "C_weighted": weighted_counts["C"],
                            "N_weighted": weighted_counts["N"],
                            "ACC_raw": raw_scores["ACC"],
                            "POD_raw": raw_scores["POD"],
                            "POFD_raw": raw_scores["POFD"],
                            "FAR_raw": raw_scores["FAR"],
                            "CSI_raw": raw_scores["CSI"],
                            "F1_raw": raw_scores["F1"],
                            "ACC": scores["ACC"],
                            "POD": scores["POD"],
                            "POFD": scores["POFD"],
                            "FAR": scores["FAR"],
                            "CSI": scores["CSI"],
                            "F1": scores["F1"],
                        }
                    )

        summary_dir = aggregate_root / "summary"

        exp_cont_rows = [
            row
            for row in continuous_summary_rows
            if row["experiment"] == experiment
        ]
        exp_skill_rows = [
            row
            for row in skill_summary_rows
            if row["experiment"] == experiment
        ]

        write_csv(
            summary_dir / "continuous_metrics_summary.csv",
            exp_cont_rows,
        )
        write_csv(
            summary_dir / "skill_metrics_summary.csv",
            exp_skill_rows,
        )

    comparison_root = (
        base_dir
        / "output"
        / "period_comparison_summary"
        / period
    )

    write_csv(
        comparison_root
        / "continuous_metrics_summary_all_experiments.csv",
        continuous_summary_rows,
    )
    write_csv(
        comparison_root
        / "skill_metrics_summary_all_experiments.csv",
        skill_summary_rows,
    )

    print()
    print("=" * 80)
    print("Aggregation completed.")
    print(f"Period: {period}")
    print(
        "Combined CSV summaries: "
        f"{comparison_root}"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()