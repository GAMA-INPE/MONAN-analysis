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
import vertical_analysis_aux as va_aux

if __name__ == "__main__":
    #===============================================================================================
    # Initialization: create folder structure if necessary
    #===============================================================================================
    print ("\n Initializing folder structure if not already existent...")
    va_aux.create_folder_structure()

    #===============================================================================================
    # Read and preprocess MONAN data 
    #===============================================================================================
    print ("\n Reading and selecting MONAN data...")
    ds_monan_selected_filepath = va_aux.read_and_preprocess_monan_data()

    #===============================================================================================
    # Read and preprocess GFS analysis data
    #===============================================================================================
    print ("\n Reading and selecting GFS data, and converting it to MONAN data format...")
    ds_gfs_in_monan_format_filepath = va_aux.read_and_preprocess_gfs_data()

    #===============================================================================================
    # Map MONAN data to GFS grid
    #===============================================================================================
    print ("\n Mapping MONAN data to GFS grid for comparison...")
    ds_monan_mapped_to_gfs_filepath = va_aux.map_monan_to_gfs_grid(
        ds_monan_selected_filepath=ds_monan_selected_filepath,
        ds_gfs_in_monan_format_filepath=ds_gfs_in_monan_format_filepath
        )

    #===============================================================================================
    # Calculate statistics
    #===============================================================================================
    print ("\n Calculating statistics...")
    ds_stats_filepath_dict = va_aux.calculate_statistics(
        ds_ref_filepath=ds_gfs_in_monan_format_filepath,
        ds_prediction_filepath=ds_monan_mapped_to_gfs_filepath
        )

    #===============================================================================================
    # Plot statistics
    #===============================================================================================
    print ("\n Plotting statistics...")
    va_aux.plot_statistics(ds_stats_filepath_dict=ds_stats_filepath_dict)
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