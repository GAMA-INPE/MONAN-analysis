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

import numpy as np
import xarray as xr
from scipy.ndimage import uniform_filter

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

def get_stats_metric_units(var_units_dict,var,metric):
    metric_units_dict = {
        "bias": var_units_dict[var],
        "relative_error": "%",
        "rmse": var_units_dict[var],
        "anomaly_correlation_coefficient": " "
    }
    return metric_units_dict[metric]

def neighborhood_fraction(
    event,
    window_size,
    spatial_dims=("lat", "lon"),
    boundary_modes=("constant", "constant"),
):
    """
    Calculate the event fraction inside a spatial neighbourhood.
    NaN values are excluded from the denominator.
    """

    if not isinstance(event, xr.DataArray):
        raise TypeError(
            "event must be an xarray.DataArray."
        )

    if len(spatial_dims) != 2:
        raise ValueError(
            "spatial_dims must contain exactly two dimensions."
        )

    if event.ndim != 2:
        raise ValueError(
            "event must be a two-dimensional field."
        )

    for dim in spatial_dims:
        if dim not in event.dims:
            raise ValueError(
                f"Dimension {dim!r} not found in event."
            )

    if not isinstance(window_size, int) or window_size < 1:
        raise ValueError(
            "window_size must be a positive integer."
        )

    if len(boundary_modes) != 2:
        raise ValueError(
            "boundary_modes must contain one mode "
            "for each spatial dimension."
        )

    event = event.transpose(*spatial_dims)

    binary = event.astype("float32")

    valid = xr.where(
        np.isfinite(binary),
        1.0,
        0.0,
    ).astype("float32")

    binary = binary.fillna(0.0)

    numerator = uniform_filter(
        binary.values,
        size=window_size,
        mode=boundary_modes,
        cval=0.0,
    )

    denominator = uniform_filter(
        valid.values,
        size=window_size,
        mode=boundary_modes,
        cval=0.0,
    )

    with np.errstate(
        invalid="ignore",
        divide="ignore",
    ):
        fraction = np.where(
            denominator > 0.0,
            numerator / denominator,
            np.nan,
        ).astype("float32")

    return xr.DataArray(
        fraction,
        coords=event.coords,
        dims=event.dims,
    )

def fractions_skill_score(
    forecast_event,
    observation_event,
    window_size,
    spatial_dims=("lat", "lon"),
    boundary_modes=("constant", "constant"),
    weights=None,
):
    """
    Calculate the Fractions Skill Score (FSS) from forecast and
    observation event fields.

    Forecast and observation events must be defined before calling
    this function. Event fields should contain:

        1   event occurrence
        0   event non-occurrence
        NaN invalid or missing points

    Events may be defined from a single threshold, multiple thresholds,
    or combinations of different variables.

    For simple threshold-based events, threshold_event() can be used
    to create the event fields.

    Examples of possible events:

        precipitation >= 10 mm
        temperature <= 0 C
        20 <= temperature <= 30 C
        temperature >= 35 C and relative humidity <= 30 %

    The function:
        1. computes neighbourhood event fractions;
        2. computes the Fractions Brier Score (FBS);
        3. computes FBSworst;
        4. computes FSS = 1 - FBS / FBSworst.

    Returns
    -------
    fss : float
        Fractions Skill Score.
    fbs : float
        Spatially averaged Fractions Brier Score.
    fbs_worst : float
        Spatially averaged worst-case Fractions Brier Score.
    """

    forecast_event, observation_event = xr.align(
        forecast_event,
        observation_event,
        join="exact",
    )

    forecast_fraction = neighborhood_fraction(
        forecast_event,
        window_size=window_size,
        spatial_dims=spatial_dims,
        boundary_modes=boundary_modes,
    )

    observation_fraction = neighborhood_fraction(
        observation_event,
        window_size=window_size,
        spatial_dims=spatial_dims,
        boundary_modes=boundary_modes,
    )

    fbs_field = (
        forecast_fraction
        - observation_fraction
    ) ** 2

    fbs_worst_field = (
        forecast_fraction ** 2
        + observation_fraction ** 2
    )

    if weights is None:
        fbs_mean = fbs_field.mean(
            dim=spatial_dims,
            skipna=True,
        )

        fbs_worst_mean = fbs_worst_field.mean(
            dim=spatial_dims,
            skipna=True,
        )

    else:
        fbs_mean = fbs_field.weighted(
            weights
        ).mean(
            dim=spatial_dims,
            skipna=True,
        )

        fbs_worst_mean = fbs_worst_field.weighted(
            weights
        ).mean(
            dim=spatial_dims,
            skipna=True,
        )

    fbs_mean = float(fbs_mean.values)
    fbs_worst_mean = float(
        fbs_worst_mean.values
    )

    if (
        not np.isfinite(fbs_mean)
        or not np.isfinite(fbs_worst_mean)
        or fbs_worst_mean == 0.0
    ):
        return np.nan, np.nan, np.nan

    fss = (
        1.0
        - fbs_mean / fbs_worst_mean
    )

    return (
        fss,
        fbs_mean,
        fbs_worst_mean,
    )
