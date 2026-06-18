# -*- coding: utf-8 -*-
"""
vertical_structure_aux.py

Based on a script by Andre Lyra (andre.lyra@inpe.br)
Last update: Feb 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last update: Apr 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last update: May 2026 by Andre Lyra (andre.lyra@inpe.br) - topography masking of pressure levels

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
from polars import var
from . import vertical_structure_config as vs_config
from . import vertical_structure_main as vs_main
import os
import xarray as xr
import pandas as pd
import numpy as np
import subprocess
import importlib

#===================================================================================================
# Functions for single run
#===================================================================================================
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
    for var in vs_config.VARIABLES_TO_ANALYZE:
        os.makedirs(vs_config.DIR_OUTPUT_FIGS+f"/date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}/var_{var}", exist_ok=True)
        for domain in vs_config.DOMAINS_TO_ANALYZE:
            os.makedirs(vs_config.DIR_OUTPUT_FIGS+f"/date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}/var_{var}/domain_{domain}", exist_ok=True)

def read_and_preprocess_monan_data():
    # Get date and write it into preprocessed filepath
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
        vs_config.YEAR,
        vs_config.MONTH,
        vs_config.DAY,
        vs_config.HOUR
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

    # Select pressure-level variables to be used for analysis
    ds_monan_selected = ds_monan[vs_config.VARIABLES_TO_ANALYZE].sel(
        level=vs_config.VERTICAL_LEVELS_TO_ANALYZE
    )

    # Include MONAN surface pressure in the same preprocessed dataset when
    # the pressure-level validity mask is enabled.
    if vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        ds_monan_selected["surface_pressure"] = ds_monan["surface_pressure"]

    # Save preprocessed MONAN dataset
    ds_monan_selected_filepath = (
        f"{vs_config.DIR_INPUT_INTERMEDIATE}/"
        f"monan_selected_variables_and_levels_date_{date_in_string}_"
        f"time_window_{vs_config.TIME_WINDOW}.nc"
    )
    ds_monan_selected.to_netcdf(ds_monan_selected_filepath)

    # If needed, print preprocessed dataset
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print("MONAN dataset with selected variables and levels:")
        print(ds_monan_selected)

    return ds_monan_selected_filepath

def read_and_preprocess_gfs_data():
    # Get date and write it into preprocessed filepath
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
        vs_config.YEAR,
        vs_config.MONTH,
        vs_config.DAY,
        vs_config.HOUR
    )

    # Define verbosity
    if vs_config.SEL_VERBOSE_LEVEL >= 2:
        verbose = 'y'
    else:
        verbose = 'n'

    # Read GFS pressure-level dataset
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
        ds_gfs,
        config.GFS_TO_MONAN_VAR_DICT
    )

    # Select pressure-level variables to be used for analysis
    ds_gfs_in_monan_format = ds_gfs_in_monan_format[
        vs_config.VARIABLES_TO_ANALYZE
    ].sel(
        level=vs_config.VERTICAL_LEVELS_TO_ANALYZE
    )

    # Include GFS surface pressure in the same preprocessed dataset when
    # the pressure-level validity mask is enabled.
    if vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        ds_gfs_sp, gfs_sp_filepath = io.read_ds_gfs(
            year=vs_config.YEAR,
            month=vs_config.MONTH,
            day=vs_config.DAY,
            hour=vs_config.HOUR,
            base_dir=vs_config.DIR_GFS_ANALYSIS,
            stream_name="surface",
            verbose=verbose
        )

        ds_gfs_sp = ds_gfs_sp[["sp"]]

        # Sort latitude to match the convention used for GFS pressure-level data
        ds_gfs_sp = ds_gfs_sp.sortby("latitude")

        # Rename dimensions and variable to match the preprocessed GFS dataset
        ds_gfs_sp = ds_gfs_sp.rename({
            "time": "Time",
            "sp": "surface_pressure"
        })

        ds_gfs_in_monan_format["surface_pressure"] = ds_gfs_sp["surface_pressure"]

    # Save preprocessed GFS dataset
    ds_gfs_in_monan_format_filepath = (
        f"{vs_config.DIR_INPUT_INTERMEDIATE}/"
        f"gfs_in_monan_format_date_{date_in_string}_"
        f"time_window_{vs_config.TIME_WINDOW}.nc"
    )
    ds_gfs_in_monan_format.to_netcdf(ds_gfs_in_monan_format_filepath)

    # If needed, print preprocessed dataset
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print("GFS dataset in MONAN data format:")
        print(ds_gfs_in_monan_format)

    return ds_gfs_in_monan_format_filepath

def interpolate_monan_gfs(ds_monan_selected_filepath, ds_gfs_in_monan_format_filepath):
    # Get date and write it into preprocessed filepath
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
    )
    if vs_config.INTERPOL_TYPE == 'monan_to_gfs':
        # Now, the mapped data is the prediction
        ds_prediction_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/monan_mapped_to_gfs_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
        # And the reference is the GFS data in MONAN format (before mapping)
        ds_ref_filepath = ds_gfs_in_monan_format_filepath
        # Map MONAN data to GFS grid
        preprocess.map_data_to_different_grid_with_cdo(
            ref_nc=ds_gfs_in_monan_format_filepath,
            input_nc=ds_monan_selected_filepath, 
            output_nc=ds_prediction_filepath
            )
        # Read interpolated data
        ds_interpolated = xr.open_dataset(ds_prediction_filepath, engine="netcdf4")
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print ("MONAN data mapped to GFS grid:")
            print (ds_interpolated)

    elif vs_config.INTERPOL_TYPE == 'gfs_to_monan':
        # Now, the mapped data is the reference
        ds_ref_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/gfs_mapped_to_monan_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
        # And the prediction is the original MONAN data (before mapping)
        ds_prediction_filepath = ds_monan_selected_filepath
        # Map GFS data to MONAN grid
        preprocess.map_data_to_different_grid_with_cdo(
            ref_nc=ds_monan_selected_filepath,
            input_nc=ds_gfs_in_monan_format_filepath, 
            output_nc=ds_ref_filepath
            )
        # Read interpolated data
        ds_interpolated = xr.open_dataset(ds_ref_filepath, engine="netcdf4")
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print ("GFS data mapped to MONAN grid:")
            print (ds_interpolated)
    
    return ds_ref_filepath, ds_prediction_filepath

def get_layer_from_level(level):
    # Classify a pressure level into a broad atmospheric layer.
    level_hpa = int(float(level) / 100)

    if level_hpa >= 700:
        return "low"
    elif 400 <= level_hpa < 700:
        return "mid"
    else:
        return "high"

def get_plot_limits(var, metric, level):
    # Get fixed plot limits based on variable, metric and pressure level.
    # If no level-specific limit is found, use the broader pressure-layer limits.

    level_key = str(int(float(level)))

    if hasattr(vs_config, "PLOT_LIMITS_BY_VAR_METRIC_LEVEL"):
        try:
            limits = vs_config.PLOT_LIMITS_BY_VAR_METRIC_LEVEL[var][metric][level_key]
        except KeyError:
            limits = None

        if limits is not None:
            vmin, vmax = limits

            if metric == "bias":
                max_abs = max(abs(vmin), abs(vmax))
                vmin, vmax = -max_abs, max_abs

            return vmin, vmax

    if not hasattr(vs_config, "PLOT_LIMITS_BY_VAR_METRIC_LAYER"):
        return None, None

    layer = get_layer_from_level(level)

    try:
        limits = vs_config.PLOT_LIMITS_BY_VAR_METRIC_LAYER[var][metric][layer]
    except KeyError:
        return None, None

    vmin, vmax = limits

    if metric == "bias":
        max_abs = max(abs(vmin), abs(vmax))
        vmin, vmax = -max_abs, max_abs

    return vmin, vmax

def convert_spechum_units_for_plot(ds, var, level):
    if var != "spechum":
        return ds, None

    layer = get_layer_from_level(level)
    level_hpa = int(float(level) / 100)

    ds = ds.copy()

    if int(level_hpa) <= 100:
        ds[var] = ds[var] * 100000000.0
        unit_label = "×0.01 mg/kg"
    elif layer in ["low", "mid"]:
        ds[var] = ds[var] * 1000.0
        unit_label = "g/kg"
    else:
        ds[var] = ds[var] * 1000000.0
        unit_label = "mg/kg"

    return ds, unit_label

def get_lat_lon_names(ds):
    lat_candidates = ["lat", "latitude"]
    lon_candidates = ["lon", "longitude"]

    lat_name = None
    lon_name = None

    for name in lat_candidates:
        if name in ds.coords or name in ds.dims:
            lat_name = name
            break

    for name in lon_candidates:
        if name in ds.coords or name in ds.dims:
            lon_name = name
            break

    if lat_name is None or lon_name is None:
        raise ValueError(
            "Could not identify latitude and longitude coordinates "
            "in the dataset."
        )

    return lat_name, lon_name


def subset_region(ds, region_name):
    region_limits = config.DOMAIN_DICT[region_name]

    lat_min, lat_max = region_limits["lat"]
    lon_min, lon_max = region_limits["lon"]

    lat_name, lon_name = get_lat_lon_names(ds)

    ds_region = ds

    lat_values = ds_region[lat_name]
    if lat_values[0] > lat_values[-1]:
        ds_region = ds_region.sel({lat_name: slice(lat_max, lat_min)})
    else:
        ds_region = ds_region.sel({lat_name: slice(lat_min, lat_max)})

    lon_values = ds_region[lon_name]

    if float(lon_values.max()) > 180.0:
        ds_region = ds_region.sel({lon_name: slice(lon_min, lon_max)})
    else:
        lon_min_180 = ((lon_min + 180.0) % 360.0) - 180.0
        lon_max_180 = ((lon_max + 180.0) % 360.0) - 180.0

        if lon_min_180 <= lon_max_180:
            ds_region = ds_region.sel({lon_name: slice(lon_min_180, lon_max_180)})
        else:
            ds_region = xr.concat(
                [
                    ds_region.sel({lon_name: slice(lon_min_180, 180.0)}),
                    ds_region.sel({lon_name: slice(-180.0, lon_max_180)}),
                ],
                dim=lon_name,
            )

    return ds_region


def spatial_mean(da):
    lat_name, lon_name = get_lat_lon_names(da)

    spatial_dims = [
        dim for dim in da.dims
        if dim not in ["Time", "level"]
    ]

    if lat_name in da.coords and lat_name in spatial_dims:
        weights = np.cos(np.deg2rad(da[lat_name]))
        return da.weighted(weights).mean(dim=spatial_dims, skipna=True)

    return da.mean(dim=spatial_dims, skipna=True)


def spatial_min(da):
    spatial_dims = [
        dim for dim in da.dims
        if dim not in ["Time", "level"]
    ]
    return da.min(dim=spatial_dims, skipna=True)


def spatial_max(da):
    spatial_dims = [
        dim for dim in da.dims
        if dim not in ["Time", "level"]
    ]
    return da.max(dim=spatial_dims, skipna=True)


def spatial_std(da):
    spatial_dims = [
        dim for dim in da.dims
        if dim not in ["Time", "level"]
    ]
    return da.std(dim=spatial_dims, skipna=True)


def get_scalar_value(da):
    value = da.values
    if np.size(value) == 0:
        return np.nan
    return float(np.asarray(value).squeeze())


def write_regional_summary_csv(
    ds,
    metric,
    output_csv,
    time_window,
    summary_type,
    date_init=None,
    date_final=None,
    date_list=None,
):
    if not getattr(vs_config, "WRITE_REGIONAL_SUMMARY_CSV", True):
        return

    rows = []

    if "Time" in ds.dims:
        if date_list is not None:
            ds = ds.assign_coords(Time=date_list)

        time_values = list(ds["Time"].values)
    else:
        time_values = [None]

    for region in vs_config.SUMMARY_REGIONS_TO_ANALYZE:
        ds_region = subset_region(ds, region)

        for var in vs_config.VARIABLES_TO_ANALYZE:
            if var not in ds_region:
                continue

            for level in vs_config.VERTICAL_LEVELS_TO_ANALYZE:
                da = ds_region[var].sel(level=float(level))

                mean_da = spatial_mean(da)
                min_da = spatial_min(da)
                max_da = spatial_max(da)
                std_da = spatial_std(da)

                for time_value in time_values:
                    if time_value is not None:
                        mean_value = get_scalar_value(mean_da.sel(Time=time_value))
                        min_value = get_scalar_value(min_da.sel(Time=time_value))
                        max_value = get_scalar_value(max_da.sel(Time=time_value))
                        std_value = get_scalar_value(std_da.sel(Time=time_value))
                        valid_date = str(time_value)
                    else:
                        mean_value = get_scalar_value(mean_da)
                        min_value = get_scalar_value(min_da)
                        max_value = get_scalar_value(max_da)
                        std_value = get_scalar_value(std_da)
                        valid_date = None

                    rows.append(
                        {
                            "summary_type": summary_type,
                            "date": valid_date,
                            "date_init": date_init,
                            "date_final": date_final,
                            "time_window": time_window,
                            "metric": metric,
                            "variable": var,
                            "level_pa": int(float(level)),
                            "level_hpa": int(float(level) / 100.0),
                            "region": region,
                            "mean": mean_value,
                            "min": min_value,
                            "max": max_value,
                            "std": std_value,
                        }
                    )

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    pd.DataFrame(rows).to_csv(output_csv, index=False)
    print(f"Regional summary CSV saved: {output_csv}")

def calculate_statistics(
    ds_ref_filepath,
    ds_prediction_filepath
):
    # Get date to include in output filenames
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
        vs_config.YEAR,
        vs_config.MONTH,
        vs_config.DAY,
        vs_config.HOUR
    )

    # Read datasets
    # GFS reference data
    ds_ref = xr.open_dataset(ds_ref_filepath, engine="netcdf4")

    # MONAN prediction data
    ds_prediction = xr.open_dataset(ds_prediction_filepath, engine="netcdf4")
    
    # Apply pressure-level validity mask based on GFS and MONAN surface pressure
    if vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        if "surface_pressure" not in ds_ref:
            raise ValueError(
                "APPLY_PRESSURE_LEVEL_VALIDITY_MASK is True, but "
                "'surface_pressure' was not found in the preprocessed GFS dataset."
            )

        if "surface_pressure" not in ds_prediction:
            raise ValueError(
                "APPLY_PRESSURE_LEVEL_VALIDITY_MASK is True, but "
                "'surface_pressure' was not found in the preprocessed MONAN dataset."
            )

        valid_ref_pressure_level_mask = preprocess.apply_pressure_level_validity_mask(
            ds=ds_ref,
            pressure_level=ds_ref["level"],
            surface_pressure_var="surface_pressure"
        )

        valid_prediction_pressure_level_mask = preprocess.apply_pressure_level_validity_mask(
            ds=ds_prediction,
            pressure_level=ds_prediction["level"],
            surface_pressure_var="surface_pressure"
        )

        valid_pressure_level_mask = (
            valid_ref_pressure_level_mask
            & valid_prediction_pressure_level_mask
        )

        # Remove surface_pressure before applying the mask to avoid expanding
        # this 2D/3D field to all pressure levels during ds.where().
        ds_ref = ds_ref.drop_vars("surface_pressure")
        ds_prediction = ds_prediction.drop_vars("surface_pressure")

        # Apply the same combined validity mask to reference and prediction.
        ds_ref = ds_ref.where(valid_pressure_level_mask)
        ds_prediction = ds_prediction.where(valid_pressure_level_mask)

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
        bias_filepath = (
            f"{vs_config.DIR_OUTPUT_DATA}/"
            f"date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}/"
            f"bias_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
        )
        ds_bias.to_netcdf(bias_filepath)
        ds_stats_filepath_dict["bias"] = bias_filepath

    bias_summary_csv = bias_filepath.replace(".nc", "_summary.csv")
    write_regional_summary_csv(
        ds=ds_bias,
        metric="bias",
        output_csv=bias_summary_csv,
        time_window=vs_config.TIME_WINDOW,
        summary_type="daily",
        date_init=date_in_string,
        date_final=date_in_string,
    )        

    if "relative_error" in vs_config.STATS_METRICS_TO_ANALYZE:
        # Compute relative error
        ds_relative_error = stats.relative_error(
            predictions=ds_prediction,
            observations=ds_ref
        )

        # Save relative error dataset in nc file
        relative_error_filepath = (
            f"{vs_config.DIR_OUTPUT_DATA}/"
            f"date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}/"
            f"relative_error_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
        )
        ds_relative_error.to_netcdf(relative_error_filepath)
        ds_stats_filepath_dict["relative_error"] = relative_error_filepath

    relative_error_summary_csv = relative_error_filepath.replace(".nc", "_summary.csv")
    write_regional_summary_csv(
        ds=ds_relative_error,
        metric="relative_error",
        output_csv=relative_error_summary_csv,
        time_window=vs_config.TIME_WINDOW,
        summary_type="daily",
        date_init=date_in_string,
        date_final=date_in_string,
    )

    return ds_stats_filepath_dict

def plot_statistics(ds_stats_filepath_dict):
    # Get date to include in output filenames
    date_in_string = utils.get_date_as_YYYYMMDDHH_str(
    vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
    )
    # Define verbosity
    if vs_config.SEL_VERBOSE_LEVEL >= 2:
        verbose = 'y'
    else:
        verbose = 'n'

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
                    
                    vmin, vmax = get_plot_limits(
                        var=var,
                        metric=metric,
                        level=level
                    )

                    unit_label = None
                    ds_to_plot = ds_stats

                    if var == "spechum":
                        ds_to_plot, unit_label = convert_spechum_units_for_plot(
                        ds=ds_stats,
                        var=var,
                        level=level
                        )

                    plots.plot_var_map(
                        ds=ds_to_plot,
                        var=var, 
                        cartopy_data_dir=vs_config.DIR_CARTOPY_DATA,
                        level=level, 
                        domain=domain,
                        output_filepath=(f"{vs_config.DIR_OUTPUT_FIGS}/date_{date_in_string}_"+
                                        f"time_window_{vs_config.TIME_WINDOW}/"+
                                        f"var_{var}/domain_{domain}/"+
                                        f"metric_{metric}_var_{var}_level_{level}_"+
                                        f"domain_{domain}_date_{date_in_string}_"+
                                        f"time_window_{vs_config.TIME_WINDOW}.png"),
                        verbose=verbose,
                        cmap_dict=vs_config.COLORMAP_DIVERGING_BY_VAR_DICT,
                        metric_name=metric,
                        time_window=vs_config.TIME_WINDOW,
                        vmin=vmin,
                        vmax=vmax,
                        unit_label=unit_label
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
#===================================================================================================


#===================================================================================================
# Functions for multiple run
#===================================================================================================
def run_main_for_each_date_and_time_window(date_list):
    vs_config_dir = os.path.dirname(os.path.abspath(__file__))
    vs_config_file_path = os.path.join(vs_config_dir, "vertical_structure_config.py")
    for date in date_list:
        for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
            print (f"\n Date:{date}; time window: {time_window}")
            print ("\n Updating analysis-specific config file...")
            update_config_file(
                config_file_path=vs_config_file_path,
                date=date, 
                time_window=time_window
                )      
            # Reload the updated config file
            importlib.reload(vs_config)
            vs_main.main()

def concatenate_datasets_for_all_dates_and_each_time_window(date_list):
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        print (f"\n Time window: {time_window}")
        # First, concatenate datasets for statistical metrics calculated for each date
        print (f"\n Stats datasets... {time_window}")
        concatenate_stats_datasets(
            date_list=date_list, 
            time_window=time_window
            )
        # Second, concatenate datasets for the variables analyzed for each date (they will be used
        # to calculate metrics that involve time averages)
        print (f"\n Vars datasets... {time_window}")
        concatenate_var_datasets(
            date_list=date_list, 
            time_window=time_window
            )

def calculate_mean_metrics_for_all_dates_and_each_time_window():
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        print (f"\n Time window: {time_window}")
        # First, mean of metrics that can be calculated for each time instant independently
        # (e.g., bias, relative error)
        calculate_mean_single_time_metrics(time_window=time_window)
        # Second, metrics that require multiple time instants for their definition
        # (e.g., RMSE, anomaly correlation coefficient)
        calculate_multi_time_metrics(time_window=time_window)

def plot_mean_metrics_for_all_dates_and_each_time_window():
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        print (f"\n Time window: {time_window}")
        plot_mean_metrics(time_window=time_window)

def update_config_file(config_file_path, date, time_window):
    """
    Updates YEAR, MONTH, DAY, HOUR, and TIME_WINDOW in the config file without changing order
    of already existing variables.

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

def concatenate_stats_datasets(date_list,time_window):
    # Create folder to save concatenated datasets
    os.makedirs(vs_config.DIR_OUTPUT_DATA+f"/date_multiple_time_window_{time_window}", exist_ok=True)
    # Construct filepaths for stats datasets to be concatenated
    for stat in vs_config.STATS_METRICS_TO_ANALYZE:
        stat_filepaths = []
        for date_str in date_list:
            stat_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_{date_str}_time_window_{time_window}/{stat}_date_{date_str}_time_window_{time_window}.nc"
            stat_filepaths.append(stat_filepath)
        # Concatenate stat datasets along "Time" dimension
        ds_stat_concat = xr.open_mfdataset(stat_filepaths, combine="nested", concat_dim="Time")
        # Save concatenated dataset in nc file
        stat_concat_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/{stat}_date_concat_from_{date_list[0]}_to_{date_list[-1]}_time_window_{time_window}.nc"
        ds_stat_concat.to_netcdf(stat_concat_filepath)
        stat_daily_summary_csv = (
            f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/"
            f"{stat}_daily_summary_date_from_{date_list[0]}_to_{date_list[-1]}_"
            f"time_window_{time_window}.csv"
        )

        write_regional_summary_csv(
            ds=ds_stat_concat,
            metric=stat,
            output_csv=stat_daily_summary_csv,
            time_window=time_window,
            summary_type="daily",
            date_init=date_list[0],
            date_final=date_list[-1],
            date_list=date_list,
        )

def calculate_mean_single_time_metrics(time_window):
    # Create folder to save mean stats metrics datasets
    os.makedirs(vs_config.DIR_OUTPUT_DATA+f"/date_multiple_time_window_{time_window}", exist_ok=True)
    # Construct filepaths for concatenated stats datasets
    for stat in vs_config.STATS_METRICS_TO_ANALYZE:
        stat_concat_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/{stat}_date_concat_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
        # Read concatenated dataset
        ds_stat_concat = xr.open_dataset(stat_concat_filepath, engine="netcdf4")
        # Calculate mean value of stat metric across all dates for each variable, level and domain
        ds_stat_mean = ds_stat_concat.mean(dim="Time")
        # Save dataset with mean values in nc file
        stat_mean_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/mean_{stat}_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
        ds_stat_mean.to_netcdf(stat_mean_filepath)
        stat_mean_summary_csv = stat_mean_filepath.replace(".nc", "_summary.csv")

        write_regional_summary_csv(
            ds=ds_stat_mean,
            metric=f"mean_{stat}",
            output_csv=stat_mean_summary_csv,
            time_window=time_window,
            summary_type="mean_period",
            date_init=vs_config.DATE_INIT,
            date_final=vs_config.DATE_FINAL,
        )

def concatenate_var_datasets(date_list,time_window,verbose='y'):
    # Create folder to save concatenated datasets
    os.makedirs(vs_config.DIR_OUTPUT_DATA+f"/date_multiple_time_window_{time_window}", exist_ok=True)
    # Construct filepaths for variable datasets to be concatenated
    var_monan_filepaths = []
    var_gfs_filepaths = []
    if vs_config.INTERPOL_TYPE == 'monan_to_gfs':
        for date_in_string in date_list:
            var_monan_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/monan_mapped_to_gfs_date_{date_in_string}_time_window_{time_window}.nc"
            var_monan_filepaths.append(var_monan_filepath)
            var_gfs_filepath = f"{vs_config.DIR_INPUT_INTERMEDIATE}/gfs_in_monan_format_date_{date_in_string}_time_window_{time_window}.nc"
            var_gfs_filepaths.append(var_gfs_filepath)
    elif vs_config.INTERPOL_TYPE == 'gfs_to_monan':
        for date_in_string in date_list:
            var_monan_filepath = f"{vs_config.DIR_INPUT_INTERMEDIATE}/monan_selected_variables_and_levels_date_{date_in_string}_time_window_{time_window}.nc"
            var_monan_filepaths.append(var_monan_filepath)
            var_gfs_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/gfs_mapped_to_monan_date_{date_in_string}_time_window_{time_window}.nc"
            var_gfs_filepaths.append(var_gfs_filepath)
    # Concatenate variable datasets along "Time" dimension
    if verbose == 'y':
        print ("Concatenating variable datasets for time window", time_window)
    ds_var_monan_concat = xr.open_mfdataset(var_monan_filepaths, combine="nested", concat_dim="Time")
    ds_var_gfs_concat = xr.open_mfdataset(var_gfs_filepaths, combine="nested", concat_dim="Time")
    if verbose == 'y':
        print ("Done concatenating variable datasets for time window", time_window)
    # Save concatenated datasets in nc file
    var_monan_concat_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/monan_concat_date_from_{date_list[0]}_to_{date_list[-1]}_time_window_{time_window}.nc"
    ds_var_monan_concat.to_netcdf(var_monan_concat_filepath)
    var_gfs_concat_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/gfs_concat_date_from_{date_list[0]}_to_{date_list[-1]}_time_window_{time_window}.nc"
    ds_var_gfs_concat.to_netcdf(var_gfs_concat_filepath)

def calculate_multi_time_metrics(time_window):
    # Create folder to save multi-time stats metrics datasets
    os.makedirs(vs_config.DIR_OUTPUT_DATA+f"/date_multiple_time_window_{time_window}", exist_ok=True)
    # Construct filepaths for concatenated variable datasets
    var_monan_concat_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/monan_concat_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
    var_gfs_concat_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/gfs_concat_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
    # Read concatenated variable datasets
    ds_var_monan_concat = xr.open_dataset(var_monan_concat_filepath, engine="netcdf4")
    ds_var_gfs_concat = xr.open_dataset(var_gfs_concat_filepath, engine="netcdf4")

    # Apply pressure-level validity mask based on GFS and MONAN surface pressure
    if vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        if "surface_pressure" not in ds_var_gfs_concat:
            raise ValueError(
                "APPLY_PRESSURE_LEVEL_VALIDITY_MASK is True, but "
                "'surface_pressure' was not found in the concatenated GFS dataset."
            )

        if "surface_pressure" not in ds_var_monan_concat:
            raise ValueError(
                "APPLY_PRESSURE_LEVEL_VALIDITY_MASK is True, but "
                "'surface_pressure' was not found in the concatenated MONAN dataset."
            )

        valid_ref_pressure_level_mask = preprocess.apply_pressure_level_validity_mask(
          ds=ds_var_gfs_concat,
          pressure_level=ds_var_gfs_concat["level"],
          surface_pressure_var="surface_pressure"
        )

        valid_prediction_pressure_level_mask = preprocess.apply_pressure_level_validity_mask(
          ds=ds_var_monan_concat,
          pressure_level=ds_var_monan_concat["level"],
          surface_pressure_var="surface_pressure"
        )

        valid_pressure_level_mask = (
          valid_ref_pressure_level_mask
          & valid_prediction_pressure_level_mask
        )

        # Remove surface_pressure before applying the mask to avoid expanding
        # this field to all pressure levels during ds.where().
        ds_var_gfs_concat = ds_var_gfs_concat.drop_vars("surface_pressure")
        ds_var_monan_concat = ds_var_monan_concat.drop_vars("surface_pressure")

        # Apply the same combined validity mask to reference and prediction.
        ds_var_gfs_concat = ds_var_gfs_concat.where(valid_pressure_level_mask)
        ds_var_monan_concat = ds_var_monan_concat.where(valid_pressure_level_mask)
    else:
        # Avoid calculating RMSE or ACC for surface_pressure if it exists in the dataset.
        ds_var_gfs_concat = ds_var_gfs_concat.drop_vars("surface_pressure", errors="ignore")
        ds_var_monan_concat = ds_var_monan_concat.drop_vars("surface_pressure", errors="ignore")

    # Calculate and save multi-time metrics across all dates for each variable, level and domain
    ## Here we could calculate any metric that involves time averages, such as anomaly correlation coefficient or rmse
    for multi_time_metric in vs_config.MULTI_TIME_STATS_METRICS_TO_ANALYZE:

        if multi_time_metric == "rmse":
            ds_rmse = stats.rmse(
                predictions=ds_var_monan_concat,
                observations=ds_var_gfs_concat,
                dim="Time"
            )

            rmse_filepath = (
                f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/"
                f"{multi_time_metric}_date_from_{vs_config.DATE_INIT}_to_"
                f"{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
            )

            ds_rmse.to_netcdf(rmse_filepath)

            rmse_summary_csv = rmse_filepath.replace(".nc", "_summary.csv")

            write_regional_summary_csv(
                ds=ds_rmse,
                metric="rmse",
                output_csv=rmse_summary_csv,
                time_window=time_window,
                summary_type="mean_period",
                date_init=vs_config.DATE_INIT,
                date_final=vs_config.DATE_FINAL,
            )

        elif multi_time_metric == "anomaly_correlation_coefficient":
            ds_acc = stats.anomaly_correlation_coefficient(
                predictions=ds_var_monan_concat,
                observations=ds_var_gfs_concat,
                dim="Time"
            )

            acc_filepath = (
                f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/"
                f"{multi_time_metric}_date_from_{vs_config.DATE_INIT}_to_"
                f"{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
            )

            ds_acc.to_netcdf(acc_filepath)

            acc_summary_csv = acc_filepath.replace(".nc", "_summary.csv")

            write_regional_summary_csv(
                ds=ds_acc,
                metric="anomaly_correlation_coefficient",
                output_csv=acc_summary_csv,
                time_window=time_window,
                summary_type="mean_period",
                date_init=vs_config.DATE_INIT,
                date_final=vs_config.DATE_FINAL,
            )

def plot_mean_metrics(time_window):
    # Define verbosity
    if vs_config.SEL_VERBOSE_LEVEL >= 2:
        verbose = 'y'
    else:
        verbose = 'n'
    # Create folders to save mean stats metrics plots
    os.makedirs(vs_config.DIR_OUTPUT_FIGS+f"/date_multiple_time_window_{time_window}", exist_ok=True)
    for var in vs_config.VARIABLES_TO_ANALYZE:
        os.makedirs(vs_config.DIR_OUTPUT_FIGS+f"/date_multiple_time_window_{time_window}/var_{var}", exist_ok=True)
        for domain in vs_config.DOMAINS_TO_ANALYZE:
            os.makedirs(vs_config.DIR_OUTPUT_FIGS+f"/date_multiple_time_window_{time_window}/var_{var}/domain_{domain}", exist_ok=True)
    # Construct filepaths for mean stats metrics datasets
    for metric in (vs_config.STATS_METRICS_TO_ANALYZE+vs_config.MULTI_TIME_STATS_METRICS_TO_ANALYZE):        
        if metric in vs_config.STATS_METRICS_TO_ANALYZE:
            stat_mean_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/mean_{metric}_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
        elif metric in vs_config.MULTI_TIME_STATS_METRICS_TO_ANALYZE:
            stat_mean_filepath = f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/{metric}_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
        # Read dataset with mean values of stat metric across all dates for each variable, level and domain
        ds_stat_mean = xr.open_dataset(stat_mean_filepath, engine="netcdf4")
        # Plot maps of mean values of stat metric for each domain, variable and level
        for domain in vs_config.DOMAINS_TO_ANALYZE:
            print ("domain:", domain)
            for var in vs_config.VARIABLES_TO_ANALYZE:
                print ("variable:", var)
                for level in vs_config.VERTICAL_LEVELS_TO_ANALYZE:
                    print ("level:", level)
                    if metric in vs_config.STATS_METRICS_TO_ANALYZE:
                        output_filepath = (f"{vs_config.DIR_OUTPUT_FIGS}/date_multiple_"+
                                         f"time_window_{time_window}/"+
                                         f"var_{var}/domain_{domain}/"+
                                         f"metric_mean_{metric}_var_{var}_level_{level}_"+
                                         f"domain_{domain}_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_"+
                                         f"time_window_{time_window}.png")
                    elif metric in vs_config.MULTI_TIME_STATS_METRICS_TO_ANALYZE:
                        output_filepath = (f"{vs_config.DIR_OUTPUT_FIGS}/date_multiple_"+
                                         f"time_window_{time_window}/"+
                                         f"var_{var}/domain_{domain}/"+
                                         f"metric_{metric}_var_{var}_level_{level}_"+
                                         f"domain_{domain}_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_"+
                                         f"time_window_{time_window}.png")
                    
                    vmin, vmax = get_plot_limits(
                        var=var,
                        metric=metric,
                        level=level
                    )                    

                    unit_label = None
                    ds_to_plot = ds_stat_mean

                    if var == "spechum":
                        ds_to_plot, unit_label = convert_spechum_units_for_plot(
                        ds=ds_stat_mean,
                        var=var,
                        level=level
                        )

                    plots.plot_var_map(
                        ds=ds_to_plot, 
                        var=var, 
                        cartopy_data_dir=vs_config.DIR_CARTOPY_DATA,
                        level=level, 
                        domain=domain,
                        output_filepath=output_filepath,
                        verbose=verbose,
                        cmap_dict=vs_config.COLORMAP_DIVERGING_BY_VAR_DICT,
                        metric_name=metric,
                        time_window=time_window,
                        vmin=vmin,
                        vmax=vmax,
                        unit_label=unit_label   
                        )
#===================================================================================================

#===================================================================================================
# Functions for latitude-pressure profile plots
#===================================================================================================
def get_profile_scale(var):
    """
    Get scale factor and unit label for latitude-pressure profile plots.
    """
    scale_config = getattr(vs_config, "LAT_PRESSURE_PROFILE_SCALE_BY_VAR", {})

    if var not in scale_config:
        return 1.0, None

    factor = scale_config[var].get("factor", 1.0)
    unit_label = scale_config[var].get("unit_label", None)

    return factor, unit_label


def get_lat_pressure_profile_limits(var, metric):
    """
    Get fixed colorbar limits for latitude-pressure profile plots.
    """
    limits_config = getattr(vs_config, "LAT_PRESSURE_PROFILE_LIMITS_BY_VAR_METRIC", {})

    try:
        vmin, vmax = limits_config[var][metric]
    except KeyError:
        return None, None

    if metric in ["bias", "mean_bias"]:
        max_abs = max(abs(vmin), abs(vmax))
        vmin, vmax = -max_abs, max_abs

    return vmin, vmax


def calculate_lat_pressure_profile(da):
    """
    Calculate the latitude-pressure profile by averaging over longitude and time.

    This is equivalent to the GrADS command:
    ave(ave(var, x=1, x=nlon), t=1, t=ntime)

    The output keeps latitude and pressure level.
    """
    lat_name, lon_name = get_lat_lon_names(da)

    mean_dims = [lon_name]

    if "Time" in da.dims:
        mean_dims.append("Time")

    da_profile = da.mean(dim=mean_dims, skipna=True)

    return da_profile

def generate_lat_pressure_profile_plots(time_window):
    """
    Plot latitude-pressure profiles from concatenated metric datasets.

    This function handles the analysis-specific workflow:
    read concatenated metric files, select domains, variables and levels,
    apply unit scaling, calculate the zonal and time mean profile,
    and call the generic plotting function from monan_analysis.plots.
    """
    if not getattr(vs_config, "PLOT_LAT_PRESSURE_PROFILES", False):
        return

    metrics_to_plot = getattr(
        vs_config,
        "LAT_PRESSURE_PROFILE_METRICS_TO_PLOT",
        vs_config.STATS_METRICS_TO_ANALYZE,
    )

    variables_to_plot = getattr(
        vs_config,
        "LAT_PRESSURE_PROFILE_VARIABLES_TO_PLOT",
        vs_config.VARIABLES_TO_ANALYZE,
    )

    domains_to_plot = getattr(
        vs_config,
        "LAT_PRESSURE_PROFILE_DOMAINS_TO_PLOT",
        ["global"],
    )

    levels_to_plot = getattr(
        vs_config,
        "LAT_PRESSURE_PROFILE_LEVELS_TO_PLOT",
        None,
    )

    for metric in metrics_to_plot:
        if metric in vs_config.STATS_METRICS_TO_ANALYZE:
            metric_filepath = (
                f"{vs_config.DIR_INPUT_PROCESSED}/"
                f"{metric}_date_concat_from_{vs_config.DATE_INIT}_to_"
                f"{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
            )

        elif metric in vs_config.MULTI_TIME_STATS_METRICS_TO_ANALYZE:
            metric_filepath = (
                f"{vs_config.DIR_OUTPUT_DATA}/"
                f"date_multiple_time_window_{time_window}/"
                f"{metric}_date_from_{vs_config.DATE_INIT}_to_"
                f"{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
            )

        else:
            print(f"Metric {metric} is not configured in STATS_METRICS_TO_ANALYZE or MULTI_TIME_STATS_METRICS_TO_ANALYZE. Skipping.")
            continue

        if not os.path.exists(metric_filepath):
            print(f"File not found, skipping: {metric_filepath}")
            continue

        ds_metric = xr.open_dataset(metric_filepath, engine="netcdf4")

        for domain in domains_to_plot:
            ds_domain = subset_region(ds_metric, domain)

            for var in variables_to_plot:
                if var not in ds_domain:
                    print(f"Variable {var} not found in {metric_filepath}, skipping.")
                    continue

                da = ds_domain[var]

                if levels_to_plot is not None:
                    levels_to_plot_float = [float(level) for level in levels_to_plot]
                    da = da.sel(level=levels_to_plot_float)

                if metric in ["bias", "rmse"]:
                    scale_factor, unit_label = get_profile_scale(var)
                    da = da * scale_factor
                elif metric == "relative_error":
                    unit_label = "%"
                elif metric == "anomaly_correlation_coefficient":
                    unit_label = ""
                else:
                    unit_label = None

                da_profile = calculate_lat_pressure_profile(da)

                vmin, vmax = get_lat_pressure_profile_limits(
                    var=var,
                    metric=metric,
                )

                output_filepath = (
                    f"{vs_config.DIR_OUTPUT_FIGS}/"
                    f"date_multiple_time_window_{time_window}/"
                    f"var_{var}/domain_{domain}/"
                    f"profile_{metric}_var_{var}_domain_{domain}_"
                    f"date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_"
                    f"time_window_{time_window}.png"
                )

                domain_label = domain.replace("_", " ")
                metric_label = metric.replace("_", " ")

                subtitle = (
                    f"Zonal and time mean, {domain_label}, "
                    f"{vs_config.DATE_INIT} to {vs_config.DATE_FINAL}, "
                    f"lead {int(time_window):03d} h"
                )

                cmap = vs_config.COLORMAP_DIVERGING_BY_VAR_DICT.get(var, "coolwarm")

                plots.plot_lat_pressure_profile(
                    da_profile=da_profile,
                    output_filepath=output_filepath,
                    var_label=var,
                    metric_label=metric_label,
                    unit_label=unit_label,
                    cmap=cmap,
                    vmin=vmin,
                    vmax=vmax,
                    subtitle=subtitle,
                )

                print(f"Latitude-pressure profile saved: {output_filepath}")

def generate_lat_pressure_profile_plots_for_all_dates_and_each_time_window():
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        print(f"\n Time window: {time_window}")
        generate_lat_pressure_profile_plots(time_window=time_window)
#===================================================================================================
