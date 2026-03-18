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
import vertical_analysis_config as va_config
import os
import xarray as xr

def create_folder_structure():
    os.makedirs("input", exist_ok=True)
    os.makedirs("input/raw", exist_ok=True)
    os.makedirs("input/intermediate", exist_ok=True)
    os.makedirs("input/processed", exist_ok=True)
    os.makedirs("output", exist_ok=True)

def read_and_preprocess_monan_data():
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
    # Save preprocessed GFS dataset
    ds_monan_selected_filepath = f"{va_config.DIR_INPUT_INTERMEDIATE}/monan_selected_variables_and_levels.nc"
    ds_monan_selected.to_netcdf(ds_monan_selected_filepath)
    # If needed, print preprocessed dataset
    if va_config.SEL_VERBOSE_LEVEL >= 1:
        print ("MONAN dataset with selected variables and levels:")
        print (ds_monan_selected)

    return ds_monan_selected_filepath

def read_and_preprocess_gfs_data():
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
    ds_gfs_in_monan_format_filepath = f"{va_config.DIR_INPUT_INTERMEDIATE}/gfs_in_monan_format.nc"
    ds_gfs_in_monan_format.to_netcdf(ds_gfs_in_monan_format_filepath)
    # If needed, print preprocessed dataset
    if va_config.SEL_VERBOSE_LEVEL >= 1:
        print ("GFS dataset in MONAN data format:")
        print (ds_gfs_in_monan_format)
    
    return ds_gfs_in_monan_format_filepath

def map_monan_to_gfs_grid(ds_monan_selected_filepath, ds_gfs_in_monan_format_filepath):
    # Get date and write it into preprocessed filepath
    date_init_in_string = utils.get_date_as_YYYYMMDDHH_str(
    va_config.YEAR, va_config.MONTH, va_config.DAY, va_config.HOUR
    )
    ds_monan_mapped_to_gfs_filepath = f"{va_config.DIR_INPUT_PROCESSED}/monan_mapped_to_gfs_{date_init_in_string}.nc"
    # Check if file already exists
    if os.path.exists(ds_monan_mapped_to_gfs_filepath):
        print ("Mapped file already exists. No mapping needed.")
    else:
        preprocess.map_data_to_different_grid_with_cdo(
            ref_nc=ds_gfs_in_monan_format_filepath,
            input_nc=ds_monan_selected_filepath, 
            output_nc=ds_monan_mapped_to_gfs_filepath,
            var_list=va_config.VARIABLES_TO_ANALYZE, 
            level_list=va_config.VERTICAL_LEVELS_TO_ANALYZE, 
            )
    # Read mapped MONAN data
    ds_monan_mapped_to_gfs = xr.open_dataset(ds_monan_mapped_to_gfs_filepath, engine="netcdf4")
    if va_config.SEL_VERBOSE_LEVEL >= 1:
        print ("MONAN data mapped to GFS grid:")
        print (ds_monan_mapped_to_gfs)