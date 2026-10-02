import xarray as xr
import numpy as np
import pandas as pd

# The goal of this script is to test how one should cleanly compute anomalies of datasets that
# contain e.g. daily time series at different years, but from which we want to compute anomalies.
# Duck.ai recommends aligning the time by day of the year.

# Create first exemplary dataset with time, lev, lon, lat coordinates
ds1 = xr.Dataset(
    {
        "var1": (("time", "lev", "lon", "lat"), 
                 10 * np.random.rand(365, 5, 10, 10)),
        "var2": (("time", "lev", "lon", "lat"), 
                 20 * np.random.rand(365, 5, 10, 10)),
    },
    coords={
        "time": pd.date_range("2000-01-01", periods=365),
        "lev": np.arange(5),
        "lon": np.linspace(0, 360, 10),
        "lat": np.linspace(-90, 90, 10),
    }
)

# Create second exemplary dataset with time, lev, lon, lat coordinates but different year
ds2 = xr.Dataset(
    {
        "var1": (("time", "lev", "lon", "lat"), 
                 10 * np.random.rand(365, 5, 10, 10)),
        "var2": (("time", "lev", "lon", "lat"), 
                 20 * np.random.rand(365, 5, 10, 10)),
    },
    coords={
        "time": pd.date_range("2001-01-01", periods=365),
        "lev": np.arange(5),
        "lon": np.linspace(0, 360, 10),
        "lat": np.linspace(-90, 90, 10),
    }
)

print (ds1)
print (ds2)
print ("\n")
print ("simply subtracting both datasets doesnt work because the time coordinates are different:")
print (ds1 - ds2)
print ("\n")
# Now we can align the time coordinates by day of the year. We can do this by creating a new 
# coordinate that represents the day of the year for each time point.
ds1_doy = ds1.assign_coords(dayofyear=ds1.time.dt.dayofyear).swap_dims({"time": "dayofyear"})
ds2_doy = ds2.assign_coords(dayofyear=ds2.time.dt.dayofyear).swap_dims({"time": "dayofyear"})
print ("\n")
print ("datasets with day of year as coordinate:")
print (ds1_doy)
print (ds2_doy)
print ("\n")
print ("now we can subtract both datasets and the time coordinates are aligned by day of the year:")
print (ds1_doy - ds2_doy)
