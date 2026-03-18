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
import argparse

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

def setup_parser():
    """Set up the argument parser with common arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--year', type=str, help='Year of initial conditions (e.g. 2025)')
    parser.add_argument('--month', type=str, help='Month of initial conditions (e.g. 12)')
    parser.add_argument('--day', type=str, help='Day of initial conditions (e.g. 01)')
    parser.add_argument('--hour', type=str, help='Hour of initial conditions (e.g. 00)')
    parser.add_argument('--time_window', type=int, help='Time window between initial conditions')
    
    args = parser.parse_args()
    return args