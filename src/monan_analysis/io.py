# -*- coding: utf-8 -*-
"""
io.py

Description
-----------
This module contains functions to be used for input and output operations.

Usage
-----
- Import this module in scripts that require input/output functions.
- Functions in this module should be general-purpose and reusable across different analyses.

Examples:
- from monan_analysis.io import get_MONAN_DIAG_filename
or 
- import monan_analysis.io as io
  filename = io.get_MONAN_DIAG_filename(date_in_string_init, date_in_string_final)

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot. 
"""

import monan_analysis.config as config
import monan_analysis.utils as utils
import xarray as xr

def example_function_io():
    print ("this is a function imported from the io.py module.")

def get_MONAN_DIAG_filename(date_in_string_init, date_in_string_final,grid_spec,vertical_level_spec):
    # Get grid string
    try:
        GRID_STRING = config.GRID_DICT[grid_spec]
    except:
        raise ValueError(f"Grid '{grid_spec}' is not recognized. Please choose a valid grid.")
    # Get vertical level string
    try:
        VERTICAL_LEVEL_STRING = config.VERTICAL_LEVEL_DICT[vertical_level_spec]
    except:
        raise ValueError(f"Vertical level configuration '{vertical_level_spec}' is not recognized. " 
                         + "Please choose a valid configuration.")
    
    filename = (f"{config.PREFIX_MONAN_DIAG_STRING}_{date_in_string_init}_{date_in_string_final}.00.00."
                f"{GRID_STRING}{VERTICAL_LEVEL_STRING}.nc")
    return filename

def get_GFS_analysis_filename(date_in_string,stream_name="levels"):
    if stream_name not in ["levels", "surface"]:
        raise ValueError("Invalid data_type. Must be 'levels' or 'surface'.")
    filename = (f"{config.PREFIX_GFS_ANALYSIS_STRING}_{stream_name}_{date_in_string}.nc")
    return filename

def get_GFS_filename(date_in_string,time_window,stream_name="levels"):
    if stream_name not in ["levels", "surface"]:
        raise ValueError("Invalid data_type. Must be 'levels' or 'surface'.")
    filename = (f"{config.PREFIX_GFS_STRING}{time_window}_{stream_name}_{date_in_string}.nc")
    return filename

def read_ds_monan(year,month,day,hour,time_window,grid_spec,
                  vertical_level_spec,base_dir,verbose='n'):
    """ Read MONAN data and return them as an xarray Dataset."""
    if verbose == 'y':
        print ("Reading MONAN output data...")
    # Get file path for reading MONAN data
    ## Compute final prediction date in datetime and string formats
    date_final_in_datetime = utils.get_date_as_datetime(
        year=year,
        month=month,
        day=day,
        hour=hour
        )
    date_final_in_string = utils.get_date_as_YYYYMMDDHH_str(
        year=year,
        month=month,
        day=day,
        hour=hour
        )
    ## Compute initial date (final date - time window)
    date_init_in_datetime = utils.get_initial_date_from_final_date(
        date_in_datetime=date_final_in_datetime,
        time_window=time_window
        )
    date_init_in_string = date_init_in_datetime.strftime(config.DATE_FORMAT_STRING)
    ## Get MONAN output filename
    filename = get_MONAN_DIAG_filename(
        date_in_string_init=date_init_in_string,
        date_in_string_final=date_final_in_string,
        grid_spec=grid_spec,
        vertical_level_spec=vertical_level_spec
        )
    ## Get complete path
    filepath = f"{base_dir}/{date_init_in_string}/{filename}"
    if verbose == 'y':
        print(f"Taking data from file: {filepath}")
    # Read dataset using complete path
    ds_monan = xr.open_dataset(filepath, engine="netcdf4")
    return ds_monan, filepath

def read_ds_gfs_analysis(year,month,day,hour,base_dir,stream_name="levels",
                verbose='n'):
    """ Read GFS analysis data and return them as an xarray Dataset."""
    # Get file path for reading GFS data
    ## Compute date in string format
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
        year=year, 
        month=month, 
        day=day, 
        hour=hour
        )
    ## Get GFS output filename
    filename = get_GFS_analysis_filename(
        date_in_string=date_in_string,
        stream_name=stream_name
        )
    ## Compute year and month only
    date_year_month_in_string = utils.get_date_as_YYYYMM_str(
        year=year,
        month=month
        )
    ## Get complete path
    filepath = f"{base_dir}/{date_year_month_in_string}/{filename}"
    if verbose == 'y':
        print(f"Reading GFS analysis data from file: {filepath}")
    # Read dataset using complete path
    ds_gfs = xr.open_dataset(filepath, engine="netcdf4")
    return ds_gfs, filepath

def read_ds_gfs(year,month,day,hour,time_window,base_dir,stream_name="levels",
                verbose='n'):
    """ Read GFS data and return them as an xarray Dataset."""
    if verbose == 'y':
        print ("Reading GFS output data...")
    # Get file path for reading GFS data
    ## Compute final prediction date in datetime and string formats
    date_final_in_datetime = utils.get_date_as_datetime(
        year=year,
        month=month,
        day=day,
        hour=hour
        )
    ## Compute initial date (final date - time window)
    date_init_in_datetime = utils.get_initial_date_from_final_date(
        date_in_datetime=date_final_in_datetime,
        time_window=time_window
        )    
    date_init_in_string = date_init_in_datetime.strftime(config.DATE_FORMAT_STRING)
    ## Get GFS output filename
    filename = get_GFS_filename(
        date_in_string=date_init_in_string,
        time_window=time_window,
        stream_name=stream_name,
        )
    ## Compute year and month from date_init_in_datetime
    date_year_month_in_string = utils.get_date_as_YYYYMM_str_from_datetime(
        date_in_datetime=date_init_in_datetime
        )
    ## Get complete path
    filepath = f"{base_dir}/{date_year_month_in_string}/{filename}"
    if verbose == 'y':
        print(f"Reading GFS forecast data from file: {filepath}")
    # Read dataset using complete path
    ds_gfs = xr.open_dataset(filepath, engine="netcdf4")
    return ds_gfs, filepath