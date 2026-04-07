# -*- coding: utf-8 -*-
"""
vertical_analysis_config.py

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
SEL_VERBOSE_LEVEL = 0
#===================================================================================================
# MONAN configurations
#===================================================================================================
# Date and forecast time window for analysis
YEAR = "2026"
MONTH = "02"
DAY = "05"
HOUR = "00"
TIME_WINDOW = "24"
# Grid specification
GRID_SPEC = "10km_uniform"
# Vertical level specification
VERTICAL_LEVEL_SPEC = "55"
# Variables to analyze
VARIABLES_TO_ANALYZE = [
    "temperature",
    "spechum",
    #"zgeo",
    #"uzonal",
    #"umeridional",
    ]
# Vertical levels to analyze
VERTICAL_LEVELS_TO_ANALYZE = [
    "92500", "85000",  #"70000",  "50000",  "40000",  "25000",  "10000"
    ]
# Domains to analyze
DOMAINS_TO_ANALYZE = [
    "global", 
    #"south_america", 
    #"central_america_and_caribbean"
    ]
#===================================================================================================
# GFS configurations
#===================================================================================================
# Name of data stream from GFS to read (e.g. "levels" or "surface")
GFS_STREAM_NAME = "levels"
#===================================================================================================
# Data interpolation configurations
#===================================================================================================
# Name of data stream from GFS to read (e.g. "levels" or "surface")
INTERPOL_TYPE = "gfs_to_monan" # "monan_to_gfs" or "gfs_to_monan"
#===================================================================================================
# Statistics configurations
#===================================================================================================
STATS_METRICS_TO_ANALYZE = [
    "bias",
    "relative_error"
    ]
#===================================================================================================
# Plot configurations
#===================================================================================================
# Divergin colormaps to use for each variable in plotting
COLORMAP_DIVERGING_BY_VAR_DICT = {
    "temperature": "coolwarm",
    "spechum": "managua",
    "zgeo": "PiYG",
    "uzonal": "PuOr",
    "umeridional": "PuOr"
}
#===================================================================================================
# Directory paths
#===================================================================================================
DIR_MONAN_PREOP = "/lustre/projetos/monan_adm/monan/ecf_PREOPER/MONAN-WorkFlow-OPER/MONAN_PRE_OPER/MONAN/scripts_CD-CT/dataout/flushout"
DIR_GFS_ANALYSIS = "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/vert_struct/GFS"
DIR_CARTOPY_DATA = "/lustre/projetos/monan_gam/andre.lyra/cartopy"
DIR_OUTPUT = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/output"
DIR_OUTPUT_FIGS = f"{DIR_OUTPUT}/figs"
DIR_OUTPUT_DATA = f"{DIR_OUTPUT}/data"
DIR_INPUT = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/input"
DIR_INPUT_INTERMEDIATE = f"{DIR_INPUT}/intermediate"
DIR_INPUT_PROCESSED = f"{DIR_INPUT}/processed"
DIR_INPUT_RAW = f"{DIR_INPUT}/raw"
#===================================================================================================
# For analysis of mutiple dates and time windows only
#===================================================================================================
# Initial date
DATE_INIT = "2026020100"
# Final date
DATE_FINAL = "2026020500"
# Date time step in hours
DATE_TIME_STEP = "24"
# Time windows to analyze
TIME_WINDOWS_TO_ANALYZE = [
    "00",
    "24",
    #"48",
    #"72",
    #"96",
    #"120"
    ]
# Multi-time stats metrics (metrics that need multiple time instants for their definition, e.g. RMSE, anomaly correlation coefficient)
MULTI_TIME_STATS_METRICS_TO_ANALYZE = [
    "rmse",
    "anomaly_correlation_coefficient"
    ]