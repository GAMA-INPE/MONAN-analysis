"""
Acknowledgement: this script was generated with ChatGPT and revised by Guilherme L. Torres Mendonça.
"""

import xarray as xr
import glob

files = sorted(glob.glob("/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/hourly/nc/era5_hourly_pl_*.nc"))

print("Files:")
for f in files:
    print(f)

ds = xr.open_mfdataset(
    files,
    combine="by_coords"
)

print(ds)
print(ds.time)

# Rename the variable if necessary
var = ds["var129"]

# Make sure time is sorted
var = var.sortby("time")

# Save a clean dataset
var.to_dataset(name="var129").to_netcdf(
    "/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/hourly/nc/concat_era5_hourly_pl_1991_2020.nc",
    format="NETCDF4"
)

print("Saved concatenated ERA5 dataset.")