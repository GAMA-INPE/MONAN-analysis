import pdf_maker_config as pdf_config
import xarray as xr
import os

def create_folder_structure():
    # Get date to include in output filenames
    os.makedirs(pdf_config.DIR_INPUT_PREPROCESSED, exist_ok=True)
    os.makedirs(pdf_config.DIR_OUTPUT_DATA, exist_ok=True)
    os.makedirs(pdf_config.DIR_OUTPUT_FIGS, exist_ok=True)

def read_and_preprocess_input_data():
    # Read input data
    ds_input = xr.open_dataset(
        f"{pdf_config.DIR_INPUT_RAW}/{pdf_config.FILENAME_INPUT_RAW}"
    )
    if pdf_config.VERBOSE:
        print(f"Input data read successfully from {pdf_config.DIR_INPUT_RAW}/{pdf_config.FILENAME_INPUT_RAW}.")
        print ("Original dataset:")
        print (ds_input)

    # Select the region of interest
    ds_roi = ds_input.sel(
        latitude=slice(float(pdf_config.LAT_MIN), float(pdf_config.LAT_MAX)),
        longitude=slice(float(pdf_config.LON_MIN), float(pdf_config.LON_MAX))
    )
    if pdf_config.VERBOSE:
        print(f"Region selected successfully: "
              f"lat {pdf_config.LAT_MIN} to {pdf_config.LAT_MAX}, "
              f"lon {pdf_config.LON_MIN} to {pdf_config.LON_MAX}.")
        print ("Dataset with the selected latitude and longitude values:")
        print (ds_roi.latitude)
        print (ds_roi.longitude)

    # Select variables of interest
    ds_selected = ds_roi[list(pdf_config.VARIABLES_AND_VALUES_FOR_PDF.keys())]
    if pdf_config.VERBOSE:
        print(f"Variables selected successfully: {list(pdf_config.VARIABLES_AND_VALUES_FOR_PDF.keys())}")
        print ("Dataset with the selected variables:")
        print (ds_selected.var)

    # Save preprocessed data to output folder
    ds_selected.to_netcdf(f"{pdf_config.DIR_INPUT_PREPROCESSED}/preprocessed_data.nc")
