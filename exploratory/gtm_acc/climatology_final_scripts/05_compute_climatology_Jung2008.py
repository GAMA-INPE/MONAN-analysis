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
    ds_climatology = calculate_climatology(ds, j_weights_dict, N_Y, N_half, start_year, final_year, 
                                           hour_UTC, verbose=verbose_all, verbose_level2=False)
    
    # Save climatology
    climatology_file_path = input_dir + f"/climatology_N_half_{N_half}_hour_UTC_{hour_UTC}_{start_year}_{final_year}.nc"
    ds_climatology.to_netcdf(climatology_file_path)

def calculate_climatology(ds, j_weights_dict, N_Y, N_half, start_year, final_year, hour_UTC, 
                          verbose=False, verbose_level2=False):
    """
    Calculates the climatology for a given dataset and variable for all horizontal grid points and
    vertical levels.

    Parameters:
    ds (xarray.Dataset): The input dataset containing the variable to compute climatology for.
    j_weights_dict (dict): A dictionary containing the weights for each day index j.
    N_Y (int): The number of years in the climatology period.
    N_half (int): The number of days on each side of the time window for smoothing.
    start_year (int): The starting year of the climatology period.
    final_year (int): The ending year of the climatology period.
    hour_UTC (int): The hour of the day in UTC for which to compute the climatology.

    Returns:
    xarray.DataArray: The climatology dataset with smoothed values for each day of the year.
    """
    
    # Add time_julian coordinate to the dataset
    julian_dates = []
    for date in ds.time.values:
        date = pd.to_datetime(date)  # Convert numpy.datetime64 to datetime
        # Convert to Julian Day
        julian_day = jd.from_gregorian(date.year, date.month, date.day, hour_UTC, 0, 0, 0)
        if verbose_level2:
            print(f"Date: {date}, Julian Day: {julian_day}")
        # Append to the list
        julian_dates.append(julian_day)
    # Add new coordinate
    ds = ds.assign_coords(time_julian=("time", julian_dates))

    # Define dates at the extremes of the climatology period in julian days to 
    # compute periodic boundary days
    # define initial date
    J_start = jd.from_gregorian(start_year, 1, 1, hour_UTC, 0, 0, 0)
    # define final date
    J_final = jd.from_gregorian(final_year+1, 1, 1, hour_UTC, 0, 0, 0)
    Delta_J = J_final - J_start

    # Define final climatology dataset
    ds_climatology = xr.zeros_like(ds.where(ds.time.dt.year == start_year, drop=True))  # Initialize with the shape of the start year
    # Define time coordinate as dayofyear instead of time
    ds_climatology = ds_climatology.assign_coords(dayofyear=("time", ds_climatology.time.dt.dayofyear.values))
    ds_climatology = ds_climatology.swap_dims({"time": "dayofyear"})
    if verbose:
        print ("\nInitial climatology dataset:", ds_climatology)

    # ds is the original dataset. Its values will be used to calculate the year-climatology.
    # ds_climatology_year is the year-climatology dataset for a specific year. For each day in that year, 
    # it takes values from ds for j in range(-N_half, N_half+1) together with the weights for each j 
    # to calculate the year-climatology for that specific year. These values will be then summed over
    # all years to obtain the final climatology dataset ds_climatology. The final climatology dataset 
    # will be then converted to MONAN format.
    sum_for_each_year = xr.zeros_like(ds_climatology)
    for year in range(start_year, final_year + 1):
        # Define dataset for year-climatology, which will then be summed for different years
        # to define final climatology.
        ds_year = xr.zeros_like(ds.sel(time=ds.time.dt.year == year))
        # Define dayofyear as dimension of ds_year for summing with sum_for_each_year
        ds_year = ds_year.assign_coords(dayofyear=("time", ds_year.time.dt.dayofyear.values))
        ds_year = ds_year.swap_dims({"time": "dayofyear"})
        # Compute the year-climatology for each day in the year
        for julian_day in ds_year.time_julian:
            julian_day = float(julian_day.values)
            # Define sum for each day of that year as dataset with almost the same shape as ds, but
            # without the time dimension (we will select ds for that julian_day), so that sum
            # can be performed with data from a different day
            sum_for_each_day_of_year = xr.zeros_like(ds.sel(time=ds.time_julian == julian_day, drop=True))
            # Squeeze the dataset to remove the 'time' dimension (since there's only one time value)
            sum_for_each_day_of_year = sum_for_each_day_of_year.squeeze(dim="time", drop=True)
            
            if verbose_level2:
                print (f"\nProcessing day {jd.to_gregorian(julian_day)} (Julian Day: {julian_day}) for year {year}")
                print ("\nInitial dataset ds_year for that year:", ds_year)
                print ("\nInitial dataset sum_for_each_day_of_year for that day:", sum_for_each_day_of_year)
            # Compute year-climatology for that day using all days around it in the time window 
            # defined by N_half
            for j in range(-N_half, N_half + 1):
                # Get julian day j (day j in the time window around the day being processed)
                julian_day_j = julian_day + j
                # Calculate the periodic julian day
                periodic_julian_day_j = periodic_julian_day(j=julian_day_j, j0=J_start, period=Delta_J)
                if verbose_level2:
                    print ("\nreference julian day:", julian_day)
                    print ("reference gregorian day:", jd.to_gregorian(julian_day))
                    print (f"\nperiodic julian day for j index {j}:", periodic_julian_day_j)
                    print (f"corresponding gregorian date:", jd.to_gregorian(periodic_julian_day_j))
                # Get data from original dataset for that periodic day, but without time dimension
                julian_day_j_data = ds.sel(time=ds.time_julian == periodic_julian_day_j, drop=True).copy(deep=True)
                # Squeeze the dataset to remove the 'time' dimension (since there's only one time value)
                julian_day_j_data = julian_day_j_data.squeeze(dim="time", drop=True)
                # Multiply it by the weight
                weights_times_data = j_weights_dict[j] * julian_day_j_data
                if verbose_level2:
                    print (f"\nDataset of sum for each day of year before adding j index {j}:", sum_for_each_day_of_year)
                # Add result to the sum for that day of the year
                sum_for_each_day_of_year = sum_for_each_day_of_year + weights_times_data
                if verbose_level2:
                    print (f"Dataset of julian periodic day {periodic_julian_day_j} (j index {j}):", julian_day_j_data)
                    print (f"Dictionary of weight for j index {j}:", j_weights_dict[j])
                    print (f"Dataset of weight times data for j index {j}:", weights_times_data)
                    print (f"Dataset of sum for each day of year after adding j index {j}:", sum_for_each_day_of_year)

            # Assign sum_for_each_day_of_year to the corresponding day and var in the 
            # year-climatology dataset
            time_gregorian_for_julian_day = jd.to_gregorian(julian_day)
            # Transform time_gregorian_for_julian_day to dayofyear format
            dayofyear = pd.Timestamp(year=year,month=time_gregorian_for_julian_day[1],day=time_gregorian_for_julian_day[2]).dayofyear
            # Select corresponding dayofyear in ds_year and assign sum_for_each_day_of_year to it
            ds_year.loc[dict(dayofyear=dayofyear)] = sum_for_each_day_of_year

            if verbose_level2:
                print (f"\nSum for day {jd.to_gregorian(julian_day)}:", sum_for_each_day_of_year)
                print (f"Year-climatology dataset for year {year} after processing day {jd.to_gregorian(julian_day)}:", ds_year)
        
        # Sum over all years k to compute the weighted mean for each day at hour_UTC nu and each grid point
        if verbose_level2:
            print (f"\nSum for each year before adding year {year}:", sum_for_each_year)
        # NOTE: for leap years, the sum is performed over the first 365 days only, while the day 366
        # is ignored!
        sum_for_each_year = sum_for_each_year + ds_year
        if verbose_level2:
            print (f"\nSum for each year after adding year {year}:", sum_for_each_year)
    
    ds_climatology = sum_for_each_year
    if verbose:
        print ("\nFinal climatology dataset after processing all years:", ds_climatology)
    
    return ds_climatology

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

def test_calculate_climatology(N_Y, N_half, start_year, final_year, hour_UTC, var_list, level_list,
                               verbose_all=True):
    """
    Test function for calculate_climatology with a small dataset with all values equal to one.
    """
    # Create dataset
    time = pd.date_range(f"{start_year}-01-01", f"{final_year}-12-31", freq='D')
    ds = xr.Dataset(
        {
            var: (["time", "plev", "lat", "lon"], np.ones((len(time), len(level_list), 2, 2))) for var in var_list
        },
        coords={
            "time": time,
            "plev": level_list,
            "lat": [0, 1],
            "lon": [0, 1],
        },
    )

    
    # Compute weights for each day index j (weights are fixed for fixed N_Y and N_half)
    j_weights_dict = compute_weights_j(N_half, N_Y, verbose=verbose_all)

    # Calculate climatology
    ds_climatology = calculate_climatology(ds, j_weights_dict, N_Y, N_half, start_year, final_year, 
                                           hour_UTC, verbose=True, verbose_level2=True)
    
    # print ("Climatology dataset for test with all values equal to one:", ds_climatology)
    # print ("Climatology dataset values for test with all values equal to one:", ds_climatology[var_list[0]].values)
        

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

    # # Compute climatology
    # run_climatology_workflow(
    #     N_Y=N_Y,
    #     N_half=N_half,
    #     start_year=start_year,
    #     final_year=final_year,
    #     hour_UTC=hour_UTC,
    #     var_list=var_list,
    #     level_list=level_list,
    #     input_dir=input_dir,
    #     raw_file_path=raw_file_path,
    #     verbose_all=True
    # )

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
    ## 5) test the calculate_climatology function with a small dataset (e.g., 2 years, 3 days, 1 variable, 1 level)
    test_calculate_climatology(N_Y=2, N_half=1, start_year=1991, final_year=1992, hour_UTC=0, var_list=["var129", "var128"], level_list=[50000, 10000])
    #===============================================================================================





