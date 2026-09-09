import pdf_maker_config as pdf_config
import xarray as xr

def read_input_data():
    
    # Read input data
    ds_input = xr.open_dataset(
        f"{pdf_config.DIR_INPUT}/{pdf_config.FILENAME_INPUT}"
    )

    print (ds_input)

    #return ds_filepath