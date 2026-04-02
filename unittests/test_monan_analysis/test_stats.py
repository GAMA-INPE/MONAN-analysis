import pytest
import xarray as xr
import numpy as np
import monan_analysis.stats as stats

# Helper function to create a synthetic xarray.Dataset
def create_test_dataset(data=np.ones((2, 2, 3, 3)), dims=("Time", "level", "latitude", "longitude")):
    shape = (2, 2, 3, 3)
    coords = {
        "Time": np.arange(shape[0]),
        "level": np.arange(shape[1]),
        "latitude": np.linspace(-90, 90, shape[2]),
        "longitude": np.linspace(0, 360, shape[3], endpoint=False),
    }
    return xr.Dataset({"var": (dims, np.array(data).reshape(shape))}, coords=coords)

def test_bias():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=np.ones((2, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((2, 2, 3, 3)))
    # Correct result from bias operation: dataset containing only values 2
    correct_result = create_test_dataset(data=2*np.ones((2, 2, 3, 3)))  # Bias = predictions - observations
    # Calculated result from operation
    calculated_result = stats.bias(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_bias_mean():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=np.ones((2, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((2, 2, 3, 3)))
    # Correct result from bias + mean operation: dataset containing a 
    # scalar value 2
    correct_result = create_test_dataset() 
    correct_result["var"] = 2.
    # Calculated result from operation
    calculated_result = stats.bias_mean(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_relative_error_all_positive():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=np.ones((2, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((2, 2, 3, 3)))
    # Correct result from relative error operation: dataset containing only values 200%
    correct_result = create_test_dataset(data=200*np.ones((2, 2, 3, 3)))
    calculated_result = stats.relative_error(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_relative_error_pred_positive_obs_negative():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=-np.ones((2, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((2, 2, 3, 3)))
    # Correct result from relative error operation: dataset containing only values 200%
    correct_result = create_test_dataset(data=400*np.ones((2, 2, 3, 3)))
    calculated_result = stats.relative_error(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_relative_error_mean_all_positive():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=np.ones((2, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((2, 2, 3, 3)))
    # Correct result from relative error mean operation: dataset 
    # containing only a scalar 200%
    correct_result = create_test_dataset() 
    correct_result["var"] = 200.
    calculated_result = stats.relative_error_mean(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_relative_error_mean_pred_positive_obs_negative():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=-np.ones((2, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((2, 2, 3, 3)))
    # Correct result from relative error mean operation: dataset 
    # containing only a scalar 200%
    correct_result = create_test_dataset() 
    correct_result["var"] = 400.
    calculated_result = stats.relative_error_mean(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_rmse():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=np.ones((2, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((2, 2, 3, 3)))
    # Correct result from rmse operation: dataset 
    # containing only a scalar 2
    correct_result = create_test_dataset() 
    correct_result["var"] = 2.
    calculated_result = stats.rmse(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)    