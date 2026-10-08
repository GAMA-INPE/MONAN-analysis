# -*- coding: utf-8 -*-
"""
multiple_run.py

Description
-----------
Runs vertical structure analysis for multiple dates and time windows but only stats part, assuming
required data have already been preprocessed. Settings defined in 
vertical_structure_src/vertical_structure_config.py.
"""
import monan_analysis.utils as utils
import vertical_structure_src.vertical_structure_config as vs_config
import vertical_structure_src.vertical_structure_aux as vs_aux
import time

if __name__ == "__main__":
    # Record starting time
    start_time = time.time()

    print ("\n ==========================================================================")
    print ("\n Running analysis in 'multiple' mode (multiple dates and/or time windows) but without" \
    " preprocessing part, assuming required data have already been preprocessed...")
    #===============================================================================================
    # Construct list of dates to analyze from analysis-specific config file
    #===============================================================================================
    print ("\n Constructing list of dates to analyze...")
    DATES_TO_ANALYZE=utils.get_date_list(
        date_init=vs_config.DATE_INIT, 
        date_final=vs_config.DATE_FINAL, 
        time_step=vs_config.DATE_TIME_STEP
        )
    print ("\n List of dates to analyze:", DATES_TO_ANALYZE)
    print ("\n List of forecast time windows to analyze:", vs_config.TIME_WINDOWS_TO_ANALYZE)
    print ("\n ==========================================================================")
    #===============================================================================================
    # Run analysis for each date and time window
    #===============================================================================================
    print ("\n --------------------------------------------------------------------------")
    print ("\n Running no-preprocessing analysis for each date and time window...")
    vs_aux.run_main_for_each_date_and_time_window(date_list=DATES_TO_ANALYZE)
    print ("\n --------------------------------------------------------------------------")
    # Record end time
    end_time = time.time()
    print(f"\n Done. Total execution time: {end_time - start_time:.2f} seconds")