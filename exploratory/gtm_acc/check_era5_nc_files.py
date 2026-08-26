#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import xarray as xr

era5_dir = '/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/mon/nc'
ds1 = xr.open_dataset(f"{era5_dir}/era5_pl_19910105.nc")
ds2 = xr.open_dataset(f"{era5_dir}/era5_pl_19910115.nc")

print (ds1.var129.values)
print (ds2.var129.values)

# Check if the arrays are numerically close within a tolerance
if np.allclose(ds1.var129.values, ds2.var129.values, atol=1e-8):
    print("The arrays are numerically close within the tolerance.")
else:
    print("The arrays are not numerically close.")

# Check if the arrays are exactly equal
if np.array_equal(ds1.var129.values, ds2.var129.values):
    print("The arrays are exactly equal.")
else:
    print("The arrays are not exactly equal.")

# Calculate and print the maximum absolute difference
max_diff = np.max(np.abs(ds1.var129.values - ds2.var129.values))
print(f"Maximum absolute difference: {max_diff}")