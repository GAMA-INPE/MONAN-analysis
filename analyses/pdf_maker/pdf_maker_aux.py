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
        f"{pdf_config.DIR_INPUT}/{pdf_config.FILENAME_INPUT}"
    )

    if pdf_config.VERBOSE:
        print(f"Input data read successfully from {pdf_config.DIR_INPUT}/{pdf_config.FILENAME_INPUT}.")

    # Select the region of interest
    ds_roi = ds_input.sel(
        latitude=slice(float(pdf_config.LAT_MIN), float(pdf_config.LAT_MAX)),
        longitude=slice(float(pdf_config.LON_MIN), float(pdf_config.LON_MAX))
    )

    if pdf_config.VERBOSE:
        print(f"Data read and preprocessed successfully. Region of interest: "
              f"lat {pdf_config.LAT_MIN} to {pdf_config.LAT_MAX}, "
              f"lon {pdf_config.LON_MIN} to {pdf_config.LON_MAX}.")
        print (ds_roi.latitude)
        print (ds_roi.longitude)

    # Save preprocessed data to output folder


    #return ds_filepath