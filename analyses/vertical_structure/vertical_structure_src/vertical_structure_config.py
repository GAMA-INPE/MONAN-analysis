# -*- coding: utf-8 -*-
"""
vertical_structure_config.py

Description
-----------
This configuration file contains settings and variables specific to the current analysis.
It includes paths to data files, analysis-specific parameters, and other settings that
are unique to this particular analysis.

Usage
-----
- Import this file in scripts that are part of this specific analysis.
- Do not use this file for general-purpose configurations.

Example:
    from analysis_folder.config import DATA_PATH, ANALYSIS_PARAM

Updates
-------
- May 2026, Andre Lyra: Added the APPLY_PRESSURE_LEVEL_VALIDITY_MASK flag
to enable or disable the topography mask in the vertical structure analysis.    

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot.    
"""
#===================================================================================================
# Selection of level of detail of log messages
#===================================================================================================
# 0: log messages from vertical_analysis_main.py only
# 1: log messages from vertical_analysis_main.py + vertical_analysis_aux.py
# 2: log messages from vertical_analysis_main.py + vertical_analysis_aux.py + monan_analysis modules
SEL_VERBOSE_LEVEL = 2
#===================================================================================================
# General analysis configurations
#===================================================================================================
# Prediction model to analyze (e.g. "monan", "gfs_analysis" (gfs forecast + assimilation), "gfs", "bam")
PREDICTION_MODEL = "gfs_analysis"
# Reference data (e.g. "gfs_analysis", "era5")
REFERENCE_DATA = "gfs_analysis"
# Date and forecast time window for analysis
YEAR = "2026"
MONTH = "06"
DAY = "30"
HOUR = "00"
TIME_WINDOW = "24"
# Domains for spatial analyses (maps)
DOMAINS_TO_ANALYZE = [
    "global", 
    "south_america", 
    "central_america_and_caribbean"
    ]
# Domains for summary analyses
SUMMARY_DOMAINS_TO_ANALYZE = [
    "global",
    "south_america",
    "central_america_and_caribbean",
    "northern_hemisphere_20_80",
    "southern_hemisphere_20_80",
    "tropics_20s_20n",
]
#===================================================================================================
# MONAN configurations
#===================================================================================================
# Grid specification
GRID_SPEC_MONAN = "10km_uniform"
# Vertical level specification
VERTICAL_LEVEL_SPEC_MONAN = "55"
# Variables to analyze
VARIABLES_TO_ANALYZE_MONAN = [
    "temperature",
    "spechum",
    "zgeo",
    "uzonal",
    "umeridional",
    ]
# Vertical levels (Pa) to analyze
VERTICAL_LEVELS_TO_ANALYZE_MONAN = [
#    "92500", "85000", "70000", "50000", "40000", "30000", "25000", "20000", "15000", "10000", "7000", "5000", "3000", "2000", "1000", "300"
    "92500", "85000", "70000", "50000", "40000", "30000", "25000", "10000", "3000", "300"
    ]
#===================================================================================================
# GFS configurations
#===================================================================================================
# Name of data stream from GFS to read (e.g. "levels" or "surface")
STREAM_NAME_GFS = "levels"
#===================================================================================================
# Data interpolation configurations
#===================================================================================================
# Type of data interpolation
INTERPOL_TYPE = "monan_to_gfs" # "monan_to_gfs" or "gfs_to_monan"
#===================================================================================================
# Statistics configurations
#===================================================================================================
STATS_METRICS_TO_ANALYZE = [
    "bias",
    "relative_error"
    ]
# Whether to write a CSV file with the regional summary of statistics
WRITE_REGIONAL_SUMMARY_CSV = True
#===================================================================================================
# Plot configurations
#===================================================================================================
# Divergin colormaps to use for each variable in plotting
COLORMAP_DIVERGING_BY_VAR_DICT = {
    "temperature": "coolwarm",
    "spechum": "coolwarm_r",
    "zgeo": "PiYG",
    "uzonal": "PuOr",
    "umeridional": "PuOr"
}
# Limits of plots for each variable, metric, and vertical level (if applicable) 
PLOT_LIMITS_BY_VAR_METRIC_LAYER = {
    "temperature": {
        "bias": {
            "low": (-5, 5),
            "mid": (-2, 2),
            "high": (-3, 3),            
        },
        "rmse": {
            "low": (0, 5),
            "mid": (0, 3),
            "high": (0, 2),
        },
    },
    "spechum": {
        "bias": {
            "low": (-2, 2),      # g/kg
            "mid": (-1, 1),      # g/kg
            "high": (-100, 100), # mg/kg
        },
        "rmse": {
            "low": (0, 4),
            "mid": (0, 2),
            "high": (0, 200),
        },
    },
    "zgeo": {
        "bias": {
            "low": (-20, 20),      
            "mid": (-30, 30),      
            "high": (-40, 40), 
        },
        "rmse": {
            "low": (0, 50),
            "mid": (0, 50),
            "high": (0, 100),
        },
    },
}
# Limits of plots for specific pressure levels:
# Keys must use the same pressure-level values used in VERTICAL_LEVELS_TO_ANALYZE, in Pa
# These limits have priority over PLOT_LIMITS_BY_VAR_METRIC_LAYER
PLOT_LIMITS_BY_VAR_METRIC_LEVEL = {
    "temperature": {
        "bias": {
            "300": (-45, 45),   # K, 3 hPa
        },
        "rmse": {
            "300": (0, 45),     # K, 3 hPa
        },
    },
    "spechum": {
        "bias": {
            "300": (-250, 250), # ×0.01 mg/kg, 3 hPa
        },
        "rmse": {
            "300": (0, 250),    # ×0.01 mg/kg, 3 hPa
        },
    },
    "zgeo": {
        "bias": {
            "300": (-900, 900), # m, 3 hPa
        },
        "rmse": {
            "300": (0, 900),    # m, 3 hPa
        },
    },
}
#===================================================================================================
# Directory paths
#===================================================================================================
#DIR_MONAN_PREOP = "/lustre/projetos/monan_adm/monan/ecf_PREOPER/MONAN-WorkFlow-OPER/MONAN_PRE_OPER/MONAN/scripts_CD-CT/dataout/flushout"
DIR_MONAN_PREOP = "/lustre/projetos/ioper/models/MONAN-WorkFlow-OPER/MONAN_PRE_OPER/posTMP"
DIR_GFS_ANALYSIS = "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/vert_struct/GFS"
DIR_GFS = "/oper/dados/ioper/tempo/GFS/0p25/brutos"
DIR_CARTOPY_DATA = "/lustre/projetos/monan_gam/andre.lyra/cartopy"
DIR_OUTPUT = f"/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/output_2026060100_to_2026063000"
DIR_OUTPUT_FIGS = f"{DIR_OUTPUT}/figs"
DIR_OUTPUT_DATA = f"{DIR_OUTPUT}/data"
DIR_INPUT = f"/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/input_2026060100_to_2026063000"
DIR_INPUT_INTERMEDIATE = f"{DIR_INPUT}/intermediate"
DIR_INPUT_PROCESSED = f"{DIR_INPUT}/processed"
DIR_INPUT_RAW = f"{DIR_INPUT}/raw"
#===================================================================================================
# Pressure-level validity mask configurations
#===================================================================================================
# If True, apply a mask based on surface pressure from MONAN and GFS before calculating statistics.
# The mask excludes grid points where the selected pressure level is greater than the surface pressure,
# which indicates that the pressure level is below the ground surface.
APPLY_PRESSURE_LEVEL_VALIDITY_MASK = True



####################################################################################################
#===================================================================================================
# For analysis of mutiple dates and time windows only
#===================================================================================================
####################################################################################################
# Initial date
DATE_INIT = "2026060100"
# Final date
DATE_FINAL = "2026063000"
# Date time step in hours
DATE_TIME_STEP = "24"
# Time windows to analyze
TIME_WINDOWS_TO_ANALYZE = [
    #"00",
    "24",
    "48",
    "72",
    "96",
    "120"
    ]
# Multi-time stats metrics (metrics that need multiple time instants for their definition, e.g. RMSE, anomaly correlation coefficient)
MULTI_TIME_STATS_METRICS_TO_ANALYZE = [
    "rmse",
    "anomaly_correlation_coefficient"
    ]
#===================================================================================================
# Latitude-pressure profile plot configurations
#===================================================================================================
# Whether to generate latitude-pressure profile plots from concatenated datasets
PLOT_LAT_PRESSURE_PROFILES = True
# Metrics to use in latitude-pressure profile plots.
LAT_PRESSURE_PROFILE_METRICS_TO_PLOT = [
    "bias",
    "relative_error",
    "rmse",
    "anomaly_correlation_coefficient"
    ]
# Variables to use in latitude-pressure profile plots
LAT_PRESSURE_PROFILE_VARIABLES_TO_PLOT = [
    "temperature",
    "spechum",
    "zgeo",
    "uzonal",
    "umeridional",
    ]
# Domains to use in latitude-pressure profile plots
LAT_PRESSURE_PROFILE_DOMAINS_TO_PLOT = [
    "global",
    "south_america", 
    "central_america_and_caribbean"
    ]
# Unit scaling for latitude-pressure profile plots
LAT_PRESSURE_PROFILE_SCALE_BY_VAR = {
    "temperature": {
        "factor": 1.0,
        "unit_label": "K",
    },
    "spechum": {
        "factor": 1.0e6,
        "unit_label": "mg/kg",
    },
    "zgeo": {
        "factor": 1.0,
        "unit_label": "m",
    },
    "uzonal": {
        "factor": 1.0,
        "unit_label": "m/s",
    },
    "umeridional": {
        "factor": 1.0,
        "unit_label": "m/s",
    },
}
# Plot limits for latitude-pressure profile plots
LAT_PRESSURE_PROFILE_LIMITS_BY_VAR_METRIC = {
    "temperature": {
        "bias": (-5, 5),
        "rmse": (0, 30),
    },
    "spechum": {
        "bias": (-500, 500),
        "rmse": (0, 500),
    },
    "zgeo": {
        "bias": (-50, 50),
        "rmse": (0, 100),
    },
    "uzonal": {
        "bias": (-5, 5),
        "rmse": (0, 10),
    },
    "umeridional": {
        "bias": (-5, 5),
        "rmse": (0, 10),
    },
}
# Pressure levels (Pa) to show in latitude-pressure profile plots:
# Use all levels from VERTICAL_LEVELS_TO_ANALYZE or only a subset
LAT_PRESSURE_PROFILE_LEVELS_TO_PLOT = [
    "92500", "85000", "70000", "50000", "40000", "30000", "25000", "10000", "3000"
    ]
