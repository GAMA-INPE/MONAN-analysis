#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
precipitation_analysis_period_plot_MAE_RMSE_series.py

Generate lead-time series of period-aggregated MAE and RMSE for the 
experiments, separately for South American sub-regions.

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

   Each figure contains the selected regional subplots and one line per experiment.

Usage
-----
python precipitation_analysis_period_plot_MAE_RMSE_series.py \
    --start-cycle YYYYMMDDHH --end-cycle YYYYMMDDHH 

Example
-------
python precipitation_analysis_period_plot_MAE_RMSE_series.py \
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

from precipitation_analysis_config import DOMAINS_CONFIG as DOMAIN_CONFIG

# =============================================================================
# Configuration
# =============================================================================

#EXPERIMENTS = (
#    ("MONAN_CTL_AMS_CAR", "CTL"),
#    ("MONAN_NEW_AMS_CAR", "NEW"),
#    ("MONAN_NEW2_AMS_CAR", "NEW2")    
#)

EXPERIMENTS = {
    "P1_v1.4.4": {
        "label": "Global v1.4.4",
        "source_domain": "GLB",
    },
    # "P1_v1.4.4_Reg": {
    #     "label": "Regional v1.4.4",
    #     "source_domain": "REG",
    # },
    "P1_v2.0.0-rc": {
        "label": "Global v2.0.0-rc",
        "source_domain": "GLB",
    },
}

DOMAIN = "GLB" # Options: "GLB", "AMS", "CAR", "REG"

SOURCE_DOMAINS = {
    config["source_domain"]
    for config in EXPERIMENTS.values()
}

COMPARISON_DOMAIN = (
    "REG" if "REG" in SOURCE_DOMAINS else DOMAIN
)

COMPARISON_NAME = "_vs_".join(EXPERIMENTS.keys())

REFERENCES = ("GPM", "GSMAP", "MSWEP")

REFERENCE_LABELS = {
    "GPM": "GPM IMERG",
    "GSMAP": "GSMaP",
    "MSWEP": "MSWEP",
}

DEFAULT_METRICS = ("MAE", "RMSE")
DEFAULT_LEADS = (24, 48, 72, 96, 120, 144, 168, 192, 216, 240)

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
FULL_DOMAIN_NAME = "Full " + COMPARISON_DOMAIN + " domain"
DEFAULT_REGIONS = tuple(REGIONS)
EXPERIMENT_LABELS = tuple(cfg["label"] for cfg in EXPERIMENTS.values())
EXPERIMENT_FILENAME_LABEL = COMPARISON_NAME
EXPERIMENT_TITLE_LABEL = " vs ".join(EXPERIMENT_LABELS)

if not EXPERIMENTS or not SOURCE_DOMAINS.issubset({"GLB", "REG"}):
    raise ValueError("At least one experiment and valid GLB/REG source domains required")
if COMPARISON_DOMAIN not in DOMAIN_CONFIG:
    raise ValueError(f"Unsupported comparison domain: {COMPARISON_DOMAIN}")


# Date helpers
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


# Paths
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
            f"mae_{reference}_{EXPERIMENTS[experiment]['source_domain']}_{period}_mean_{lead:03d}h.nc"
        )
    elif metric == "RMSE":
        filename = (
            f"rmse_{reference}_{EXPERIMENTS[experiment]['source_domain']}_{period}_{lead:03d}h.nc"
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

    This only crops the existing common grid. No mask or remapping is
    introduced.
    """
    if region_code == FULL_DOMAIN_CODE:
        return subset_analysis_domain(da)

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

def determine_comparison_extent(base_dir: Path, period: str, metric: str,
                                reference: str, lead: int):
    """Return [west, east, south, north] in -180..180 or None for global."""
    cfg = DOMAIN_CONFIG[COMPARISON_DOMAIN]
    if "REG" not in SOURCE_DOMAINS:
        if COMPARISON_DOMAIN == "GLB":
            return None
        if COMPARISON_DOMAIN == "REG":
            return list(cfg["comparison_extent"])
        sl = cfg["slice"]
        lon_min, lon_max = sorted((float(sl["lon"].start), float(sl["lon"].stop)))
        lat_min, lat_max = sorted((float(sl["lat"].start), float(sl["lat"].stop)))
        # longitude may be in 0..360; convert for spatial region inclusion
        return [((lon_min + 180) % 360) - 180,
                ((lon_max + 180) % 360) - 180, lat_min, lat_max]

    bounds = []
    for experiment, config in EXPERIMENTS.items():
        if config["source_domain"] != "REG":
            continue
        path = input_path(base_dir, experiment, period, metric, reference, lead)
        if not path.exists():
            raise FileNotFoundError(path)
        with xr.open_dataset(path) as ds:
            lat_name = "lat" if "lat" in ds.coords else "latitude"
            lon_name = "lon" if "lon" in ds.coords else "longitude"
            lat = np.asarray(ds[lat_name].values, dtype=float)
            lon = np.asarray(ds[lon_name].values, dtype=float)
        if lat.ndim != 1 or lon.ndim != 1 or not np.isfinite(lat).all() or not np.isfinite(lon).all():
            raise ValueError(f"Invalid 1-D REG coordinates: {path}")
        lon = (lon + 180) % 360 - 180
        if np.ptp(lon) > 180:
            raise ValueError(f"Regional longitude crosses -180/180 seam: {path}")
        bounds.append([lon.min(), lon.max(), lat.min(), lat.max()])

    extent = [max(x[0] for x in bounds), min(x[1] for x in bounds),
              max(x[2] for x in bounds), min(x[3] for x in bounds)]
    requested = cfg.get("comparison_extent")
    if requested is not None:
        extent = [max(extent[0], requested[0]), min(extent[1], requested[1]),
                  max(extent[2], requested[2]), min(extent[3], requested[3])]
    if extent[0] >= extent[1] or extent[2] >= extent[3]:
        raise ValueError(f"Empty geographic overlap for REG: {extent}")
    return list(map(float, extent))


def region_inside_extent(region_code: str, extent, tol=1e-6) -> bool:
    """Only accept fully contained rectangular regions, not partial crops."""
    if region_code == FULL_DOMAIN_CODE or extent is None:
        return True
    west, east, south, north = extent
    r = REGIONS[region_code]
    return (r["lon"][0] >= west - tol and r["lon"][1] <= east + tol
            and r["lat"][0] >= south - tol and r["lat"][1] <= north + tol)


def select_available_regions(region_codes, extent):
    included = tuple(code for code in region_codes if region_inside_extent(code, extent))
    excluded = tuple(code for code in region_codes if code not in included)
    if excluded:
        print(f"  Skipping regions not fully contained in comparison extent: {excluded}")
    return included


def crop_extent(da: xr.DataArray, extent):
    if extent is None:
        return da
    west, east, south, north = extent
    if float(da.lat[0]) > float(da.lat[-1]):
        da = da.sortby("lat")
    da = da.sel(lat=slice(south, north))
    w, e = west % 360, east % 360
    if east - west >= 360:
        pass
    elif w <= e:
        da = da.sel(lon=slice(w, e))
    else:
        da = da.where((da.lon >= w) | (da.lon <= e), drop=True)
    if not da.sizes.get("lat") or not da.sizes.get("lon"):
        raise ValueError(f"Empty geographic crop for {extent}")
    return da


def common_validity_masks(fields):
    """Transfer only Boolean masks by nearest neighbour, never actual metrics."""
    validity = {experiment: np.isfinite(field) for experiment, field in fields.items()}
    if "REG" not in SOURCE_DOMAINS:
        return validity
    masks = {}
    for experiment, target in validity.items():
        common = target.copy()
        for other_exp, other in validity.items():
            if experiment == other_exp:
                continue
            if target.lat.equals(other.lat) and target.lon.equals(other.lon):
                matched = other
            else:
                matched = (other.astype("float32").interp(
                    lat=target.lat, lon=target.lon, method="nearest",
                    kwargs={"fill_value": 0.0}) > 0.5)
            common = common & matched
        if not bool(common.any().item()):
            raise ValueError(f"No valid common cells for {experiment}")
        masks[experiment] = common
    return masks


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

def calculate_all_values(
    base_dir: Path, start_cycle: str, end_cycle: str,
    metrics: tuple[str, ...], leads: tuple[int, ...],
    region_codes: tuple[str, ...], strict: bool,
) -> tuple[list[dict], tuple[str, ...]]:
    """Open each experiment file once per metric/reference/lead and compare masks."""
    period = f"{start_cycle}_{end_cycle}"
    rows = []
    available_by_combo = []
    for metric in metrics:
        for reference in REFERENCES:
            for lead in leads:
                try:
                    extent = determine_comparison_extent(base_dir, period, metric, reference, lead)
                    available = select_available_regions(region_codes, extent)
                    available_by_combo.append(set(available))
                    fields, paths = {}, {}
                    for experiment in EXPERIMENTS:
                        path = input_path(base_dir, experiment, period, metric, reference, lead)
                        if not path.exists():
                            raise FileNotFoundError(path)
                        var_name = PRECIP_VAR_NAME if metric == "MAE" else MEAN_SQERR_VAR_NAME
                        with xr.open_dataset(path) as ds:
                            if var_name not in ds:
                                raise KeyError(f"Missing {var_name} in {path}")
                            field = crop_extent(standardize_lat_lon(ds[var_name]), extent)
                            field = field.load().astype("float64")
                            if "n_valid_cases" in ds:
                                n_valid = crop_extent(standardize_lat_lon(ds["n_valid_cases"]), extent).load()
                                xr.align(field, n_valid, join="exact", copy=False)
                                field = field.where(n_valid > 0)
                        fields[experiment] = field
                        paths[experiment] = path
                    masks = common_validity_masks(fields)
                    first_valid, last_valid = valid_period(start_cycle, end_cycle, lead)
                    for experiment, field in fields.items():
                        field = field.where(masks[experiment])
                        for region_code in (*available, FULL_DOMAIN_CODE):
                            region = field if region_code == FULL_DOMAIN_CODE else subset_region(field, region_code)
                            if not np.isfinite(region).any().item():
                                raise ValueError(f"No valid data: {experiment}, {region_code}")
                            value = weighted_mean(region)
                            if metric == "RMSE":
                                if value < -1e-10:
                                    raise ValueError(f"Negative mean squared error: {value}")
                                value = float(np.sqrt(max(value, 0.0)))
                            cfg = REGIONS.get(region_code)
                            exp_info = EXPERIMENTS[experiment]
                            rows.append({
                                "metric": metric,
                                "reference": reference,
                                "experiment": experiment,
                                "experiment_label": exp_info["label"],
                                "region": region_code,
                                "region_name": cfg["name"] if cfg else FULL_DOMAIN_NAME,
                                "lat_min": cfg["lat"][0] if cfg else None,
                                "lat_max": cfg["lat"][1] if cfg else None,
                                "lon_min": cfg["lon"][0] if cfg else None,
                                "lon_max": cfg["lon"][1] if cfg else None,
                                "lead_h": lead,
                                "start_cycle": start_cycle,
                                "end_cycle": end_cycle,
                                "first_valid_time": first_valid,
                                "last_valid_time": last_valid,
                                "value_mm": float(value),
                                "n_valid_gridpoints": int(np.isfinite(region).sum().item()),
                                "source_file": str(paths[experiment]),
                            })
                            print(f"{metric:4s} | {reference:5s} | {exp_info['label']} "
                                  f"| {region_code:4s} | F{lead:03d} | {value:.3f} mm")
                except Exception as exc:
                    if strict:
                        raise
                    print(f"WARNING: skipping {metric}, {reference}, F{lead:03d}: {exc}")
    # Only show regions available for every successfully evaluated combination.
    if available_by_combo:
        common_regions = set.intersection(*available_by_combo)
        selected = tuple(code for code in region_codes if code in common_regions)
    else:
        selected = ()
    if not rows:
        raise RuntimeError("No valid metrics calculated")
    return rows, selected


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


# Plotting
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

    line_styles = (
        {
            "linestyle": "-",
            "marker": "o",
        },
        {
            "linestyle": "--",
            "marker": "s",
        },
        {
            "linestyle": "-.",
            "marker": "^",
        },
        {
            "linestyle": ":",
            "marker": "D",
        },
    )

    for col, reference in enumerate(REFERENCES):

        ax = axes[col]

        for exp_index, experiment_label in enumerate(EXPERIMENT_LABELS):

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
                **line_styles[
                    exp_index % len(line_styles)
                ],
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
        ncol=len(EXPERIMENTS),
        frameon=False,
        bbox_to_anchor=(0.5, 0.92),
    )

    fig.suptitle(
        f"Full {COMPARISON_DOMAIN} domain {metric} by forecast lead | "
        f"{EXPERIMENT_TITLE_LABEL}\n"
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
        / COMPARISON_NAME
        / "Full_domain_series"
        / metric
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / (
        f"{metric}_{EXPERIMENT_FILENAME_LABEL}_"
        f"full_{COMPARISON_DOMAIN}_{period}.png"
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
    Plot forecast lead series for one metric/reference across regions for experiments.
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

    line_styles = (
        {
            "linestyle": "-",
            "marker": "o",
        },
        {
            "linestyle": "--",
            "marker": "s",
        },
        {
            "linestyle": "-.",
            "marker": "^",
        },
        {
            "linestyle": ":",
            "marker": "D",
        },
    )

    for idx, region_code in enumerate(region_codes):
        ax = axes_flat[idx]
        cfg = REGIONS[region_code]

        for exp_index, experiment_label in enumerate(EXPERIMENT_LABELS):
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
                **line_styles[exp_index % len(line_styles)],
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
        ncol=len(EXPERIMENTS),
        frameon=False,
        bbox_to_anchor=(0.5, 0.92),
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
        / COMPARISON_NAME
        / "Regional_series"
        / metric
    )
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / (
        f"{metric}_{reference}_{EXPERIMENT_FILENAME_LABEL}_"
        f"regional_series_{COMPARISON_DOMAIN}_{period}.png"
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
            "NetCDF fields and plot lead-time series for experiments."
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

    print("=" * 80)
    print("Regional continuous-metric lead series: " f"{EXPERIMENT_TITLE_LABEL}")
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

    rows, available_regions = calculate_all_values(
        base_dir=base_dir,
        start_cycle=args.start_cycle,
        end_cycle=args.end_cycle,
        metrics=metrics,
        leads=leads,
        region_codes=region_codes,
        strict=args.strict,
    )

    csv_path = (
        summary_root
        / period
        / COMPARISON_NAME
        / f"continuous_metrics_regional_by_lead_{COMPARISON_DOMAIN}.csv"
    )

    write_csv(
        output_path=csv_path,
        rows=rows,
    )

    for metric in metrics:
        for reference in REFERENCES:
            if not available_regions:
                print("WARNING: no fully contained regions for regional series")
                break
            plot_metric_reference(
                rows=rows,
                metric=metric,
                reference=reference,
                region_codes=available_regions,
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
