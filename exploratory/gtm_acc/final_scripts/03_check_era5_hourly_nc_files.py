#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.feature as cfeature
import cartopy.crs as ccrs

era5_dir = '/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/hourly/nc'
ds1 = xr.open_dataset(f"{era5_dir}/era5_hourly_pl_1994.nc")
ds2 = xr.open_dataset(f"{era5_dir}/concat_era5_hourly_pl_1991_2020.nc")

# print the datasets to check their contents
print (ds1)
print (ds2)

# print the dimensions
print("Dimensions of ds1:", ds1.dims)
print("Dimensions of ds2:", ds2.dims)

# print the coordinates
print("Coordinates of ds1:", ds1.coords)
print("Coordinates of ds2:", ds2.coords)

# print values for coords
print ("Values of ds1 time coordinate:", ds1['time'].values)
print ("Values of ds2 time coordinate:", ds2['time'].values)
print ("Values of ds1 plev coordinate:", ds1['plev'].values)
print ("Values of ds2 plev coordinate:", ds2['plev'].values)

# choose two dates for plotting the field var129
date1_jan = '1994-01-01'
date1_jun = '1994-06-01'
date2_jan = '2005-01-01'
date2_jun = '2005-06-01'

# plot fields separately and also difference for each date
# Extract var129 at 500 hPa for the specified dates
level_500 = 50000  # Pressure level in hPa

# Function to plot a single map
def plot_map(data, title, ax):
    ax.set_global()
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, edgecolor='black', facecolor='lightgray')
    im = ax.contourf(data.lon, data.lat, data, transform=ccrs.PlateCarree(), cmap='coolwarm')
    plt.colorbar(im, ax=ax, orientation='horizontal', pad=0.05)
    ax.set_title(title)

# Create subplots for each date and dataset
fig, axes = plt.subplots(2, 3, figsize=(18, 12), subplot_kw={'projection': ccrs.PlateCarree()})

# january dates
# Extract data for ds1 and ds2
var1 = ds1['var129'].sel(plev=level_500, time=date1_jan)
var2 = ds2['var129'].sel(plev=level_500, time=date2_jan)
diff = var2 - var1
# Plot ds1, ds2, and their difference
plot_map(var1, f"ds1: {date1_jan}", axes[0, 0])
plot_map(var2, f"ds2: {date2_jan}", axes[0, 1])
plot_map(diff, f"Difference: {date2_jan}-{date1_jan}", axes[0, 2])

# june dates
var1 = ds1['var129'].sel(plev=level_500, time=date1_jun)
var2 = ds2['var129'].sel(plev=level_500, time=date2_jun)
diff = var2 - var1
# Plot ds1, ds2, and their difference
plot_map(var1, f"ds1: {date1_jun}", axes[1, 0])
plot_map(var2, f"ds2: {date2_jun}", axes[1, 1])
plot_map(diff, f"Difference: {date2_jun}-{date1_jun}", axes[1, 2])

# Adjust layout and show the plot
plt.tight_layout()
plt.show()
plt.savefig(f"era5_hourly_pl_1994_2005_concat_file_comparison.png", dpi=300)