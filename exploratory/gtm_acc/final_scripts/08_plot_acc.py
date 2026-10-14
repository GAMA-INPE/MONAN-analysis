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

# Controls over processing steps
DO_PREPROCESSING = False
DO_CHECK_FIELDS = True
DO_PLOT_ACC_TIME_SERIES = True
DO_ANNUAL_MEAN_PLOT = True

# Directory containing output_YYYYMMDDHH_to_YYYYMMDDHH directories.
BASE_DIR = Path("/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/results")

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
    "northern_hemisphere_20_80",
    "southern_hemisphere_20_80",
]

# Optional temporal filtering based on date_init.
# Use None to include all dates, or specify a date in "YYYYMMDDHH" format.
#DATE_INIT_MIN = "2025060100"
#DATE_INIT_MAX = "2026063000"
DATE_MIN = 2025060100
DATE_MAX = 2026053100

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
    "time_window",
    "variable",
    "level_hpa",
    "region",
    "mean",
}

def main() -> None:
    if DO_PREPROCESSING:
        # Find summary files where metric values are written according to the configuration
        print (f"Searching for summary files in: {BASE_DIR}")
        files = find_summary_files()
        print(f"Found {len(files)} files for metric: {METRIC}")

        # Write files to a text file for reference
        with open("checks_08_plot_acc/01_list_of_all_found_csv_files.txt", "w") as f:
            for file in files:
                f.write(str(file) + "\n")
        
        # Load and process the data from the summary files
        print ("Loading and processing data from summary files...")
        data = load_data(files)

        # Select only those columns relevant for the calculation and plotting, and sort the data for easier inspection
        data = data[[
            'time_window',
            'date',
            'mean',
            'region',
            'metric',
            'variable',
            'level_hpa',
            'source_file'
            ]].sort_values(by=['source_file', 'date', 'time_window', 'region']).reset_index(drop=True)

        # Save data to .csv file
        output_csv_path = "checks_08_plot_acc/02_preprocessed_data_with_all_models.csv"
        data.to_csv(output_csv_path, index=False)

        # Extract the model name from the source_file column
        data['model'] = data['source_file'].str.extract(r'output_10d_(\w+)/')[0]

        # Split the data by model
        print ("Splitting data by model and saving to separate CSV files...")
        for model in MODELS:
            model_data = data[data['model'] == model]
            model_data = model_data[['model', 'date', 'region', 'time_window', 'mean']].sort_values(by=['date', 'region', 'time_window'])
            model_data.to_csv(f'checks_08_plot_acc/03_filtered_data_{model}.csv', index=False)

    if DO_CHECK_FIELDS:
        # Check that the each filtered data file contains for each period from DATE_INIT_MIN to
        # DATE_INIT_MAX all region in REGIONS and all time_window in TIME_WINDOWS
        for model in MODELS:
            print (f"Checking data duplication and completeness for model: {model}")
            model_data = pd.read_csv(f'checks_08_plot_acc/03_filtered_data_{model}.csv')
            check_data_duplication_and_completeness(model_data, model)
    
    if DO_PLOT_ACC_TIME_SERIES:
        plt.figure(figsize=(10, 6))
        for model in MODELS:
            print (f"Calculating 30-day running mean for model: {model}")
            input_file = f'checks_08_plot_acc/03_filtered_data_{model}.csv'
            output_file = f'checks_08_plot_acc/03_filtered_data_{model}_monthly_mean.csv'
            calculate_30d_running_mean(input_file, output_file)
            # Now, plot acc running mean
            print (f"Plotting ACC time series for model: {model}")
            # Read model data
            model_data = pd.read_csv(f'checks_08_plot_acc/03_filtered_data_{model}_30d_running_mean.csv')
            # Select only northern hemisphere and time_window = 120
            model_data = model_data[(model_data['region'] == 'northern_hemisphere_20_80') & (model_data['time_window'] == 120)]
            # The x-ticks should be only the 12 months to avoid too crowded plot
            xticks = model_data['date'].unique()[::30]  # Every 30 days
            # Plot
            plt.plot(model_data['date'], model_data['mean'], marker='o', label=f"{model}", linewidth=2)
        plt.xlabel('Date', fontsize=12)
        plt.title(f'ACC 500 hPa {VARIABLE_LABELS["zgeo"]}, NH (20\u00b0-80\u00b0 N), 5 days', fontsize=14)
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=12)
        plt.tight_layout()
        # Set monthly x-ticks
        plt.xticks(xticks, [pd.to_datetime(x).strftime('%Y-%m') for x in xticks], fontsize=14)
        plt.yticks(fontsize=14)
        plt.savefig(f'checks_08_plot_acc/04_acc_time_series_30d_running_mean.png', dpi=300, bbox_inches='tight')

        # Do the same now for monthly mean
        plt.figure(figsize=(10, 6))
        for model in MODELS:
            print (f"Calculating monthly mean for model: {model}")
            input_file = f'checks_08_plot_acc/03_filtered_data_{model}.csv'
            output_file = f'checks_08_plot_acc/03_filtered_data_{model}_monthly_mean.csv'
            calculate_monthly_mean(input_file, output_file)
            # Now, plot acc monthly mean
            print (f"Plotting ACC time series for model: {model}")
            # Read model data
            model_data = pd.read_csv(f'checks_08_plot_acc/03_filtered_data_{model}_monthly_mean.csv')
            # Select only northern hemisphere and time_window = 120
            model_data = model_data[(model_data['region'] == 'northern_hemisphere_20_80') & (model_data['time_window'] == 120)]
            # The x-ticks should be only the 12 months to avoid too crowded plot
            xticks = model_data['date'].unique()[::30]
            # Plot
            plt.plot(model_data['date'], model_data['mean'], marker='o', label=f"{model}", linewidth=2)
        plt.xlabel('Date', fontsize=12)
        plt.title(f'ACC 500 hPa {VARIABLE_LABELS["zgeo"]}, NH (20\u00b0-80\u00b0 N), 5 days', fontsize=14)
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=12)
        plt.tight_layout()
        # Set monthly x-ticks
        plt.xticks(xticks, [pd.to_datetime(x).strftime('%Y-%m') for x in xticks], fontsize=14)
        plt.yticks(fontsize=14)
        plt.savefig(f'checks_08_plot_acc/04_acc_time_series_monthly_mean.png', dpi=300, bbox_inches='tight')
        
    if DO_ANNUAL_MEAN_PLOT:
        # Calculate annual mean for each model, region, and time_window
        for model in MODELS:
            print (f"Calculating annual mean for model: {model}")
            input_file = f'checks_08_plot_acc/03_filtered_data_{model}.csv'
            output_file = f'checks_08_plot_acc/03_filtered_data_{model}_annual_mean.csv'
            calculate_annual_mean(input_file, output_file)

        # Plot annual mean ACC for each model, with time_window in x-axis
        # Set xticks to be exactly the 10 forecast days
        days = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        plt.figure(figsize=(10, 6))
        for model in MODELS:
            model_data = pd.read_csv(f'checks_08_plot_acc/03_filtered_data_{model}_annual_mean.csv')
            # Select only northern hemisphere
            model_data = model_data[model_data['region'] == 'northern_hemisphere_20_80']
            plt.plot(days, model_data['mean'], marker='o', label=f"{model}", linewidth=2)
        plt.xlabel('Forecast day', fontsize=14)
        plt.ylabel('ACC', fontsize=14)
        plt.title(f'Annual mean ACC 500 hPa {VARIABLE_LABELS["zgeo"]}, NH (20\u00b0-80\u00b0 N)', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=12)
        plt.tight_layout()
        plt.xticks(days, fontsize=14)
        plt.yticks(fontsize=14)
        plt.savefig(f'checks_08_plot_acc/05_acc_annual_mean_NH.png', dpi=300, bbox_inches='tight')

        # Now for southern hemisphere
        plt.figure(figsize=(10, 6))
        for model in MODELS:
            model_data = pd.read_csv(f'checks_08_plot_acc/03_filtered_data_{model}_annual_mean.csv')
            # Select only southern hemisphere
            model_data = model_data[model_data['region'] == 'southern_hemisphere_20_80']
            plt.plot(days, model_data['mean'], marker='o', label=f"{model}", linewidth=2)
        plt.xlabel('Forecast day', fontsize=14)
        plt.ylabel('ACC', fontsize=14)
        plt.title(f'Annual mean ACC 500 hPa {VARIABLE_LABELS["zgeo"]}, SH (20\u00b0-80\u00b0 S)', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=12)
        plt.tight_layout()
        plt.xticks(days, fontsize=14)
        plt.yticks(fontsize=14)
        plt.savefig(f'checks_08_plot_acc/05_acc_annual_mean_SH.png', dpi=300, bbox_inches='tight')

def calculate_annual_mean(input_file, output_file):
    """
    Reads a CSV file, calculates the annual mean for each group of
    'region' and 'time_window', and writes the result to a new CSV file.

    Parameters:
        input_file (str): Path to the input CSV file.
        output_file (str): Path to the output CSV file.
    """
    # Read the input file
    data = pd.read_csv(input_file)
    
    # Ensure 'date' is in datetime format
    data['date'] = pd.to_datetime(data['date'])

    # Problem here: we want the mean for the whole 365-day period, which encompasses two years.
    # Hence: assuming that the data contains the full period from 2025-06-01 to 2026-05-31, we 
    # can calculate the annual mean by taking the mean over all values for each region and time_window.
    annual_mean = data.groupby(['region', 'time_window'])['mean'].mean().reset_index()

    # Write the result to the output file
    annual_mean.to_csv(output_file, index=False)

def calculate_monthly_mean(input_file, output_file):
    """
    Reads a CSV file, calculates the monthly mean for each group of
    'region' and 'time_window', and writes the result to a new CSV file.

    Parameters:
        input_file (str): Path to the input CSV file.
        output_file (str): Path to the output CSV file.
    """
    # Read the input file
    data = pd.read_csv(input_file)
    
    # Ensure 'date' is in datetime format
    data['date'] = pd.to_datetime(data['date'])
    
    # Extract year and month for grouping
    data['year_month'] = data['date'].dt.to_period('M')
    
    # Group by 'region', 'time_window', and 'year_month', then calculate the mean
    monthly_mean = data.groupby(['region', 'time_window', 'year_month'])['mean'].mean().reset_index()
    
    # Convert 'year_month' back to a datetime object for easier handling
    monthly_mean['date'] = monthly_mean['year_month'].dt.to_timestamp()
    monthly_mean = monthly_mean.drop(columns=['year_month'])
    
    # Write the result to the output file
    monthly_mean.to_csv(output_file, index=False)

def calculate_30d_running_mean(input_file, output_file):
    """
    Reads a CSV file, calculates the 30-day running mean for each group of
    'region' and 'time_window', and writes the result to a new CSV file.
    The data is returned in the same order as the original dataset:
    ordered by 'model', 'date', 'region', and 'time_window'.

    Parameters:
        input_file (str): Path to the input CSV file.
        output_file (str): Path to the output CSV file.
    """
    # Read the input file
    data = pd.read_csv(input_file)
    
    # Ensure 'date' is in datetime format
    data['date'] = pd.to_datetime(data['date'])
    
    # Sort the data by 'model', 'date', 'region', and 'time_window'
    data = data.sort_values(by=['model', 'date', 'region', 'time_window'])
    
    # Group by 'region' and 'time_window', then calculate the 30-day rolling mean
    data['mean'] = data.groupby(['region', 'time_window'])['mean'].transform(
        lambda x: x.rolling(window=30, min_periods=1, center=True).mean()
    )
    
    # Write the result to the output file
    data.to_csv(output_file, index=False)

def check_data_duplication_and_completeness(data, model) -> None:
    """
    Check that for each period from DATE_INIT_MIN to DATE_INIT_MAX, all regions in REGIONS
    and all time_windows in TIME_WINDOWS are present in the data for each model.

    Parameters:
        data (pd.DataFrame): Input data containing columns:
            ['model', 'period', 'region', 'time_window', 'mean']
    """
    # Ensure the 'date' column in 'data' is in datetime64[ns] format
    data['date'] = pd.to_datetime(data['date'], format="%Y-%m-%d")

    # Ensure 'model' is list-like
    if not isinstance(model, (list, tuple, pd.Series, np.ndarray)):
        model = [model]

    # Check for duplicates in the data
    if data.duplicated().any():
        raise ValueError("Duplicate rows found in the input data. Please ensure the data contains unique rows.")
    else:
        print(f"No duplicate rows found in the input data for model: {model}.")

    # Create a complete set of expected combinations with daily frequency
    expected_periods = pd.date_range(
        start=pd.to_datetime(DATE_MIN, format="%Y%m%d%H"),
        end=pd.to_datetime(DATE_MAX, format="%Y%m%d%H"),
        freq='D'
    )
    expected_combinations = pd.MultiIndex.from_product(
        [model, expected_periods, REGIONS, TIME_WINDOWS],
        names=['model', 'date', 'region', 'time_window']
    )

    # Create a DataFrame from the expected combinations
    expected_df = pd.DataFrame(index=expected_combinations).reset_index()

    # Merge with the actual data to find missing combinations
    merged_df = expected_df.merge(data, on=['model', 'date', 'region', 'time_window'], how='left', indicator=True)

    # Identify missing combinations
    missing_combinations = merged_df[merged_df['_merge'] == 'left_only']

    if not missing_combinations.empty:
        print("Missing combinations of model, date, region, and time_window:")
        print(missing_combinations[['model', 'date', 'region', 'time_window']])
        raise ValueError("Data is incomplete. Please check the missing combinations above.")
    else:
        print(f"All expected combinations are present for model: {model}.")


def find_summary_files() -> list[Path]:
    """Find summary CSV files for the selected metric."""
    pattern = (
        f"output_10d_*/data/date_*_time_window_*/"
        f"{METRIC}_date_*_time_window_*.csv"
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
    """Read, combine, filter the summary files."""
    frames = []

    # Check if the list of files is empty
    for path in files:
        try:
            frames.append(read_summary_file(path))
        # Stop execution if any file cannot be read
        except Exception as e:
            raise RuntimeError(f"Error reading file {path}: {e}. Please check at least that file.") from e            
    # Check if any valid frames were read
    if not frames:
        raise RuntimeError("No valid summary CSV file could be read.")

    # Combine all dataframes into one
    data = pd.concat(frames, ignore_index=True)

    # Select only the rows that match the specified metric, variable, and level_hpa
    data = data.loc[
        (data["summary_type"] == "instantaneous")
        & (data["variable"] == VARIABLE)
        & (data["level_hpa"] == LEVEL_HPA)
    ].copy()

    # Filter by date_init if specified
    if TIME_WINDOWS is not None:
        data = data[data["time_window"].isin(TIME_WINDOWS)]

    # Filter by region if specified
    if REGIONS is not None:
        data = data[data["region"].isin(REGIONS)]

    # Transform date values to datetime objects for easier filtering and plotting
    data["date"] = pd.to_datetime(data["date"], format="%Y%m%d%H")

    # Filter by date if specified
    if DATE_MIN is not None:
        data = data[data["date"] >= pd.to_datetime(DATE_MIN, format="%Y%m%d%H")]
    if DATE_MAX is not None:
        data = data[data["date"] <= pd.to_datetime(DATE_MAX, format="%Y%m%d%H")]
    
    # Check if any rows remain after filtering
    if data.empty:
        raise ValueError(
            "No rows remained after applying metric, variable, level, "
            "lead, region and date filters."
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

    # Get regions for plotting
    regions = get_regions_to_plot(data)
    if not regions:
        raise ValueError("None of the requested regions is available.")

    # Determine the number of rows needed for the subplots
    n_rows = math.ceil(len(regions) / N_COLUMNS)

    # Create the subplots
    fig, axes = plt.subplots(
        nrows=n_rows,
        ncols=N_COLUMNS,
        figsize=(6.2 * N_COLUMNS, 3.7 * n_rows),
        sharex=True,
        sharey=Y_LIMITS is not None,
        squeeze=False,
    )

    # Flatten the axes array for easier iteration
    axes_flat = axes.ravel()
    available_leads = sorted(data["time_window"].unique())

    # Plot each region in its respective subplot
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