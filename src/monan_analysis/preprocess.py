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

def remap_grid_with_cdo(ref_nc, input_nc, output_nc):
    """ 
    Remap input_nc to the grid of ref_nc 
    and save the output in output_nc using CDO.
    """
    if not os.path.exists(output_nc):
        subprocess.run(
            ["cdo", "-f", "nc", f"-remapcon,{ref_nc}", input_nc, output_nc],
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
    
    # Rename variables using the mapping dictionary
    ds_gfs_in_monan_format = ds_gfs.rename(gfs_to_monan_var_dict)
    
    return ds_gfs_in_monan_format