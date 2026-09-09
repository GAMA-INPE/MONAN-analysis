# -*- coding: utf-8 -*-
"""
pdf_maker_config.py

Description
-----------

Usage
-----

Updates
-------
"""
#===================================================================================================
# Directory and file paths
#===================================================================================================
DIR_INPUT_RAW = "/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/saulo"
FILENAME_INPUT_RAW = "cnv11_M2.0_30km.nc"
DIR_INPUT_PREPROCESSED = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/pdf_maker/results/input/preprocessed"
DIR_OUTPUT_DATA = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/pdf_maker/results/output/data"
DIR_OUTPUT_FIGS = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/pdf_maker/results/output/figs"
#===================================================================================================

#===================================================================================================
# PDF generation settings
#==================================================================================================
# Domain
LAT_MIN = "-10.0"
LAT_MAX = "0"
LON_MIN = "-60.0"
LON_MAX = "20.0"
# Variables for building pdf
VARIABLES_AND_VALUES_FOR_PDF = {
    "rtopdpcu": {
        "min": 0,
        "max": 20000,
        "bin_size": 1000
    },
    # "uzonal": {
    #     "min": -50,
    #     "max": 50,
    #     "bin_size": 2
    # }
}

#===================================================================================================
# Log configurations
#===================================================================================================
VERBOSE = False