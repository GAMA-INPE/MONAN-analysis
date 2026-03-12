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
# Standard strings for MONAN output filenames
## Standard prefix in output filenames
PREFIX_STRING = "MONAN_DIAG_G_POS_GFS"
## Strings for each grid configuration
GRID_DICT = {
    "10km_uniform": "x5898242",
    "24km_uniform": "x1024002"
    }
## Strings for each vertical level configuration
VERTICAL_LEVEL_DICT = {
    "30": "L30",
    "55": "L55"
    }
## Domains
DOMAIN_DICT = {
    "global": {
        "lat": (-90, 90),
        "lon": (0, 360)
    },
    "south_america": {
        "lat": (-55, 20),
        "lon": (275, 340)
    },
    "central_america_and_caribbean": {
        "lat": (-10, 35),
        "lon": (242, 335)
    }
}
# Standard date format in MONAN output filenames
DATE_FORMAT_STRING = "%Y%m%d%H"