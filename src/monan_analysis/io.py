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

def get_MONAN_DIAG_filename(date_in_string_init, date_in_string_final,grid_spec,vertical_level_spec,domain_type,initial_condition_type):
    # Get grid string
    try:
        GRID_STRING = config.GRID_DICT[grid_spec]
    except:
        raise ValueError(f"Grid '{grid_spec}' is not recognized. Please choose a valid grid.")
   # Get domain type string
    try:
        DOMAIN_TYPE_STRING = config.DOMAIN_TYPE_DICT[domain_type]
    except:
        raise ValueError(f"Domain type '{domain_type}' is not recognized. Please choose a valid domain type: 'global' or 'regional'.")
    # Get initial condition type string
    try:
        INITIAL_CONDITION_TYPE_STRING = config.INITIAL_CONDITIONS_TYPE_DICT[initial_condition_type]
    except:
        raise ValueError(f"Initial condition type '{initial_condition_type}' is not recognized. Please choose a valid initial condition type: 'GFS' or 'ERA5'.")

    # Get vertical level string
    try:
        VERTICAL_LEVEL_STRING = config.VERTICAL_LEVEL_DICT[vertical_level_spec]
    except:
        raise ValueError(f"Vertical level configuration '{vertical_level_spec}' is not recognized. " 
                         + "Please choose a valid configuration.")
    
    # filename = (f"{config.PREFIX_MONAN_DIAG_STRING}_{date_in_string_init}_{date_in_string_final}.00.00."
    #             f"{GRID_STRING}{VERTICAL_LEVEL_STRING}.nc")
    filename = (f"{config.PREFIX_MONAN_SHORT}_{DOMAIN_TYPE_STRING}_POS_{INITIAL_CONDITION_TYPE_STRING}_{date_in_string_init}_{date_in_string_final}.00.00."
                f"{GRID_STRING}{VERTICAL_LEVEL_STRING}.nc")
    return filename

def get_MONAN_unstructured_filename(date_in_string_init, date_in_string_final,grid_spec,vertical_level_spec,domain_type,initial_condition_type):
    # Grid string is directly specified by the user for unstructured data to increase, so we don't need to look it up in a dictionary.
    GRID_STRING = grid_spec
    # Get domain type string
    try:
        DOMAIN_TYPE_STRING = config.DOMAIN_TYPE_DICT[domain_type]
    except:
        raise ValueError(f"Domain type '{domain_type}' is not recognized. Please choose a valid domain type: 'global' or 'regional'.")
    # Get initial condition type string
    try:
        INITIAL_CONDITION_TYPE_STRING = config.INITIAL_CONDITIONS_TYPE_DICT[initial_condition_type]
    except:
        raise ValueError(f"Initial condition type '{initial_condition_type}' is not recognized. Please choose a valid initial condition type: 'GFS' or 'ERA5'.")
    # Get vertical level string
    try:
        VERTICAL_LEVEL_STRING = config.VERTICAL_LEVEL_DICT[vertical_level_spec]
    except:
        raise ValueError(f"Vertical level configuration '{vertical_level_spec}' is not recognized. " 
                         + "Please choose a valid configuration.")
    
    filename = (f"{config.PREFIX_MONAN_SHORT}_{DOMAIN_TYPE_STRING}_MOD_{INITIAL_CONDITION_TYPE_STRING}_{date_in_string_init}_{date_in_string_final}.00.00."
                f"{GRID_STRING}{VERTICAL_LEVEL_STRING}.nc")
    return filename

def get_GFS_analysis_filename(date_in_string,stream_name="levels"):
    if stream_name not in ["levels", "surface"]:
        raise ValueError("Invalid data_type. Must be 'levels' or 'surface'.")
    filename = (f"{config.PREFIX_GFS_ANALYSIS_STRING}_{stream_name}_{date_in_string}.nc")
    return filename

def get_ERA5_reanalysis_filename(variable):
    filename = (f"{config.ERA5_TO_MONAN_VAR_DICT[variable]['era5_longname']}.nc")
    return filename

def get_CERES_dataset_filename(date_in_string, stream_name, edition):
    edition_name = config.CERES_EDITION_DICT[edition]
    ceres_key = f"{stream_name}_{edition_name}"
    filename = (f"{config.CERES_DATASET}-{stream_name}_{edition_name}_{config.CERES_CODE_DICT[ceres_key]}.{date_in_string}.hdf")
    return filename

def read_ds_monan(year,month,day,hour,time_window,grid_spec,
                  vertical_level_spec,base_dir,domain_type="G",initial_condition_type="GFS",verbose='n'):
    """ Read MONAN data and return them as an xarray Dataset."""
    if verbose == 'y':
        print ("Reading MONAN output data...")
    # Get file path for reading MONAN data
    ## Compute final prediction date in datetime and string formats
    date_final_in_datetime = utils.get_date_as_datetime(
        year, month, day, hour
        )
    date_final_in_string = utils.get_date_as_YYYYMMDDHH_str(
        year, month, day, hour
        )
    ## Compute initial date (final date - time window)
    date_init_in_datetime = utils.get_initial_date_from_final_date(
        date_final_in_datetime, time_window
        )
    date_init_in_string = date_init_in_datetime.strftime(config.DATE_FORMAT_STRING)
    ## Get MONAN output filename
    filename = get_MONAN_DIAG_filename(
        date_init_in_string,
        date_final_in_string,
        grid_spec=grid_spec,
        vertical_level_spec=vertical_level_spec,
        domain_type=domain_type,
        initial_condition_type=initial_condition_type,
        )
    ## Should receive complete path, the base_dir should be passed complete, as in the unstructured case, to allow for generalization
    ## Sometimes structured output will be under "Post" directory, sometimes directly under the "{initial_date_init_in_datetime}" directory,
    ## and other structures are possible
    filepath = f"{base_dir}/{filename}"
    if verbose == 'y':
        print(f"Taking data from file: {filepath}")
    # Read dataset using complete path'
    ds_monan = xr.open_dataset(filepath, engine="netcdf4")
    return ds_monan, filepath

def read_ds_monan_unstructured(date_in_string_init, date_in_string_final, grid_spec,
                  domain_type,vertical_level_spec,
                  base_dir,initial_condition_type="GFS",verbose='n'):
    """ Read MONAN data and return them as an xarray Dataset."""
    if verbose == 'y':
        print ("Reading MONAN output data...")
    # Get file path for reading MONAN data
    ## Get MONAN output filename
    filename = get_MONAN_unstructured_filename(
        date_in_string_init,
        date_in_string_final,
        grid_spec=grid_spec,
        domain_type=domain_type,
        initial_condition_type=initial_condition_type,
        vertical_level_spec=vertical_level_spec,
        initial_condition_type=initial_condition_type
        )
    ## Get complete path - won't assume that the base_dir has a subdirectory for each date, as in the structured case, since we can have test case names
    filepath = f"{base_dir}/{filename}"
    if verbose == 'y':
        print(f"Taking data from file: {filepath}")
    # Read dataset using complete path
    ds_monan = xr.open_dataset(filepath, engine="netcdf4")
    return ds_monan, filepath

def read_ds_gfs(year,month,day,hour,base_dir,stream_name="levels",
                verbose='n'):
    """ Read GFS data and return them as an xarray Dataset."""
    # Get file path for reading GFS data
    ## Compute date in string format
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
        year, month, day, hour
        )
    ## Get GFS output filename
    filename = get_GFS_analysis_filename(
        date_in_string,
        stream_name
        )
    ## Compute year and month only
    date_year_month_in_string = utils.get_date_as_YYYYMM_str(
        year, month
        )
    ## Should receive complete path, the base_dir should be passed complete, as in the structured case, to allow for generalization
    ## Sometimes structured output will be under "Model" directory, sometimes directly under the "{initial_date_init_in_datetime}" directory, 
    ## and other structures are possible
    filepath = f"{base_dir}/{filename}"
    if verbose == 'y':
        print(f"Reading GFS analysis data from file: {filepath}")
    # Read dataset using complete path
    ds_gfs = xr.open_dataset(filepath, engine="netcdf4")
    return ds_gfs, filepath

def read_ds_era5(year,month,base_dir,variable,stream_name="single_levels",
                verbose='n'):
    """ 
    Read ERA5 data downloaded in netcdf format and return them as an xarray Dataset.
    It assumes ERA5 data is downloaded as one month of data for a single variable, 
    and that the file is within directory <base_dir>/single_levels/<year>/<month>/<variable>.nc".
    """
    # Get file path for reading ERA5 data
    ## Get ERA5 output filename
    filename = get_ERA5_reanalysis_filename(variable)
    ## Get complete path
    filepath = f"{base_dir}/{stream_name}/{year}/{month}/{filename}"
    if verbose == 'y':
        print(f"Reading ERA5 analysis data from file: {filepath}")
    # Read dataset using complete path
    ds_era5 = xr.open_dataset(filepath, engine="netcdf4")

    return ds_era5, filepath


def read_ds_ceres(year,month,day,base_dir,edition,stream_name, variable,
                verbose='y'):
    """ 
    Read CERES data downloaded in netcdf format and return them as an xarray Dataset.
    It assumes CERES data is downloaded as one month of data, and that the file is
    within directory <base_dir>/<CERES_DATASET>/<stream_name>/<edition>/<filename>.
    """
    date_in_string = utils.get_date_as_YYYYMMDD_str(
        year, month, day
        )
    ceres_var_name = config.CERES_TO_MONAN_VAR_DICT[variable]['ceres_name']

    ## Get CERES output filename
    filename = get_CERES_dataset_filename(date_in_string, stream_name, edition)
    ## Get file path for reading CERES data
    filepath = f"{base_dir}/{config.CERES_DATASET}/{stream_name}/{config.CERES_EDITION_DICT[edition]}/{filename}"
    if verbose == 'y':
        print(f"Reading CERES analysis data from file: {filepath}")

    from pyhdf.SD import SD, SDC
    import numpy as np
    import pandas as pd

    sd = SD(str(filepath), SDC.READ)
    datasets_info = list(sd.datasets().keys())
    if ceres_var_name not in datasets_info:
        raise KeyError(f"{ceres_var_name} not found in {filepath}")

    var = sd.select(ceres_var_name)
    arr = np.asarray(var.get(), dtype=np.float64)
    attrs = var.attributes()

    for key in ["_FillValue", "fillvalue", "missing_value"]:
        if key in attrs:
            arr = np.where(arr == attrs[key], np.nan, arr)

    if arr.ndim == 3:
        nlon, nlat, nhour = arr.shape
        lon = np.linspace(-179.5, 179.5, nlon)
        lat = np.linspace(-89.5, 89.5, nlat)
        time = pd.date_range(
            start=pd.to_datetime(date_in_string, format="%Y%m%d"),
            periods=nhour,
            freq="1h",
        )
        ds_ceres = xr.DataArray(
            arr,
            dims=("longitude", "latitude", "time"),
            coords={"longitude": lon, "latitude": lat, "time": time},
        )

        ds_ceres= ds_ceres.transpose("time", "longitude", "latitude")
    elif arr.ndim == 4:
        nlon, nlat, nhour, nprofile = arr.shape
        lon = np.linspace(-179.5, 179.5, nlon)
        lat = np.linspace(-89.5, 89.5, nlat)
        time = pd.date_range(
            start=pd.to_datetime(date_in_string, format="%Y%m%d"),
            periods=nhour,
            freq="1h",
        )
        group_name = str(attrs.get("group", "")).lower()
        if "cloud" in group_name or "profile" in group_name or "layer" in group_name:
            profile_dim = "cloud_layer"
        else:
            profile_dim = "level"
        ds_ceres = xr.DataArray(
            arr,
            dims=("longitude", "latitude", "time", profile_dim),
            coords={
                "longitude": lon,
                "latitude": lat,
                "time": time,
                profile_dim: np.arange(1, nprofile + 1),
            },
        )
    else:
        ds_ceres = xr.DataArray(arr)

    ds_ceres = ds_ceres.to_dataset(name=ceres_var_name)

    return ds_ceres, filepath