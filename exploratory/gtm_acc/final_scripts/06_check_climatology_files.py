#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.feature as cfeature
import cartopy.crs as ccrs

era5_dir = '/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/hourly/nc'

# Goal: compare zgeo fields for boundary days, one day in between for 
# 1) original era5 concatenated dataset
# 2) climatology with N_half = 1
# 3) climatology with N_half = 2

# Read datasets
ds_original = xr.open_dataset(f"{era5_dir}/concat_era5_hourly_pl_1991_2020.nc")
ds_climatology_N_half_1 = xr.open_dataset(f"{era5_dir}/climatology_N_half_1_hour_UTC_0_1991_2020.nc")
ds_climatology_N_half_10 = xr.open_dataset(f"{era5_dir}/climatology_N_half_10_hour_UTC_0_1991_2020.nc")

# print the datasets to check their contents
print (ds_original)
print (ds_climatology_N_half_1)
print (ds_climatology_N_half_10)

# First, for comparison, transform var129 to geopotential height (zgeo) using the formula: zgeo = var129 / 9.80665
# for original dataset
ds_original['zgeo'] = ds_original['var129'] / 9.80665

# choose three dates for plotting the field zgeo for each dataset
## original file dates
date_original_jan = '1991-01-01'
date_original_jun = '1994-06-17'
date_original_dec = '2020-12-31'
## climatology dates (only 1991)
date_climatology_jan = 1
date_climatology_jun = 168
date_climatology_dec = 365

# plot fields separately and also difference for each date
# Extract var129 at 500 hPa for the specified dates
level_500 = 50000  # Pressure level in hPa

# Function to plot a single map
def plot_map(data, title, ax, vmin=4600, vmax=6000):
    ax.set_global()
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, edgecolor='black', facecolor='lightgray')
    im = ax.contourf(data.lon, data.lat, data, transform=ccrs.PlateCarree(), cmap='coolwarm')
    # set scale colorbar
    im.set_clim(vmin, vmax)
    plt.colorbar(im, ax=ax, orientation='horizontal', pad=0.05)
    ax.set_title(title)

# Create subplots for each date and dataset
fig, axes = plt.subplots(3, 3, figsize=(18, 12), subplot_kw={'projection': ccrs.PlateCarree()})

# january dates
# Extract data
var1_jan = ds_original['zgeo'].sel(plev=level_500, time=date_original_jan)
var2_jan = ds_climatology_N_half_1['zgeo'].sel(plev=level_500, dayofyear=date_climatology_jan)
var3_jan = ds_climatology_N_half_10['zgeo'].sel(plev=level_500, dayofyear=date_climatology_jan)
# Plot all maps
plot_map(var1_jan, f"ds_original: {date_original_jan}", axes[0, 0])
plot_map(var2_jan, f"ds_climatology_N_half_1: {date_climatology_jan}", axes[0, 1])
plot_map(var3_jan, f"ds_climatology_N_half_10: {date_climatology_jan}", axes[0, 2])

# june dates
# Extract data
var1_jun = ds_original['zgeo'].sel(plev=level_500, time=date_original_jun)
var2_jun = ds_climatology_N_half_1['zgeo'].sel(plev=level_500, dayofyear=date_climatology_jun)
var3_jun = ds_climatology_N_half_10['zgeo'].sel(plev=level_500, dayofyear=date_climatology_jun)
# Plot all maps
plot_map(var1_jun, f"ds_original: {date_original_jun}", axes[1, 0])
plot_map(var2_jun, f"ds_climatology_N_half_1: {date_climatology_jun}", axes[1, 1])
plot_map(var3_jun, f"ds_climatology_N_half_10: {date_climatology_jun}", axes[1, 2])

# december dates
# Extract data
var1_dec = ds_original['zgeo'].sel(plev=level_500, time=date_original_dec)
var2_dec = ds_climatology_N_half_1['zgeo'].sel(plev=level_500, dayofyear=date_climatology_dec)
var3_dec = ds_climatology_N_half_10['zgeo'].sel(plev=level_500, dayofyear=date_climatology_dec)
# Plot all maps
plot_map(var1_dec, f"ds_original: {date_original_dec}", axes[2, 0])
plot_map(var2_dec, f"ds_climatology_N_half_1: {date_climatology_dec}", axes[2, 1])
plot_map(var3_dec, f"ds_climatology_N_half_10: {date_climatology_dec}", axes[2, 2])

# Adjust layout and show the plot
plt.tight_layout()
plt.show()
plt.savefig(f"checks/06_original_data_and_climatology_comparison.png", dpi=300)