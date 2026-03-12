# -*- coding: utf-8 -*-
"""
io.py

Description
-----------
This module contains functions to be used for input and output operations.

Usage
-----
- Import this module in scripts that require input/output functions.
- Functions in this module should be general-purpose and reusable across different analyses.

Examples:
- from monan_analysis.io import get_MONAN_DIAG_filename
or 
- import monan_analysis.io as io
  filename = io.get_MONAN_DIAG_filename(date_in_string_init, date_in_string_final)

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot. 
"""

import monan_analysis.config as config

def example_function_io():
    print ("this is a function imported from the io.py module.")

def get_MONAN_DIAG_filename(date_in_string_init, date_in_string_final,grid_spec,vertical_level_spec):
    # Get grid string
    try:
        GRID_STRING = config.GRID_DICT[grid_spec]
    except:
        raise ValueError(f"Grid '{grid_spec}' is not recognized. Please choose a valid grid.")
    # Get vertical level string
    try:
        VERTICAL_LEVEL_STRING = config.VERTICAL_LEVEL_DICT[vertical_level_spec]
    except:
        raise ValueError(f"Vertical level configuration '{vertical_level_spec}' is not recognized. " 
                         + "Please choose a valid configuration.")
    
    filename = (f"{config.PREFIX_STRING}_{date_in_string_init}_{date_in_string_final}.00.00."
                f"{GRID_STRING}{VERTICAL_LEVEL_STRING}.nc")
    return filename