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
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
import os

def example_function_plots():
    print ("this is a function imported from the plots.py module.")

def plot_var_map(ds, var, cartopy_data_dir, level=None, Time=None, 
                 domain="global", output_filepath=None, verbose='y',
                 cmap_dict=None,metric_name=None, time_window=None,
                 vmin=None, vmax=None, unit_label=None):
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
            level = ds_subset["level"].values.item()
            level_label = f"{int(float(level)/100)} hPa,"
        else:
            if verbose == 'y':
                print(f"'level' in data coords, and input value given. Choosing 'level'={level}")
            ds_subset = ds_subset.sel(level=int(level))
            level=int(level)
            level_label = f"{int(float(level)/100)} hPa,"
    else:
        if verbose == 'y':
            print ("'level' coordinate not found in dataset. Proceeding without 'level' selection.")
        level=None
        level_label = ""
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

    # Calculate area-weighted domain mean
    latitude_weights = np.cos(np.deg2rad(data["latitude"]))

    domain_mean = (
        data.weighted(latitude_weights)
        .mean(dim=("latitude", "longitude"), skipna=True)
        .item()
    )

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
    # Use fixed limits when provided by the calling function.
    # Otherwise, keep the previous automatic behavior.
    if vmin is not None and vmax is not None:
        if verbose == 'y':
            print(f"Using fixed colorbar limits: vmin={vmin}, vmax={vmax}")
    else:
        # Determine the maximum absolute value for symmetric colorbar
        max_abs_value = max(abs(data_min), abs(data_max))
        # Check if data contains both positive and negative values
        if data_min < 0 and data_max > 0:
            if verbose == 'y':
                print("Data contains both positive and negative values. Setting symmetric colorbar limits.")
            vmin, vmax = -max_abs_value, max_abs_value
        # If only positive or only negative values exist, Matplotlib chooses the scale
        else:
            if verbose == 'y':
                print("Data contains only positive or only negative values. Using default colorbar limits.")
            vmin, vmax = None, None
            
    # Use pcolormesh for raw data plotting (no interpolation)
    mesh = ax.pcolormesh(data.longitude, data.latitude, data, transform=ccrs.PlateCarree(), 
                         cmap=cmap, vmin=vmin, vmax=vmax)

    # Define metric units
    if unit_label is not None:
        metric_units = unit_label
    else:
        metric_units = (
            stats.get_stats_metric_units(
                var_units_dict=config.VAR_UNITS_DICT,
                var=var,
                metric=metric_name
            )
            if metric_name is not None
            else config.VAR_UNITS_DICT[var]
        )

    cbar_label = (
        f"{metric_name} [{metric_units}]"
        if metric_name is not None
        else f"{var} [{metric_units}]"
    )

    cbar = plt.colorbar(mesh, label=cbar_label)
    cbar.set_label(cbar_label, fontsize=14)
    cbar.ax.tick_params(labelsize=12)
    
    time_window_label = (
        f"lead {int(time_window):03d} h"
        if time_window is not None
        else ""
    )

    mean_label = f"mean = {domain_mean:.2f} {metric_units}"
    
    plt.title(
        (
            f"{var}, {level_label} {metric_name} [{metric_units}], {time_window_label}\n{mean_label}"
            if metric_name is not None
            else f"{var} [{metric_units}], {level_label}{time_window_label}\n{mean_label}"
        ),
        fontsize=14,
    )

    # Save figure
    if output_filepath is not None:
        figure_filepath = output_filepath
    else:
        ## If needed, create output directory
        os.makedirs("output", exist_ok=True)
        figure_filepath = f"output/map_var_{var}_level_{level}_domain_{domain}.png"
    plt.savefig(figure_filepath)
    plt.close()

def plot_lat_pressure_profile(
    da_profile,
    output_filepath=None,
    var_label=None,
    metric_label=None,
    unit_label=None,
    cmap="coolwarm",
    vmin=None,
    vmax=None,
    title=None,
    subtitle=None,
    xlabel="Latitude",
    ylabel="Pressure level (hPa)",
):
    """
    Plot a latitude-pressure section from a DataArray.

    Expected input:
    da_profile: xarray.DataArray with latitude and level dimensions.

    Notes:
    This function only plots the provided DataArray.
    Any filtering by domain, variable, metric, time window or date period
    should be done before calling this function.
    """

    if "latitude" in da_profile.coords or "latitude" in da_profile.dims:
        lat_name = "latitude"
    elif "lat" in da_profile.coords or "lat" in da_profile.dims:
        lat_name = "lat"
    else:
        raise ValueError("Could not identify latitude coordinate in da_profile.")

    if "level" not in da_profile.coords and "level" not in da_profile.dims:
        raise ValueError("Could not identify level coordinate in da_profile.")

    pressure_hpa = da_profile["level"].values.astype(float) / 100.0
    latitude = da_profile[lat_name].values

    if da_profile.dims[0] == lat_name:
        data_values = da_profile.values.T
    else:
        data_values = da_profile.values

    fig, ax = plt.subplots(figsize=(11, 6))

    if vmin is not None and vmax is not None:
        contour_levels = np.linspace(vmin, vmax, 21)
    else:
        contour_levels = 21

    contour = ax.contourf(
        latitude,
        pressure_hpa,
        data_values,
        levels=contour_levels,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        extend="both",
    )

    ax.set_yscale("log")
    ax.invert_yaxis()

    pressure_ticks = pressure_hpa.tolist()

    ax.yaxis.set_major_locator(mticker.FixedLocator(pressure_ticks))
    ax.yaxis.set_major_formatter(
        mticker.FixedFormatter([f"{p:g}" for p in pressure_ticks])
    )

    # Remove completely the automatic minor ticks from the log scale
    ax.yaxis.set_minor_locator(mticker.NullLocator())
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    if title is None:
        title_parts = []

        if var_label is not None and metric_label is not None:
            if unit_label is not None:
                title_parts.append(f"{var_label}, {metric_label} [{unit_label}]")
            else:
                title_parts.append(f"{var_label}, {metric_label}")
        elif var_label is not None:
            if unit_label is not None:
                title_parts.append(f"{var_label} [{unit_label}]")
            else:
                title_parts.append(f"{var_label}")
        elif metric_label is not None:
            if unit_label is not None:
                title_parts.append(f"{metric_label} [{unit_label}]")
            else:
                title_parts.append(f"{metric_label}")

        if subtitle is not None:
            title_parts.append(subtitle)

        if title_parts:
            title = "\n".join(title_parts)

    if title is not None:
        ax.set_title(title, fontsize=14)

    if metric_label is not None and unit_label is not None:
        cbar_label = f"{metric_label} [{unit_label}]"
    elif metric_label is not None:
        cbar_label = metric_label
    elif unit_label is not None:
        cbar_label = unit_label
    else:
        cbar_label = ""

    cbar = fig.colorbar(contour, ax=ax, pad=0.02)

    if cbar_label:
        cbar.set_label(cbar_label, fontsize=14)

    cbar.ax.tick_params(labelsize=12)

    ax.grid(True, linestyle=":", linewidth=0.5)

    if output_filepath is not None:
        figure_filepath = output_filepath

        output_dir = os.path.dirname(figure_filepath)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
    else:
        os.makedirs("output", exist_ok=True)
        figure_filepath = "output/lat_pressure_profile.png"

    plt.savefig(figure_filepath, bbox_inches="tight")
    plt.close(fig)
