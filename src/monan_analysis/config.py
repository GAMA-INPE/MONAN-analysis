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
#===================================================================================================
# Standard settings for MONAN data
#===================================================================================================
# Standard prefix in MONAN output filenames
PREFIX_MONAN_DIAG_STRING = "MONAN_DIAG_G_POS_GFS"
# Strings for each grid configuration
GRID_DICT = {
    "10km_uniform": "x5898242",
    "24km_uniform": "x1024002"
    }
# Strings for each vertical level configuration
VERTICAL_LEVEL_DICT = {
    "30": "L30",
    "55": "L55"
    }
# Standard date format in MONAN output filenames
DATE_FORMAT_STRING = "%Y%m%d%H"
# Variable units
VAR_UNITS_DICT = {
    "temperature": "K",
    "spechum": "kg/kg",
    "zgeo": "m",
    "uzonal": "m/s",
    "umeridional": "m/s"
}
#===================================================================================================
# Standard settings for GFS analysis data
#===================================================================================================
# Standard prefix in GFS analysis filenames
PREFIX_GFS_ANALYSIS_STRING = "GFS_anl"
# Dictionary mapping GFS var names to MONAN var names
GFS_TO_MONAN_VAR_DICT = {
    "time": "Time",
    "t": "temperature",
    "q": "spechum",
    "gh": "zgeo",
    "u": "uzonal",
    "v": "umeridional",
}
#===================================================================================================
# Domain definitions
#===================================================================================================
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
    },
    "northern_hemisphere_20_80": {
        "lat": (20, 80),
        "lon": (0, 360)
    },
    "southern_hemisphere_20_80": {
        "lat": (-80, -20),
        "lon": (0, 360)
    },
    "tropics_20s_20n": {
        "lat": (-20, 20),
        "lon": (0, 360)
    }
}