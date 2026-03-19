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

def example_function_stats():
    print ("this is a function imported from the stats.py module.")

def bias(observations, predictions):
    """Calculate the bias between observations and predictions."""
    predictions = predictions.squeeze()
    observations = observations.squeeze()
    return (predictions - observations)

def bias_mean(observations, predictions):
    """Calculate the mean bias between observations and predictions."""
    predictions = predictions.squeeze()
    observations = observations.squeeze()
    return bias(observations, predictions).mean()

def absolute_error(observations, predictions):
    """Calculate the absolute error between observations and predictions."""
    predictions = predictions.squeeze()
    observations = observations.squeeze()
    return abs(predictions - observations)

def absolute_error_mean(observations, predictions):
    """Calculate the mean absolute error between observations and predictions."""
    predictions = predictions.squeeze()
    observations = observations.squeeze()
    return absolute_error(observations, predictions).mean()

def rmse(observations, predictions):
    """Calculate the root mean square error between observations and predictions."""
    predictions = predictions.squeeze()
    observations = observations.squeeze()
    return ((predictions - observations) ** 2).mean() ** 0.5

def anomaly_correlation(observations, predictions):
    """Calculate the anomaly correlation between observations and predictions."""
    predictions = predictions.squeeze()
    observations = observations.squeeze()
    obs_anomaly = observations - observations.mean()
    pred_anomaly = predictions - predictions.mean()
    return (obs_anomaly * pred_anomaly).mean() / ((obs_anomaly ** 2).mean() ** 0.5 * (pred_anomaly ** 2).mean() ** 0.5)