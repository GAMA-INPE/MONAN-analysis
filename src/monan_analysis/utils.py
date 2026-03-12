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

def get_final_date_from_initial_date(date_in_datetime, time_window):
    date_final_in_datetime = date_in_datetime + datetime.timedelta(hours=int(time_window))
    return date_final_in_datetime

def get_lon_from_minus_180_to_180(lon_range):
    if lon_range[0] >= 0 and lon_range[1] > 180:
       lon_range = (lon_range[0] - 360, lon_range[1] - 360)
    # Validate longitude and latitude ranges
    if lon_range[0] == lon_range[1]:
        raise ValueError(f"Invalid longitude range: {lon_range}. Ensure min_lon != max_lon.")
    return lon_range
