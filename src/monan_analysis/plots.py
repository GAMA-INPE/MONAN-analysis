# -*- coding: utf-8 -*-
"""
plots.py

Description
-----------
This module contains various functions for plotting results from analyses.

Usage
-----
- Import this module in scripts that require plot functions.
- Functions in this module should be general-purpose and reusable across different analyses.

Examples:
- from monan_analysis.plots import example_function_plots
or 
- import monan_analysis.plots as plots
  filename = plots.example_function_plots()

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot. 
"""

import monan_analysis.config as config
import monan_analysis.utils as utils
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
from cartopy.util import add_cyclic_point

def example_function_plots():
    print ("this is a function imported from the plots.py module.")

def plot_var_map(ds, var, cartopy_data_dir, level=None, Time=None, 
                 domain="global", output_filepath=None):
    """Plot map of a variable at a given level and domain."""
    # Set the Cartopy data directory
    os.environ["CARTOPY_USER_DATA_DIR"] = cartopy_data_dir
    
    # Select domain
    lat_range = config.DOMAIN_DICT[domain]["lat"]
    lon_range = config.DOMAIN_DICT[domain]["lon"]     

     # Treat edge case where global domain is defined as 0 to 360 longitude (same point in cartopy)
    if lon_range == (0,360):
        lon_range = (0,359.9999)

    # Subset the dataset to the specified domain
    ds_subset = ds.sel(latitude=slice(*lat_range), longitude=slice(*lon_range))

    # Handle level selection
    if "level" in ds_subset.sizes:
        if level is None:
            print("'level' in data coords, but no value given. Choosing 'level' index 0")
            ds_subset = ds_subset.isel(level=0)
        else:
            print(f"'level' in data coords, and input value given. Choosing 'level'={level}")
            ds_subset = ds_subset.sel(level=int(level))

    # Handle time selection
    if "Time" in ds_subset.sizes:
        if Time is None:
            print("'Time' in data coords, but no value given. Choosing 'Time' index 0")
            ds_subset = ds_subset.isel(Time=0)
        else:
            print(f"'Time' in data coords, and input value given. Choosing 'Time'={Time}")
            ds_subset = ds_subset.sel(Time=int(Time))
    else:
        raise ValueError("'Time' coordinate not found in dataset. Cannot select time step for plotting.")

    # Extract the variable data
    data = ds_subset[var]
    print("data:")
    print(data)

    # Choose colormap based on variable
    if "temp" in var.lower():  # For temperature variables
        cmap = "coolwarm"  # Red for high, blue for low
    else:
        cmap = "viridis"  # Default colormap

    # Plot map within the specified domain
    plt.figure(figsize=(10, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_range[0], lon_range[1], lat_range[0], lat_range[1]], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    # Use pcolormesh for raw data plotting (no interpolation)
    mesh = ax.pcolormesh(data.longitude, data.latitude, data, transform=ccrs.PlateCarree(), cmap=cmap)
    plt.colorbar(mesh, label=var)
    plt.title(f"{var}")
    plt.show()

    # Save figure
    if output_filepath is not None:
        figure_filepath = output_filepath
    else:
        ## If needed, create output directory
        os.makedirs("output", exist_ok=True)
        figure_filepath = f"output/map_var_{var}_level_{level}_domain_{domain}.png"
    plt.savefig(figure_filepath)

