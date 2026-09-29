"""
Script to compute climatology following the methodology of 

Thomas Jung and Martin Leutbecher, 2008, Scale-dependent verification of ensemble forecasts, 
Quarterly Journal of the Royal Meteorological Society.

Acknowledgement: This script was created with the assistance of ChatGPT and Gemini.
"""

import juliandate as jd
import matplotlib.pyplot as plt

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
        print ("Computing weight for day index j:", j)
        weight_j = (
        3 * (N_half + 1)
        / (N_Y * (2 * N_half + 1) * (2 * N_half + 3))
        * (1 - (j / (N_half + 1)) ** 2)
    )
        j_weights_dict[j] = weight_j
    
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

def compute_climatology():
    """
    Computes the climatology following the methodology of Jung and Leutbecher (2008).
 
    Steps:
    0) Define climatology parameters: N_Y, N_half, start_year, final_year, hour_UTC, var_list
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
    # Compute weights for each day index j (weights are fixed for fixed N_Y and N_half)
    j_weights_dict = compute_weights_j(N_half, N_Y)

    # Define dates in julian days
    # define initial date
    J_0 = jd.from_gregorian(start_year, 1, 1, 0, 0, 0, 0)
    # define final date
    J_end = jd.from_gregorian(final_year+1, 1, 1, 0, 0, 0, 0)
    Delta_J = J_end - J_0


    


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

    # Compute climatology
    #compute_climatology()

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





