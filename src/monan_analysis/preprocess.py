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
import numpy as np
import operator

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

# Define strings to operators for thresholding events
_EVENT_OPERATORS = {
    "ge": operator.ge,
    "gt": operator.gt,
    "le": operator.le,
    "lt": operator.lt,
}

def threshold_event(
    data,
    threshold,
    comparison="ge",
    valid_mask=None,
):
    """
    Convert a continuous field into a binary event field.

    Parameters
    ----------
    data : xarray.DataArray
        Continuous field to threshold.
    threshold : float or xarray.DataArray
        Threshold defining the event.
    comparison : {"ge", "gt", "le", "lt"}
        Comparison used to define the event.
    valid_mask : xarray.DataArray, optional
        Boolean mask defining valid points.

    Returns
    -------
    xarray.DataArray
        Event field containing 1, 0 and NaN.
    """

    if not isinstance(data, xr.DataArray):
        raise TypeError(
            "data must be an xarray.DataArray."
        )

    if comparison not in _EVENT_OPERATORS:
        raise ValueError(
            "comparison must be one of "
            "'ge', 'gt', 'le' or 'lt'."
        )

    if valid_mask is None:
        valid_mask = np.isfinite(data)

    operator_func = _EVENT_OPERATORS[comparison]

    event = operator_func(
        data,
        threshold,
    )

    return xr.where(
        valid_mask,
        event,
        np.nan,
    )