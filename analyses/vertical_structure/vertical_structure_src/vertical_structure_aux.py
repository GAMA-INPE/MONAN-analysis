# -*- coding: utf-8 -*-
"""
vertical_analysis_aux.py

Based on a script by Andre Lyra (andre.lyra@inpe.br)
Last update: Feb 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last update: Apr 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)

Description
-----------
This module contains auxiliary functions to be used specifically in this analysis.

Usage
-----
- Import this module in scripts that are part of this specific analysis.
- Do not use this module for defining general-purpose functions.

Examples:
- from vertical_analysis_aux import setup_parser
or
- import vertical_analysis_aux as va_aux
  args = va_aux.setup_parser()

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot.    
"""

import monan_analysis
import monan_analysis.config as config
import monan_analysis.io as io
import monan_analysis.utils as utils
import monan_analysis.preprocess as preprocess
import monan_analysis.stats as stats
import monan_analysis.plots as plots
from . import vertical_structure_config as vs_config
import os
import xarray as xr
import subprocess

def create_folder_structure():
    # Get date to include in output filenames
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
    )
    os.makedirs(vs_config.DIR_INPUT, exist_ok=True)
    os.makedirs(vs_config.DIR_INPUT_RAW, exist_ok=True)
    os.makedirs(vs_config.DIR_INPUT_INTERMEDIATE, exist_ok=True)
    os.makedirs(vs_config.DIR_INPUT_PROCESSED, exist_ok=True)
    os.makedirs(vs_config.DIR_OUTPUT, exist_ok=True)
    os.makedirs(vs_config.DIR_OUTPUT_DATA, exist_ok=True)
    os.makedirs(vs_config.DIR_OUTPUT_DATA+f"/date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}", exist_ok=True)
    os.makedirs(vs_config.DIR_OUTPUT_FIGS, exist_ok=True)
    os.makedirs(vs_config.DIR_OUTPUT_FIGS+f"/date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}", exist_ok=True)

def read_and_preprocess_monan_data():
    # Get date and write it into preprocessed filepath
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
    )
    # Define verbosity
    if vs_config.SEL_VERBOSE_LEVEL >= 2:
        verbose = 'y'
    else:
        verbose = 'n'
    # Read dataset
    ds_monan, monan_filepath = io.read_ds_monan(
        year=vs_config.YEAR,
        month=vs_config.MONTH,
        day=vs_config.DAY,
        hour=vs_config.HOUR,
        time_window=vs_config.TIME_WINDOW,
        grid_spec=vs_config.GRID_SPEC,
        vertical_level_spec=vs_config.VERTICAL_LEVEL_SPEC,
        base_dir=vs_config.DIR_MONAN_PREOP,
        verbose=verbose
        )
    # Select only data to be used for analysis
    ds_monan_selected = ds_monan[vs_config.VARIABLES_TO_ANALYZE].sel(level=vs_config.VERTICAL_LEVELS_TO_ANALYZE)
    # Save preprocessed MONAN dataset
    ds_monan_selected_filepath = f"{vs_config.DIR_INPUT_INTERMEDIATE}/monan_selected_variables_and_levels_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
    ds_monan_selected.to_netcdf(ds_monan_selected_filepath)
    # If needed, print preprocessed dataset
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print ("MONAN dataset with selected variables and levels:")
        print (ds_monan_selected)

    return ds_monan_selected_filepath

def read_and_preprocess_gfs_data():
    # Get date and write it into preprocessed filepath
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
    )
    # Define verbosity
    if vs_config.SEL_VERBOSE_LEVEL >= 2:
        verbose = 'y'
    else:
        verbose = 'n'
    # Read dataset
    ds_gfs, gfs_filepath = io.read_ds_gfs(
        year=vs_config.YEAR,
        month=vs_config.MONTH,
        day=vs_config.DAY,
        hour=vs_config.HOUR,
        base_dir=vs_config.DIR_GFS_ANALYSIS,
        stream_name=vs_config.GFS_STREAM_NAME,
        verbose=verbose
        )
    # Configure GFS dataset to match MONAN format
    ds_gfs_in_monan_format = preprocess.get_gfs_data_in_monan_format(
        ds_gfs, config.GFS_TO_MONAN_VAR_DICT)
    # Select only data to be used for analysis
    ds_gfs_in_monan_format = ds_gfs_in_monan_format[vs_config.VARIABLES_TO_ANALYZE].sel(
        level=vs_config.VERTICAL_LEVELS_TO_ANALYZE)
    # Save preprocessed GFS dataset
    ds_gfs_in_monan_format_filepath = f"{vs_config.DIR_INPUT_INTERMEDIATE}/gfs_in_monan_format_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
    ds_gfs_in_monan_format.to_netcdf(ds_gfs_in_monan_format_filepath)
    # If needed, print preprocessed dataset
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print ("GFS dataset in MONAN data format:")
        print (ds_gfs_in_monan_format)
    
    return ds_gfs_in_monan_format_filepath

def map_monan_to_gfs_grid(ds_monan_selected_filepath, ds_gfs_in_monan_format_filepath):
    # Get date and write it into preprocessed filepath
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
    )
    ds_monan_mapped_to_gfs_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/monan_mapped_to_gfs_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
    # Map MONAN data to GFS grid
    preprocess.map_data_to_different_grid_with_cdo(
        ref_nc=ds_gfs_in_monan_format_filepath,
        input_nc=ds_monan_selected_filepath, 
        output_nc=ds_monan_mapped_to_gfs_filepath
        )
    # Read mapped MONAN data
    ds_monan_mapped_to_gfs = xr.open_dataset(ds_monan_mapped_to_gfs_filepath, engine="netcdf4")
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print ("MONAN data mapped to GFS grid:")
        print (ds_monan_mapped_to_gfs)
    
    return ds_monan_mapped_to_gfs_filepath

def calculate_statistics(ds_ref_filepath, ds_prediction_filepath):
    # Get date to include in output filenames
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
    )

    # Read datasets
    ## GFS reference data
    ds_ref = xr.open_dataset(ds_ref_filepath, engine="netcdf4")
    ## MONAN prediction mapped to GFS grid
    ds_prediction = xr.open_dataset(ds_prediction_filepath, engine="netcdf4")

    # Initialize list of output filepaths for statistics datasets
    ds_stats_filepath_dict = {}

    # Create a dataset for each metric.
    # Each dataset will contain all selected variables at all selected levels.
    # We will not care about the domain now: since variables are all in 
    # the same grid, we can compute each metric for 
    # the whole grid and then subset it for different domains.
    if "bias" in vs_config.STATS_METRICS_TO_ANALYZE:
        # Compute bias
        ds_bias = stats.bias(predictions=ds_prediction, observations=ds_ref)
        # Save bias dataset in nc file
        bias_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}/bias_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
        ds_bias.to_netcdf(bias_filepath)
        ds_stats_filepath_dict["bias"]=bias_filepath
    if "relative_error" in vs_config.STATS_METRICS_TO_ANALYZE:
        # Compute relative error
        ds_relative_error = stats.relative_error(predictions=ds_prediction, observations=ds_ref)
        # Save relative error dataset in nc file
        relative_error_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}/relative_error_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
        ds_relative_error.to_netcdf(relative_error_filepath)
        ds_stats_filepath_dict["relative_error"]=relative_error_filepath

    return ds_stats_filepath_dict

def plot_statistics(ds_stats_filepath_dict):
    # Get date to include in output filenames
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
    )
    # Maps of statistics for each metric, domain, variable and level
    for metric in ds_stats_filepath_dict.keys():
        print (f"Metric: {metric}")
        ds_stats = xr.open_dataset(ds_stats_filepath_dict[metric], engine="netcdf4")
        for domain in vs_config.DOMAINS_TO_ANALYZE:
            print ("domain:", domain)
            for var in vs_config.VARIABLES_TO_ANALYZE:
                print ("variable:", var)
                for level in vs_config.VERTICAL_LEVELS_TO_ANALYZE:
                    print ("level:", level)
                    plots.plot_var_map(
                        ds=ds_stats, 
                        var=var, 
                        cartopy_data_dir=vs_config.DIR_CARTOPY_DATA,
                        level=level, 
                        domain=domain,
                        output_filepath=f"{vs_config.DIR_OUTPUT_FIGS}/date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}/metric_{metric}_var_{var}_level_{level}_domain_{domain}_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.png"
                        )

def cp_config_files():
    # Get date to include in output filenames
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
    )
    # Analysis-specific config file
    ## Get absolute path to vertical_structure_src/, where vertical_structure_config.py is located
    vs_config_dir = os.path.dirname(os.path.abspath(__file__))
    ## Construct path to analysis-specific config file
    vs_config_file_path = os.path.join(vs_config_dir, "vertical_structure_config.py")
    ## Copy analysis-specifig config file
    subprocess.run(["cp", vs_config_file_path, vs_config.DIR_OUTPUT_DATA+f"/date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}"], check=True)
    # General config file
    ## Get absolute path to monan_analysis/, where config.py is located
    gen_config_package_dir = os.path.dirname(monan_analysis.__file__)
    ## Construct path to general config.py file
    gen_config_file_path = os.path.join(gen_config_package_dir, "config.py")
    ## Copy general config file
    subprocess.run(["cp", gen_config_file_path, vs_config.DIR_OUTPUT_DATA+f"/date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}"], check=True)

def update_config_file(config_file_path, date, time_window):
    """
    Updates YEAR, MONTH, DAY, HOUR, and TIME_WINDOW in the config file without changing the order.

    Args:
        config_file_path (str): Path to the vertical_structure_config.py file.
        date (str): Date string in the format "%Y%m%d%H".
        time_window (int): Time window value to be added.

    Returns:
        None
    """
    # Parse the date string
    YEAR = date[:4]
    MONTH = date[4:6]
    DAY = date[6:8]
    HOUR = date[8:10]

    # Read the current content of the config file
    with open(config_file_path, 'r') as file:
        lines = file.readlines()

    # Define the variables to update (ensure values are strings)
    variables = {
        "YEAR": f'"{YEAR}"',
        "MONTH": f'"{MONTH}"',
        "DAY": f'"{DAY}"',
        "HOUR": f'"{HOUR}"',
        "TIME_WINDOW": f'"{time_window}"'
    }

    # Update the lines in the file
    updated_lines = []
    existing_vars = set()
    for line in lines:
        updated = False
        for var, value in variables.items():
            if line.strip().startswith(f"{var} ="):
                updated_lines.append(f"{var} = {value}\n")
                existing_vars.add(var)
                updated = True
                break
        if not updated:
            updated_lines.append(line)

    # Add any missing variables at the end
    for var, value in variables.items():
        if var not in existing_vars:
            updated_lines.append(f"{var} = {value}\n")

    # Write the updated content back to the config file
    with open(config_file_path, 'w') as file:
        file.writelines(updated_lines)

def concatenate_datasets(date_list,time_window):
    # Create folder to save concatenated datasets
    os.makedirs(vs_config.DIR_OUTPUT_DATA+f"/date_multiple_time_window_{time_window}", exist_ok=True)
    # Get date to include in output filenames
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
    )
    # Construct filepaths for stats datasets to be concatenated
    for stat in vs_config.STATS_METRICS_TO_ANALYZE:
        stat_filepaths = []
        for date in date_list:
            date_in_string = utils.get_date_as_YYYYMMDDHH_str(
                year=date[:4], 
                month=date[4:6], 
                day=date[6:8], 
                hour=date[8:10]
            )
            stat_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_{date_in_string}_time_window_{time_window}/{stat}_date_{date_in_string}_time_window_{time_window}.nc"
            stat_filepaths.append(stat_filepath)
        # Concatenate stat datasets along "Time" dimension
        ds_stat_concat = xr.open_mfdataset(stat_filepaths, combine="nested", concat_dim="Time")
        # Save concatenated dataset in nc file
        stat_concat_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/{stat}_date_concat_from_{date_list[0]}_to_{date_list[-1]}_time_window_{time_window}.nc"
        ds_stat_concat.to_netcdf(stat_concat_filepath)

def calculate_mean_stats_across_dates(time_window):
    # Create folder to save mean stats metrics datasets
    os.makedirs(vs_config.DIR_OUTPUT_DATA+f"/date_multiple_time_window_{time_window}", exist_ok=True)
    # Construct filepaths for concatenated stats datasets
    for stat in vs_config.STATS_METRICS_TO_ANALYZE:
        stat_concat_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/{stat}_date_concat_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
        # Read concatenated dataset
        ds_stat_concat = xr.open_dataset(stat_concat_filepath, engine="netcdf4")
        # Calculate mean value of stat metric across all dates for each variable, level and domain
        ds_stat_mean = ds_stat_concat.mean(dim="Time")
        # Save dataset with mean values in nc file
        stat_mean_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/mean_{stat}_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
        ds_stat_mean.to_netcdf(stat_mean_filepath)

def plot_mean_stats_across_dates(time_window):
    # Create folder to save mean stats metrics plots
    os.makedirs(vs_config.DIR_OUTPUT_FIGS+f"/date_multiple_time_window_{time_window}", exist_ok=True)
    # Construct filepaths for mean stats metrics datasets
    for stat in vs_config.STATS_METRICS_TO_ANALYZE:
        stat_mean_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/mean_{stat}_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
        # Read dataset with mean values of stat metric across all dates for each variable, level and domain
        ds_stat_mean = xr.open_dataset(stat_mean_filepath, engine="netcdf4")
        # Plot maps of mean values of stat metric for each domain, variable and level
        for domain in vs_config.DOMAINS_TO_ANALYZE:
            print ("domain:", domain)
            for var in vs_config.VARIABLES_TO_ANALYZE:
                print ("variable:", var)
                for level in vs_config.VERTICAL_LEVELS_TO_ANALYZE:
                    print ("level:", level)
                    plots.plot_var_map(
                        ds=ds_stat_mean, 
                        var=var, 
                        cartopy_data_dir=vs_config.DIR_CARTOPY_DATA,
                        level=level, 
                        domain=domain,
                        output_filepath=f"{vs_config.DIR_OUTPUT_FIGS}/date_multiple_time_window_{time_window}/metric_mean_{stat}_var_{var}_level_{level}_domain_{domain}_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.png"
                        )