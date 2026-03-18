# -*- coding: utf-8 -*-
"""
vertical_analysis_aux.py

Based on a script by Andre Lyra (andre.lyra@inpe.br)
Last update: Feb 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)

Description
-----------
This module contains auxiliary functions to be used specifically in this analysis.

Usage
-----
- Import this module in scripts that are part of this specific analysis.
- Do not use this module for defining general-purpose functions.

Examples:
- from vertical_analysis_aux import setup_parser
or
- import vertical_analysis_aux as va_aux
  args = va_aux.setup_parser()

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot.    
"""

import monan_analysis.config as config
import monan_analysis.io as io
import monan_analysis.utils as utils
import monan_analysis.plots as plots
import monan_analysis.config as config
import vertical_analysis_config as va_config
import argparse
import xarray as xr

def setup_parser():
    """Set up the argument parser with common arguments."""
    parser = argparse.ArgumentParser(
        description="Vertical analysis of MONAN simulations.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--year', type=str, help='Year of initial conditions (e.g. 2025)')
    parser.add_argument('--month', type=str, help='Month of initial conditions (e.g. 12)')
    parser.add_argument('--day', type=str, help='Day of initial conditions (e.g. 01)')
    parser.add_argument('--hour', type=str, help='Hour of initial conditions (e.g. 00)')
    parser.add_argument('--time_window', type=int, help='Time window between initial conditions')
    
    args = parser.parse_args()
    return args