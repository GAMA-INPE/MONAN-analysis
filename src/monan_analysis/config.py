# -*- coding: utf-8 -*-
"""
config.py

Description
-----------
This configuration file contains general-purpose settings and constants that are
shared across multiple analyses. It includes reusable strings, default
parameters, and other general configurations.

Usage
-----
- Import this file in scripts that require general-purpose settings.
- Avoid adding project-specific configurations to this file.

Examples:
- from monan_analysis.config import PREFIX_STRING
or 
- import monan_analysis.config as config
  prefix_string = config.PREFIX_STRING

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot. 
"""
# Standard strings for filenames
PREFIX_STRING = "MONAN_DIAG_G_POS_GFS"
GRID_10KM_UNIFORM_STRING = "x5898242"
GRID_24KM_UNIFORM_STRING = "x1024002"
VERTICAL_LEVELS_STRING = "L55"

# Standard date configuration
DATE_FORMAT = '%Y%m%d%H'