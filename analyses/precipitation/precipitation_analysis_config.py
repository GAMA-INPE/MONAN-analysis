# -*- coding: utf-8 -*-
"""
precipitation_analysis_config.py

Based on initial scripts developed by Andre Lyra (andre.lyra@inpe.br) and
based on the repository methodology proposed by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last updated: March 2026 by Andre Lyra (andre.lyra@inpe.br)

Description
-----------
Configuration file for the MONAN 24 h accumulated precipitation analysis.

This file contains parameters specific to the precipitation workflow,
including cycle date, lead times, observational references, domains,
metrics, thresholds, plotting options, and directory settings.

Usage
-----
- Import this file in scripts that are part of this specific analysis.
- Do not use this file for general-purpose configurations.

Example:
    from analysis_folder.config import DATA_PATH, ANALYSIS_PARAM
 
"""
import monan_analysis.config as monan_config
import os
from matplotlib.colors import ListedColormap


#===================================================================================================
# Selection of level of detail of log messages
#===================================================================================================
# 0: log messages from precipitation_analysis_main.py only
# 1: log messages from precipitation_analysis_main.py + precipitation_analysis_aux.py
# 2: log messages from precipitation_analysis_main.py + precipitation_analysis_aux.py + monan_analysis modules
SEL_VERBOSE_LEVEL = 2
#===================================================================================================

# =================================================================================================
# Forecast cycle configuration
# =================================================================================================
YEAR = "2026"
MONTH = "02"
DAY = "01"
HOUR = "00"

FORECAST_TOTAL_H = 120
LEAD_STEP_H = 24
ACCUM_WINDOW_H = 24

# =================================================================================================
# MONAN configuration
# =================================================================================================
GRID_SPEC = "10km_uniform"
VERTICAL_LEVEL_SPEC = "55"
MONAN_FILE_PREFIX = monan_config.PREFIX_MONAN_DIAG_STRING
MONAN_GRID_STRING = monan_config.GRID_DICT[GRID_SPEC]
MONAN_VERTICAL_LEVEL_STRING = monan_config.VERTICAL_LEVEL_DICT[VERTICAL_LEVEL_SPEC]
DATE_FORMAT_STRING = monan_config.DATE_FORMAT_STRING

# =================================================================================================
# Analysis switches
# =================================================================================================
GENERATE_MONAN_24H_ACCUM = True
RUN_PLOTTING = True
RUN_REMAP = True
OVERWRITE_REMAP = False
OVERWRITE_OUTPUTS = True
SAVE_INTERMEDIATE_NETCDF = True
SAVE_SKILL_NETCDF = True
SAVE_SKILL_TXT = True

# =================================================================================================
# Variables and references
# =================================================================================================
PRECIP_VAR_NAME = "prec"
MONAN_RAINNC_NAME = "rainnc"
MONAN_RAINC_NAME = "rainc"
MONAN_LAT_NAME = "latitude"
MONAN_LON_NAME = "longitude"
MONAN_TIME_DIM_NAME = "Time"

OBS_REFERENCE_LIST = ["GPM", "GSMAP", "MSWEP"]
STATS_METRICS_TO_ANALYZE = [
    "bias",
    "mae",
    "sqerr",
    "skill",
]

SKILL_THRESHOLDS_MM = [1, 2, 5, 10, 20, 50]
SKILL_METRICS_TO_SAVE = ["ACC", "POD", "POFD", "FAR", "CSI", "F1"]

# =================================================================================================
# Domains
# lon is kept in 0 to 360 to match the current MONAN precipitation workflow
# =================================================================================================
DOMAINS = {
    "GLB": {
        "monan_domain_key": "global",
        "slice": None,
        "extent": None,
        "xticks": list(range(-180, 181, 60)),
        "yticks": list(range(-60, 61, 30)),
    },
    "AMS": {
        "monan_domain_key": "south_america",
        "slice": {
            "lat": slice(*monan_config.DOMAIN_DICT["south_america"]["lat"]),
            "lon": slice(*monan_config.DOMAIN_DICT["south_america"]["lon"]),
        },
        "extent": [-85, -20, -55, 20],
        "xticks": list(range(-80, -19, 10)),
        "yticks": list(range(-50, 21, 10)),
    },
    "ACC": {
        "monan_domain_key": "central_america_and_caribbean",
        "slice": {
            "lat": slice(*monan_config.DOMAIN_DICT["central_america_and_caribbean"]["lat"]),
            "lon": slice(*monan_config.DOMAIN_DICT["central_america_and_caribbean"]["lon"]),
        },
        "extent": [-118, -35, -10, 35],
        "xticks": list(range(-110, -34, 10)),
        "yticks": list(range(-10, 36, 10)),
    },
}

# =================================================================================================
# Plotting configuration
# =================================================================================================
MONAN_ACCUM_COLORS_RGB = [
    (255, 255, 255),
    (220, 220, 220),
    (180, 180, 180),
    (20, 0, 150),
    (0, 0, 255),
    (0, 100, 100),
    (0, 200, 0),
    (150, 255, 0),
    (255, 255, 0),
    (255, 220, 0),
    (255, 130, 0),
    (230, 25, 25),
    (100, 0, 0),
]

MONAN_ACCUM_LEVELS = [0, 1, 2, 4, 6, 10, 15, 25, 35, 50, 75, 100, 150]
MONAN_ACCUM_CBAR_LABEL = "(mm/day)"

BIAS_COLORS_RGB = [
    (130, 0, 0),      # 20
    (192, 3, 0),      # 15
    (225, 18, 0),     # 12
    (255, 96, 2),     # 9
    (255, 193, 60),   # 6
    (255, 251, 190),  # 3
    (255, 255, 255),  # 0
    (179, 230, 249),  # -3
    (150, 200, 249),  # -6
    (75, 155, 244),   # -9
    (36, 116, 241),   # -12
    (25, 90, 234),    # -15
    (0, 45, 220),     # -20
]
BIAS_LEVELS = [-25, -20, -15, -12, -9, -6, -3, 3, 6, 9, 12, 15, 20, 25]
BIAS_CMAP = ListedColormap([(r / 255, g / 255, b / 255) for r, g, b in BIAS_COLORS_RGB])
BIAS_EXTEND = "both"
BIAS_CBAR_LABEL = "Bias [mm/24 h]"

ABS_ERROR_LEVELS = [0, 2, 4, 6, 8, 10, 15, 20, 30, 40, 50]
PRECIP_LEVELS = [0.5, 1, 3, 5, 7.5, 10, 12.5, 15, 20, 25, 30, 35]

ABS_ERROR_CMAP_NAME = "YlOrRd"
PRECIP_CMAP_NAME = "turbo"

FIG_DPI = 300
FIGSIZE_GLOBAL = (10, 5)
FIGSIZE_REGIONAL = (10, 5)

# =================================================================================================
# Paths
# Adjust these paths to your environment if needed.
# =================================================================================================
DIR_MONAN_PREOP = (
    "/lustre/projetos/monan_adm/monan/ecf_PREOPER/"
    "MONAN-WorkFlow-OPER/MONAN_PRE_OPER/MONAN/scripts_CD-CT/dataout/flushout"
)
DIR_NETCDF_MONAN_24H = "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/MONAN"
DIR_NETCDF_GPM_24H = "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/GPM_IMERG"
DIR_NETCDF_GSMAP_24H = "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/GSMAP"
DIR_NETCDF_MSWEP_24H = "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/MSWEP"
DIR_NETCDF_CONTINGENCY = "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/CONTINGENCIA"

DIR_CARTOPY_DATA = "/lustre/projetos/monan_gam/andre.lyra/cartopy"

BASE_ANALYSIS_DIR = "/lustre/projetos/monan_gam/Scripts/MONAN-analysis/analyses/precipitation"
DIR_INPUT = f"{BASE_ANALYSIS_DIR}/input"
DIR_INPUT_RAW = f"{DIR_INPUT}/raw"
DIR_INPUT_INTERMEDIATE = f"{DIR_INPUT}/intermediate"
DIR_INPUT_PROCESSED = f"{DIR_INPUT}/processed"

DIR_OUTPUT = f"{BASE_ANALYSIS_DIR}/output"

DIR_OUTPUT_DATA = f"{DIR_OUTPUT}/data"
DIR_OUTPUT_DATA_BIAS = os.path.join(DIR_OUTPUT_DATA, "Bias")
DIR_OUTPUT_DATA_MAE = os.path.join(DIR_OUTPUT_DATA, "MAE")
DIR_OUTPUT_DATA_SQERR = os.path.join(DIR_OUTPUT_DATA, "SQERR")
DIR_OUTPUT_DATA_SKILL = os.path.join(DIR_OUTPUT_DATA, "Skill")
DIR_OUTPUT_DATA_MONAN = os.path.join(DIR_OUTPUT_DATA, "MONAN")

DIR_OUTPUT_TXT = f"{DIR_OUTPUT}/txt"
DIR_OUTPUT_TXT_SKILL = os.path.join(DIR_OUTPUT_TXT, "Skill")

DIR_OUTPUT_FIGS = os.path.join(DIR_OUTPUT, "figs")
DIR_OUTPUT_FIG_MONAN = os.path.join(DIR_OUTPUT_FIGS, "MONAN")
DIR_OUTPUT_FIG_BIAS = os.path.join(DIR_OUTPUT_FIGS, "Bias")
DIR_OUTPUT_FIG_MAE = os.path.join(DIR_OUTPUT_FIGS, "MAE")
DIR_OUTPUT_FIG_RMSE = os.path.join(DIR_OUTPUT_FIGS, "RMSE")
DIR_OUTPUT_TXT = os.path.join(DIR_OUTPUT, "txt")


