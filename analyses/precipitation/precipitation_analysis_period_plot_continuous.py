#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
precipitation_analysis_period_plot_continuous.py

Compare period-aggregated continuous precipitation verification metrics
between MONAN CTL and MONAN NEW experiments.

Layout
------
rows:    CTL, NEW
columns: GPM, GSMAP, MSWEP

Metrics
-------
Bias, MAE, RMSE

Methodological conventions
---------------------------
- The aggregation period is defined by forecast INITIALIZATION cycles.
- The same initialization cycles are used for every lead and both experiments.
- No additional remapping, masking, or spatial cropping is performed here.
  The script plots the full common REG grid already used by the aggregated
  verification products.
- Bias and MAE panel values are cosine(latitude)-weighted spatial means.
- RMSE maps use the aggregated RMSE field stored in ``prec``.
- The scalar RMSE shown in each panel is:
      sqrt(weighted spatial mean(mean_sqerr))
  and is therefore not the spatial mean of the RMSE map.
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


REFERENCES = ("GPM", "GSMAP", "MSWEP")

EXPERIMENTS = (
    ("MONAN_CTL_AMS_CAR", "CTL"),
    ("MONAN_NEW_AMS_CAR", "NEW"),
)

DEFAULT_LEADS = (24, 48, 72, 96, 120)

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

    if metric == "Bias":
        filename = f"bias_{reference}_REG_{period}_mean_{lead:03d}h.nc"
    elif metric == "MAE":
        filename = f"mae_{reference}_REG_{period}_mean_{lead:03d}h.nc"
    elif metric == "RMSE":
        filename = f"rmse_{reference}_REG_{period}_{lead:03d}h.nc"
    else:
        raise ValueError(f"Unsupported metric: {metric}")

    return data_dir / filename


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
) -> tuple[xr.DataArray, float, Path]:
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

        field = standardize_lat_lon(
            ds[PRECIP_VAR_NAME].load()
        ).astype("float64")

        if metric == "RMSE":
            if MEAN_SQERR_VAR_NAME not in ds:
                raise KeyError(
                    f"RMSE file {path} does not contain "
                    f"'{MEAN_SQERR_VAR_NAME}'. "
                    "Cannot reproduce the Regional monthly aggregation "
                    "methodology without silently changing the RMSE definition."
                )

            mean_sqerr = standardize_lat_lon(
                ds[MEAN_SQERR_VAR_NAME].load()
            ).astype("float64")

            if not field["lat"].equals(mean_sqerr["lat"]):
                raise ValueError(f"Latitude mismatch inside {path}")

            if not field["lon"].equals(mean_sqerr["lon"]):
                raise ValueError(f"Longitude mismatch inside {path}")

            aggregate = float(
                np.sqrt(max(weighted_mean(mean_sqerr), 0.0))
            )
        else:
            aggregate = weighted_mean(field)

    return field, aggregate, path


def validate_experiment_grids(
    fields: dict[tuple[str, str], xr.DataArray],
) -> None:
    first_key = next(iter(fields))
    first = fields[first_key]

    for key, field in fields.items():
        if not first["lat"].equals(field["lat"]):
            raise ValueError(
                f"Latitude grid mismatch between {first_key} and {key}."
            )

        if not first["lon"].equals(field["lon"]):
            raise ValueError(
                f"Longitude grid mismatch between {first_key} and {key}."
            )


def configure_map_axis(
    ax,
    field: xr.DataArray,
    row: int,
    col: int,
) -> None:
    lon_min = float(field["lon"].min())
    lon_max = float(field["lon"].max())
    lat_min = float(field["lat"].min())
    lat_max = float(field["lat"].max())

    ax.set_extent(
        (lon_min, lon_max, lat_min, lat_max),
        crs=ccrs.PlateCarree(),
    )

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

    fields = {}
    aggregates = {}
    paths = {}

    for experiment, short_label in EXPERIMENTS:
        for reference in REFERENCES:
            field, aggregate, path = load_metric(
                base_dir=base_dir,
                experiment=experiment,
                period=period,
                metric=metric,
                reference=reference,
                lead=lead,
            )

            key = (short_label, reference)
            fields[key] = field
            aggregates[key] = aggregate
            paths[key] = path

    validate_experiment_grids(fields)

    fig, axes = plt.subplots(
        nrows=len(EXPERIMENTS),
        ncols=len(REFERENCES),
        figsize=(15.5, 8.5),
        subplot_kw={"projection": ccrs.PlateCarree()},
        gridspec_kw={"hspace": 0.16, "wspace": 0.08},
    )

    last_image = None

    for row, (_, short_label) in enumerate(EXPERIMENTS):
        for col, reference in enumerate(REFERENCES):
            ax = axes[row, col]
            key = (short_label, reference)
            field = fields[key]
            aggregate = aggregates[key]

            last_image = ax.pcolormesh(
                field["lon"],
                field["lat"],
                field,
                transform=ccrs.PlateCarree(),
                cmap=cfg["cmap"],
                vmin=cfg["vmin"],
                vmax=cfg["vmax"],
                shading="auto",
            )

            configure_map_axis(
                ax=ax,
                field=field,
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

    output_file = output_dir / (
        f"{metric}_CTL_vs_NEW_REG_{period}_p{lead:03d}h.png"
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
            "for MONAN CTL and NEW experiments."
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
    print("Continuous precipitation comparison: CTL vs NEW")
    print(f"Base directory: {base_dir}")
    print(
        "Domain treatment: full REG grid from the aggregated products; "
        "no additional crop or mask"
    )
    print(
        "Spatial aggregation: cosine(latitude)-weighted mean; "
        "RMSE scalar = sqrt(weighted mean(mean_sqerr))"
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