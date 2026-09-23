# -*- coding: utf-8 -*-
"""
preprocess.py

Description
-----------
This module contains various functions for preprocessing data for analyses.

Usage
-----
- Import this module in scripts that require preprocessing data.
- Functions in this module should be general-purpose and reusable across different analyses.

Examples:
- from monan_analysis.preprocess import get_gfs_data_in_monan_format
or 
- import monan_analysis.preprocess as preprocess
  ds = preprocess.get_gfs_data_in_monan_format(ds_gfs, gfs_to_monan_var_dict)

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot. 
"""
import os
import subprocess
import xarray as xr
import monan_analysis.utils as utils
import monan_analysis.config as config
import numpy as np

def map_data_to_different_grid_with_cdo(ref_grid_nc, input_nc, output_nc):
    """ 
    Remap input_nc to the grid of ref_nc 
    and save the output in output_nc using CDO.
    """
    if os.path.exists(output_nc):
        print ("Mapped file already exists. Overwriting it...")

    # Run cdo command only for those vars and levels
    subprocess.run([
        "bash", "-l", "-c", 
        f"module load cdo && "
        f"cdo -f nc -remapcon,{ref_grid_nc} {input_nc} {output_nc}"
        ],
    check=True
    )

def get_gfs_data_in_monan_format(ds_gfs, gfs_to_monan_var_dict):
    """
    Maps a GFS dataset to the MONAN dataset format using the 
    provided variable mapping dictionary.

    Parameters:
    - ds_gfs: xarray.Dataset
        The input GFS dataset.
    - gfs_to_monan_var_dict: dict
        A dictionary mapping GFS variable names to MONAN variable names.

    Returns:
    - xarray.Dataset
        The dataset formatted to match the MONAN dataset structure.
    """
    # Sort by latitude
    ds_gfs = ds_gfs.sortby('latitude')
    # Convert GFS levels from hPa to Pa
    ds_gfs["level"] = (ds_gfs["level"] * 100).astype(float)
    ds_gfs["level"].attrs["units"] = "Pa"
    # Sort by level
    ds_gfs = ds_gfs.sortby('level', ascending=False)

    # Rename variables using the mapping dictionary
    ds_gfs_in_monan_format = ds_gfs.rename(gfs_to_monan_var_dict)

    return ds_gfs_in_monan_format

def apply_pressure_level_validity_mask(
    ds,
    pressure_level,
    surface_pressure_var="surface_pressure",
):
    """
    Build a pressure-level validity mask based on surface pressure.

    Grid points are valid where surface pressure is greater than or equal to
    the selected pressure level. Points where the selected pressure level is
    greater than surface pressure are invalid, because they correspond to
    pressure levels below the ground surface.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset containing the surface pressure field.
    pressure_level : xr.DataArray, int or float
        Pressure level or pressure-level coordinate used to build the validity mask.
    surface_pressure_var : str
        Name of the surface pressure variable.

    Returns
    -------
    xr.DataArray
        Boolean mask with True for valid pressure-level grid points.
    """
    if surface_pressure_var not in ds:
        raise ValueError(
            f"Surface pressure variable '{surface_pressure_var}' was not found "
            "in the dataset."
        )

    surface_pressure = ds[surface_pressure_var]

    if "Time" in surface_pressure.dims and surface_pressure.sizes["Time"] == 1:
        surface_pressure = surface_pressure.isel(Time=0)

    return surface_pressure >= pressure_level

def spatial_mean(da):
    lat_name, lon_name = utils.get_lat_lon_names(da)

    spatial_dims = [
        dim for dim in da.dims
        if dim not in ["Time", "level"]
    ]

    if lat_name in da.coords and lat_name in spatial_dims:
        weights = np.cos(np.deg2rad(da[lat_name]))
        return da.weighted(weights).mean(dim=spatial_dims, skipna=True)

    return da.mean(dim=spatial_dims, skipna=True)

def spatial_min(da):
    spatial_dims = [
        dim for dim in da.dims
        if dim not in ["Time", "level"]
    ]
    return da.min(dim=spatial_dims, skipna=True)

def spatial_max(da):
    spatial_dims = [
        dim for dim in da.dims
        if dim not in ["Time", "level"]
    ]
    return da.max(dim=spatial_dims, skipna=True)

def spatial_std(da):
    spatial_dims = [
        dim for dim in da.dims
        if dim not in ["Time", "level"]
    ]
    return da.std(dim=spatial_dims, skipna=True)

def subset_region(ds, region_name):
    region_limits = config.DOMAIN_DICT[region_name]

    lat_min, lat_max = region_limits["lat"]
    lon_min, lon_max = region_limits["lon"]

    lat_name, lon_name = utils.get_lat_lon_names(ds)

    ds_region = ds

    lat_values = ds_region[lat_name]
    if lat_values[0] > lat_values[-1]:
        ds_region = ds_region.sel({lat_name: slice(lat_max, lat_min)})
    else:
        ds_region = ds_region.sel({lat_name: slice(lat_min, lat_max)})

    lon_values = ds_region[lon_name]

    if float(lon_values.max()) > 180.0:
        ds_region = ds_region.sel({lon_name: slice(lon_min, lon_max)})
    else:
        lon_min_180 = ((lon_min + 180.0) % 360.0) - 180.0
        lon_max_180 = ((lon_max + 180.0) % 360.0) - 180.0

        if lon_min_180 <= lon_max_180:
            ds_region = ds_region.sel({lon_name: slice(lon_min_180, lon_max_180)})
        else:
            ds_region = xr.concat(
                [
                    ds_region.sel({lon_name: slice(lon_min_180, 180.0)}),
                    ds_region.sel({lon_name: slice(-180.0, lon_max_180)}),
                ],
                dim=lon_name,
            )

    return ds_region