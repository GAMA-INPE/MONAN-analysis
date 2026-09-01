import pytest
import xarray as xr
import numpy as np
import monan_analysis.stats as stats

def create_test_dataset(data=np.ones((10, 2, 3, 3)), dims=("Time", "level", "latitude", "longitude")):
    shape = (10, 2, 3, 3)
    coords = {
        "Time": np.arange(shape[0]),
        "level": np.arange(shape[1]),
        "latitude": np.linspace(-90, 90, shape[2]),
        "longitude": np.linspace(0, 360, shape[3], endpoint=False),
    }
    return xr.Dataset({"var": (dims, np.array(data).reshape(shape))}, coords=coords)

def create_test_dataset_without_Time(data=np.ones((2, 3, 3)), dims=("level", "latitude", "longitude")):
    shape = (2, 3, 3)
    coords = {
        "level": np.arange(shape[0]),
        "latitude": np.linspace(-90, 90, shape[1]),
        "longitude": np.linspace(0, 360, shape[2], endpoint=False),
    }
    return xr.Dataset({"var": (dims, np.array(data).reshape(shape))}, coords=coords)

def test_bias():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=np.ones((10, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((10, 2, 3, 3)))
    # Correct result from bias operation: dataset containing only values 2
    correct_result = create_test_dataset(data=2*np.ones((10, 2, 3, 3)))  # Bias = predictions - observations
    # Calculated result from operation
    calculated_result = stats.bias(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_bias_mean():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=np.ones((10, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((10, 2, 3, 3)))
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
    observations = create_test_dataset(data=np.ones((10, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((10, 2, 3, 3)))
    # Correct result from relative error operation: dataset containing only values 200%
    correct_result = create_test_dataset(data=200*np.ones((10, 2, 3, 3)))
    calculated_result = stats.relative_error(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_relative_error_pred_positive_obs_negative():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=-np.ones((10, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((10, 2, 3, 3)))
    # Correct result from relative error operation: dataset containing only values 400%
    correct_result = create_test_dataset(data=400*np.ones((10, 2, 3, 3)))
    calculated_result = stats.relative_error(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_relative_error_pred_negative_obs_positive():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=5*np.ones((10, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=-10*np.ones((10, 2, 3, 3)))
    # Correct result from relative error operation: dataset containing only values -300%
    correct_result = create_test_dataset(data=-300*np.ones((10, 2, 3, 3)))
    calculated_result = stats.relative_error(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_relative_error_mean_all_positive():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=np.ones((10, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((10, 2, 3, 3)))
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
    observations = create_test_dataset(data=-np.ones((10, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((10, 2, 3, 3)))
    # Correct result from relative error mean operation: dataset 
    # containing only a scalar 400%
    correct_result = create_test_dataset() 
    correct_result["var"] = 400.
    calculated_result = stats.relative_error_mean(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_relative_error_mean_pred_negative_obs_positive():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=2*np.ones((10, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=-3*np.ones((10, 2, 3, 3)))
    # Correct result from relative error mean operation: dataset 
    # containing only a scalar -250%
    correct_result = create_test_dataset() 
    correct_result["var"] = -250.
    calculated_result = stats.relative_error_mean(
        predictions=predictions,
        observations=observations
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)

def test_rmse():
    # Dataset for observations containing only values 1
    observations = create_test_dataset(data=np.ones((10, 2, 3, 3)))
    # Dataset for predictions containing only values 3
    predictions = create_test_dataset(data=3*np.ones((10, 2, 3, 3)))
    # Correct result from rmse operation: dataset 
    # containing only a scalar 2
    correct_result = create_test_dataset_without_Time(data=2.0*np.ones((2, 3, 3)))
 
    # Calculate rmse along time dimension
    calculated_result = stats.rmse(
        predictions=predictions,
        observations=observations,
        dim="Time"
        )
    # Test if calculated and correct results match
    xr.testing.assert_equal(calculated_result, correct_result)    

def test_anomaly_correlation_perfect_correlation():
    # Create sine wave data for predictions and observations
    time = np.linspace(0, 2 * np.pi, 10)  # 10 time steps
    sine_wave = np.sin(time)  # Sine wave for the time dimension
    
    # Expand sine wave to match the test_dataset shape (10, 2, 3, 3)
    ## Reshape to (10, 1, 1, 1)
    sine_wave = sine_wave[:, np.newaxis, np.newaxis, np.newaxis]  
    ## Tile to (10, 2, 3, 3)
    sine_wave = np.tile(sine_wave, (1, 2, 3, 3))
    # Create data with correct dimensions
    predictions_data = 3 * sine_wave
    observations_data = 2 * sine_wave
    
    # Use create_test_dataset to generate datasets
    predictions = create_test_dataset(data=predictions_data)
    observations = create_test_dataset(data=observations_data)
    
    # Correct result: perfect correlation (1.0)
    correct_result = create_test_dataset_without_Time(data=1.0*np.ones((2, 3, 3)))
    
    # Calculate anomaly correlation
    calculated_result = stats.anomaly_correlation_coefficient(predictions=predictions, observations=observations, dim="Time")
    
    # Test if calculated and correct results match
    xr.testing.assert_allclose(calculated_result, correct_result)

def test_anomaly_correlation_perfect_anti_correlation():
    # Create sine wave data for predictions and observations
    time = np.linspace(0, 2 * np.pi, 10)  # 10 time steps
    sine_wave = np.sin(time)  # Sine wave for the time dimension
    
    # Expand sine wave to match the test_dataset shape (10, 2, 3, 3)
    ## Reshape to (10, 1, 1, 1)
    sine_wave = sine_wave[:, np.newaxis, np.newaxis, np.newaxis]  
    ## Tile to (10, 2, 3, 3)
    sine_wave = np.tile(sine_wave, (1, 2, 3, 3))
    # Create data with correct dimensions
    predictions_data = 2 * sine_wave
    observations_data = -4 * sine_wave
    
    # Use create_test_dataset to generate datasets
    predictions = create_test_dataset(data=predictions_data)
    observations = create_test_dataset(data=observations_data)
    
    # Correct result: perfect anti-correlation (-1.0)
    correct_result = create_test_dataset_without_Time(data=-1.0*np.ones((2, 3, 3)))
    
    # Calculate anomaly correlation
    calculated_result = stats.anomaly_correlation_coefficient(predictions=predictions, observations=observations, dim="Time")
    
    # Test if calculated and correct results match
    xr.testing.assert_allclose(calculated_result, correct_result)

def test_anomaly_correlation_perfect_anti_correlation_with_offset():
    # Create sine wave data for predictions and observations
    time = np.linspace(0, 2 * np.pi, 10)  # 10 time steps
    sine_wave = np.sin(time)  # Sine wave for the time dimension
    
    # Expand sine wave to match the test_dataset shape (10, 2, 3, 3)
    ## Reshape to (10, 1, 1, 1)
    sine_wave = sine_wave[:, np.newaxis, np.newaxis, np.newaxis]  
    ## Tile to (10, 2, 3, 3)
    sine_wave = np.tile(sine_wave, (1, 2, 3, 3))
    # Create data with correct dimensions
    predictions_data = 2 * sine_wave + 5
    observations_data = -4 * sine_wave - 2
    
    # Use create_test_dataset to generate datasets
    predictions = create_test_dataset(data=predictions_data)
    observations = create_test_dataset(data=observations_data)
    
    # Correct result: perfect anti-correlation (-1.0)
    correct_result = create_test_dataset_without_Time(data=-1.0*np.ones((2, 3, 3)))
    
    # Calculate anomaly correlation
    calculated_result = stats.anomaly_correlation_coefficient(predictions=predictions, observations=observations, dim="Time")
    
    # Test if calculated and correct results match
    xr.testing.assert_allclose(calculated_result, correct_result)

def test_anomaly_correlation_zero_correlation_with_offset():
    # Create sine wave data for predictions and observations
    time = np.linspace(0, 2 * np.pi, 10)  # 10 time steps
    sine_wave = np.sin(time)  # Sine wave for the time dimension
    cos_wave = np.cos(time)  # Cosine wave for the time dimension (orthogonal to sine wave)
    
    # Expand sine and cos wave to match the test_dataset shape (10, 2, 3, 3)
    ## Reshape to (10, 1, 1, 1)
    sine_wave = sine_wave[:, np.newaxis, np.newaxis, np.newaxis]  
    cos_wave = cos_wave[:, np.newaxis, np.newaxis, np.newaxis]
    ## Tile to (10, 2, 3, 3)
    sine_wave = np.tile(sine_wave, (1, 2, 3, 3))
    cos_wave = np.tile(cos_wave, (1, 2, 3, 3))
    # Create data with correct dimensions
    predictions_data = 2 * cos_wave + 5
    observations_data = -4 * sine_wave - 2
    
    # Use create_test_dataset to generate datasets
    predictions = create_test_dataset(data=predictions_data)
    observations = create_test_dataset(data=observations_data)
    
    # Correct result: zero correlation (0.0)
    correct_result = create_test_dataset_without_Time(data=np.zeros((2, 3, 3)))
    
    # Calculate anomaly correlation
    calculated_result = stats.anomaly_correlation_coefficient(predictions=predictions, observations=observations, dim="Time")
    
    # Test if calculated and correct results match
    xr.testing.assert_allclose(calculated_result, correct_result)


def create_fss_event(data, lat=None, lon=None):
    # Create an xarray DataArray representing a binary event field for FSS testing.
    data = np.asarray(data, dtype=float)

    if lat is None:
        lat = np.arange(data.shape[0], dtype=float)

    if lon is None:
        lon = np.arange(data.shape[1], dtype=float)

    return xr.DataArray(
        data,
        coords={
            "lat": lat,
            "lon": lon,
        },
        dims=("lat", "lon"),
    )


def test_neighborhood_fraction_window_one():
    # Test that the neighborhood_fraction function returns the same event field when the window size is 1.
    event = create_fss_event([
        [1.0, 0.0],
        [np.nan, 1.0],
    ])

    # The correct result is the same as the input event field since the window size is 1.
    calculated_result = stats.neighborhood_fraction(
        event=event,
        window_size=1,
    )

    xr.testing.assert_allclose(
        calculated_result,
        event,
    )


def test_neighborhood_fraction_constant_boundaries():
    # Test that the neighborhood_fraction function correctly calculates the neighborhood fraction with constant boundary conditions.
    event = create_fss_event([
        [0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0],
    ])

    # The correct result is a 3x3 array where the center cell has a neighborhood fraction of 1/9, and the adjacent cells have a neighborhood fraction of 1/6, while the corners have a neighborhood fraction of 1/4.
    correct_result = create_fss_event([
        [1.0 / 4.0, 1.0 / 6.0, 1.0 / 4.0],
        [1.0 / 6.0, 1.0 / 9.0, 1.0 / 6.0],
        [1.0 / 4.0, 1.0 / 6.0, 1.0 / 4.0],
    ])

    # Calculate the neighborhood fraction with a window size of 3 and constant boundary conditions.
    calculated_result = stats.neighborhood_fraction(
        event=event,
        window_size=3,
        boundary_modes=("constant", "constant"),
    )

    xr.testing.assert_allclose(
        calculated_result,
        correct_result,
    )

def test_neighborhood_fraction_periodic_longitude():
    # Test that the neighborhood_fraction function correctly calculates the neighborhood fraction with periodic boundary conditions in the longitude direction.
    event = create_fss_event([
        [1.0, 0.0, 0.0, 0.0],
    ])

    correct_result = create_fss_event([
        [1.0 / 3.0, 1.0 / 3.0, 0.0, 1.0 / 3.0],
    ])

    calculated_result = stats.neighborhood_fraction(
        event=event,
        window_size=3,
        boundary_modes=("nearest", "wrap"),
    )

    xr.testing.assert_allclose(
        calculated_result,
        correct_result,
    )


def test_fractions_skill_score_perfect_forecast():
    # Test that the fractions_skill_score function returns perfect scores when the forecast and observation events are identical.
    forecast_event = create_fss_event([
        [1.0, 0.0],
        [0.0, 0.0],
    ])

    observation_event = forecast_event.copy()

    fss, fbs, fbs_worst = stats.fractions_skill_score(
        forecast_event=forecast_event,
        observation_event=observation_event,
        window_size=1,
    )

    assert fss == pytest.approx(1.0)
    assert fbs == pytest.approx(0.0)
    assert fbs_worst == pytest.approx(0.5)


def test_fractions_skill_score_displaced_events_window_one():
    forecast_event = create_fss_event([
        [1.0, 0.0],
        [0.0, 0.0],
    ])

    observation_event = create_fss_event([
        [0.0, 1.0],
        [0.0, 0.0],
    ])

    fss, fbs, fbs_worst = stats.fractions_skill_score(
        forecast_event=forecast_event,
        observation_event=observation_event,
        window_size=1,
    )

    assert fss == pytest.approx(0.0)
    assert fbs == pytest.approx(0.5)
    assert fbs_worst == pytest.approx(0.5)


def test_fractions_skill_score_no_events():
    # Test that the fractions_skill_score function returns NaN scores when there are no events in either the forecast or observation.
    forecast_event = create_fss_event([
        [0.0, 0.0],
        [0.0, 0.0],
    ])

    observation_event = forecast_event.copy()

    fss, fbs, fbs_worst = stats.fractions_skill_score(
        forecast_event=forecast_event,
        observation_event=observation_event,
        window_size=1,
    )

    assert np.isnan(fss)
    assert np.isnan(fbs)
    assert np.isnan(fbs_worst)


def test_fractions_skill_score_with_weights():
    # Test that the fractions_skill_score function correctly incorporates weights into the calculation.
    forecast_event = create_fss_event([
        [1.0, 0.0],
        [0.0, 0.0],
    ])

    observation_event = create_fss_event([
        [1.0, 0.0],
        [1.0, 0.0],
    ])

    weights = xr.DataArray(
        [1.0, 2.0],
        coords={"lat": forecast_event["lat"]},
        dims=["lat"],
    )

    fss, fbs, fbs_worst = stats.fractions_skill_score(
        forecast_event=forecast_event,
        observation_event=observation_event,
        window_size=1,
        weights=weights,
    )

    assert fss == pytest.approx(0.5)
    assert fbs == pytest.approx(1.0 / 3.0)
    assert fbs_worst == pytest.approx(2.0 / 3.0)