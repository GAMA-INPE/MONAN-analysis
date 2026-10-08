#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.feature as cfeature
import cartopy.crs as ccrs

# dir for era5 climatology dataset
era5_dir = '/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/hourly/nc'
# Read dataset
ds_climatology = xr.open_dataset(f"{era5_dir}/climatology_N_half_10_hour_UTC_0_1991_2020.nc")
# # Rename coords and dimensions to MONAN format
# ERA5_TO_MONAN_VAR_DICT = {
#     "lat": "latitude",
#     "lon": "longitude",
#     "plev": "level"
# }
# ds_climatology = ds_climatology.rename(ERA5_TO_MONAN_VAR_DICT, errors="raise")
# Convert latitude and longitude to match predictions dataset
ds_climatology = ds_climatology.sortby('latitude')

ds_climatology = ds_climatology.assign_coords(
    latitude=ds_climatology["latitude"].astype("float32"),
    longitude=(((ds_climatology["longitude"] + 180) % 360).astype("float32"))
)
# Save dataset (overwrite)
ds_climatology.to_netcdf(f"{era5_dir}/climatology_N_half_10_hour_UTC_0_1991_2020_converted.nc")