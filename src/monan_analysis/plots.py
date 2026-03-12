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

def example_function_plots():
    print ("this is a function imported from the plots.py module.")

def plot_var_map(ds, var, cartopy_data_dir,level=None, domain="global"):
    """ Plot map of a variable at a given level and domain."""
    # Set the Cartopy data directory
    os.environ["CARTOPY_USER_DATA_DIR"] = cartopy_data_dir
    
    # Select domain
    lat_range = config.DOMAIN_DICT[domain]["lat"]
    lon_range = config.DOMAIN_DICT[domain]["lon"]

    # If needed, correct longitudinal range for cartopy plotting
    lon_range = utils.get_lon_from_minus_180_to_180(lon_range)

    # Subset the dataset to the specified domain
    ds_subset = ds.sel(latitude=slice(*lat_range), longitude=slice(*lon_range))

    # If a level is provided, subset the dataset to that level
    if level is not None:
        ds_subset = ds_subset.sel(level=int(level))

    # Extract the variable data
    data = ds_subset[var]

    plt.figure(figsize=(10, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_range[0], lon_range[1], lat_range[0], lat_range[1]], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    plt.contourf(data.longitude, data.latitude, data, transform=ccrs.PlateCarree(), cmap="viridis")
    plt.colorbar(label=var)
    plt.title(f"{var} Map")
    plt.show()
    plt.savefig("../../exploratory/gtm_vertical_analysis/plot.png")