#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
precipitation_analysis_period_plot_continuous.py

Compare period-aggregated continuous precipitation verification metrics
between experiments.

Layout
------
rows:    Exp 1, Exp 2
columns: GPM, GSMAP, MSWEP

Metrics
-------
Bias, MAE, RMSE

Methodological conventions
---------------------------
- The aggregation period is defined by forecast INITIALIZATION cycles.
- The same initialization cycles are used for every lead and both experiments.
- Global-only comparisons use DOMAIN; any REG experiment selects its regional
  bounding box automatically. Data are spatially cropped before statistics.
- REG comparisons approximately match the valid spatial footprint across
  native verification grids by nearest-neighbor *mask* transfer only. Metrics
  themselves are not remapped and original aggregated NetCDFs are unchanged.
- Bias and MAE panel values are cosine(latitude)-weighted spatial means.
- RMSE maps use the aggregated RMSE field stored in ``prec``.
- The scalar RMSE shown in each panel is:
      sqrt(weighted spatial mean(mean_sqerr))
  and is therefore not the spatial mean of the RMSE map.

Usage:  python precipitation_analysis_period_plot_continuous.py --start-cycle YYYYMMDDHH --end-cycle YYYYMMDDHH
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.ticker as mticker

from precipitation_analysis_config import DOMAINS_CONFIG as DOMAIN_CONFIG

REFERENCES = ("GPM", "GSMAP", "MSWEP")

EXPERIMENTS = {
    "P1_v1.4.4": {
        "label": "Global v1.4.4",
        "source_domain": "GLB",
    },
#    "P1_v1.4.4_Reg": {
#        "label": "Regional v1.4.4",
#        "source_domain": "REG",
#    },
    "P1_v2.0.0-rc": {
        "label": "Global v2.0.0-rc",
        "source_domain": "GLB",
    },
}

# Used when every experiment is global. If a regional is present, the smaller
# regional coverage is automatically selected instead of DOMAIN.
DOMAIN = "GLB"  # Options for global-only comparisons: GLB, AMS, ACC, REG

SOURCE_DOMAINS = {cfg["source_domain"] for cfg in EXPERIMENTS.values()}
if not SOURCE_DOMAINS.issubset({"GLB", "REG"}):
    raise ValueError(f"Unsupported experiment domains: {SOURCE_DOMAINS}")

COMPARISON_DOMAIN = "REG" if "REG" in SOURCE_DOMAINS else DOMAIN
DOMAIN_INFO = DOMAIN_CONFIG[COMPARISON_DOMAIN].copy()

# Do not alter DOMAIN_CONFIG['REG']['extent']: daily plots rely on None.
# When a REG experiment exists, the extent is read from its NetCDF grid.
# For global-only comparisons explicitly requesting DOMAIN='REG', add
# 'comparison_extent' to DOMAIN_CONFIG['REG'] in the config file.

DEFAULT_LEADS = [24, 48, 72, 96, 120, 144, 168, 192, 216, 240]

PRECIP_VAR_NAME = "prec"
MEAN_SQERR_VAR_NAME = "mean_sqerr"

base_rmse_cmap = plt.get_cmap("hot_r")
RMSE_CMAP = LinearSegmentedColormap.from_list(
    "hot_r_sem_preto",
    base_rmse_cmap(np.linspace(0.0, 0.9, 256)),
)

PLOT_CONFIG = {
    "Bias": {
        "vmin": -10.0,
        "vmax": 10.0,
        "cmap": "RdBu",
        "label": "Bias (mm)",
        "title": "Mean 24 h Precipitation Bias",
    },
    "MAE": {
        "vmin": 0.0,
        "vmax": 20.0,
        "cmap": "YlOrRd",
        "label": "MAE (mm)",
        "title": "Mean 24 h Precipitation MAE",
    },
    "RMSE": {
        "vmin": 0.0,
        "vmax": 50.0,
        "cmap": RMSE_CMAP,
        "label": "RMSE (mm)",
        "title": "24 h Precipitation RMSE",
    },
}


def parse_cycle(cycle: str) -> datetime:
    try:
        return datetime.strptime(cycle, "%Y%m%d%H")
    except ValueError as exc:
        raise ValueError(
            f"Invalid cycle '{cycle}'. Expected YYYYMMDDHH."
        ) from exc


def valid_period(start_cycle: str, end_cycle: str, lead: int) -> tuple[str, str]:
    start_valid = parse_cycle(start_cycle) + timedelta(hours=lead)
    end_valid = parse_cycle(end_cycle) + timedelta(hours=lead)

    return (
        start_valid.strftime("%Y%m%d%H"),
        end_valid.strftime("%Y%m%d%H"),
    )


def input_path(
    base_dir: Path,
    experiment: str,
    period: str,
    metric: str,
    reference: str,
    lead: int,
) -> Path:
    data_dir = (
        base_dir
        / "output"
        / experiment
        / "aggregated"
        / period
        / "data"
        / metric
    )

    source_domain = EXPERIMENTS[experiment]["source_domain"]

    if metric == "Bias":
        filename = f"bias_{reference}_{source_domain}_{period}_mean_{lead:03d}h.nc"
    elif metric == "MAE":
        filename = f"mae_{reference}_{source_domain}_{period}_mean_{lead:03d}h.nc"
    elif metric == "RMSE":
        filename = f"rmse_{reference}_{source_domain}_{period}_{lead:03d}h.nc"
    else:
        raise ValueError(f"Unsupported metric: {metric}")

    return data_dir / filename


def determine_comparison_extent(
    base_dir: Path,
    period: str,
    metric: str,
    lead: int,
) -> list[float] | None:
    """Select the plotted box without modifying the daily REG configuration.

    For REG experiments use the intersection of their actual grid bounding
    boxes. Global-only comparisons honor DOMAIN exactly.
    """
    if COMPARISON_DOMAIN != "REG":
        return DOMAIN_INFO["extent"]

    regional_experiments = [
        exp for exp, info in EXPERIMENTS.items()
        if info["source_domain"] == "REG"
    ]
    if not regional_experiments:
        extent = DOMAIN_INFO.get("comparison_extent")
        if extent is None:
            raise ValueError(
                "DOMAIN='REG' with only global experiments requires "
                "DOMAIN_CONFIG['REG']['comparison_extent']."
            )
        return list(extent)

    bounds = []
    for experiment in regional_experiments:
        path = next(
            (
                candidate for reference in REFERENCES
                if (candidate := input_path(
                    base_dir, experiment, period, metric, reference, lead
                )).exists()
            ),
            None,
        )
        if path is None:
            raise FileNotFoundError(
                f"No REG NetCDF for experiment={experiment}, metric={metric}, "
                f"period={period}, lead={lead}"
            )
        with xr.open_dataset(path) as ds:
            lat = np.asarray(ds["lat"].values, dtype="float64")
            lon = np.asarray(ds["lon"].values, dtype="float64")
        lon_plot = (lon + 180.0) % 360.0 - 180.0
        if not (np.isfinite(lat).all() and np.isfinite(lon_plot).all()):
            raise ValueError(f"Invalid geographic coordinates in {path}")
        if np.ptp(lon_plot) > 180.0:
            raise ValueError(
                f"REG grid crosses the plot longitude seam in {path}. "
                "A split-domain procedure is required."
            )
        bounds.append([
            float(lon_plot.min()), float(lon_plot.max()),
            float(lat.min()), float(lat.max()),
        ])

    extent = [
        max(b[0] for b in bounds), min(b[1] for b in bounds),
        max(b[2] for b in bounds), min(b[3] for b in bounds),
    ]
    # Optional tighter comparison extent, independent of daily-map 'extent'.
    requested = DOMAIN_INFO.get("comparison_extent")
    if requested is not None:
        extent = [
            max(extent[0], requested[0]),
            min(extent[1], requested[1]),
            max(extent[2], requested[2]),
            min(extent[3], requested[3]),
        ]
    if extent[0] >= extent[1] or extent[2] >= extent[3]:
        raise ValueError(
            f"REG grids/comparison_extent have no common box: {bounds}"
        )
    return extent


def subset_comparison_extent(
    da: xr.DataArray,
    extent: list[float] | None,
) -> xr.DataArray:
    """Crop to the plotted geographic extent, without interpolating data."""
    if extent is None:
        return da

    west, east, south, north = extent
    if float(da.lat[0]) > float(da.lat[-1]):
        da = da.sortby("lat")
    da = da.sel(lat=slice(south, north))

    # Coordinates already standardized as 0..360; handle a 0-degree crossing.
    west360, east360 = west % 360.0, east % 360.0
    if east - west >= 360.0:
        pass
    elif west360 <= east360:
        da = da.sel(lon=slice(west360, east360))
    else:
        da = da.where((da.lon >= west360) | (da.lon <= east360), drop=True)

    if da.sizes.get("lat", 0) == 0 or da.sizes.get("lon", 0) == 0:
        raise ValueError(f"Empty spatial subset for extent={extent}")
    return da


def mask_for_common_coverage(
    fields: dict[tuple[str, str], xr.DataArray],
    mean_sqerr_fields: dict[tuple[str, str], xr.DataArray],
    metric: str,
) -> tuple[dict, dict]:
    """Apply a reference-specific common valid footprint on native grids.

    Nearest-neighbor transfers ONLY the Boolean validity mask, never the
    metric field. This is approximate matching at different resolutions.
    All-global comparisons retain the previous per-field missing-value rule.
    """
    if "REG" not in SOURCE_DOMAINS:
        return fields, mean_sqerr_fields

    for reference in REFERENCES:
        keys = [
            (info["label"], reference) for info in EXPERIMENTS.values()
        ]
        validity = {}
        for key in keys:
            valid = np.isfinite(fields[key])
            if metric == "RMSE":
                valid = valid & np.isfinite(mean_sqerr_fields[key])
            validity[key] = valid

        # Calculate masks before changing any field, then apply them together.
        common_masks = {}
        for key in keys:
            target = fields[key]
            common = validity[key].copy()
            for other_key in keys:
                if key == other_key:
                    continue
                other = validity[other_key]
                if (
                    target.lat.equals(other.lat)
                    and target.lon.equals(other.lon)
                ):
                    matched = other
                else:
                    matched = other.astype("float32").interp(
                        lat=target.lat,
                        lon=target.lon,
                        method="nearest",
                        kwargs={"fill_value": 0.0},
                    ) > 0.5
                common = common & matched
            common_masks[key] = common

        for key in keys:
            fields[key] = fields[key].where(common_masks[key])
            if metric == "RMSE":
                mean_sqerr_fields[key] = mean_sqerr_fields[key].where(
                    common_masks[key]
                )
    return fields, mean_sqerr_fields


def standardize_lat_lon(da: xr.DataArray) -> xr.DataArray:
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
            f"Expected lat/lon coordinates. Available: {list(da.coords)}"
        )

    if da["lat"].ndim != 1 or da["lon"].ndim != 1:
        raise ValueError(
            "This plotting script expects a regular 1-D lat/lon grid."
        )

    if float(da["lon"].min()) < 0.0:
        da = (
            da.assign_coords(lon=(da["lon"] + 360.0) % 360.0)
            .sortby("lon")
        )

    return da


def latitude_weights(da: xr.DataArray) -> xr.DataArray:
    return xr.DataArray(
        np.cos(np.deg2rad(da["lat"])),
        coords={"lat": da["lat"]},
        dims=("lat",),
    )


def weighted_mean(da: xr.DataArray) -> float:
    weights = latitude_weights(da)
    value = da.weighted(weights).mean(
        dim=("lat", "lon"),
        skipna=True,
    )
    return float(value.item())


def load_metric(
    base_dir: Path,
    experiment: str,
    period: str,
    metric: str,
    reference: str,
    lead: int,
    extent: list[float] | None,
) -> tuple[xr.DataArray, xr.DataArray | None, Path]:
    """Load fields cropped to the plotted box; calculate means afterwards."""
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
        if PRECIP_VAR_NAME not in ds:
            raise KeyError(
                f"Variable '{PRECIP_VAR_NAME}' not found in {path}. "
                f"Available: {list(ds.data_vars)}"
            )

        field = subset_comparison_extent(
            standardize_lat_lon(ds[PRECIP_VAR_NAME]), extent
        ).load().astype("float64")

        mean_sqerr = None
        if metric == "RMSE":
            if MEAN_SQERR_VAR_NAME not in ds:
                raise KeyError(
                    f"RMSE file {path} does not contain "
                    f"'{MEAN_SQERR_VAR_NAME}'. "
                    "Cannot calculate spatial RMSE with the correct definition."
                )
            mean_sqerr = subset_comparison_extent(
                standardize_lat_lon(ds[MEAN_SQERR_VAR_NAME]), extent
            ).load().astype("float64")
            xr.align(field, mean_sqerr, join="exact", copy=False)

        if "n_valid_cases" in ds:
            n_valid = subset_comparison_extent(
                standardize_lat_lon(ds["n_valid_cases"]), extent
            ).load()
            xr.align(field, n_valid, join="exact", copy=False)
            field = field.where(n_valid > 0)
            if mean_sqerr is not None:
                mean_sqerr = mean_sqerr.where(n_valid > 0)

    return field, mean_sqerr, path


def validate_experiment_grids(
    fields: dict[tuple[str, str], xr.DataArray],
) -> None:
    """
    Validate grids within each experiment.
    Different experiments may use different grids.
    However, all observational references within the
    same experiment must share identical lat/lon
    coordinates.
    """
    experiment_grids = {}

    for (short_label, reference), field in fields.items():

        # Validate coordinates
        for coord in ("lat", "lon"):
            if coord not in field.coords:
                raise ValueError(
                    f"Missing {coord} coordinate in "
                    f"{short_label} x {reference}."
                )

            values = np.asarray(field[coord].values)

            if values.ndim != 1:
                raise ValueError(
                    f"{coord} must be one-dimensional in "
                    f"{short_label} x {reference}."
                )

            if not np.all(np.isfinite(values)):
                raise ValueError(
                    f"Non-finite {coord} coordinates in "
                    f"{short_label} x {reference}."
                )

            if len(np.unique(values)) != len(values):
                raise ValueError(
                    f"Duplicate {coord} coordinates in "
                    f"{short_label} x {reference}."
                )

        # First reference defines the experiment grid
        if short_label not in experiment_grids:
            experiment_grids[short_label] = (
                reference,
                field,
            )
            continue

        # Compare references within the same experiment
        first_reference, first_field = experiment_grids[
            short_label
        ]

        if not first_field["lat"].equals(field["lat"]):
            raise ValueError(
                f"Latitude grid mismatch in {short_label}: "
                f"{first_reference} vs {reference}."
            )

        if not first_field["lon"].equals(field["lon"]):
            raise ValueError(
                f"Longitude grid mismatch in {short_label}: "
                f"{first_reference} vs {reference}."
            )

    # Report experiment grids
    print("\nGrid validation:")

    for short_label, (reference, field) in experiment_grids.items():
        print(
            f"  {short_label}: "
            f"lat={field.sizes['lat']}, "
            f"lon={field.sizes['lon']} "
            f"(reference: {reference})"
        )

    print(
        "  Different grids between experiments "
        "are allowed for visualization."
    )


def configure_map_axis(
    ax,
    row: int,
    col: int,
) -> None:
    extent = DOMAIN_INFO["extent"]

    if extent is None:
        ax.set_global()
    else:
        ax.set_extent(extent, crs=ccrs.PlateCarree())

    ax.coastlines(resolution="110m", linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linewidth=0.4)

    gl = ax.gridlines(
        draw_labels=True,
        linewidth=0.3,
        color="gray",
        alpha=0.5,
        linestyle=":",
    )

    gl.top_labels = False
    gl.right_labels = False
    gl.bottom_labels = row == len(EXPERIMENTS) - 1
    gl.left_labels = col == 0
    gl.xlabel_style = {"size": 8}
    gl.ylabel_style = {"size": 8}
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER

    if DOMAIN_INFO["xticks"] is not None:
        gl.xlocator = mticker.FixedLocator(DOMAIN_INFO["xticks"])
    if DOMAIN_INFO["yticks"] is not None:
        gl.ylocator = mticker.FixedLocator(DOMAIN_INFO["yticks"])


def prepare_field_for_plot(field: xr.DataArray) -> tuple[xr.DataArray, np.ndarray]:
    lon = np.asarray(field["lon"].values, dtype=float)

    # Para mapas regionais com extent em -180..180,
    # converter a longitude apenas para visualização.
    if DOMAIN_INFO["extent"] is not None and np.nanmax(lon) > 180.0:
        lon_plot = ((lon + 180.0) % 360.0) - 180.0
        order = np.argsort(lon_plot)
        field_plot = field.isel(lon=order)
        lon_plot = lon_plot[order]
    else:
        field_plot = field
        lon_plot = lon

    return field_plot, lon_plot


def plot_period_metric(
    base_dir: Path,
    start_cycle: str,
    end_cycle: str,
    metric: str,
    lead: int,
    output_root: Path,
) -> Path:
    period = f"{start_cycle}_{end_cycle}"
    cfg = PLOT_CONFIG[metric]

    extent = determine_comparison_extent(base_dir, period, metric, lead)
    DOMAIN_INFO["extent"] = extent
    print(f"  Comparison domain: {COMPARISON_DOMAIN}, extent: {extent}")

    fields = {}
    mean_sqerr_fields = {}
    aggregates = {}
    paths = {}

    for experiment, exp_info in EXPERIMENTS.items():
        short_label = exp_info["label"]
        source_domain = exp_info["source_domain"]

        for reference in REFERENCES:
            field, mean_sqerr, path = load_metric(
                base_dir=base_dir,
                experiment=experiment,
                period=period,
                metric=metric,
                reference=reference,
                lead=lead,
                extent=extent,
            )

            key = (short_label, reference)
            fields[key] = field
            if mean_sqerr is not None:
                mean_sqerr_fields[key] = mean_sqerr
            paths[key] = path

    validate_experiment_grids(fields)
    fields, mean_sqerr_fields = mask_for_common_coverage(
        fields, mean_sqerr_fields, metric
    )

    for key, field in fields.items():
        if metric == "RMSE":
            mse_value = weighted_mean(mean_sqerr_fields[key])
            aggregates[key] = float(np.sqrt(max(mse_value, 0.0)))
        else:
            aggregates[key] = weighted_mean(field)

    fig, axes = plt.subplots(
        nrows=len(EXPERIMENTS),
        ncols=len(REFERENCES),
        figsize=(15.5, 4.25 * len(EXPERIMENTS)),
        squeeze=False,
        subplot_kw={"projection": ccrs.PlateCarree()},
        gridspec_kw={"hspace": 0.16, "wspace": 0.08},
    )

    last_image = None

    for row, (experiment, config) in enumerate(EXPERIMENTS.items()):
        short_label = config["label"]
        source_domain = config["source_domain"]
        for col, reference in enumerate(REFERENCES):
            ax = axes[row, col]
            key = (short_label, reference)
            field = fields[key]
            aggregate = aggregates[key]

            field_plot, lon_plot = prepare_field_for_plot(field)

            last_image = ax.pcolormesh(
                lon_plot,
                field_plot["lat"],
                field_plot,
                transform=ccrs.PlateCarree(),
                cmap=cfg["cmap"],
                vmin=cfg["vmin"],
                vmax=cfg["vmax"],
                shading="auto",
            )

            configure_map_axis(
                ax=ax,
                row=row,
                col=col,
            )

            ax.set_title(
                f"{short_label} × {reference}\n"
                f"{metric}: {aggregate:.2f} mm",
                fontsize=10,
                pad=4,
            )

            print(
                f"  {short_label:3s} x {reference:6s}: "
                f"{paths[key].name}"
            )

    cbar = fig.colorbar(
        last_image,
        ax=axes,
        orientation="vertical",
        shrink=0.88,
        pad=0.018,
    )
    cbar.set_label(cfg["label"], fontsize=11)
    cbar.ax.tick_params(labelsize=10)

    first_valid, last_valid = valid_period(
        start_cycle=start_cycle,
        end_cycle=end_cycle,
        lead=lead,
    )

    fig.suptitle(
        f"{cfg['title']} | F{lead:03d}\n"
        f"Initialization cycles: {start_cycle}–{end_cycle} | "
        f"valid times: {first_valid}–{last_valid}",
        fontsize=14,
        y=0.98,
    )

    output_dir = output_root / period / "Continuous" / metric
    output_dir.mkdir(parents=True, exist_ok=True)

    experiments_label = "_vs_".join(EXPERIMENTS.keys())
    output_file = output_dir / (
        f"{metric}_{experiments_label}_"
        f"{COMPARISON_DOMAIN}_{period}_p{lead:03d}h.png"
    )

    fig.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    print(f"  Figure saved: {output_file}")
    return output_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot period-aggregated Bias, MAE and RMSE "
            "for experiments."
        )
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
        "--metrics",
        nargs="+",
        choices=tuple(PLOT_CONFIG),
        default=("Bias", "MAE", "RMSE"),
    )

    parser.add_argument(
        "--leads",
        nargs="+",
        type=int,
        default=DEFAULT_LEADS,
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
            "Optional figure root. Default: "
            "output/period_comparison_figures"
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Stop on the first missing file or plotting error.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    parse_cycle(args.start_cycle)
    parse_cycle(args.end_cycle)

    if parse_cycle(args.end_cycle) < parse_cycle(args.start_cycle):
        raise ValueError("end-cycle must be >= start-cycle.")

    base_dir = Path(args.base_dir).resolve()

    output_root = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else base_dir / "output" / "period_comparison_figures"
    )

    print("=" * 80)
    print("Continuous precipitation comparison: Bias, MAE, RMSE")
    print(f"Base directory: {base_dir}")
    print(
        "Domain treatment: global-only uses DOMAIN; REG experiments "
        "select REG grid bounds. Data are cropped before spatial means."
    )
    print(
        "Spatial aggregation: cosine(latitude)-weighted mean; "
        "RMSE scalar = sqrt(weighted mean(mean_sqerr)). "
        "REG mode transfers validity masks by nearest neighbor between grids."
    )
    print("=" * 80)

    for metric in args.metrics:
        for lead in args.leads:
            print("=" * 78)
            print(
                f"Generating {metric} | "
                f"{args.start_cycle}_{args.end_cycle} | "
                f"F{lead:03d}"
            )

            try:
                plot_period_metric(
                    base_dir=base_dir,
                    start_cycle=args.start_cycle,
                    end_cycle=args.end_cycle,
                    metric=metric,
                    lead=lead,
                    output_root=output_root,
                )
            except Exception as exc:
                if args.strict:
                    raise
                print(f"  WARNING: figure not generated: {exc}")


if __name__ == "__main__":
    main()
