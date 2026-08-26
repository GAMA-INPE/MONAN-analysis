# -*- coding: utf-8 -*-
"""
vertical_structure_aux.py

Based on a script by Andre Lyra (andre.lyra@inpe.br)
Last update: Feb 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last update: Apr 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last update: May 2026 by Andre Lyra (andre.lyra@inpe.br) - topography masking of pressure levels
Last update: Aug 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)

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

import gc
import monan_analysis
import monan_analysis.config as config
import monan_analysis.io as io
import monan_analysis.utils as utils
import monan_analysis.preprocess as preprocess
import monan_analysis.stats as stats
import monan_analysis.plots as plots
from . import vertical_structure_config as vs_config
from . import vertical_structure_main as vs_main
import os
import xarray as xr
import pandas as pd
import numpy as np
import subprocess
import importlib
from concurrent.futures import ProcessPoolExecutor, as_completed

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

def read_and_preprocess_prediction_data():
    if vs_config.PREDICTION_MODEL == "monan":
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print("Reading and preprocessing data from prediction model: MONAN. Selected routine: "
                  "read_and_preprocess_monan_prediction_data...")
        return read_and_preprocess_monan_prediction_data()
    elif vs_config.PREDICTION_MODEL == "gfs_analysis":
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print("Reading and preprocessing data from prediction model: GFS analysis. Selected routine: "
                  "read_and_preprocess_gfs_analysis_prediction_data...")
        return read_and_preprocess_gfs_analysis_prediction_data()
    elif vs_config.PREDICTION_MODEL == "gfs":
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print("Reading and preprocessing data from prediction model: GFS. Selected routine:"
                  "read_and_preprocess_gfs_prediction_data...")
        return read_and_preprocess_gfs_prediction_data()
    else:
        raise ValueError(f"Unsupported prediction model: {vs_config.PREDICTION_MODEL}")
    
def read_and_preprocess_monan_prediction_data():
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
        grid_spec=vs_config.GRID_SPEC_MONAN,
        vertical_level_spec=vs_config.VERTICAL_LEVEL_SPEC_MONAN,
        base_dir=vs_config.DIR_MONAN_PREOP,
        verbose=verbose
    )

    # Select pressure-level variables to be used for analysis
    ds_monan_selected = ds_monan[vs_config.VARIABLES_TO_ANALYZE].sel(
        level=vs_config.VERTICAL_LEVELS_TO_ANALYZE
    )

    # Include MONAN surface pressure in the same preprocessed dataset when
    # the pressure-level validity mask is enabled
    if vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        ds_monan_selected["surface_pressure"] = ds_monan["surface_pressure"]

    # Save preprocessed MONAN dataset
    ds_monan_selected_filepath = (
        f"{vs_config.DIR_INPUT_INTERMEDIATE}/"
        f"prediction_{vs_config.PREDICTION_MODEL}_in_monan_format_date_{date_in_string}_"
        f"time_window_{vs_config.TIME_WINDOW}.nc"
    )
    ds_monan_selected.to_netcdf(ds_monan_selected_filepath)

    # If needed, print preprocessed dataset
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print("MONAN dataset with selected variables and levels:")
        print(ds_monan_selected)

    return ds_monan_selected_filepath

def read_and_preprocess_gfs_analysis_prediction_data():
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
    ds_gfs, gfs_filepath = io.read_ds_gfs_analysis(
        year=vs_config.YEAR,
        month=vs_config.MONTH,
        day=vs_config.DAY,
        hour=vs_config.HOUR,
        base_dir=vs_config.DIR_GFS_ANALYSIS,
        stream_name=vs_config.STREAM_NAME_GFS,
        verbose=verbose
    )

    # Configure GFS dataset to match MONAN format
    ds_gfs_in_monan_format = preprocess.get_gfs_data_in_monan_format(
        ds_gfs=ds_gfs,
        gfs_to_monan_var_dict=config.GFS_TO_MONAN_VAR_DICT
    )

    # Select pressure-level variables to be used for analysis
    ds_gfs_in_monan_format = ds_gfs_in_monan_format[
        vs_config.VARIABLES_TO_ANALYZE
    ].sel(
        level=vs_config.VERTICAL_LEVELS_TO_ANALYZE
    )

    # Include GFS surface pressure in the same preprocessed dataset when
    # the pressure-level validity mask is enabled
    if vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        ds_gfs_sp, gfs_sp_filepath = io.read_ds_gfs_analysis(
            year=vs_config.YEAR,
            month=vs_config.MONTH,
            day=vs_config.DAY,
            hour=vs_config.HOUR,
            base_dir=vs_config.DIR_GFS_ANALYSIS,
            stream_name="surface",
            verbose=verbose
        )

        # Select and configure GFS surface pressure
        surface_pressure = (
            ds_gfs_sp["sp"]
            .sortby("latitude")
            .isel(time=0, drop=True)
            .rename("surface_pressure")
        )

        # Include GFS surface pressure in the pressure-level dataset
        ds_gfs_in_monan_format["surface_pressure"] = surface_pressure

    # Save preprocessed GFS dataset as prediction model
    ds_gfs_in_monan_format_filepath = (
        f"{vs_config.DIR_INPUT_INTERMEDIATE}/"
        f"prediction_{vs_config.PREDICTION_MODEL}_in_monan_format_date_{date_in_string}_"
        f"time_window_{vs_config.TIME_WINDOW}.nc"
    )
    ds_gfs_in_monan_format.to_netcdf(ds_gfs_in_monan_format_filepath)

    # If needed, print preprocessed dataset
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print("GFS prediction dataset in MONAN data format:")
        print(ds_gfs_in_monan_format)

    return ds_gfs_in_monan_format_filepath

def read_and_preprocess_gfs_prediction_data():
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
        time_window=vs_config.TIME_WINDOW,
        base_dir=vs_config.DIR_GFS,
        stream_name=vs_config.STREAM_NAME_GFS,
        verbose=verbose
    )

    # Configure GFS dataset to match MONAN format
    ds_gfs_in_monan_format = preprocess.get_gfs_data_in_monan_format(
        ds_gfs=ds_gfs,
        gfs_to_monan_var_dict=config.GFS_TO_MONAN_VAR_DICT
    )

    # Select pressure-level variables to be used for analysis
    ds_gfs_in_monan_format = ds_gfs_in_monan_format[
        vs_config.VARIABLES_TO_ANALYZE
    ].sel(
        level=vs_config.VERTICAL_LEVELS_TO_ANALYZE
    )

    # Include GFS surface pressure in the same preprocessed dataset when
    # the pressure-level validity mask is enabled
    if vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        ds_gfs_sp, gfs_sp_filepath = io.read_ds_gfs(
            year=vs_config.YEAR,
            month=vs_config.MONTH,
            day=vs_config.DAY,
            hour=vs_config.HOUR,
            time_window=vs_config.TIME_WINDOW,
            base_dir=vs_config.DIR_GFS,
            stream_name="surface",
            verbose=verbose
        )

        # Select and configure GFS surface pressure
        surface_pressure = (
            ds_gfs_sp["sp"]
            .sortby("latitude")
            .isel(time=0, drop=True)
            .rename("surface_pressure")
        )

        # Include GFS surface pressure in the pressure-level dataset
        ds_gfs_in_monan_format["surface_pressure"] = surface_pressure

    # Save preprocessed GFS dataset as prediction model
    ds_gfs_in_monan_format_filepath = (
        f"{vs_config.DIR_INPUT_INTERMEDIATE}/"
        f"prediction_{vs_config.PREDICTION_MODEL}_in_monan_format_date_{date_in_string}_"
        f"time_window_{vs_config.TIME_WINDOW}.nc"
    )
    ds_gfs_in_monan_format.to_netcdf(ds_gfs_in_monan_format_filepath)

    # If needed, print preprocessed dataset
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print("GFS prediction dataset in MONAN data format:")
        print(ds_gfs_in_monan_format)

    return ds_gfs_in_monan_format_filepath

def read_and_preprocess_ref_data():
    if vs_config.REFERENCE_DATA == "gfs_analysis":
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print("Reading and preprocessing reference data: GFS analysis. Selected routine: "
                  "read_and_preprocess_gfs_analysis_ref_data...")
        return read_and_preprocess_gfs_analysis_ref_data()
    else:
        raise ValueError(f"Unsupported reference data: {vs_config.REFERENCE_DATA}")

def read_and_preprocess_gfs_analysis_ref_data():
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
    ds_gfs, gfs_filepath = io.read_ds_gfs_analysis(
        year=vs_config.YEAR,
        month=vs_config.MONTH,
        day=vs_config.DAY,
        hour=vs_config.HOUR,
        base_dir=vs_config.DIR_GFS_ANALYSIS,
        stream_name=vs_config.STREAM_NAME_GFS,
        verbose=verbose
    )

    # Configure GFS dataset to match MONAN format
    ds_gfs_in_monan_format = preprocess.get_gfs_data_in_monan_format(
        ds_gfs=ds_gfs,
        gfs_to_monan_var_dict=config.GFS_TO_MONAN_VAR_DICT
    )

    # Select pressure-level variables to be used for analysis
    ds_gfs_in_monan_format = ds_gfs_in_monan_format[
        vs_config.VARIABLES_TO_ANALYZE
    ].sel(
        level=vs_config.VERTICAL_LEVELS_TO_ANALYZE
    )

    # Include GFS surface pressure in the same preprocessed dataset when
    # the pressure-level validity mask is enabled
    if vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        ds_gfs_sp, gfs_sp_filepath = io.read_ds_gfs_analysis(
            year=vs_config.YEAR,
            month=vs_config.MONTH,
            day=vs_config.DAY,
            hour=vs_config.HOUR,
            base_dir=vs_config.DIR_GFS_ANALYSIS,
            stream_name="surface",
            verbose=verbose
        )

        # Select and configure GFS surface pressure
        surface_pressure = (
            ds_gfs_sp["sp"]
            .sortby("latitude")
            .isel(time=0, drop=True)
            .rename("surface_pressure")
        )

        # Include GFS surface pressure in the pressure-level dataset
        ds_gfs_in_monan_format["surface_pressure"] = surface_pressure

    # Save preprocessed GFS dataset
    ds_gfs_in_monan_format_filepath = (
        f"{vs_config.DIR_INPUT_INTERMEDIATE}/"
        f"ref_{vs_config.REFERENCE_DATA}_in_monan_format_date_{date_in_string}_"
        f"time_window_{vs_config.TIME_WINDOW}.nc"
    )
    ds_gfs_in_monan_format.to_netcdf(ds_gfs_in_monan_format_filepath)

    # If needed, print preprocessed dataset
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print("GFS ref dataset in MONAN data format:")
        print(ds_gfs_in_monan_format)

    return ds_gfs_in_monan_format_filepath

def interpolate_prediction_ref(ds_prediction_model_filepath, ds_ref_data_filepath, output_nc=None,
                               force_interpolation = 'n'):
    if force_interpolation == 'n' and (vs_config.PREDICTION_MODEL == vs_config.REFERENCE_DATA or (vs_config.PREDICTION_MODEL == 'gfs' and vs_config.REFERENCE_DATA == 'gfs_analysis')):
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print(f"No interpolation routine needed because "
                  f"prediction model: {vs_config.PREDICTION_MODEL} is the same as "
                  f"reference data: {vs_config.REFERENCE_DATA}")
        return ds_ref_data_filepath, ds_prediction_model_filepath
    else:
        # Get date and write it into preprocessed filepath
        date_in_string = utils.get_date_as_YYYYMMDDHH_str(
        vs_config.YEAR, vs_config.MONTH, vs_config.DAY, vs_config.HOUR
        )
        if vs_config.INTERPOL_TYPE == 'prediction_to_ref':
            if vs_config.SEL_VERBOSE_LEVEL >= 1:
                print(f"Interpolating prediction model data to reference data grid because "
                      f"INTERPOL_TYPE is set to 'prediction_to_ref' for "
                      f"prediction model: {vs_config.PREDICTION_MODEL} and "
                      f"reference data: {vs_config.REFERENCE_DATA}.")
            # Now, the mapped grid is that from the prediction model
            ds_mapped_grid_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/prediction_{vs_config.PREDICTION_MODEL}_mapped_to_ref_{vs_config.REFERENCE_DATA}_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
            # And the reference grid is that from the reference data
            ds_ref_grid_filepath = ds_ref_data_filepath
            # Map prediction model data to reference data grid
            if output_nc:
                ds_mapped_grid_filepath = output_nc
            preprocess.map_data_to_different_grid_with_cdo(
                ref_grid_nc=ds_ref_grid_filepath,
                input_nc=ds_prediction_model_filepath, 
                output_nc=ds_mapped_grid_filepath
                )
            # Thus the final reference data filepath is the same as that from the original reference 
            # data, and the final prediction model filepath is that from the prediction model mapped
            # to the reference data grid
            ds_prediction_model_filepath = ds_mapped_grid_filepath
            # If needed, show the mapped data
            if vs_config.SEL_VERBOSE_LEVEL >= 1:
                # Read interpolated data
                ds_interpolated = xr.open_dataset(ds_mapped_grid_filepath, engine="netcdf4")
                print (f"{vs_config.PREDICTION_MODEL} data mapped to {vs_config.REFERENCE_DATA} grid:")
                print (ds_interpolated)
            return ds_ref_data_filepath, ds_prediction_model_filepath

        elif vs_config.INTERPOL_TYPE == 'ref_to_prediction':
            if vs_config.SEL_VERBOSE_LEVEL >= 1:
                print(f"Interpolating reference data to prediction model grid because "
                      f"INTERPOL_TYPE is set to 'ref_to_prediction' for "
                      f"prediction model: {vs_config.PREDICTION_MODEL} and "
                      f"reference data: {vs_config.REFERENCE_DATA}.")
            # Now, the mapped grid is that from the reference data
            ds_mapped_grid_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/ref_{vs_config.REFERENCE_DATA}_mapped_to_prediction_{vs_config.PREDICTION_MODEL}_date_{date_in_string}_time_window_{vs_config.TIME_WINDOW}.nc"
            # And the reference grid is that from the prediction model
            ds_ref_grid_filepath = ds_prediction_model_filepath
            # Map reference data to prediction model grid
            if output_nc:
                ds_mapped_grid_filepath = output_nc
            preprocess.map_data_to_different_grid_with_cdo(
                ref_grid_nc=ds_ref_grid_filepath,
                input_nc=ds_ref_data_filepath, 
                output_nc=ds_mapped_grid_filepath
                )
            # Thus, the final reference data filepath is that from the original reference data 
            # mapped to the prediction model grid, and the final prediction model filepath is 
            # the same as that from the original prediction model data
            ds_ref_data_filepath = ds_mapped_grid_filepath
            # If needed, show the mapped data
            if vs_config.SEL_VERBOSE_LEVEL >= 1:
                # Read interpolated data
                ds_interpolated = xr.open_dataset(ds_mapped_grid_filepath, engine="netcdf4")
                print (f"{vs_config.REFERENCE_DATA} data mapped to {vs_config.PREDICTION_MODEL} grid:")
                print (ds_interpolated)
            return ds_ref_data_filepath, ds_prediction_model_filepath
        else:
            raise ValueError(
                f"Unsupported interpolation type: {vs_config.INTERPOL_TYPE} for " 
                f"combination of prediction model: {vs_config.PREDICTION_MODEL} and " 
                f"reference data: {vs_config.REFERENCE_DATA}."
                )

def calculate_statistics(ds_ref_filepath, ds_prediction_filepath):
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
        
        # Obtain validity masks for reference dataset
        valid_ref_pressure_level_mask = preprocess.apply_pressure_level_validity_mask(
            ds=ds_ref,
            pressure_level=ds_ref["level"],
            surface_pressure_var="surface_pressure"
        )

        # Obtain validity masks for prediction dataset
        valid_prediction_pressure_level_mask = preprocess.apply_pressure_level_validity_mask(
            ds=ds_prediction,
            pressure_level=ds_prediction["level"],
            surface_pressure_var="surface_pressure"
        )

        # Obtain validity mask considering both datasets
        valid_pressure_level_mask = (
            valid_ref_pressure_level_mask
            & valid_prediction_pressure_level_mask
        )

        # Remove surface_pressure before applying the mask to avoid expanding
        # this 2D/3D field to all pressure levels during ds.where()
        ds_ref = ds_ref.drop_vars("surface_pressure")
        ds_prediction = ds_prediction.drop_vars("surface_pressure")

        # Apply the same combined validity mask to reference and prediction
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
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print(f"Metric: {metric}")

        with xr.open_dataset(ds_stats_filepath_dict[metric], engine="netcdf4") as ds_stats:
            for domain in vs_config.DOMAINS_TO_ANALYZE:
                if vs_config.SEL_VERBOSE_LEVEL >= 1:
                    print("domain:", domain)
                for var in vs_config.VARIABLES_TO_ANALYZE:
                    if vs_config.SEL_VERBOSE_LEVEL >= 1:
                        print("variable:", var)
                    for level in vs_config.VERTICAL_LEVELS_TO_ANALYZE:
                        if vs_config.SEL_VERBOSE_LEVEL >= 1:
                            print("level:", level)

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
                            output_filepath=(
                                f"{vs_config.DIR_OUTPUT_FIGS}/date_{date_in_string}_"
                                f"time_window_{vs_config.TIME_WINDOW}/"
                                f"var_{var}/domain_{domain}/"
                                f"metric_{metric}_var_{var}_level_{level}_"
                                f"domain_{domain}_date_{date_in_string}_"
                                f"time_window_{vs_config.TIME_WINDOW}.png"
                            ),
                            verbose=verbose,
                            cmap_dict=vs_config.COLORMAP_DIVERGING_BY_VAR_DICT,
                            metric_name=metric,
                            time_window=vs_config.TIME_WINDOW,
                            vmin=vmin,
                            vmax=vmax,
                            unit_label=unit_label
                        )

def convert_spechum_units_for_plot(ds, var, level):
    if var != "spechum":
        return ds, None

    layer = get_layer_from_level(level)
    level_hpa = int(float(level) / 100)

    ds = ds.copy()

    if int(level_hpa) <= 100: # ×0.01 mg/kg at 100 hPa and lower-pressure levels
        ds[var] = ds[var] * 100000000.0
        unit_label = "×0.01 mg/kg"
    elif layer in ["low", "mid"]:
        ds[var] = ds[var] * 1000.0
        unit_label = "g/kg"
    else:
        ds[var] = ds[var] * 1000000.0
        unit_label = "mg/kg"

    return ds, unit_label

def get_layer_from_level(level):
    # Classify a pressure level into a broad atmospheric layer
    level_hpa = int(float(level) / 100)

    if level_hpa >= 700:
        return "low"
    elif 400 <= level_hpa < 700:
        return "mid"
    else:
        return "high"

def get_plot_limits(var, metric, level):
    # Get fixed plot limits based on variable, metric and pressure level
    # If no level-specific limit is found, use the broader pressure-layer limits

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

    for region in vs_config.SUMMARY_DOMAINS_TO_ANALYZE:
        ds_region = preprocess.subset_region(ds, region)

        for var in vs_config.VARIABLES_TO_ANALYZE:
            if var not in ds_region:
                continue

            for level in vs_config.VERTICAL_LEVELS_TO_ANALYZE:
                da = ds_region[var].sel(level=float(level))

                mean_da = preprocess.spatial_mean(da)
                min_da = preprocess.spatial_min(da)
                max_da = preprocess.spatial_max(da)
                std_da = preprocess.spatial_std(da)

                for time_value in time_values:
                    if time_value is not None:
                        mean_value = utils.get_scalar_value(mean_da.sel(Time=time_value))
                        min_value = utils.get_scalar_value(min_da.sel(Time=time_value))
                        max_value = utils.get_scalar_value(max_da.sel(Time=time_value))
                        std_value = utils.get_scalar_value(std_da.sel(Time=time_value))
                        valid_date = str(time_value)
                    else:
                        mean_value = utils.get_scalar_value(mean_da)
                        min_value = utils.get_scalar_value(min_da)
                        max_value = utils.get_scalar_value(max_da)
                        std_value = utils.get_scalar_value(std_da)
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
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print(f"Regional summary CSV saved: {output_csv}")

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
# Tentative functions for running this in parallel (CURRENTLY NOT WORKING!):
# def process_date_and_time_window(date, time_window, vs_config_dir):
#     """
#     Process a single combination of date and time window.
#     """
#     vs_config_file_path = os.path.join(vs_config_dir, "vertical_structure_config.py")
#     if vs_config.SEL_VERBOSE_LEVEL >= 1:
#         print(f"\n Date:{date}; time window: {time_window}")
#         print("\n Updating analysis-specific config file...")
#     update_config_file(
#         config_file_path=vs_config_file_path,
#         date=date,
#         time_window=time_window
#     )
#     # Reload the updated config file
#     importlib.reload(vs_config)
#     vs_main.main()
#     gc.collect()

# def run_main_for_each_date_and_time_window(date_list):
#     """
#     Run the main function for each combination of date and time window in parallel.
#     """
#     vs_config_dir = os.path.dirname(os.path.abspath(__file__))
#     tasks = []

#     # Use ProcessPoolExecutor for parallel execution
#     with ProcessPoolExecutor() as executor:
#         for date in date_list:
#             for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
#                 # Submit each combination as a separate task
#                 tasks.append(executor.submit(process_date_and_time_window, date, time_window, vs_config_dir))

#         # Collect results and handle exceptions
#         for future in as_completed(tasks):
#             try:
#                 future.result()  # Wait for the task to complete
#             except Exception as e:
#                 print(f"Task failed with exception: {e}")

def run_main_for_each_date_and_time_window(date_list):
    vs_config_dir = os.path.dirname(os.path.abspath(__file__))
    vs_config_file_path = os.path.join(vs_config_dir, "vertical_structure_config.py")
    for date in date_list:
        for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
            if vs_config.SEL_VERBOSE_LEVEL >= 1:
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
            gc.collect()

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

def concatenate_datasets_for_all_dates_and_each_time_window(date_list):
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print (f"\n Time window: {time_window}")
        # First, concatenate datasets for statistical metrics calculated for each date
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print (f"\n Stats datasets... {time_window}")
        concatenate_stats_datasets(
            date_list=date_list, 
            time_window=time_window
            )
        # Second, concatenate datasets for the variables analyzed for each date (they will be used
        # to calculate metrics that involve time averages)
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print (f"\n Vars datasets... {time_window}")
        concatenate_var_datasets(
            date_list=date_list, 
            time_window=time_window
            )

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
        
        # Save summary CSV for concatenated stat dataset
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

def concatenate_var_datasets(date_list,time_window):
    # Create folder to save concatenated datasets
    os.makedirs(vs_config.DIR_OUTPUT_DATA+f"/date_multiple_time_window_{time_window}", exist_ok=True)

    # Construct filepaths for variable datasets to be concatenated
    var_prediction_filepaths = []
    var_ref_filepaths = []

    # Check if prediction model and reference data are the same, in which case no mapping was applied
    if vs_config.PREDICTION_MODEL == vs_config.REFERENCE_DATA or (vs_config.PREDICTION_MODEL == 'gfs' and vs_config.REFERENCE_DATA == 'gfs_analysis'):
        for date_in_string in date_list:
            var_prediction_filepath = f"{vs_config.DIR_INPUT_INTERMEDIATE}/prediction_{vs_config.PREDICTION_MODEL}_in_monan_format_date_{date_in_string}_time_window_{time_window}.nc"
            var_prediction_filepaths.append(var_prediction_filepath)
            var_ref_filepath = f"{vs_config.DIR_INPUT_INTERMEDIATE}/ref_{vs_config.REFERENCE_DATA}_in_monan_format_date_{date_in_string}_time_window_{time_window}.nc"
            var_ref_filepaths.append(var_ref_filepath)
    # If not, look for the correct mapped and reference data depending on the employed type of interpolation
    else:
        if vs_config.INTERPOL_TYPE == "prediction_to_ref":
            for date_in_string in date_list:
                var_prediction_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/prediction_{vs_config.PREDICTION_MODEL}_mapped_to_ref_{vs_config.REFERENCE_DATA}_date_{date_in_string}_time_window_{time_window}.nc"
                var_prediction_filepaths.append(var_prediction_filepath)
                var_ref_filepath = f"{vs_config.DIR_INPUT_INTERMEDIATE}/ref_{vs_config.REFERENCE_DATA}_in_monan_format_date_{date_in_string}_time_window_{time_window}.nc"
                var_ref_filepaths.append(var_ref_filepath)
        elif vs_config.INTERPOL_TYPE == "ref_to_prediction":
            for date_in_string in date_list:
                var_prediction_filepath = f"{vs_config.DIR_INPUT_INTERMEDIATE}/prediction_{vs_config.PREDICTION_MODEL}_in_monan_format_date_{date_in_string}_time_window_{time_window}.nc"
                var_prediction_filepaths.append(var_prediction_filepath)
                var_ref_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/ref_{vs_config.REFERENCE_DATA}_mapped_to_{vs_config.PREDICTION_MODEL}_date_{date_in_string}_time_window_{time_window}.nc"
                var_ref_filepaths.append(var_ref_filepath)

    # Concatenate variable datasets along "Time" dimension
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print ("Concatenating variable datasets for time window", time_window)
    ds_var_prediction_concat = xr.open_mfdataset(var_prediction_filepaths, combine="nested", concat_dim="Time")
    ds_var_ref_concat = xr.open_mfdataset(var_prediction_filepaths, combine="nested", concat_dim="Time")
    if vs_config.SEL_VERBOSE_LEVEL >= 1:
        print ("Done concatenating variable datasets for time window", time_window)
    # Save concatenated datasets in nc file
    var_prediction_concat_filepath, var_ref_concat_filepath = get_prediction_ref_concat_filepath(time_window)
    ds_var_prediction_concat.to_netcdf(var_prediction_concat_filepath)
    ds_var_ref_concat.to_netcdf(var_ref_concat_filepath)

def get_prediction_ref_concat_filepath(time_window):
    prediction_concat_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/prediction_{vs_config.PREDICTION_MODEL}_concat_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
    ref_concat_filepath = f"{vs_config.DIR_INPUT_PROCESSED}/ref_{vs_config.REFERENCE_DATA}_concat_date_from_{vs_config.DATE_INIT}_to_{vs_config.DATE_FINAL}_time_window_{vs_config.TIME_WINDOW}.nc"
    return prediction_concat_filepath, ref_concat_filepath

def calculate_mean_metrics_for_all_dates_and_each_time_window():
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print (f"\n Time window: {time_window}")
        # First, mean of metrics that can be calculated for each time instant independently
        # (e.g., bias, relative error)
        calculate_mean_single_time_metrics(time_window=time_window)
        # Second, metrics that require multiple time instants for their definition
        # (e.g., RMSE, anomaly correlation coefficient)
        calculate_multi_time_metrics(time_window=time_window)

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

        # Write summary of mean values to CSV file
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

def calculate_multi_time_metrics(time_window):
    # Create folder to save multi-time stats metrics datasets
    os.makedirs(vs_config.DIR_OUTPUT_DATA+f"/date_multiple_time_window_{time_window}", exist_ok=True)
    # Construct filepaths for concatenated variable datasets
    var_prediction_concat_filepath, var_ref_concat_filepath = get_prediction_ref_concat_filepath(time_window)
    # Read concatenated variable datasets
    ds_var_prediction_concat = xr.open_dataset(var_prediction_concat_filepath, engine="netcdf4")
    ds_var_ref_concat = xr.open_dataset(var_ref_concat_filepath, engine="netcdf4")

    # Apply pressure-level validity mask based on ref and prediction model surface pressure
    if vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        if "surface_pressure" not in ds_var_ref_concat:
            raise ValueError(
                "APPLY_PRESSURE_LEVEL_VALIDITY_MASK is True, but "
                "'surface_pressure' was not found in the concatenated ref dataset."
            )

        if "surface_pressure" not in ds_var_prediction_concat:
            raise ValueError(
                "APPLY_PRESSURE_LEVEL_VALIDITY_MASK is True, but "
                "'surface_pressure' was not found in the concatenated prediction model dataset."
            )

        # Obtain validity mask for reference dataset 
        valid_ref_pressure_level_mask = preprocess.apply_pressure_level_validity_mask(
          ds=ds_var_ref_concat,
          pressure_level=ds_var_ref_concat["level"],
          surface_pressure_var="surface_pressure"
        )

        # Obtain validity mask for prediction dataset
        valid_prediction_pressure_level_mask = preprocess.apply_pressure_level_validity_mask(
          ds=ds_var_prediction_concat,
          pressure_level=ds_var_prediction_concat["level"],
          surface_pressure_var="surface_pressure"
        )

        # Combine validity masks for reference and prediction datasets
        valid_pressure_level_mask = (
          valid_ref_pressure_level_mask
          & valid_prediction_pressure_level_mask
        )

        # Remove surface_pressure before applying the mask to avoid expanding
        # this field to all pressure levels during ds.where()
        ds_var_ref_concat = ds_var_ref_concat.drop_vars("surface_pressure")
        ds_var_prediction_concat = ds_var_prediction_concat.drop_vars("surface_pressure")

        # Apply the same combined validity mask to reference and prediction
        ds_var_ref_concat = ds_var_ref_concat.where(valid_pressure_level_mask)
        ds_var_prediction_concat = ds_var_prediction_concat.where(valid_pressure_level_mask)
    else:
        # Avoid calculating RMSE or ACC for surface_pressure if it exists in the dataset
        ds_var_ref_concat = ds_var_ref_concat.drop_vars("surface_pressure", errors="ignore")
        ds_var_prediction_concat = ds_var_prediction_concat.drop_vars("surface_pressure", errors="ignore")

    # Calculate and save multi-time metrics across all dates for each variable, level and domain
    ## Here we could calculate any metric that involves time averages, such as anomaly correlation coefficient or rmse
    for multi_time_metric in vs_config.MULTI_TIME_STATS_METRICS_TO_ANALYZE:

        if multi_time_metric == "rmse":
            ds_rmse = stats.rmse(
                predictions=ds_var_prediction_concat,
                observations=ds_var_ref_concat,
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
                predictions=ds_var_prediction_concat,
                observations=ds_var_ref_concat,
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

        elif multi_time_metric == "anomaly_correlation_coefficient_standard":
            # # Interpolate climatology to ref grid
            # interpolate_prediction_ref(
            #     ds_prediction_model_filepath=vs_config.FILEPATH_CLIMATOLOGY,
            #     ds_ref_data_filepath=ds_var_ref_concat,
            #     output_nc=vs_config.DIR_INPUT_PROCESSED+f"/climatology_mapped_to_ref_{vs_config.REFERENCE_DATA}.nc",
            #     force_interpolation='y'
            # )
            # Read mapped climatology
            #ds_climatology = xr.open_dataset(vs_config.DIR_INPUT_PROCESSED+f"/climatology_mapped_to_ref_{vs_config.REFERENCE_DATA}.nc", engine="netcdf4")
            ds_climatology = xr.open_dataset(vs_config.FILEPATH_CLIMATOLOGY, engine="netcdf4")

            ds_acc = stats.anomaly_correlation_coefficient_standard(
                var="zgeo", 
                predictions_monthly=ds_var_prediction_concat.mean(dim="Time", keep_attrs=True).sel(level="50000"),
                observations_monthly=ds_var_ref_concat.mean(dim="Time", keep_attrs=True).sel(level="50000"),
                climatology_monthly=ds_climatology.sel(level="50000", Time=7)
            )

            acc_filepath = (
                f"{vs_config.DIR_OUTPUT_DATA}/date_multiple_time_window_{time_window}/"
                f"{multi_time_metric}_date_from_{vs_config.DATE_INIT}_to_"
                f"{vs_config.DATE_FINAL}_time_window_{time_window}.nc"
            )

            ds_acc.to_netcdf(acc_filepath)

def plot_mean_metrics_for_all_dates_and_each_time_window():
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print (f"\n Time window: {time_window}")
        plot_mean_metrics(time_window=time_window)

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
            if vs_config.SEL_VERBOSE_LEVEL >= 1:
                print ("domain:", domain)
            for var in vs_config.VARIABLES_TO_ANALYZE:
                if vs_config.SEL_VERBOSE_LEVEL >= 1:
                    print ("variable:", var)
                for level in vs_config.VERTICAL_LEVELS_TO_ANALYZE:
                    if vs_config.SEL_VERBOSE_LEVEL >= 1:
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
def generate_lat_pressure_profile_plots_for_all_dates_and_each_time_window():
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        if vs_config.SEL_VERBOSE_LEVEL >= 1:
            print(f"\n Time window: {time_window}")
        generate_lat_pressure_profile_plots(time_window=time_window)

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

    # Get metrics for lat-pressure profile plots; if no specific metrics for that were given
    # in vertical_structure_config, then get those from STATS_METRICS_TO_ANALYZE
    metrics_to_plot = getattr(
        vs_config,
        "LAT_PRESSURE_PROFILE_METRICS_TO_PLOT",
        vs_config.STATS_METRICS_TO_ANALYZE,
    )
    # Get variables for lat-pressure profile plots; if no specific variables for that were given
    # in vertical_structure_config, then get those from STATS_METRICS_TO_ANALYZE
    variables_to_plot = getattr(
        vs_config,
        "LAT_PRESSURE_PROFILE_VARIABLES_TO_PLOT",
        vs_config.VARIABLES_TO_ANALYZE,
    )
    # Get domains for lat-pressure profile plots; if no specific domains for that were given
    # in vertical_structure_config, then get those from DOMAINS_TO_ANALYZE
    domains_to_plot = getattr(
        vs_config,
        "LAT_PRESSURE_PROFILE_DOMAINS_TO_PLOT",
        vs_config.DOMAINS_TO_ANALYZE,
    )
    # Get levels for lat-pressure profile plots; if no specific levels for that were given
    # in vertical_structure_config, then get those from VERTICAL_LEVELS_TO_ANALYZE
    levels_to_plot = getattr(
        vs_config,
        "LAT_PRESSURE_PROFILE_LEVELS_TO_PLOT",
        vs_config.VERTICAL_LEVELS_TO_ANALYZE,
    )

    # Get metrics filepaths
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

        # Read metric dataset
        ds_metric = xr.open_dataset(metric_filepath, engine="netcdf4")

        # Loop over domains, variables, and levels to generate latitude-pressure profile plots
        for domain in domains_to_plot:
            ds_domain = preprocess.subset_region(ds_metric, domain)

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
                if vs_config.SEL_VERBOSE_LEVEL >= 1:
                    print(f"Latitude-pressure profile saved: {output_filepath}")

def get_profile_scale(var):
    """
    Get scale factor and unit label for latitude-pressure profile plots
    """
    scale_config = getattr(vs_config, "LAT_PRESSURE_PROFILE_SCALE_BY_VAR", {})

    if var not in scale_config:
        return 1.0, None

    factor = scale_config[var].get("factor", 1.0)
    unit_label = scale_config[var].get("unit_label", None)

    return factor, unit_label

def get_lat_pressure_profile_limits(var, metric):
    """
    Get fixed colorbar limits for latitude-pressure profile plots based on variable and metric
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
    lat_name, lon_name = utils.get_lat_lon_names(da)

    mean_dims = [lon_name]

    if "Time" in da.dims:
        mean_dims.append("Time")

    da_profile = da.mean(dim=mean_dims, skipna=True)

    return da_profile
#===================================================================================================
