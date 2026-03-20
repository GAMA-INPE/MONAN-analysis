# -*- coding: utf-8 -*-
"""
stats.py

Description
-----------
This module contains functions for calculations of statistics of analyses.

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

def example_function_stats():
    print ("this is a function imported from the stats.py module.")

def bias(predictions, observations):
    """Calculate the bias between predictions and observations while preserving dataset structure."""
    # Ensure inputs are xarray Datasets
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    # Perform the subtraction for each data variable
    result = predictions.copy()
    for var in predictions.data_vars:
        result[var] = predictions[var] - observations[var]
    
    return result

def bias_mean(predictions, observations):
    """Calculate the mean bias between predictions and observations."""
    # Ensure inputs are xarray Datasets
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    # Perform the subtraction for each data variable and then take the mean
    result = predictions.copy()
    for var in predictions.data_vars:
        result[var] = (predictions[var] - observations[var]).mean()
    
    return result

def relative_error(predictions, observations):
    """Calculate the relative error between predictions and observations."""
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    result = predictions.copy()
    for var in predictions.data_vars:
        result[var] = (predictions[var] - observations[var]) / observations[var] * 100
    
    return result

def relative_error_mean(predictions, observations):
    """Calculate the mean relative error between predictions and observations."""
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    result = predictions.copy()
    for var in predictions.data_vars:
        result[var] = ((predictions[var] - observations[var]) / observations[var] * 100).mean()
    
    return result

def rmse(predictions, observations):
    """Calculate the root mean square error between predictions and observations."""
    if not isinstance(predictions, xr.Dataset) or not isinstance(observations, xr.Dataset):
        raise TypeError("Both predictions and observations must be xarray Datasets.")
    
    result = predictions.copy()
    for var in predictions.data_vars:
        result[var] = (((predictions[var] - observations[var]) ** 2).mean()) ** 0.5
    
    return result