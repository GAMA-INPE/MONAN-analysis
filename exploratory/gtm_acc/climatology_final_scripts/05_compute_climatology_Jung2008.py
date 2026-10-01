"""
Script to compute climatology following the methodology of 

Thomas Jung and Martin Leutbecher, 2008, Scale-dependent verification of ensemble forecasts, 
Quarterly Journal of the Royal Meteorological Society.

Acknowledgement: This script was created with the assistance of ChatGPT, Gemini, and Github Copilot.
"""

import juliandate as jd
import matplotlib.pyplot as plt
import os
import xarray as xr
import numpy as np
import pandas as pd

def periodic_julian_day(j: float, j0: float, period: float) -> float:
    """
    Calculates the periodic (cyclic) Julian Day.
    
    Parameters:
    j (float): The current Julian Day number.
    j0 (float): The starting Julian Day (epoch/baseline) of the cycle.
    period (float): The length of the cycle in days (P).
    
    Returns:
    float: The Julian Day mapped into the repeating period.
    """
    # 1. Shift to zero (j-j0), 2. Apply modulo (%), 3. Shift back to baseline (+ j0)
    return ((j - j0) % period) + j0

def compute_weights_j(N_half, N_Y, verbose=False):
    """
    Computes the weights for each day j in the time window.
    
    Returns:
    list: A list of weights corresponding to each day in the window.
    """
    # Create dictionary of indices from -N_half to N_half indicating which days 
    # belong to time window
    j_weights_dict = {j: j for j in range(-N_half, N_half + 1)}

    # Compute weights using definition (A3) from Jung and Leutbecher (2008)
    for j in j_weights_dict:
        weight_j = (
        3 * (N_half + 1)
        / (N_Y * (2 * N_half + 1) * (2 * N_half + 3))
        * (1 - (j / (N_half + 1)) ** 2)
    )
        j_weights_dict[j] = weight_j
        if verbose:
            print ("Weight for day index j:", j, "is:", weight_j)
    
    return j_weights_dict

def compute_weighted_mean(values, weights, N_half, N_Y, verbose=False):
    """
    Computes the weighted mean of a list of values given corresponding weights.
    
    Parameters:
    values (dict): A dictionary of j values for each day from -N_half to N_half 
                   for each year k from 1 to N_Y.
    weights (dict): A diciontary of weights for each day j from -N_half to N_half.
    
    Returns:
    float: The weighted mean of the values.
    """
    
    sum_jk = 0
    for k in range(1, N_Y + 1):
        if verbose:
            print ("Year:", k)
        for j in range(-N_half, N_half + 1):
            if verbose:
                print ("Day index j:", j, "Value:", values[k][j], "Weight:", weights[j])
            sum_jk = sum_jk + values[k][j] * weights[j]
    
    return sum_jk

def test_periodic_julian_day():
    """
    Test function for periodic_julian_day.
    """
    # Define test parameters
    start_year = 1991
    final_year = 2020
    J_0 = jd.from_gregorian(start_year, 1, 1, 0, 0, 0, 0)
    J_end = jd.from_gregorian(final_year+1, 1, 1, 0, 0, 0, 0)
    Delta_J = J_end - J_0

    # Test date: last day before beginning of the climatology period (should give last day of 
    # climatology period when mapped)
    J_test = jd.from_gregorian(1990, 12, 31, 0, 0, 0, 0)
    J_prime = periodic_julian_day(J_test, j0=J_0, period=Delta_J)

    print("Test Gregorian Date:", jd.to_gregorian(J_test))
    print("Test Julian Day:", J_test)
    print("Mapped Julian Day:", J_prime)
    print("Mapped Gregorian Date:", jd.to_gregorian(J_prime))

    # Test date: first day after end of the climatology period (should give first day of climatology 
    # period when mapped)
    J_test = jd.from_gregorian(2021, 1, 1, 0, 0, 0, 0)
    J_prime = periodic_julian_day(J_test, j0=J_0, period=Delta_J)

    print("Test Gregorian Date:", jd.to_gregorian(J_test))
    print("Test Julian Day:", J_test)
    print("Mapped Julian Day:", J_prime)
    print("Mapped Gregorian Date:", jd.to_gregorian(J_prime))

def test_compute_weights_j(N_half, N_Y):
    """
    Test function for compute_weights_j.
    """
    j_dict = compute_weights_j(N_half, N_Y, verbose=True)
    print("Weights for each day in the time window:", j_dict)
    plt.figure("Weights for each day in the time window")
    plt.plot(list(j_dict.keys()), list(j_dict.values()))
    plt.xlabel("Day index (j)")
    plt.ylabel("Weight (w_j)")
    plt.title(f"Weights for N_half={N_half}, N_Y={N_Y}")
    plt.grid()
    plt.savefig(f"checks/weights_j_Nhalf{N_half}_NY{N_Y}.png")

def test_compute_weighted_mean(N_half, N_Y):
    """
    Test function for compute_weighted_mean.
    """
    # Create dummy values for testing
    # use values = {k: {j: 1 for j in range(-N_half, N_half + 1)} for k in range(1, N_Y + 1)};
    # the weighted mean should be 1.0 if the weights are computed correctly!
    values = {k: {j:1 for j in range(-N_half, N_half + 1)} for k in range(1, N_Y + 1)}
    weights = compute_weights_j(N_half, N_Y)
    
    weighted_mean = compute_weighted_mean(values, weights, N_half, N_Y, verbose=True)
    print("Computed weighted mean:", weighted_mean)

def run_climatology_workflow(N_Y, N_half, start_year, final_year, hour_UTC, var_list, level_list, 
                        input_dir, raw_file_path, verbose_all=False):
    """
    Computes the climatology following the methodology of Jung and Leutbecher (2008).
 
    Steps:
    0) Receive input climatology parameters: N_Y, N_half, start_year, final_year, hour_UTC, var_list
    1) Read raw dataset (e.g. from ERA5) containing values for variables in var_list for each 
       grid point and each day at hour_UTC in the climatology period (from start_year to final_year)
    2) Convert variables if needed (e.g. in the case of geopotential, convert if to geopotential height)
    3) Compute weights for each day index j (weights are fixed for fixed N_Y and N_half params)
    4) For each year k, each grid point, each day at hour_UTC nu, compute sum_j values[k][j] * weights[j] term
       ("climatology" for each day at hour_UTC nu and each grid point in a single year)  (try vectorizing in spatial domain)
    5) Sum over all years k to compute the weighted mean for each day at hour_UTC nu and each grid point
    6) Convert resulting dataset format to MONAN dataset format (rename variables, dimensions, etc.
      to match standard MONAN format; if needed, regrid to grid where MONAN data are also regridded)
    """
    # Read raw dataset (e.g. from ERA5)
    ds = read_raw_dataset(raw_file_path, var_list, level_list, start_year, final_year, hour_UTC, verbose=verbose_all)

    # Convert variables if needed (e.g. in the case of geopotential, convert if to geopotential height)
    ds = convert_variables(ds, var_list, input_dir, verbose=verbose_all)

    # Compute weights for each day index j (weights are fixed for fixed N_Y and N_half)
    j_weights_dict = compute_weights_j(N_half, N_Y, verbose=verbose_all)

    # Calculate climatology
    ds_climatology = calculate_climatology(ds, j_weights_dict, N_Y, N_half, start_year, final_year, hour_UTC, verbose=verbose_all)

def calculate_climatology(ds, j_weights_dict, N_Y, N_half, start_year, final_year, hour_UTC, 
                          verbose=False):
    """
    Calculates the climatology for a given dataset and variable for all horizontal grid points and
    vertical levels.

    Parameters:
    ds (xarray.Dataset): The input dataset containing the variable.
    var (str): The variable name to calculate the climatology for.
    N_half (int): Half the window size for smoothing.
    verbose (bool): If True, prints progress information.

    Returns:
    xarray.DataArray: The climatology dataset with smoothed values for each day of the year.
    """
    
    # Add time_julian coordinate to the dataset
    julian_dates = []
    for date in ds.time.values:
        date = pd.to_datetime(date)  # Convert numpy.datetime64 to datetime
        # Convert to Julian Day
        julian_day = jd.from_gregorian(date.year, date.month, date.day, hour_UTC, 0, 0, 0)
        if verbose:
            print(f"Date: {date}, Julian Day: {julian_day}")
        # Append to the list
        julian_dates.append(julian_day)
    # Add new coordinate
    ds = ds.assign_coords(time_julian=("time", julian_dates))
    if verbose:
        print ("Dataset with time_julian coordinate:", ds)

    # Define dates at the extremes of the climatology period in julian days to 
    # compute periodic boundary days
    # define initial date
    J_start = jd.from_gregorian(start_year, 1, 1, hour_UTC, 0, 0, 0)
    # define final date
    J_final = jd.from_gregorian(final_year+1, 1, 1, hour_UTC, 0, 0, 0)
    Delta_J = J_final - J_start

    # Define final climatology dataset
    ds_climatology = xr.zeros_like(ds.sel(time=ds.time.dt.year == final_year))  # Initialize with the shape of the final year

    # ds is the original dataset. Its values will be used to calculate the year-climatology.
    # ds_climatology_year is the year-climatology dataset for a specific year. For each day in that year, 
    # it takes values from ds for j in range(-N_half, N_half+1) together with the weights for each j 
    # to calculate the year-climatology for that specific year. These values will be then summed over
    # all years to obtain the final climatology dataset ds_climatology. The final climatology dataset 
    # will be then converted to MONAN format.
    #for year in range(start_year, final_year + 1):
    for year in range(start_year, start_year + 1):
        ds_year = xr.zeros_like(ds.sel(time=ds.time.dt.year == year))
        if verbose:
            print(f"Processing year: {year}")
            print (ds_year)
        # Compute the year-climatology for each day in the year
        #for julian_day in ds_year.time_julian:
        # Take only first days to check
        for julian_day in ds_year.time_julian[:3]:
            julian_day = float(julian_day.values)
            print ("reference julian day:", julian_day)
            print ("reference gregorian day:", jd.to_gregorian(julian_day))
            sum_for_each_day_of_year = 0.0
            for j in range(-N_half, N_half + 1):
                # Get julian day j
                julian_day_j = julian_day + j
                # Calculate the periodic Julian day
                periodic_day = periodic_julian_day(j=julian_day_j, j0=J_start, period=Delta_J)
                print (f"periodic julian day for j index {j}:", periodic_day)
                print (f"corresponding gregorian date for j index {j}:", jd.to_gregorian(periodic_day))
            #     # Get the corresponding day's data
            #     day_data = ds.sel(time=ds.time.dt.dayofyear == periodic_day)
            #     # Multiply by the weight and add to the smoothed value
            #     if not day_data.isnull().all():
            #         smoothed_value += j_weights_dict[j] * day_data
            # # Assign the smoothed value to the climatology for that year and day
            # ds_year.loc[{"time": ds_year.time.dt.dayofyear == day}] = smoothed_value

    # # Compute weights dictionary
    # j_weights_dict = {j: 3 * (N_half + 1) / (N_Y * (2 * N_half + 1) * (2 * N_half + 3)) for j in range(-N_half, N_half + 1)}

    # # Create an empty array to store the climatology
    # days_of_year = np.arange(1, 366)  # Julian days
    # climatology = xr.DataArray(
    #     np.zeros((len(days_of_year), *ds[var].shape[1:])),
    #     dims=["dayofyear", *ds[var].dims[1:]],
    #     coords={"dayofyear": days_of_year, **{dim: ds[var][dim] for dim in ds[var].dims[1:]}}
    # )

    # # Group data by year
    # grouped_years = ds.groupby("time.year")

    # # Iterate over each year to calculate the year-climatology
    # for year, year_data in grouped_years:
    #     if verbose:
    #         print(f"Processing year: {year}")

    #     # Iterate over each day of the year
    #     for day in days_of_year:
    #         smoothed_value = 0.0

    #         # Apply smoothing over the window (-N_half, N_half + 1)
    #         for j in range(-N_half, N_half + 1):
    #             # Calculate the periodic Julian day
    #             periodic_day = periodic_julian_day(day + j, 1, period)

    #             # Get the corresponding day's data
    #             day_data = year_data.sel(time=year_data['time.dayofyear'] == periodic_day)

    #             # Multiply by the weight and add to the smoothed value
    #             if not day_data[var].isnull().all():
    #                 smoothed_value += j_weights_dict[j] * day_data[var]

    #         # Assign the smoothed value to the climatology
    #         climatology.loc[{"dayofyear": day}] += smoothed_value

    # return climatology

def read_raw_dataset(raw_file_path, var_list, level_list, start_year, final_year, hour_UTC, 
                     verbose=False):
    """
    Reads the raw dataset (e.g., from ERA5) containing values for variables in var_list for each 
    grid point and each day at hour_UTC in the climatology period (from start_year to final_year).
    
    Parameters:
    raw_file_path (str): Path to the raw dataset file.
    var_list (list): List of variable names to read from the dataset.
    start_year (int): Starting year of the climatology period.
    final_year (int): Ending year of the climatology period.
    hour_UTC (int): Hour of the day in UTC for which to extract data.
    
    Returns:
    xarray.Dataset: The dataset containing the requested variables and time range.
    """
    import xarray as xr

    # Open the dataset
    ds = xr.open_dataset(raw_file_path)
    if verbose:
        print ("raw dataset:", ds)

    # Select the period and hour for climatology
    ds = ds.sel(time=ds.time.dt.year.isin(range(start_year, final_year + 1)) & (ds.time.dt.hour == hour_UTC))
    #ds = ds.sel(time=slice(f"{start_year}-01-01T{hour_UTC:02d}:00:00", f"{final_year}-12-31T{hour_UTC:02d}:00:00"))

    # Select only the requested levels (assuming pressure level)
    if 'plev' in ds.coords:
        ds = ds.sel(plev=level_list)

    # Select only the requested variables
    ds = ds[var_list]
    if verbose:
        print ("raw dataset with selection of time, level and vars:", ds)

    return ds

def convert_variables(ds, var_list, input_dir, verbose=False):
    """
    Converts variables if needed (e.g., in the case of geopotential, convert to geopotential height).
    
    Parameters:
    ds (xarray.Dataset): The dataset containing the variables to convert.
    var_list (list): List of variable names to check for conversion.
    
    Returns:
    xarray.Dataset: The dataset with converted variables.
    """
    # Check if dataset with converted variables already exists
    converted_file_path = input_dir + "/raw_dataset_with_converted_variables.nc"
    # If so, load it and skip conversion step
    if os.path.exists(converted_file_path):
        if verbose:
            print(f"Converted dataset already exists at {converted_file_path}. Loading it and skipping conversion step.")
        ds = xr.open_dataset(converted_file_path)
        return ds
    # Else, proceed with conversion and save dataset
    else:
        # Example conversion: if 'var129' is geopotential, convert to geopotential height
        if 'var129' in var_list:
            if verbose:
                print ("Dataset value before conversion to check variables values:", ds["var129"].isel(time=0,lat=0,lon=0).values[0])
            # Assuming var129 is geopotential in m^2/s^2, convert to geopotential height in meters
            ds['zgeo'] = ds['var129'] / 9.80665  # g = 9.80665 m/s^2
            # Drop the original variable
            ds = ds.drop_vars('var129')
            if verbose:
                print("Converted var129 from geopotential to geopotential height.")
                print ("Dataset value after conversion to check variables values:", ds["zgeo"].isel(time=0,lat=0,lon=0).values[0])
        # Save the converted dataset for future use
        ds.to_netcdf(converted_file_path)
    
    return ds

if __name__ == "__main__":
    # Set parameters
    # number of years
    N_Y = 30
    # number of days for each side of time window (21-d centered window)
    N_half = 10
    # initial and final year
    start_year = 1991
    final_year = 2020
    # hour (UTC) for the climatology calculation (0 for midnight, 12 for noon)
    hour_UTC = 0
    # variable list for climatology calculation (e.g., geopotential, temperature, wind components, specific humidity)
    var_list = ["var129"]
    # pressure level list for climatology calculation (e.g., 50000 Pa)
    level_list = [50000]
    # path to input data
    input_dir = "/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/hourly/nc"
    # path to raw data for computing the climatology
    raw_file_path = input_dir+"/"+"concat_era5_hourly_pl_1991_2020.nc"

    # Compute climatology
    run_climatology_workflow(
        N_Y=N_Y,
        N_half=N_half,
        start_year=start_year,
        final_year=final_year,
        hour_UTC=hour_UTC,
        var_list=var_list,
        level_list=level_list,
        input_dir=input_dir,
        raw_file_path=raw_file_path,
        verbose_all=True
    )

    #===============================================================================================
    ## Test functions used in the script
    ## 1) see if the julian date calculation is correct
    ## J_0 = jd.from_gregorian(-4713, 11, 24, 12, 0, 0, 0)
    ## print (J_0) # J_0 gives 0 julian days
    ## 2) test the periodic_julian_day function
    ## test_periodic_julian_day()
    ## 3) test the compute_weights_j function
    ## test_compute_weights_j(N_half, N_Y)
    ## 4) test the compute_weighted_mean function with dummy values
    ## test_compute_weighted_mean(N_half=10, N_Y=30)
    #===============================================================================================





