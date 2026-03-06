# -*- coding: utf-8 -*-
"""
vertical_analysis_main.py

Based on a script by Andre Lyra (andre.lyra@inpe.br)
Last update: Feb 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last update: Mar 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)

Description
-----------
Takes in data from MONAN and from GFS and performs an analysis of the vertical structure of MONAN.

Steps:
1. Read data from MONAN and from GFS
2. Preprocess data
3. Calculate statistics
4. Plot and save results

Input
-----
- ds_monan (xr.Dataset): netcdf file containing MONAN data
- ds_gfs (xr.Dataset): netcdf file containing GFS data

Output
------
- RMSE values
- Analysis maps

Main variables
--------------
- RMSE (float64): root mean square error

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot. 
"""

import vertical_analysis_aux as va_aux
import monan_analysis.config as config
import monan_analysis.io as io
import monan_analysis.utils as utils
import xarray as xr
import vertical_analysis_config as vac

if __name__ == "__main__":
    # Get input arguments
    args = va_aux.setup_parser()

    # Get filename for reading MONAN data
    ## Date for initial conditions
    date_init_in_datetime = utils.date_as_datetime(args.year, args.month, args.day, args.hour)
    date_init_in_string = utils.date_as_YYYYMMDDHH_str(args.year, args.month, args.day, args.hour)
    ## Date for end of time window
    date_final_in_datetime = utils.get_final_date_from_initial_date(date_init_in_datetime, args.time_window)
    date_final_in_string = date_final_in_datetime.strftime(config.DATE_FORMAT)
    ## MONAN output filename
    filename = io.get_MONAN_DIAG_filename(date_init_in_string,date_final_in_string)
    print (filename)

    # Read data from MONAN
    ## Get complete path
    filepath = f"{vac.MONAN_PREOP}/{date_init_in_string}/{filename}"
    print (filepath)
    ds_monan = xr.open_dataset(filepath, engine="netcdf4")
    print (ds_monan)