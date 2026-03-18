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
# Selection of types of analysis to perform
#===================================================================================================
# Print details of analysis steps
SEL_VERBOSE_ANALYSIS_STEPS = "n"
# Initial maps showing MONAN fields
SEL_INITIAL_MONAN_MAPS = "n"
#===================================================================================================
# MONAN configurations
#===================================================================================================
# Date and forecast time window for analysis
YEAR = "2026"
MONTH = "02"
DAY = "01"
HOUR = "00"
TIME_WINDOW = "48"
# Grid specification
GRID_SPEC = "10km_uniform"
# Vertical level specification
VERTICAL_LEVEL_SPEC = "55"
# Variables to analyze
VARIABLES_TO_ANALYZE = [
    "temperature",
    #"relhum",
    #"spechum",
    #"zgeo",
    #"uzonal",
    #"umeridional",
    ]
# Vertical levels to analyze
VERTICAL_LEVELS_TO_ANALYZE = [
    "92500"#, "85000",  "70000",  "50000",  "40000",  "25000",  "10000"
    ]
# Domains to analyze
DOMAINS_TO_ANALYZE = [
    "global", 
    "south_america", 
    "central_america_and_caribbean"
    ]
#===================================================================================================
# GFS configurations
#===================================================================================================
# Name of data stream from GFS to read (e.g. "levels" or "surface")
GFS_STREAM_NAME = "levels"
#===================================================================================================
# Directory paths
#===================================================================================================
DIR_MONAN_PREOP = "/lustre/projetos/monan_adm/monan/ecf_PREOPER/MONAN-WorkFlow-OPER/MONAN_PRE_OPER/MONAN/scripts_CD-CT/dataout/flushout"
DIR_GFS_ANALYSIS = "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/vert_struct/GFS"
DIR_CARTOPY_DATA = "/lustre/projetos/monan_gam/andre.lyra/cartopy"
DIR_OUTPUT = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/exploratory/gtm_vertical_analysis/output"
DIR_INPUT = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/exploratory/gtm_vertical_analysis/input"
DIR_INPUT_INTERMEDIATE = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/exploratory/gtm_vertical_analysis/input/intermediate"
DIR_INPUT_PROCESSED = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/exploratory/gtm_vertical_analysis/input/processed"
DIR_INPUT_RAW = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/exploratory/gtm_vertical_analysis/input/raw"