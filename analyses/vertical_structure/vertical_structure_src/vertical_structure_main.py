# -*- coding: utf-8 -*-
"""
vertical_structure_main.py

Based on a script by Andre Lyra (andre.lyra@inpe.br)
Last update: Feb 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last update: Mar 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last update: May 2026 by Andre Lyra (andre.lyra@inpe.br) - topography masking of pressure levels


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
- ds_monan_sp (xr.Dataset): netcdf file containing MONAN data
- ds_gfs (xr.Dataset): netCDF file containing GFS pressure-level data
- ds_gfs_sp (xr.Dataset): netCDF file containing GFS surface pressure

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
from . import vertical_structure_aux as vs_aux
from . import vertical_structure_config as vs_config

def main():
    #===============================================================================================
    # Initialization: create folder structure if necessary
    #===============================================================================================
    print ("\n Initializing folder structure if not already existent...")
    vs_aux.create_folder_structure()

    #===============================================================================================
    # Read and preprocess MONAN data 
    #===============================================================================================
    print ("\n Reading and selecting MONAN data...")
    #ds_monan_selected_filepath, ds_monan_sp_filepath = vs_aux.read_and_preprocess_monan_data()
    ds_monan_selected_filepath, ds_monan_sp_filepath = vs_aux.read_and_preprocess_monan_data(
        read_surface_pressure=vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK
    )
    #===============================================================================================
    # Read and preprocess GFS analysis data
    #===============================================================================================
    print ("\n Reading and selecting GFS data, and converting it to MONAN data format...")
    ds_gfs_in_monan_format_filepath = vs_aux.read_and_preprocess_gfs_data()

    #===============================================================================================
    # Read and preprocess GFS surface pressure data
    #===============================================================================================
    if vs_config.APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        print ("\n Reading and selecting GFS surface pressure data...")
        ds_gfs_sp_filepath = vs_aux.read_and_preprocess_gfs_surface_pressure_data()
    else:
        ds_gfs_sp_filepath = None

    #===============================================================================================
    # Interpolate MONAN / GFS data for comparability
    #===============================================================================================
    print ("\n Interpolating MONAN / GFS data for comparability...")
    ds_ref_filepath, ds_prediction_filepath = vs_aux.interpolate_monan_gfs(
        ds_monan_selected_filepath=ds_monan_selected_filepath,
        ds_gfs_in_monan_format_filepath=ds_gfs_in_monan_format_filepath
        )

    #===============================================================================================
    # Calculate statistics
    #===============================================================================================
    print ("\n Calculating statistics...")
    ds_stats_filepath_dict = vs_aux.calculate_statistics(
        ds_ref_filepath=ds_ref_filepath,
        ds_prediction_filepath=ds_prediction_filepath,
        ds_gfs_sp_filepath=ds_gfs_sp_filepath,
        ds_monan_sp_filepath=ds_monan_sp_filepath   
    )

    #===============================================================================================
    # Plot statistics
    #===============================================================================================
    print ("\n Plotting statistics...")
    vs_aux.plot_statistics(ds_stats_filepath_dict=ds_stats_filepath_dict)
    
    #============================
    # Copy config files
    #============================
    print ("\n Copying config files...")
    vs_aux.cp_config_files()
    print("\n Done.")

if __name__ == "__main__":
    main()