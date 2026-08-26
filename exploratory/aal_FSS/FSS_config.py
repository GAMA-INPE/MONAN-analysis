#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: André Lyra <andre.lyra@inpe.br>

"""
This script contains configuration parameters for calculating the Fractions Skill Score (FSS).
The parameters include paths to precipitation data, output directories, models, references,
thresholds, window sizes, and domains.
"""

from pathlib import Path

# Base directory for precipitation data
BASE_PRECIP = Path(
    "/lustre/projetos/monan_gam/andre.lyra/"
    "NetCDFs/precip_24h"
)

# Output directory for FSS results
OUTDIR_FSS = BASE_PRECIP / "FSS_remapcon_common_grid"

MODELOS = [
    "MONAN",
    "BAM",
    "GFS",
]

REFERENCIAS = [
    "GPM_IMERG",
    "MSWEP",
    "GSMAP",
]

THRESHOLDS = [
    1.0,
    2.0,
    5.0,
    10.0,
    20.0,
    50.0,
]

WINDOW_SIZES = [
    1,
    3,
    5,
    9,
    15,
    25,
]

PRAZOS = range(24, 241, 24)

VAR_PREC = "prec"

DOMINIOS = {
    "GLB": {
        "lat": (-90, 90),
        "lon": (0, 360),
    },
    "AMS": {
        "lat": (-55, 20),
        "lon": (275, 340),
    },
    "ACC": {
        "lat": (-10, 35),
        "lon": (242, 335),
    },
}

# None uses each model's native grid.
# "GFS" interpolates all models in memory to the GFS grid.
TARGET_GRID = "GFS"

# If True, the CDO(remapcon) files may be precomputed and saved on PRECOMPUTED_REMAPCON_DIR
USE_PRECOMPUTED_REMAPCON = True

PRECOMPUTED_REMAPCON_DIR = (
    BASE_PRECIP
    / "MONAN_BAM_common_grid_GFS"
    / "remapcon_GFS"
)

# If USE_PRECOMPUTED_REMAPCON is False, specifies the interpolation method: "linear" or "nearest".
# Unlike CDO remapcon, these methods are not conservative.
REGRID_METHOD = "linear"  