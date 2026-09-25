#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
precipitation_analysis_period_plot_regional_series.py

Generate lead-time series of period-aggregated MAE and RMSE for the MONAN
CTL and NEW experiments, separately for South American sub-regions.

IMPORTANT
---------
The regional values are calculated directly from the aggregated NetCDF fields.
The script does NOT read the aggregated summary CSVs.

For MAE:
    regional MAE = cosine(latitude)-weighted spatial mean of the aggregated
                   MAE field (variable "prec").

For RMSE:
    regional RMSE = sqrt(
        cosine(latitude)-weighted spatial mean of "mean_sqerr"
    )

Thus, RMSE is NOT calculated as the spatial mean of the RMSE map.

Regionalization
---------------
The default boxes follow Gomes et al. (2022), Atmosphere, 13, 107,
"WRF Sensitivity for Seasonal Climate Simulations of Precipitation Fields
on the CORDEX South America Domain", DOI: 10.3390/atmos13010107.

The eight physical sub-domains used here are:
    AMZN  - North Amazon
    AMZS  - South Amazon
    NEBN  - North-Northeast Brazil
    NEBS  - South-Northeast Brazil
    PEQU  - Peru-Ecuador
    CHAC  - Chaco
    SUDE  - Southeast Brazil
    SURU  - South Brazil and Uruguay

Subdomains from Gomes et al. (2022) WRF Sensitivity for Seasonal Climate 
Simulations of Precipitation Fields on the CORDEX South America Domain
https://www.mdpi.com/2073-4433/13/1/107

Output
------
1. One CSV calculated from the NetCDF fields:
   output/period_comparison_summary/<period>/
       continuous_metrics_regional_by_lead.csv

2. Six figures by default:
   2 metrics (MAE, RMSE) x 3 observational references.

   Each figure contains the selected regional subplots and two lines:
   CTL and NEW.

Example
-------
python precipitation_analysis_period_plot_regional_series.py \
    --start-cycle 2026010100 \
    --end-cycle 2026011000 \
    --strict
"""

from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


# =============================================================================
# Configuration
# =============================================================================

EXPERIMENTS = (
    ("MONAN_CTL_AMS_CAR", "CTL"),
    ("MONAN_NEW_AMS_CAR", "NEW"),
)

REFERENCES = ("GPM", "GSMAP", "MSWEP")

REFERENCE_LABELS = {
    "GPM": "GPM IMERG",
    "GSMAP": "GSMaP",
    "MSWEP": "MSWEP",
}

DEFAULT_METRICS = ("MAE", "RMSE")
DEFAULT_LEADS = (24, 48, 72, 96, 120)

PRECIP_VAR_NAME = "prec"
MEAN_SQERR_VAR_NAME = "mean_sqerr"

# Gomes et al. (2022), Atmosphere 13, 107.
# Longitudes are stored here in the conventional -180..180 notation.
REGIONS = {
    "AMZN": {
        "name": "North Amazon",
        "lat": (-5.0, 5.0),
        "lon": (-70.0, -50.0),
    },
    "AMZS": {
        "name": "South Amazon",
        "lat": (-15.0, -5.0),
        "lon": (-70.0, -50.0),
    },
    "NEBN": {
        "name": "North-Northeast Brazil",
        "lat": (-8.0, -3.0),
        "lon": (-44.0, -35.0),
    },
    "NEBS": {
        "name": "South-Northeast Brazil",
        "lat": (-15.0, -8.0),
        "lon": (-44.0, -35.0),
    },
    "PEQU": {
        "name": "Peru-Ecuador",
        "lat": (-10.0, 0.0),
        "lon": (-83.0, -75.0),
    },
    "CHAC": {
        "name": "Chaco",
        "lat": (-23.0, -15.0),
        "lon": (-64.0, -55.0),
    },
    "SUDE": {
        "name": "Southeast Brazil",
        "lat": (-23.0, -15.0),
        "lon": (-55.0, -39.0),
    },
    "SURU": {
        "name": "South Brazil and Uruguay",
        "lat": (-35.0, -23.0),
        "lon": (-60.0, -50.0),
    },
}

FULL_DOMAIN_CODE = "FULL"
FULL_DOMAIN_NAME = "Full REG domain"

DEFAULT_REGIONS = tuple(REGIONS)

# =============================================================================
# Date helpers
# =============================================================================

def parse_cycle(cycle: str) -> datetime:
    """Parse YYYYMMDDHH."""
    try:
        return datetime.strptime(cycle, "%Y%m%d%H")
    except ValueError as exc:
        raise ValueError(
            f"Invalid cycle '{cycle}'. Expected YYYYMMDDHH."
        ) from exc


def valid_period(
    start_cycle: str,
    end_cycle: str,
    lead: int,
) -> tuple[str, str]:
    """Return first and last valid times for one lead."""
    start = parse_cycle(start_cycle) + timedelta(hours=lead)
    end = parse_cycle(end_cycle) + timedelta(hours=lead)

    return (
        start.strftime("%Y%m%d%H"),
        end.strftime("%Y%m%d%H"),
    )


# =============================================================================
# Paths
# =============================================================================

def input_path(
    base_dir: Path,
    experiment: str,
    period: str,
    metric: str,
    reference: str,
    lead: int,
) -> Path:
    """Build path to one aggregated continuous-metric NetCDF."""
    data_dir = (
        base_dir
        / "output"
        / experiment
        / "aggregated"
        / period
        / "data"
        / metric
    )

    if metric == "MAE":
        filename = (
            f"mae_{reference}_REG_{period}_mean_{lead:03d}h.nc"
        )
    elif metric == "RMSE":
        filename = (
            f"rmse_{reference}_REG_{period}_{lead:03d}h.nc"
        )
    else:
        raise ValueError(
            f"Unsupported metric '{metric}'. Use MAE and/or RMSE."
        )

    return data_dir / filename


# =============================================================================
# Coordinate and spatial helpers
# =============================================================================

def standardize_lat_lon(da: xr.DataArray) -> xr.DataArray:
    """
    Rename latitude/longitude to lat/lon and normalize longitude to 0..360.

    No remapping is performed.
    """
    rename = {}

    if "latitude" in da.dims or "latitude" in da.coords:
        rename["latitude"] = "lat"

    if "longitude" in da.dims or "longitude" in da.coords:
        rename["longitude"] = "lon"

    if rename:
        da = da.rename(rename)

    da = da.squeeze(drop=True)

    if "lat" not in da.coords or "lon" not in da.coords:
        raise ValueError(
            f"Expected lat/lon coordinates; available coordinates: "
            f"{list(da.coords)}"
        )

    if da["lat"].ndim != 1 or da["lon"].ndim != 1:
        raise ValueError(
            "This script expects a regular 1-D latitude/longitude grid."
        )

    if float(da["lon"].min()) < 0.0:
        da = (
            da.assign_coords(lon=(da["lon"] + 360.0) % 360.0)
            .sortby("lon")
        )

    return da


def lon_to_360(lon: float) -> float:
    """Convert longitude from -180..180 to 0..360."""
    return lon % 360.0


def subset_region(
    da: xr.DataArray,
    region_code: str,
) -> xr.DataArray:
    """
    Crop a DataArray to one literature-defined rectangular sub-domain.

    This only crops the existing common REG grid. No mask or remapping is
    introduced.
    """
    if region_code == FULL_DOMAIN_CODE:
        return da

    cfg = REGIONS[region_code]

    lat_min, lat_max = cfg["lat"]
    lon_min_raw, lon_max_raw = cfg["lon"]

    lon_min = lon_to_360(lon_min_raw)
    lon_max = lon_to_360(lon_max_raw)

    if float(da["lat"][0]) > float(da["lat"][-1]):
        lat_slice = slice(lat_max, lat_min)
    else:
        lat_slice = slice(lat_min, lat_max)

    # All default regions are west of Greenwich and do not cross 0/360
    # after conversion, e.g. -70..-50 -> 290..310.
    if lon_min <= lon_max:
        sub = da.sel(
            lat=lat_slice,
            lon=slice(lon_min, lon_max),
        )
    else:
        # Generic fallback for a region crossing 0/360.
        west = da.sel(
            lat=lat_slice,
            lon=slice(lon_min, 360.0),
        )
        east = da.sel(
            lat=lat_slice,
            lon=slice(0.0, lon_max),
        )
        sub = xr.concat([west, east], dim="lon")

    if (
        sub.sizes.get("lat", 0) == 0
        or sub.sizes.get("lon", 0) == 0
    ):
        raise ValueError(
            f"Empty spatial subset for region {region_code}: "
            f"lat={cfg['lat']}, lon={cfg['lon']}."
        )

    return sub


def latitude_weights(da: xr.DataArray) -> xr.DataArray:
    """Cosine(latitude) weights for a regular lat/lon grid."""
    return xr.DataArray(
        np.cos(np.deg2rad(da["lat"])),
        coords={"lat": da["lat"]},
        dims=("lat",),
    )


def weighted_mean(da: xr.DataArray) -> float:
    """Cosine(latitude)-weighted spatial mean."""
    weights = latitude_weights(da)

    value = da.weighted(weights).mean(
        dim=("lat", "lon"),
        skipna=True,
    )

    return float(value.item())


# =============================================================================
# Metric calculation directly from aggregated NetCDF fields
# =============================================================================

def regional_metric_value(
    base_dir: Path,
    experiment: str,
    period: str,
    metric: str,
    reference: str,
    lead: int,
    region_code: str,
) -> tuple[float, int, Path]:
    """
    Calculate one regional scalar directly from an aggregated NetCDF.

    MAE:
        area-weighted mean of the aggregated MAE field.

    RMSE:
        sqrt(area-weighted mean of the aggregated mean squared error).
    """
    path = input_path(
        base_dir=base_dir,
        experiment=experiment,
        period=period,
        metric=metric,
        reference=reference,
        lead=lead,
    )

    if not path.exists():
        raise FileNotFoundError(path)

    with xr.open_dataset(path) as ds:
        if metric == "MAE":
            if PRECIP_VAR_NAME not in ds:
                raise KeyError(
                    f"Variable '{PRECIP_VAR_NAME}' not found in {path}. "
                    f"Available: {list(ds.data_vars)}"
                )

            field = standardize_lat_lon(
                ds[PRECIP_VAR_NAME].load()
            ).astype("float64")

            region = subset_region(
                field,
                region_code,
            )

            value = weighted_mean(region)
            n_valid_gridpoints = int(
                np.isfinite(region).sum().item()
            )

        elif metric == "RMSE":
            if MEAN_SQERR_VAR_NAME not in ds:
                raise KeyError(
                    f"Variable '{MEAN_SQERR_VAR_NAME}' not found in {path}. "
                    "RMSE will not be approximated from the spatial mean of "
                    "the RMSE map because that changes the metric definition."
                )

            mean_sqerr = standardize_lat_lon(
                ds[MEAN_SQERR_VAR_NAME].load()
            ).astype("float64")

            region = subset_region(
                mean_sqerr,
                region_code,
            )

            mse_regional = weighted_mean(region)

            if mse_regional < 0.0:
                # Numerical noise could theoretically produce a tiny
                # negative value, but a substantial negative value is invalid.
                if mse_regional < -1.0e-10:
                    raise ValueError(
                        f"Negative regional mean squared error "
                        f"({mse_regional}) in {path}, region {region_code}."
                    )
                mse_regional = 0.0

            value = float(np.sqrt(mse_regional))
            n_valid_gridpoints = int(
                np.isfinite(region).sum().item()
            )

        else:
            raise ValueError(metric)

    return value, n_valid_gridpoints, path


def calculate_all_values(
    base_dir: Path,
    start_cycle: str,
    end_cycle: str,
    metrics: tuple[str, ...],
    leads: tuple[int, ...],
    region_codes: tuple[str, ...],
    strict: bool,
) -> list[dict]:
    """Calculate all regional values from aggregated NetCDF fields."""
    period = f"{start_cycle}_{end_cycle}"
    rows: list[dict] = []

    for metric in metrics:
        for reference in REFERENCES:
            for experiment, experiment_label in EXPERIMENTS:
                for region_code in region_codes:

                    if region_code == FULL_DOMAIN_CODE:
                        region_name = FULL_DOMAIN_NAME
                        lat_limits = (None, None)
                        lon_limits = (None, None)
                    else:
                        region_cfg = REGIONS[region_code]
                        region_name = region_cfg["name"]
                        lat_limits = region_cfg["lat"]
                        lon_limits = region_cfg["lon"]

                    for lead in leads:
                        first_valid, last_valid = valid_period(
                            start_cycle,
                            end_cycle,
                            lead,
                        )

                        try:
                            value, n_valid, path = regional_metric_value(
                                base_dir=base_dir,
                                experiment=experiment,
                                period=period,
                                metric=metric,
                                reference=reference,
                                lead=lead,
                                region_code=region_code,
                            )
                        except Exception as exc:
                            if strict:
                                raise

                            print(
                                "WARNING: skipped "
                                f"{metric} {reference} {experiment_label} "
                                f"{region_code} F{lead:03d}: {exc}"
                            )
                            continue

                        rows.append(
                            {
                                "metric": metric,
                                "reference": reference,
                                "experiment": experiment,
                                "experiment_label": experiment_label,
                                "region": region_code,
                                "region_name": region_name,
                                "lat_min": lat_limits[0],
                                "lat_max": lat_limits[1],
                                "lon_min": lon_limits[0],
                                "lon_max": lon_limits[1],
                                "lead_h": lead,
                                "start_cycle": start_cycle,
                                "end_cycle": end_cycle,
                                "first_valid_time": first_valid,
                                "last_valid_time": last_valid,
                                "value_mm": value,
                                "n_valid_gridpoints": n_valid,
                                "source_file": str(path),
                            }
                        )

                        print(
                            f"{metric:4s} | {reference:5s} | "
                            f"{experiment_label:3s} | {region_code:4s} | "
                            f"F{lead:03d} | {value:7.3f} mm | "
                            f"Ngrid={n_valid}"
                        )

    return rows


# =============================================================================
# CSV
# =============================================================================

def write_csv(
    output_path: Path,
    rows: list[dict],
) -> None:
    """Write values calculated from the NetCDF fields."""
    if not rows:
        raise RuntimeError("No regional values were calculated.")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = list(rows[0].keys())

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as fobj:
        writer = csv.DictWriter(
            fobj,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV saved: {output_path}")


# =============================================================================
# Plotting
# =============================================================================

def select_rows(
    rows: list[dict],
    metric: str,
    reference: str,
    experiment_label: str,
    region_code: str,
) -> list[dict]:
    """Select and order rows for one line."""
    selected = [
        row
        for row in rows
        if (
            row["metric"] == metric
            and row["reference"] == reference
            and row["experiment_label"] == experiment_label
            and row["region"] == region_code
        )
    ]

    return sorted(
        selected,
        key=lambda row: row["lead_h"],
    )

def plot_full_domain_metric(
    rows: list[dict],
    metric: str,
    start_cycle: str,
    end_cycle: str,
    output_root: Path,
) -> Path:

    fig, axes = plt.subplots(
        nrows=1,
        ncols=3,
        figsize=(13.5, 4.2),
        sharex=True,
        sharey=True,
    )

    figure_values = [
        row["value_mm"]
        for row in rows
        if (
            row["metric"] == metric
            and row["region"] == FULL_DOMAIN_CODE
            and np.isfinite(row["value_mm"])
        )
    ]

    if not figure_values:
        raise RuntimeError(
            f"No full-domain values available for {metric}."
        )

    ymax = max(figure_values)
    y_upper = ymax * 1.10 if ymax > 0.0 else 1.0

    line_styles = {
        "CTL": {
            "linestyle": "-",
            "marker": "o",
        },
        "NEW": {
            "linestyle": "--",
            "marker": "s",
        },
    }

    for col, reference in enumerate(REFERENCES):

        ax = axes[col]

        for experiment_label in ("CTL", "NEW"):

            series_rows = select_rows(
                rows=rows,
                metric=metric,
                reference=reference,
                experiment_label=experiment_label,
                region_code=FULL_DOMAIN_CODE,
            )

            x = [
                row["lead_h"]
                for row in series_rows
            ]

            y = [
                row["value_mm"]
                for row in series_rows
            ]

            ax.plot(
                x,
                y,
                linewidth=1.8,
                markersize=5.0,
                label=experiment_label,
                **line_styles[experiment_label],
            )

        ax.set_title(
            REFERENCE_LABELS[reference],
            fontsize=11,
        )

        ax.set_xticks(DEFAULT_LEADS)
        ax.set_ylim(0.0, y_upper)

        ax.grid(
            True,
            linewidth=0.4,
            alpha=0.4,
            linestyle=":",
        )

        ax.set_xlabel("Forecast lead (h)")

        if col == 0:
            ax.set_ylabel(f"{metric} (mm)")

    handles, labels = axes[0].get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 0.92),
    )

    fig.suptitle(
        f"Full REG domain {metric} by forecast lead\n"
        f"Initialization cycles: "
        f"{start_cycle}–{end_cycle}",
        fontsize=14,
        y=1.00,
    )

    fig.tight_layout(
        rect=(0.0, 0.0, 1.0, 0.87),
    )

    period = f"{start_cycle}_{end_cycle}"

    output_dir = (
        output_root
        / period
        / "Full_domain_series"
        / metric
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / (
        f"{metric}_CTL_vs_NEW_full_REG_"
        f"{period}.png"
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"Full-domain figure saved: "
        f"{output_path}"
    )

    return output_path

def plot_metric_reference(
    rows: list[dict],
    metric: str,
    reference: str,
    region_codes: tuple[str, ...],
    start_cycle: str,
    end_cycle: str,
    output_root: Path,
) -> Path:
    """
    Plot CTL and NEW lead series for one metric/reference across regions.
    """
    n_regions = len(region_codes)
    ncols = min(4, n_regions)
    nrows = math.ceil(n_regions / ncols)

    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=(4.3 * ncols, 3.7 * nrows),
        sharex=True,
        sharey=True,
        squeeze=False,
    )

    axes_flat = axes.ravel()

    # Determine one common y-axis for all subplots in the same figure.
    figure_values = [
        row["value_mm"]
        for row in rows
        if (
            row["metric"] == metric
            and row["reference"] == reference
            and row["region"] in region_codes
            and np.isfinite(row["value_mm"])
        )
    ]

    if not figure_values:
        raise RuntimeError(
            f"No values available for {metric}, {reference}."
        )

    ymax = max(figure_values)
    y_upper = ymax * 1.10 if ymax > 0.0 else 1.0

    line_styles = {
        "CTL": {
            "linestyle": "-",
            "marker": "o",
        },
        "NEW": {
            "linestyle": "--",
            "marker": "s",
        },
    }

    for idx, region_code in enumerate(region_codes):
        ax = axes_flat[idx]
        cfg = REGIONS[region_code]

        for experiment_label in ("CTL", "NEW"):
            series_rows = select_rows(
                rows=rows,
                metric=metric,
                reference=reference,
                experiment_label=experiment_label,
                region_code=region_code,
            )

            if not series_rows:
                continue

            x = [row["lead_h"] for row in series_rows]
            y = [row["value_mm"] for row in series_rows]

            ax.plot(
                x,
                y,
                linewidth=1.8,
                markersize=5.0,
                label=experiment_label,
                **line_styles[experiment_label],
            )

        ax.set_title(
            f"{region_code} — {cfg['name']}",
            fontsize=10,
        )
        ax.set_xticks(DEFAULT_LEADS)
        ax.set_ylim(0.0, y_upper)
        ax.grid(
            True,
            linewidth=0.4,
            alpha=0.4,
            linestyle=":",
        )

        if idx % ncols == 0:
            ax.set_ylabel(f"{metric} (mm)")

        if idx // ncols == nrows - 1:
            ax.set_xlabel("Forecast lead (h)")

    for idx in range(n_regions, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    handles, labels = axes_flat[0].get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 0.945),
    )

    fig.suptitle(
        f"Regional {metric} by forecast lead — "
        f"{REFERENCE_LABELS[reference]}\n"
        f"Initialization cycles: {start_cycle}–{end_cycle}",
        fontsize=14,
        y=0.995,
    )

    fig.tight_layout(
        rect=(0.0, 0.0, 1.0, 0.91),
    )

    period = f"{start_cycle}_{end_cycle}"

    output_dir = (
        output_root
        / period
        / "Regional_series"
        / metric
    )
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / (
        f"{metric}_{reference}_CTL_vs_NEW_"
        f"regional_series_{period}.png"
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    print(f"Figure saved: {output_path}")
    return output_path


# =============================================================================
# Command line
# =============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate regional MAE/RMSE directly from period-aggregated "
            "NetCDF fields and plot CTL-vs-NEW lead-time series."
        )
    )

    parser.add_argument(
        "--start-cycle",
        required=True,
        help="First forecast initialization cycle, YYYYMMDDHH.",
    )

    parser.add_argument(
        "--end-cycle",
        required=True,
        help="Last forecast initialization cycle, YYYYMMDDHH, inclusive.",
    )

    parser.add_argument(
        "--metrics",
        nargs="+",
        choices=DEFAULT_METRICS,
        default=DEFAULT_METRICS,
    )

    parser.add_argument(
        "--leads",
        nargs="+",
        type=int,
        default=DEFAULT_LEADS,
    )

    parser.add_argument(
        "--regions",
        nargs="+",
        choices=DEFAULT_REGIONS,
        default=DEFAULT_REGIONS,
        help=(
            "Regional boxes. Default uses all eight Gomes et al. (2022) "
            "sub-domains."
        ),
    )

    parser.add_argument(
        "--base-dir",
        default=str(Path(__file__).resolve().parent),
        help="analyses/precipitation directory.",
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Figure root. Default: "
            "output/period_comparison_figures"
        ),
    )

    parser.add_argument(
        "--summary-dir",
        default=None,
        help=(
            "Summary root. Default: "
            "output/period_comparison_summary"
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Stop at the first missing/inconsistent input file.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    start = parse_cycle(args.start_cycle)
    end = parse_cycle(args.end_cycle)

    if end < start:
        raise ValueError("end-cycle must be >= start-cycle.")

    base_dir = Path(args.base_dir).resolve()
    period = f"{args.start_cycle}_{args.end_cycle}"

    output_root = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else base_dir
        / "output"
        / "period_comparison_figures"
    )

    summary_root = (
        Path(args.summary_dir).resolve()
        if args.summary_dir
        else base_dir
        / "output"
        / "period_comparison_summary"
    )

    metrics = tuple(args.metrics)
    leads = tuple(args.leads)

    region_codes = tuple(args.regions)

    calculation_domains = (
        *region_codes,
        FULL_DOMAIN_CODE,
    )

    print("=" * 80)
    print("Regional continuous-metric lead series: CTL vs NEW")
    print(f"Period definition: forecast initialization cycles")
    print(f"Start cycle: {args.start_cycle}")
    print(f"End cycle:   {args.end_cycle}")
    print(f"Metrics: {metrics}")
    print(f"Leads: {leads}")
    print(f"Regions: {region_codes}")
    print(
        "Input source: aggregated NetCDF fields "
        "(summary CSVs are not used)"
    )
    print(
        "Spatial weighting: cos(latitude); "
        "RMSE = sqrt(weighted mean(mean_sqerr))"
    )
    print("=" * 80)

    rows = calculate_all_values(
        base_dir=base_dir,
        start_cycle=args.start_cycle,
        end_cycle=args.end_cycle,
        metrics=metrics,
        leads=leads,
        region_codes=calculation_domains,
        strict=args.strict,
    )

    csv_path = (
        summary_root
        / period
        / "continuous_metrics_regional_by_lead.csv"
    )

    write_csv(
        output_path=csv_path,
        rows=rows,
    )

    for metric in metrics:
        for reference in REFERENCES:
            plot_metric_reference(
                rows=rows,
                metric=metric,
                reference=reference,
                region_codes=region_codes,
                start_cycle=args.start_cycle,
                end_cycle=args.end_cycle,
                output_root=output_root,
            )

    for metric in metrics:
        plot_full_domain_metric(
            rows=rows,
            metric=metric,
            start_cycle=args.start_cycle,
            end_cycle=args.end_cycle,
            output_root=output_root,
        )

if __name__ == "__main__":
    main()
