# -*- coding: utf-8 -*-
"""
vertical_analysis_aux.py

Based on a script by Andre Lyra (andre.lyra@inpe.br)
Last update: Feb 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)

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

import monan_analysis.config as config
import monan_analysis.io as io
import monan_analysis.utils as utils
import monan_analysis.config as config
import monan_analysis.preprocess as preprocess
import monan_analysis.stats as stats
import monan_analysis.plots as plots
import vertical_analysis_config as va_config
import os
import xarray as xr

def create_folder_structure():
    # Get date to include in output filenames
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    va_config.YEAR, va_config.MONTH, va_config.DAY, va_config.HOUR
    )
    os.makedirs(va_config.DIR_INPUT, exist_ok=True)
    os.makedirs(va_config.DIR_INPUT_RAW, exist_ok=True)
    os.makedirs(va_config.DIR_INPUT_INTERMEDIATE, exist_ok=True)
    os.makedirs(va_config.DIR_INPUT_PROCESSED, exist_ok=True)
    os.makedirs(va_config.DIR_OUTPUT, exist_ok=True)
    os.makedirs(va_config.DIR_OUTPUT_DATA, exist_ok=True)
    os.makedirs(va_config.DIR_OUTPUT_DATA+f"/{date_in_string}", exist_ok=True)
    os.makedirs(va_config.DIR_OUTPUT_FIGS, exist_ok=True)
    os.makedirs(va_config.DIR_OUTPUT_FIGS+f"/{date_in_string}", exist_ok=True)

def read_and_preprocess_monan_data():
    # Get date and write it into preprocessed filepath
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    va_config.YEAR, va_config.MONTH, va_config.DAY, va_config.HOUR
    )
    # Define verbosity
    if va_config.SEL_VERBOSE_LEVEL >= 2:
        verbose = 'y'
    else:
        verbose = 'n'
    # Read dataset
    ds_monan, monan_filepath = io.read_ds_monan(
        year=va_config.YEAR,
        month=va_config.MONTH,
        day=va_config.DAY,
        hour=va_config.HOUR,
        time_window=va_config.TIME_WINDOW,
        grid_spec=va_config.GRID_SPEC,
        vertical_level_spec=va_config.VERTICAL_LEVEL_SPEC,
        base_dir=va_config.DIR_MONAN_PREOP,
        verbose=verbose
        )
    # Select only data to be used for analysis
    ds_monan_selected = ds_monan[va_config.VARIABLES_TO_ANALYZE].sel(level=va_config.VERTICAL_LEVELS_TO_ANALYZE)
    # Save preprocessed MONAN dataset
    ds_monan_selected_filepath = f"{va_config.DIR_INPUT_INTERMEDIATE}/monan_selected_variables_and_levels_{date_in_string}.nc"
    ds_monan_selected.to_netcdf(ds_monan_selected_filepath)
    # If needed, print preprocessed dataset
    if va_config.SEL_VERBOSE_LEVEL >= 1:
        print ("MONAN dataset with selected variables and levels:")
        print (ds_monan_selected)

    return ds_monan_selected_filepath

def read_and_preprocess_gfs_data():
    # Get date and write it into preprocessed filepath
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    va_config.YEAR, va_config.MONTH, va_config.DAY, va_config.HOUR
    )
    # Define verbosity
    if va_config.SEL_VERBOSE_LEVEL >= 2:
        verbose = 'y'
    else:
        verbose = 'n'
    # Read dataset
    ds_gfs, gfs_filepath = io.read_ds_gfs(
        year=va_config.YEAR,
        month=va_config.MONTH,
        day=va_config.DAY,
        hour=va_config.HOUR,
        base_dir=va_config.DIR_GFS_ANALYSIS,
        stream_name=va_config.GFS_STREAM_NAME,
        verbose=verbose
        )
    # Configure GFS dataset to match MONAN format
    ds_gfs_in_monan_format = preprocess.get_gfs_data_in_monan_format(
        ds_gfs, config.GFS_TO_MONAN_VAR_DICT)
    # Select only data to be used for analysis
    ds_gfs_in_monan_format = ds_gfs_in_monan_format[va_config.VARIABLES_TO_ANALYZE].sel(
        level=va_config.VERTICAL_LEVELS_TO_ANALYZE)
    # Save preprocessed GFS dataset
    ds_gfs_in_monan_format_filepath = f"{va_config.DIR_INPUT_INTERMEDIATE}/gfs_in_monan_format_{date_in_string}.nc"
    ds_gfs_in_monan_format.to_netcdf(ds_gfs_in_monan_format_filepath)
    # If needed, print preprocessed dataset
    if va_config.SEL_VERBOSE_LEVEL >= 1:
        print ("GFS dataset in MONAN data format:")
        print (ds_gfs_in_monan_format)
    
    return ds_gfs_in_monan_format_filepath

def map_monan_to_gfs_grid(ds_monan_selected_filepath, ds_gfs_in_monan_format_filepath):
    # Get date and write it into preprocessed filepath
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    va_config.YEAR, va_config.MONTH, va_config.DAY, va_config.HOUR
    )
    ds_monan_mapped_to_gfs_filepath = f"{va_config.DIR_INPUT_PROCESSED}/monan_mapped_to_gfs_{date_in_string}.nc"
    # Map MONAN data to GFS grid
    preprocess.map_data_to_different_grid_with_cdo(
        ref_nc=ds_gfs_in_monan_format_filepath,
        input_nc=ds_monan_selected_filepath, 
        output_nc=ds_monan_mapped_to_gfs_filepath
        )
    # Read mapped MONAN data
    ds_monan_mapped_to_gfs = xr.open_dataset(ds_monan_mapped_to_gfs_filepath, engine="netcdf4")
    if va_config.SEL_VERBOSE_LEVEL >= 1:
        print ("MONAN data mapped to GFS grid:")
        print (ds_monan_mapped_to_gfs)
    
    return ds_monan_mapped_to_gfs_filepath

def calculate_statistics(ds_ref_filepath, ds_prediction_filepath):
    # Get date to include in output filenames
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    va_config.YEAR, va_config.MONTH, va_config.DAY, va_config.HOUR
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
    if "bias" in va_config.STATS_METRICS_TO_ANALYZE:
        # Compute bias
        ds_bias = stats.bias(observations=ds_ref, predictions=ds_prediction)
        # Save bias dataset in nc file
        bias_filepath = f"{va_config.DIR_OUTPUT_DATA}/{date_in_string}/bias_{date_in_string}.nc"
        ds_bias.to_netcdf(bias_filepath)
        ds_stats_filepath_dict["bias"]=bias_filepath
    if "absolute_error" in va_config.STATS_METRICS_TO_ANALYZE:
        # Compute absolute error
        ds_absolute_error = stats.absolute_error(observations=ds_ref, predictions=ds_prediction)
        # Save absolute error dataset in nc file
        absolute_error_filepath = f"{va_config.DIR_OUTPUT_DATA}/{date_in_string}/absolute_error_{date_in_string}.nc"
        ds_absolute_error.to_netcdf(absolute_error_filepath)
        ds_stats_filepath_dict["absolute_error"]=absolute_error_filepath

    return ds_stats_filepath_dict

def plot_statistics(ds_stats_filepath_dict):
    # Get date to include in output filenames
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    va_config.YEAR, va_config.MONTH, va_config.DAY, va_config.HOUR
    )
    # Maps of statistics for each metric, domain, variable and level
    for metric in ds_stats_filepath_dict.keys():
        print (f"Metric: {metric}")
        ds_stats = xr.open_dataset(ds_stats_filepath_dict[metric], engine="netcdf4")
        for domain in va_config.DOMAINS_TO_ANALYZE:
            print ("domain:", domain)
            for var in va_config.VARIABLES_TO_ANALYZE:
                print ("variable:", var)
                for level in va_config.VERTICAL_LEVELS_TO_ANALYZE:
                    print ("level:", level)
                    plots.plot_var_map(
                        ds=ds_stats, 
                        var=var, 
                        cartopy_data_dir=va_config.DIR_CARTOPY_DATA,
                        level=level, 
                        domain=domain,
                        output_filepath=f"{va_config.DIR_OUTPUT_FIGS}/{date_in_string}/metric_{metric}_var_{var}_level_{level}_domain_{domain}_date_{date_in_string}.png"
                        )