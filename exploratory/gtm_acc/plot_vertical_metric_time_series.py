#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plot temporal evolution of vertical-structure verification metrics.

The script searches the MONAN-analysis output directories for summary CSV files
and creates one panel for each verification region. Each line represents a
forecast lead.

Examples of supported summary files:
    mean_bias_date_from_*_time_window_*_summary.csv
    mean_relative_error_date_from_*_time_window_*_summary.csv
    rmse_date_from_*_time_window_*_summary.csv
    anomaly_correlation_coefficient_date_from_*_time_window_*_summary.csv

"""

from __future__ import annotations

from pathlib import Path
import math
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


# Configuration
# Directory containing output_YYYYMMDDHH_to_YYYYMMDDHH directories.
BASE_DIR = Path("/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/results/gfs_202606_to_202607")

# Metric filename prefix.
# Options:
#   "mean_bias"
#   "mean_relative_error"
#   "rmse"
#   "anomaly_correlation_coefficient"
METRIC = "anomaly_correlation_coefficient"

# Variable name as stored in the CSV files.
# Common options:
#   "temperature"
#   "spechum"
#   "zgeo"
#   "uzonal"
#   "umeridional"
VARIABLE = "zgeo"

LEVEL_HPA = 500

# Forecast leads to plot. Use None to include all available leads.
TIME_WINDOWS = [120] #[24, 48, 72, 96, 120]

# Regions to plot. Use None to include all regions available in the CSV files.
REGIONS = [
    "global",
    "south_america",
    "central_america_and_caribbean",
    "northern_hemisphere_20_80",
    "southern_hemisphere_20_80",
    "tropics_20s_20n",
]

# Optional temporal filtering based on date_init.
# Use None to include all dates, or specify a date in "YYYYMMDDHH" format.
#DATE_INIT_MIN = "2025060100"
#DATE_INIT_MAX = "2026063000"
DATE_INIT_MIN = None
DATE_INIT_MAX = None

# Number of subplot columns.
N_COLUMNS = 2

# Set manually, for example (0.70, 1.00), or use None for automatic limits.
Y_LIMITS = (0.70, 1.02)

# Output settings.
OUTPUT_DIR = Path("figs_time_series")
OUTPUT_DPI = 300

# Labels
METRIC_LABELS = {
    "mean_bias": "Mean bias",
    "mean_relative_error": "Mean relative error",
    "rmse": "RMSE",
    "anomaly_correlation_coefficient": "Anomaly correlation coefficient",
}

METRIC_AXIS_LABELS = {
    "mean_bias": "Mean bias",
    "mean_relative_error": "Mean relative error",
    "rmse": "RMSE",
    "anomaly_correlation_coefficient": "ACC",
}

VARIABLE_LABELS = {
    "temperature": "Temperature",
    "spechum": "Specific humidity",
    "zgeo": "Geopotential height",
    "uzonal": "Zonal wind",
    "umeridional": "Meridional wind",
}

REGION_LABELS = {
    "global": "Global",
    "south_america": "South America",
    "central_america_and_caribbean": "Central America and Caribbean",
    "northern_hemisphere_20_80": "Northern Hemisphere, 20 to 80°",
    "southern_hemisphere_20_80": "Southern Hemisphere, 20 to 80°",
    "tropics_20s_20n": "Tropics, 20°S to 20°N",
}

# Data reading
REQUIRED_COLUMNS = {
    "summary_type",
    "date_init",
    "date_final",
    "time_window",
    "variable",
    "level_hpa",
    "region",
    "mean",
}


def find_summary_files() -> list[Path]:
    """Find summary CSV files for the selected metric."""
    pattern = (
        f"output_*/data/date_multiple_time_window_*/"
        f"{METRIC}_date_from_*_time_window_*_summary.csv"
    )
    files = sorted(BASE_DIR.glob(pattern))

    if not files:
        raise FileNotFoundError(
            "No CSV files were found with pattern:\n"
            f"  {BASE_DIR / pattern}"
        )

    return files


def read_summary_file(path: Path) -> pd.DataFrame:
    """Read and validate one summary CSV file."""
    df = pd.read_csv(path)

    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(
            f"File {path} does not contain required columns: "
            f"{sorted(missing)}"
        )

    df["source_file"] = str(path)
    return df


def load_data(files: list[Path]) -> pd.DataFrame:
    """Read, combine, filter and deduplicate the summary files."""
    frames = []

    for path in files:
        try:
            frames.append(read_summary_file(path))
        except Exception as error:
            print(f"Warning: skipping {path}: {error}", file=sys.stderr)

    if not frames:
        raise RuntimeError("No valid summary CSV file could be read.")

    data = pd.concat(frames, ignore_index=True)

    data = data.loc[
        (data["summary_type"] == "mean_period")
        & (data["variable"] == VARIABLE)
        & (data["level_hpa"] == LEVEL_HPA)
    ].copy()

    if TIME_WINDOWS is not None:
        data = data[data["time_window"].isin(TIME_WINDOWS)]

    if REGIONS is not None:
        data = data[data["region"].isin(REGIONS)]

    data["date_init_dt"] = pd.to_datetime(
        data["date_init"].astype(str),
        format="%Y%m%d%H",
        errors="coerce",
    )
    data["date_final_dt"] = pd.to_datetime(
        data["date_final"].astype(str),
        format="%Y%m%d%H",
        errors="coerce",
    )

    data = data.dropna(subset=["date_init_dt", "date_final_dt", "mean"])

    if DATE_INIT_MIN is not None:
        start = pd.to_datetime(DATE_INIT_MIN, format="%Y%m%d%H")
        data = data[data["date_init_dt"] >= start]

    if DATE_INIT_MAX is not None:
        end = pd.to_datetime(DATE_INIT_MAX, format="%Y%m%d%H")
        data = data[data["date_init_dt"] <= end]

    if data.empty:
        raise ValueError(
            "No rows remained after applying metric, variable, level, "
            "lead, region and date filters."
        )

    # Use the first day of each month as the x coordinate.
    data["period"] = data["date_init_dt"].dt.to_period("M").dt.to_timestamp()

    # Some output directories can contain both partial and complete summaries
    # for the same month. Keep the summary covering the longest interval.
    data["period_duration"] = data["date_final_dt"] - data["date_init_dt"]

    group_columns = [
        "period",
        "time_window",
        "variable",
        "level_hpa",
        "region",
    ]

    data = (
        data.sort_values("period_duration")
        .drop_duplicates(subset=group_columns, keep="last")
        .sort_values(["region", "time_window", "period"])
    )

    return data


# Plotting
def get_regions_to_plot(data: pd.DataFrame) -> list[str]:
    """Return regions in the requested order, excluding unavailable regions."""
    available = set(data["region"].unique())

    if REGIONS is None:
        return sorted(available)

    return [region for region in REGIONS if region in available]


def set_automatic_y_limits(ax: plt.Axes, values: pd.Series) -> None:
    """Set readable automatic limits with a small vertical margin."""
    value_min = values.min()
    value_max = values.max()

    if pd.isna(value_min) or pd.isna(value_max):
        return

    if value_min == value_max:
        margin = max(abs(value_min) * 0.05, 0.1)
    else:
        margin = (value_max - value_min) * 0.08

    lower = value_min - margin
    upper = value_max + margin

    if METRIC == "anomaly_correlation_coefficient":
        lower = max(-1.0, lower)
        upper = min(1.0, upper)

    ax.set_ylim(lower, upper)


def plot_time_series(data: pd.DataFrame) -> Path:
    """Create the multi-region time-series figure."""
    regions = get_regions_to_plot(data)

    if not regions:
        raise ValueError("None of the requested regions is available.")

    n_rows = math.ceil(len(regions) / N_COLUMNS)

    fig, axes = plt.subplots(
        nrows=n_rows,
        ncols=N_COLUMNS,
        figsize=(6.2 * N_COLUMNS, 3.7 * n_rows),
        sharex=True,
        sharey=Y_LIMITS is not None,
        squeeze=False,
    )

    axes_flat = axes.ravel()
    available_leads = sorted(data["time_window"].unique())

    for ax, region in zip(axes_flat, regions):
        region_data = data[data["region"] == region]

        for lead in available_leads:
            lead_data = region_data[region_data["time_window"] == lead]

            if lead_data.empty:
                continue

            ax.plot(
                lead_data["period"],
                lead_data["mean"],
                marker="o",
                linewidth=1.8,
                markersize=5,
                label=f"{lead} h",
            )

        ax.set_title(
            REGION_LABELS.get(region, region.replace("_", " ").title()),
            fontsize=11,
            loc="left",
        )
        ax.set_ylabel(METRIC_AXIS_LABELS.get(METRIC, METRIC))
        ax.grid(True, alpha=0.3)

        if Y_LIMITS is not None:
            ax.set_ylim(*Y_LIMITS)
        else:
            set_automatic_y_limits(ax, region_data["mean"])

        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))

    # Hide unused panels.
    for ax in axes_flat[len(regions):]:
        ax.set_visible(False)

    handles, labels = axes_flat[0].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles,
            labels,
            title="Forecast lead",
            loc="upper center",
            ncol=len(labels),
            bbox_to_anchor=(0.5, 0.955),
            frameon=False,
        )

    period_min = data["period"].min().strftime("%b %Y")
    period_max = data["period"].max().strftime("%b %Y")

    metric_label = METRIC_LABELS.get(
        METRIC,
        METRIC.replace("_", " ").title(),
    )
    variable_label = VARIABLE_LABELS.get(
        VARIABLE,
        VARIABLE.replace("_", " ").title(),
    )

    fig.suptitle(
        f"Monthly {metric_label.lower()} for {variable_label.lower()} "
        f"at {LEVEL_HPA} hPa\n"
        f"All regions, {period_min} to {period_max}",
        fontsize=15,
        y=0.995,
    )

    fig.tight_layout(rect=(0, 0, 1, 0.925))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_name = (
        f"{METRIC}_time_series_{VARIABLE}_{LEVEL_HPA}hPa_"
        f"all_regions_{data['period'].min():%Y%m}_"
        f"{data['period'].max():%Y%m}.png"
    )
    output_path = OUTPUT_DIR / output_name

    fig.savefig(output_path, dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close(fig)

    return output_path


def main() -> None:
    files = find_summary_files()
    print(f"Found {len(files)} files for metric: {METRIC}")

    data = load_data(files)

    print("Variables available in selected files:")
    print(", ".join(sorted(pd.concat(
        [pd.read_csv(path, usecols=["variable"]) for path in files],
        ignore_index=True,
    )["variable"].dropna().unique())))

    print("Regions included:")
    print(", ".join(get_regions_to_plot(data)))

    output_path = plot_time_series(data)
    print(f"Figure saved to: {output_path}")


if __name__ == "__main__":
    main()

