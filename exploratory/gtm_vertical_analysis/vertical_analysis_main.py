# -*- coding: utf-8 -*-
"""
vertical_analysis_main.py

Based on a script by Andre Lyra (andre.lyra@inpe.br)
Last update: Feb 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last update: Mar 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)

Description
-----------
Takes in data from MONAN and from GFS and performs an analysis of the vertical structure of MONAN.

Steps:
1. Read data from MONAN and from GFS
2. Preprocess data
3. Calculate statistics
4. Plot and save results

Input
-----
- ds_monan (xr.Dataset): netcdf file containing MONAN data
- ds_gfs (xr.Dataset): netcdf file containing GFS data

Output
------
- Analysis maps
- RMSE values

Main variables
--------------
- RMSE (float64): root mean square error

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot. 
"""
import monan_analysis
import monan_analysis.plots as plots
import monan_analysis.io as io
import monan_analysis.config as config
import monan_analysis.preprocess as preprocess
import monan_analysis.utils as utils
import vertical_analysis_config as va_config
import subprocess
import os
import xarray as xr

if __name__ == "__main__":
    #===============================================================================================
    # Read and preprocess MONAN data 
    #===============================================================================================
    print ("\n Reading MONAN data...")
    ds_monan, monan_filepath = io.read_ds_monan(
        year=va_config.YEAR,
        month=va_config.MONTH,
        day=va_config.DAY,
        hour=va_config.HOUR,
        time_window=va_config.TIME_WINDOW,
        grid_spec=va_config.GRID_SPEC,
        vertical_level_spec=va_config.VERTICAL_LEVEL_SPEC,
        base_dir=va_config.DIR_MONAN_PREOP,
        verbose='n'
        )
    # Select only data to be used for analysis
    ds_monan_selected = ds_monan[va_config.VARIABLES_TO_ANALYZE].sel(level=va_config.VERTICAL_LEVELS_TO_ANALYZE)
    # Save preprocessed GFS dataset
    ds_monan_selected_filepath = f"{va_config.DIR_INPUT_INTERMEDIATE}/monan_selected_variables_and_levels.nc"
    ds_monan_selected.to_netcdf(ds_monan_selected_filepath)
    # If needed, print preprocessed dataset
    if va_config.SEL_VERBOSE_ANALYSIS_STEPS == "y":
        print ("MONAN dataset with selected variables and levels:")
        print (ds_monan_selected)

    #===============================================================================================
    # If needed, plot initial MONAN maps for each domain, variable and level
    #===============================================================================================
    if va_config.SEL_INITIAL_MONAN_MAPS == "y":
        print ("\n initial MONAN plots...")
        for domain in va_config.DOMAINS_TO_ANALYZE:
            print ("domain:", domain)
            for var in va_config.VARIABLES_TO_ANALYZE:
                print ("variable:", var)
                for level in va_config.VERTICAL_LEVELS_TO_ANALYZE:
                    print ("level:", level)
                    plots.plot_var_map(
                        ds=ds_monan, 
                        var=var, 
                        cartopy_data_dir=va_config.DIR_CARTOPY_DATA,
                        level=level, 
                        domain=domain
                        )

    #===============================================================================================
    # Read and preprocess analysis data from GFS 
    #===============================================================================================
    # Read GFS analysis dataset
    print ("\n Reading and preprocessing GFS data...")
    ds_gfs, gfs_filepath = io.read_ds_gfs(
        year=va_config.YEAR,
        month=va_config.MONTH,
        day=va_config.DAY,
        hour=va_config.HOUR,
        base_dir=va_config.DIR_GFS_ANALYSIS,
        stream_name=va_config.GFS_STREAM_NAME,
        verbose='n'
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
    if va_config.SEL_VERBOSE_ANALYSIS_STEPS == "y":
        print ("GFS dataset in MONAN data format:")
        print (ds_gfs_in_monan_format)

    #===============================================================================================
    # Map MONAN data to GFS grid
    #===============================================================================================
    print ("\n Mapping MONAN data to GFS grid...")
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
    if va_config.SEL_VERBOSE_ANALYSIS_STEPS == "y":
        print ("MONAN data mapped to GFS grid:")
        print (ds_monan_mapped_to_gfs)

    # plots.plot_var_map(
    #                 ds=ds_monan_processed, 
    #                 var="temperature", 
    #                 cartopy_data_dir=va_config.CARTOPY_DATA_DIR,
    #                 level="92500", 
    #                 domain="global",
    #                 output_filename="monan_processed"
    #                 )

    # #======================
    # # Calculate statistics
    # #======================
    # # Remap MONAN data to GFS grid       
    

    # #==============
    # # Plot results
    # #==============

    # #============================
    # # Copy config files
    # #============================
    # # Analysis-specific config file
    # subprocess.run(["cp", "vertical_analysis_config.py", va_config.DIR_OUTPUT], check=True)
    # # General config file
    # ## Get absolute path to monan_analysis package
    # gen_config_package_dir = os.path.dirname(monan_analysis.__file__)
    # ## Construct path to general config.py file
    # gen_config_file_path = os.path.join(gen_config_package_dir, "config.py")
    # ## Copy general config file
    # subprocess.run(["cp", gen_config_file_path, va_config.DIR_OUTPUT], check=True)