import pdf_maker_config as pdf_config
import xarray as xr
import os
import numpy as np
import matplotlib.pyplot as plt
import subprocess

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

def build_pdf():
    # Read preprocessed data
    ds_preprocessed = xr.open_dataset(f"{pdf_config.DIR_INPUT_PREPROCESSED}/preprocessed_data.nc")
    
    if pdf_config.VERBOSE:
        print(f"Preprocessed data read successfully from {pdf_config.DIR_INPUT_PREPROCESSED}/preprocessed_data.nc.")
        print ("Dataset with the preprocessed data:")
        print (ds_preprocessed)

    # Loop through each variable and build PDF
    for variable, params in pdf_config.VARIABLES_AND_VALUES_FOR_PDF.items():
        # Extract the variable data
        var_data = ds_preprocessed[variable].values.flatten()

        # Extract the unit from the metadata
        unit = ds_preprocessed[variable].attrs.get("units", "unknown")

        # Build histogram
        hist, bin_edges = np.histogram(var_data, bins=np.arange(params["min"], params["max"] + params["bin_size"], params["bin_size"]))
        probabilities = hist / np.sum(hist)

        # Save histogram data to output folder
        np.savez(f"{pdf_config.DIR_OUTPUT_DATA}/{variable}_histogram.npz", hist=hist, bin_edges=bin_edges)

        # Plot pdf
        plt.figure()
        plt.bar(bin_edges[:-1], probabilities, width=params["bin_size"], edgecolor='black')
        plt.xlabel(f"{variable} ({unit})")
        plt.ylabel('Probability')
        plt.title(f'PDF of {variable}, bin size = {params["bin_size"]}, min = {params["min"]}, max = {params["max"]}')
        plt.savefig(f"{pdf_config.DIR_OUTPUT_FIGS}/{variable}_histogram.png")

        if pdf_config.VERBOSE:
            print(f"Histogram for variable '{variable}' built and saved successfully.")

def cp_config_files():
    # Analysis-specific config file
    ## Get absolute path to pdf_maker/, where pdf_maker_config.py is located
    pdf_config_dir = os.path.dirname(os.path.abspath(__file__))
    ## Construct path to analysis-specific config file
    pdf_config_file_path = os.path.join(pdf_config_dir, "pdf_maker_config.py")
    ## Copy analysis-specifig config file
    subprocess.run(["cp", pdf_config_file_path, pdf_config.DIR_OUTPUT_DATA], check=True)
    if pdf_config.VERBOSE:
        print(f"Config file copied to {pdf_config.DIR_OUTPUT_DATA}/pdf_maker_config.py for reference.")