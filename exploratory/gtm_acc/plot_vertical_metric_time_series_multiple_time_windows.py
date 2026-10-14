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
import numpy as np


# Configuration
# Directory containing output_YYYYMMDDHH_to_YYYYMMDDHH directories.
BASE_DIR = Path("/lustre/projetos/monan_gam/Scripts/MONAN-analysis_clone_guilherme/analyses/vertical_structure")

# Models to include in the analysis.
MODELS = ["bam", "monan", "gfs"]

# Metric filename prefix.
# Options:
#   "mean_bias"
#   "mean_relative_error"
#   "rmse"
#   "anomaly_correlation_coefficient"
METRIC = "anomaly_correlation_coefficient_standard"

# Variable name as stored in the CSV files.
# Common options:
#   "temperature"
#   "spechum"
#   "zgeo"
#   "uzonal"
#   "umeridional"
VARIABLE = "zgeo"

# Vertical level in hPa as stored in the CSV files.
LEVEL_HPA = 500

# Forecast leads to plot. Use None to include all available leads.
TIME_WINDOWS = [24, 48, 72, 96, 120, 144, 168, 192, 216, 240]

# Regions to plot. Use None to include all regions available in the CSV files.
REGIONS = [
    "global",
    "northern_hemisphere_20_80",
    "southern_hemisphere_20_80",
]

# Optional temporal filtering based on date_init.
# Use None to include all dates, or specify a date in "YYYYMMDDHH" format.
#DATE_INIT_MIN = "2025060100"
#DATE_INIT_MAX = "2026063000"
DATE_INIT_MIN = 2025060100
DATE_INIT_MAX = 2026053100

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
    "northern_hemisphere_20_80": "Northern Hemisphere, 20° to 80°",
    "southern_hemisphere_20_80": "Southern Hemisphere, -20° to -80°",
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

def main() -> None:
    # Find summary files where metric values are written according to the configuration
    print (f"Searching for summary files in: {BASE_DIR}")
    files = find_summary_files()
    print(f"Found {len(files)} files for metric: {METRIC}")

    # Write files to a text file for reference
    with open("summary_files.txt", "w") as f:
        for file in files:
            f.write(str(file) + "\n")
    
    # Load and process the data from the summary files
    print ("Loading and processing data from summary files...")
    data = load_data(files)

    # Select only those columns relevant for the calculation and plotting, and sort the data for easier inspection
    data = data[[
        'time_window',
        'mean',
        'period',
        'region',
        'metric',
        'variable',
        'level_hpa',
        'source_file'
        ]].sort_values(by=['source_file', 'period', 'time_window', 'region']).reset_index(drop=True)

    # Save data to .csv file
    output_csv_path = "data.csv"
    data.to_csv(output_csv_path, index=False)

    # Extract the model name from the source_file column
    data['model'] = data['source_file'].str.extract(r'output_10d_(\w+)/')[0]

    # Split the data by model
    print ("Splitting data by model and saving to separate CSV files...")
    for model in MODELS:
        model_data = data[data['model'] == model]
        model_data = model_data[['model', 'period', 'region', 'time_window', 'mean']].sort_values(by=['period', 'region', 'time_window'])
        model_data.to_csv(f'filtered_data_{model}.csv', index=False)

    # Check that the each filtered data file contains for each period from DATE_INIT_MIN to
    # DATE_INIT_MAX all region in REGIONS and all time_window in TIME_WINDOWS
    for model in MODELS:
        print (f"Checking data duplication and completeness for model: {model}")
        model_data = pd.read_csv(f'filtered_data_{model}.csv')
        check_data_duplication_and_completeness(model_data, model)

    # For each model, region, and time_window, compute annual means,
    # and plot annual mean ACC for each model (in same plot, different line), with time_window in x-axis, and ACC in y-axis
    for model in MODELS:
        print (f"Calculating annual means for model: {model}")
        model_data = pd.read_csv(f'filtered_data_{model}.csv')
        model_data['year'] = pd.to_datetime(model_data['period']).dt.year
        annual_means = (
            model_data.groupby(['model', 'region', 'time_window'])['mean']
            .mean()
            .reset_index()
        )
        annual_means.to_csv(f'annual_means_{model}.csv', index=False)

    # Plot annual mean ACC for each model, with time_window in x-axis
    for region in REGIONS:
        plt.figure(figsize=(10, 6))
        for model in MODELS:
            # Read annual means for a particular model
            annual_means = pd.read_csv(f'annual_means_{model}.csv')
            print (f"Plotting annual mean ACC for region: {region}, model: {model}")
            regional_annual_mean = annual_means[annual_means['region'] == region]    
            # Convert time_window from hours to days for x-axis
            regional_annual_mean['time_window'] = regional_annual_mean['time_window'] / 24
            plt.plot(regional_annual_mean['time_window'], regional_annual_mean['mean']*100, marker='o', label=model, linewidth=2)
        plt.xlabel('Forecast day', fontsize=12)
        plt.ylabel(f'ACC 500 hPa {VARIABLE_LABELS['zgeo']} [%]', fontsize=12)
        plt.title(f'Annual mean ACC - {REGION_LABELS[region]}', fontsize=14)
        plt.xticks(regional_annual_mean['time_window'])
        plt.grid(True, alpha=0.3)
        plt.legend(title='Model', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(f'annual_mean_ACC_{region}.png', dpi=300, bbox_inches='tight')


def check_data_duplication_and_completeness(data, model) -> None:
    """
    Check that for each period from DATE_INIT_MIN to DATE_INIT_MAX, all regions in REGIONS
    and all time_windows in TIME_WINDOWS are present in the data for each model.

    Parameters:
        data (pd.DataFrame): Input data containing columns:
            ['model', 'period', 'region', 'time_window', 'mean']
    """
    # Ensure the 'period' column in 'data' is in datetime64[ns] format
    data['period'] = pd.to_datetime(data['period'], format="%Y-%m-%d")

    # Ensure 'model' is list-like
    if not isinstance(model, (list, tuple, pd.Series, np.ndarray)):
        model = [model]

    # Check for duplicates in the data
    if data.duplicated().any():
        raise ValueError("Duplicate rows found in the input data. Please ensure the data contains unique rows.")
    else:
        print(f"No duplicate rows found in the input data for model: {model}.")

    # Create a complete set of expected combinations
    expected_periods = pd.date_range(
        start=pd.to_datetime(DATE_INIT_MIN, format="%Y%m%d%H"),
        end=pd.to_datetime(DATE_INIT_MAX, format="%Y%m%d%H"),
        freq='MS'
    )
    expected_combinations = pd.MultiIndex.from_product(
        [model, expected_periods, REGIONS, TIME_WINDOWS],
        names=['model', 'period', 'region', 'time_window']
    )

    # Create a DataFrame from the expected combinations
    expected_df = pd.DataFrame(index=expected_combinations).reset_index()

    # Merge with the actual data to find missing combinations
    merged_df = expected_df.merge(data, on=['model', 'period', 'region', 'time_window'], how='left', indicator=True)

    # Identify missing combinations
    missing_combinations = merged_df[merged_df['_merge'] == 'left_only']

    if not missing_combinations.empty:
        print("Missing combinations of model, period, region, and time_window:")
        print(missing_combinations[['model', 'period', 'region', 'time_window']])
        raise ValueError("Data is incomplete. Please check the missing combinations above.")
    else:
        print(f"All expected combinations are present for model: {model}.")


def find_summary_files() -> list[Path]:
    """Find summary CSV files for the selected metric."""
    pattern = (
        f"output_10d_*/data/date_multiple_time_window_*/"
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
        # Stop execution if any file cannot be read
        except Exception as e:
            raise RuntimeError(f"Error reading file {path}: {e}. Please check at least that file.") from e            

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

    # Create columns that define a unique group for each summary, to be used for deduplication.
    group_columns = [
        "source_file",
        "date_init_dt",
        "date_final_dt",
        "period",
        "time_window",
        "variable",
        "level_hpa",
        "region",
    ]
    
    # Deuplicate the data by keeping the row with the longest period_duration for each unique group.
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

if __name__ == "__main__":
    main()