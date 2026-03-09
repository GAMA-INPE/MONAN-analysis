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

# Paths to data files
MONAN_PREOP = "/lustre/projetos/monan_adm/monan/ecf_PREOPER/MONAN-WorkFlow-OPER/MONAN_PRE_OPER/MONAN/scripts_CD-CT/dataout/flushout"
CARTOPY_DATA_DIR = "/lustre/projetos/monan_gam/andre.lyra/cartopy"

# Grid type
GRID_SPEC = '10km_uniform'