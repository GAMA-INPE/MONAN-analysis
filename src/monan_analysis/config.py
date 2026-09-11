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
PREFIX_MONAN_SHORT = "MONAN_DIAG"
# Global or regional domain specifications
DOMAIN_TYPE_DICT = {
    "global": "G",
    "regional": "R"
}
INITIAL_CONDITIONS_TYPE_DICT = {
    "GFS": "GFS",
    "ERA5": "ERA"
}
# Standard prefix in MONAN output filenames
PREFIX_MONAN_DIAG_STRING = "MONAN_DIAG_G_POS_GFS"
# Strings for each grid configuration
GRID_DICT = {
    "10km_uniform": "x5898242",
    "24km_uniform": "x1024002",
    "30km_uniform": "x655362",
    "30km_uniform_Amazonia": "x655362_AMAZONIA"
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
# Standard settings for ERA5 analysis data
#===================================================================================================
# Dictionary mapping levels to ERA5 name convention
ERA5_LEVEL_DICT = {"pressure_levels":"pl", "single_levels":"sl"}
# Dictionary mapping ERA5 var names to MONAN var names
ERA5_TO_MONAN_VAR_DICT = {
    "swdnb": {
        "era5_name" : "ssrd",
        "era5_longname" :"surface_solar_radiation_downwards"
        },
    "swdnbc": {
        "era5_name" : "ssrdc",
        "era5_longname" :"surface_solar_radiation_downward_clear_sky",
        },
    "lwupt": {        
        "era5_name": "ttr",
        "era5_longname" :"top_net_thermal_radiation",
        },
    "lwuptc": {
        "era5_name": "ttrc",
        "era5_longname": "top_net_thermal_radiation_clear_sky",
        },
    "swdnt": {
        "era5_name" : "tisr",
        "era5_longname" : "toa_incident_solar_radiation",
        },
    "precipc": {
        "era5_name" : "tclw",
        "era5_longname" :"total_column_cloud_liquid_water",
        },
    "precipi": {
        "era5_name": "tciw",
        "era5_longname" :"total_column_cloud_ice_water",
        },
    "precipw": {
        "era5_name" : "tcwv",
        "era5_longname" :"total_column_water_vapour",
        },

}
#===================================================================================================
# Standard settings for CRES  data
#===================================================================================================
CERES_DATASET="CER_SYN1deg"
CERES_EDITION_DICT={"4A":"Terra-Aqua-MODIS_Edition4A",
                    "4B":"Terra-Aqua-NOAA20_Edition4B"}
CERES_CODE_DICT = {"1Hour_Terra-Aqua-MODIS_Edition4A":"407406",
                   "1Hour_Terra-Aqua-NOAA20_Edition4B":"415412",
                   "MHour_Terra-Aqua-MODIS_Edition4A":"407406",
                   "MHour_Terra-Aqua-NOAA20_Edition4B":"407412",}
# Dictionary mapping CERES var names to MONAN var names
CERES_TO_MONAN_VAR_DICT = {
    "swdnb": {
        "ceres_name" : "adj_all_sw_dn",
        },
    "swdnbc": {
        "ceres_name" : "adj_clr_sw_dn", 
        },
    "lwupt": {        
        "ceres_name" : "adj_all_lw_up", 
        },
    "lwuptc": {
        "ceres_name" : "adj_clr_lw_up", 
        },
    "swdnt": {
       "ceres_name" : "toa_sw_insol", 
        },
    "precipc": {
        "ceres_name" : "adj_cld_lwp", 
        },
    "precipi": {
        "ceres_name" : "adj_cld_iwp", 
        },
    "precipw": {
         "ceres_name" : "adj_pw", 
        },

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