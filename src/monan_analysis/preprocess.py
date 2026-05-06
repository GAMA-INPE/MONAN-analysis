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


def map_data_to_different_grid_with_cdo(ref_nc, input_nc, output_nc):
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
        f"cdo -f nc -remapcon,{ref_nc} {input_nc} {output_nc}"
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

def rename_horizontal_dims_to_match_ref(data, ref):
    """
    Rename horizontal dimensions in a Dataset or DataArray to match a reference object.

    This function standardizes common latitude and longitude dimension names
    between two xarray objects, for example lat/lon and latitude/longitude.

    Parameters
    ----------
    data : xarray.Dataset or xarray.DataArray
        Input object whose horizontal dimensions will be renamed.
    ref : xarray.Dataset or xarray.DataArray
        Reference object that defines the target horizontal dimension names.

    Returns
    -------
    xarray.Dataset or xarray.DataArray
        Object with horizontal dimensions renamed to match the reference object.
    """

    lat_ref = None
    lon_ref = None

    if "lat" in ref.dims:
        lat_ref = "lat"
    elif "latitude" in ref.dims:
        lat_ref = "latitude"

    if "lon" in ref.dims:
        lon_ref = "lon"
    elif "longitude" in ref.dims:
        lon_ref = "longitude"

    rename_dims = {}

    if lat_ref is not None:
        if "lat" in data.dims and lat_ref != "lat":
            rename_dims["lat"] = lat_ref
        elif "latitude" in data.dims and lat_ref != "latitude":
            rename_dims["latitude"] = lat_ref

    if lon_ref is not None:
        if "lon" in data.dims and lon_ref != "lon":
            rename_dims["lon"] = lon_ref
        elif "longitude" in data.dims and lon_ref != "longitude":
            rename_dims["longitude"] = lon_ref

    if rename_dims:
        data = data.rename(rename_dims)

    return data