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
import monan_analysis.utils as utils
import vertical_analysis_aux as va_aux
import vertical_analysis_config as va_config
import subprocess
import os
import xarray as xr

if __name__ == "__main__":
    #=============================
    # Read output data from MONAN 
    #=============================
    ds_monan, monan_filepath = va_aux.read_ds_monan(verbose='y')

    #=============================================================
    # Plot initial MONAN maps for each domain, variable and level
    #=============================================================
    print ("initial map plots...")
    for domain in va_config.DOMAINS_TO_ANALYZE:
        print ("domain:", domain)
        for var in va_config.VARIABLES_TO_ANALYZE:
            print ("variable:", var)
            for level in va_config.VERTICAL_LEVELS_TO_ANALYZE:
                print ("level:", level)
                plots.plot_var_map(
                    ds=ds_monan, 
                    var=var, 
                    cartopy_data_dir=va_config.CARTOPY_DATA_DIR,
                    level=level, 
                    domain=domain
                    )

    #=============================
    # Read analysis data from GFS 
    #=============================
    ds_gfs, gfs_filepath = va_aux.read_ds_gfs(verbose='y')
    print (ds_gfs)

    #===============================
    # Preprocess MONAN and GFS data
    #===============================
    # Remap MONAN data to GFS grid
    print ("Remapping MONAN data to GFS grid...")
    utils.remap_cdo(
        ref_nc=gfs_filepath,
        input_nc=monan_filepath, 
        output_nc=f"{va_config.INPUT_INTERMEDIATE_DIR}/monan_remapped.nc"
        )
    # Read remapped MONAN data
    ds_monan_processed = xr.open_dataset(f"{va_config.INPUT_INTERMEDIATE_DIR}/monan_remapped.nc", engine="netcdf4")
    print ("MONAN remapped:")
    print (ds_monan_processed)

    #======================
    # Calculate statistics
    #======================
    # Remap MONAN data to GFS grid       

    #==============
    # Plot results
    #==============

    #============================
    # Copy config files
    #============================
    # Analysis-specific config file
    subprocess.run(["cp", "vertical_analysis_config.py", va_config.OUTPUT_DIR], check=True)
    # General config file
    ## Get absolute path to monan_analysis package
    gen_config_package_dir = os.path.dirname(monan_analysis.__file__)
    ## Construct path to general config.py file
    gen_config_file_path = os.path.join(gen_config_package_dir, "config.py")
    ## Copy general config file
    subprocess.run(["cp", gen_config_file_path, va_config.OUTPUT_DIR], check=True)