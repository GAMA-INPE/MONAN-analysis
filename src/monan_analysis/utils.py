# -*- coding: utf-8 -*-
"""
utils.py

Description
-----------
This module contains generally useful auxiliary functions.

Usage
-----
- Import this module in scripts that require auxiliary functions.
- Functions in this module should be general-purpose and reusable across different analyses.

Examples:
- from monan_analysis.utils import date_as_datetime
or 
- import monan_analysis.utils as utils
  date_as_datetime = utils.date_as_datetime(year,month,day,hour)

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot. 
"""

import datetime
import os
import subprocess

def example_function_utils():
    print ("this is a function imported from the utils.py module.")

def get_date_as_datetime(year,month,day,hour):
    date_in_datetime = datetime.datetime(
            int(year), 
            int(month), 
            int(day), 
            int(hour)
        )
    return date_in_datetime

def get_date_as_YYYYMMDDHH_str(year,month,day,hour):
    date_in_string = f"{year}{month}{day}{hour}" 
    return date_in_string

def get_date_as_YYYYMM_str(year,month):
    date_in_string = f"{year}{month}" 
    return date_in_string

def get_final_date_from_initial_date(date_in_datetime, time_window):
    date_final_in_datetime = date_in_datetime + datetime.timedelta(hours=int(time_window))
    return date_final_in_datetime

def remap_cdo(ref_nc, input_nc, output_nc):
    """ 
    Remap input_nc to the grid of ref_nc 
    and save the output in output_nc using CDO.
    """
    if not os.path.exists(output_nc):
        subprocess.run(
            ["cdo", "-f", "nc", f"-remapcon,{ref_nc}", input_nc, output_nc],
            check=True
        )
