# -*- coding: utf-8 -*-
"""
run_single.py

Description
-----------
Runs vertical structure analysis for multiple dates and time windows, with settings defined in 
vertical_structure_src/vertical_structure_config.py.
"""
import monan_analysis.utils as utils
import vertical_structure_src.vertical_structure_config as vs_config
import vertical_structure_src.vertical_structure_main as vs_main

if __name__ == "__main__":
    print ("\n Running analysis in 'multiple' mode: multiple dates and/or time windows...")
    #===============================================================================================
    # Read high-level settings for multiple runs
    #===============================================================================================
    print ("\n Reading dates and time windows for multiple runs...")
    date_list=utils.get_date_list(
        date_init=vs_config.DATE_INIT, 
        date_final=vs_config.DATE_FINAL, 
        time_step=vs_config.DATE_TIME_STEP
        )
    print (date_list)
    
