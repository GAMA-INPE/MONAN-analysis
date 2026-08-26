# -*- coding: utf-8 -*-
"""
stats.py

Description
-----------
This module contains functions for calculations and settings of analysis statistics.

Usage
-----
- Import this module in scripts that require functions for statistical analysis.
- Functions in this module should be general-purpose and reusable across different analyses.

Examples:
- from monan_analysis.stats import example_function_stats
or 
- import monan_analysis.stats as stats
  filename = stats.example_function_stats()

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot. 
"""

import xarray as xr
import monan_analysis.preprocess as preprocess

def example_function_stats():
    print ("this is a function imported from the stats.py module.")

def bias(predictions, observations):
    """
    Calculate the bias between predictions and observations while preserving xarray dataset structure.
    
    Bias may be defined as the 'systematic difference' between a predicted variable and the corresponding
    observed variable, where 'systematic' means that the difference is performed for averages of the 
    variable over a spatial and time domain (1,2). The spatial and time averaging of the variable 
    is left to the user. This function only calculates the difference

    bias[var] = predictions[var] - observations[var]

    References:
    1. Maraun et al, 2016, "Towards process-oriented bias adjustment of climate change simulations", 
    Nature Climate Change, v 7, n 11, 764-773
    2. Ehret et al, 2012, "HESS Opinions: Should we apply bias correction to global and regional 
    climate model data?", Hydrology and Earth System Sciences, v 16, n 9, 3391-3404
    """
    # Ensure inputs are xarray Datasets
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    # Perform the subtraction for each data variable
    result = predictions.copy()
    for var in predictions.data_vars:
        result[var] = predictions[var] - observations[var]
    
    return result

def bias_mean(predictions, observations):
    """
    Calculate the mean bias between predictions and observations.
    
    Bias may be defined as the 'systematic difference' between a predicted variable and the corresponding
    observed variable, where 'systematic' means that the difference is performed for averages of the 
    variables over a spatial and time domain (1,2). The spatial and time averaging of the variables 
    is left to the user. This function calculates the difference

    bias[var] = predictions[var] - observations[var]

    and then takes its overall mean over the bias[var] array.

    References:
    1. Maraun et al, 2016, "Towards process-oriented bias adjustment of climate change simulations", 
    Nature Climate Change, v 7, n 11, 764-773
    2. Ehret et al, 2012, "HESS Opinions: Should we apply bias correction to global and regional 
    climate model data?", Hydrology and Earth System Sciences, v 16, n 9, 3391-3404 
    """
    # Ensure inputs are xarray Datasets
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    # Perform the subtraction for each data variable and then take the mean
    result = predictions.copy()
    for var in predictions.data_vars:
        result[var] = (predictions[var] - observations[var]).mean()
    
    return result

def relative_error(predictions, observations):
    """
    Calculate the relative error between predictions and observations.
    
    Relative error is here defined as

    relative_error = 100*(predictions - observations) / |observations|,

    assuming observations are the true value of the variable, and predictions are an approximation.
    This is roughly the definition given in (1), except that here we do not take the absolute value
    of the numerator so that the direction of the error is taken into account.

    Reference:
    1. Burden and Faires, Numerical Analysis, 9th edition, 2011
    """
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    result = predictions.copy()
    for var in predictions.data_vars:
        result[var] = 100*(predictions[var] - observations[var]) / abs(observations[var])
    
    return result

def relative_error_mean(predictions, observations):
    """
    Calculate the mean relative error between predictions and observations.
    
    Relative error is here defined as

    relative_error = 100*(predictions - observations) / |observations|,

    assuming observations are the true value of the variable, and predictions are an approximation (1).
    This function calculates the mean of the relative_error array defined above.

    Reference:
    1. Burden and Faires, Numerical Analysis, 9th edition, 2011
    """
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    result = predictions.copy()
    for var in predictions.data_vars:
        result[var] = 100*((predictions[var] - observations[var]) / abs(observations[var])).mean()
    
    return result

def rmse(predictions, observations, dim):
    """
    Calculate the root mean square error (rmse) between predictions and observations.
    
    Rmse is here defined as the root of the mean squared error as defined in (1), i.e.

    RMSE = sqrt(1/n sum_{i=1}^{n} (prediction_i - observation_i)**2),

    where the mean is taken over the dimension(s) specified by the user in the dim argument, 
    and n is the number of components in the field.

    Reference:
    1. Jolliffe and Stephenson, Forecast Verification: A Practitioner's Guide in Atmospheric Science, 2003
    """
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    result = predictions.copy()
    for var in predictions.data_vars:
        result[var] = (((predictions[var] - observations[var]) ** 2).mean(dim=dim)) ** 0.5

    # Explicitly drop the specified dimension from the result dataset
    if dim in result.dims:
        result = result.drop_dims(dim)
    
    return result

def anomaly_correlation_coefficient(predictions, observations, dim):
    """
    Calculate the anomaly correlation coefficient between predictions and observations.
    
    The anomaly correlation coefficient is here defined as the mean of the product of the anomalies 
    of the predictions and observations, divided by the product of the standard deviations of the 
    anomalies of the predictions and observations. 
    This definition follows roughly that of (1), except that in (1) the anomalies are calculated by 
    subtracting the climatological mean of the variable and then again its spatial mean, while here 
    we subtract only the mean of the variable over the dimension specified by the user in the dim argument. 
    The user is expected to calculate the anomalies as she/he sees fit.

    Mathematically, we define

    ACC = (pred_anom * obs_anom).mean(dim=dim) / ((pred_anom ** 2).mean() ** 0.5 * (obs_anom ** 2).mean() ** 0.5),

    where
    pred_anom = predictions - predictions.mean()
    obs_anom = observations - observations.mean()
    n = number of components in the field

    Reference:
    1. Jolliffe and Stephenson, Forecast Verification: A Practitioner's Guide in Atmospheric Science, 2003
    """
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    result = predictions.copy()
    for var in predictions.data_vars:
        pred_anom = predictions[var] - predictions[var].mean(dim=dim)
        obs_anom = observations[var] - observations[var].mean(dim=dim)
        result[var] = (pred_anom * obs_anom).mean(dim=dim) / (
            (pred_anom ** 2).mean(dim=dim) ** 0.5 *
            (obs_anom ** 2).mean(dim=dim) ** 0.5
        )

    # Explicitly drop the specified dimension from the result dataset
    if dim in result.dims:
        result = result.drop_dims(dim)

    return result

def anomaly_correlation_coefficient_standard(var, predictions_monthly, observations_monthly, climatology_monthly):
    """
    Calculate the anomaly correlation coefficient (ACC) for a specific variable between monthly 
    predictions and observations, using the standard definition employed in operational centers (1,2,3,4).
    
    The ACC is here defined as the spatial mean of the product of the anomalies of the predictions 
    and observations, divided by the product of the standard deviations of the anomalies of the 
    predictions and observations.

    Mathematically:

    ACC = (pred_anom * obs_anom).mean(dim=space) / ((pred_anom ** 2).mean(dim=space) ** 0.5 * (obs_anom ** 2).mean(dim=space) ** 0.5),

    where
    pred_anom = (predictions_monthly - climatology_monthly) - (predictions_monthly - climatology_monthly).mean(dim=space)
    obs_anom = (observations_monthly - climatology_monthly) - (observations_monthly - climatology_monthly).mean(dim=space)

    Parameters:
        predictions_monthly (xr.Dataset): Dataset containing monthly-averaged predictions.
        observations_monthly (xr.Dataset): Dataset containing monthly-averaged observations.
        climatology_monthly (xr.Dataset): Dataset containing monthly-averaged climatology.
        var (str): Variable name to calculate the anomaly correlation coefficient for.
        dim (str or list): Dimension(s) over which to calculate the correlation.

    Returns:
        xr.Dataset: Dataset containing the anomaly correlation coefficient for the specified variable.

    References:
    1. Jolliffe and Stephenson, Forecast Verification: A Practitioner's Guide in Atmospheric Science, 2003
    2. Hollingsworth et al, Comparison of Medium Range Forecasts Made with Two Parametrization Schemes, 1979
    3. ECMWF Forecaster User Guide, available at: 
    https://confluence.ecmwf.int/spaces/FUG/pages/673551834/Section+12.A+Statistical+Concepts+-+Deterministic+Data#Section12.AStatisticalConceptsDeterministicData-MeasureofSkill-theAnomalyCorrelationCoefficient(ACC)
    4. Livezey et al, Verification of Official Monthly Mean 700-hPa Height Forecasts: An Update, 1995
    """
    if not isinstance(predictions_monthly, xr.Dataset) or not isinstance(observations_monthly, xr.Dataset) \
        or not isinstance(climatology_monthly, xr.Dataset):
        raise TypeError("Predictions, observations, and climatology must be xarray Datasets.")
    
    if var not in predictions_monthly or var not in observations_monthly or var not in climatology_monthly:
        raise ValueError(f"The variable '{var}' must exist in predictions, observations, and climatology datasets.")

    # Create an empty dataset for the result
    result = xr.Dataset()

    # Compute anomalies
    pred_anom = (predictions_monthly[var] - climatology_monthly[var]) - preprocess.spatial_mean(predictions_monthly[var] - climatology_monthly[var])
    obs_anom = (observations_monthly[var] - climatology_monthly[var]) - preprocess.spatial_mean(observations_monthly[var] - climatology_monthly[var])

    # Compute ACC and store in the result dataset
    result[var] = preprocess.spatial_mean(pred_anom * obs_anom) / (
        (preprocess.spatial_mean(pred_anom ** 2)) ** 0.5 *
        (preprocess.spatial_mean(obs_anom ** 2)) ** 0.5
    )

    return result

def get_stats_metric_units(var_units_dict,var,metric):
    metric_units_dict = {
        "bias": var_units_dict[var],
        "relative_error": "%",
        "rmse": var_units_dict[var],
        "anomaly_correlation_coefficient": " "
    }
    return metric_units_dict[metric]