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
import monan_analysis.stats as stats
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os

def example_function_plots():
    print ("this is a function imported from the plots.py module.")

def plot_var_map(ds, var, cartopy_data_dir, level=None, Time=None, 
                 domain="global", output_filepath=None, verbose='y',
                 cmap_dict=None,metric_name=None):
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
            if verbose == 'y':
                print("'level' in data coords, but no value given. Choosing 'level' index 0")
            ds_subset = ds_subset.isel(level=0)
            level="N/A"
        else:
            if verbose == 'y':
                print(f"'level' in data coords, and input value given. Choosing 'level'={level}")
            ds_subset = ds_subset.sel(level=int(level))
            level=int(level)
    else:
        if verbose == 'y':
            print ("'level' coordinate not found in dataset. Proceeding without 'level' selection.")
        level="N/A"
    # Handle time selection
    if "Time" in ds_subset.sizes:
        if Time is None:
            if verbose == 'y':
                print("'Time' in data coords, but no value given. Choosing 'Time' index 0")
            ds_subset = ds_subset.isel(Time=0)
        else:
            if verbose == 'y':
                print(f"'Time' in data coords, and input value given. Choosing 'Time'={Time}")
            ds_subset = ds_subset.sel(Time=int(Time))
    else:
        if verbose == 'y':
            print("'Time' coordinate not found in dataset. Proceeding without 'Time' selection.")

    # Extract the variable data
    data = ds_subset[var]

    # Choose colormap based on variable, if cmap_dict provided
    if cmap_dict is not None and var in cmap_dict:
        cmap = cmap_dict[var]
    else:
        cmap = "viridis"
    
    # Plot map within the specified domain
    plt.figure(figsize=(10, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_range[0], lon_range[1], lat_range[0], lat_range[1]], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    # Convert reduced xarray values to Python scalars before scalar comparisons
    data_min = data.min().item()
    data_max = data.max().item()
    # Determine the maximum absolute value for symmetric colorbar
    max_abs_value = max(abs(data_min), abs(data_max))
    # Check if data contains both positive and negative values
    if data_min < 0 and data_max > 0:
        if verbose == 'y':
            print ("Data contains both positive and negative values. Setting symmetric colorbar limits.")
        vmin, vmax = -max_abs_value, max_abs_value
    # If only positive or only negative values exist, Matplotlib chooses the scale
    else:
        if verbose == 'y':
            print ("Data contains only positive or only negative values. Using default colorbar limits.")
        vmin, vmax = None, None
    # Use pcolormesh for raw data plotting (no interpolation)
    mesh = ax.pcolormesh(data.longitude, data.latitude, data, transform=ccrs.PlateCarree(), 
                         cmap=cmap, vmin=vmin, vmax=vmax)

    def _coerce_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_numeric_level(level_value, data_array):
        numeric_level = _coerce_float(level_value)
        if numeric_level is not None:
            return numeric_level, "Pa"

        coords = getattr(data_array, "coords", {})
        for coord_name, unit in (
            ("level", "Pa"),
            ("lev", "Pa"),
            ("pressure", "hPa"),
            ("isobaricInPa", "Pa"),
            ("isobaricInhPa", "hPa"),
        ):
            if coord_name in coords:
                coord = coords[coord_name]
                coord_values = getattr(coord, "values", coord)
                if getattr(coord_values, "size", 1) == 0:
                    continue
                if getattr(coord_values, "shape", ()) == ():
                    candidate = coord_values.item() if hasattr(coord_values, "item") else coord_values
                else:
                    candidate = coord_values.flat[0] if hasattr(coord_values, "flat") else coord_values[0]
                numeric_level = _coerce_float(candidate)
                if numeric_level is not None:
                    return numeric_level, unit

        return None, None

    numeric_level, numeric_level_unit = _get_numeric_level(level, data)
    if numeric_level is not None:
        display_level = int(numeric_level / 100) if numeric_level_unit == "Pa" else int(numeric_level)
        level_label = f"{display_level} hPa"
    else:
        level_label = None

    # Define metric units
    metric_units = stats.get_stats_metric_units(var_units_dict=config.VAR_UNITS_DICT, var=var, metric=metric_name) if metric_name is not None else "N/A"
    plt.colorbar(mesh, label=f"{metric_name} [{metric_units}]" if metric_name is not None else f"{var} [{config.VAR_UNITS_DICT[var]}]")
    if metric_name is not None:
        title = f"{var} [{config.VAR_UNITS_DICT[var]}], {level_label}, {metric_name} [{metric_units}]" if level_label is not None else f"{var} [{config.VAR_UNITS_DICT[var]}], {metric_name} [{metric_units}]"
    else:
        title = f"{var}, {level_label}" if level_label is not None else f"{var}"
    plt.title(title)

    # Save figure
    if output_filepath is not None:
        figure_filepath = output_filepath
    else:
        ## If needed, create output directory
        os.makedirs("output", exist_ok=True)
        figure_filepath = f"output/map_var_{var}_level_{level}_domain_{domain}.png"
    plt.savefig(figure_filepath)

