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

import monan_analysis.plots as plots
import vertical_analysis_aux as va_aux
import vertical_analysis_config as va_config

if __name__ == "__main__":
    #=============================
    # Read output data from MONAN 
    #=============================
    ds_monan = va_aux.read_ds_monan(verbose='n')

    #===============================================
    # Plot maps for each domain, variable and level
    #===============================================
    print ("initial plots...")
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
            #print (var, lev)

    # Preprocess MONAN data
    #var='temperature'
    #ds_monan_preprocessed = va_aux.preprocess_monan_data(ds_monan)

    # Plot MONAN data
    #ds = xr.open_dataset("/lustre/projetos/monan_atm/guilherme.mendonca/scratch/output2.nc", engine="netcdf4")
    #print (ds)
    #plt.figure(figsize=(10, 6))

    

    # # Extract data
    # temperature = ds['temperature'].squeeze()  # Remove single-dimensional entries (e.g., Time, lon)
    # levels = ds['level']
    # print (levels)
    # latitudes = ds['lat']
    # print (latitudes)

    # # Create the plot
    # plt.figure(figsize=(10, 6))
    # contour = plt.contourf(latitudes, levels, temperature, levels=18, cmap='coolwarm')

    # # Invert the y-axis so pressure levels decrease upward
    # plt.gca().invert_yaxis()

    # # Add labels and title
    # plt.xlabel('Latitude')
    # plt.ylabel('Pressure Level (hPa)')
    # plt.title('Zonal Mean Temperature')
    # plt.colorbar(contour, label='Temperature (K)')

    # # Show the plot
    # plt.show()
    # plt.savefig('zonal_mean_temperature.png', dpi=300, bbox_inches='tight')  # Save as PNG with high resolution
    # plt.close()
