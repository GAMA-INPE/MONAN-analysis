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
import vertical_structure_src.vertical_structure_aux as vs_aux
import importlib

if __name__ == "__main__":
    print ("\n ==========================================================================")
    print ("\n Running analysis in 'multiple' mode: multiple dates and/or time windows...")
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
    print ("\n Running analysis for each date and time window...")
    for date in DATES_TO_ANALYZE:
        for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
            print (f"\n Date:{date}; time window: {time_window}")
            print ("\n Updating analysis-specific config file...")
            vs_aux.update_config_file(
                config_file_path="vertical_structure_src/vertical_structure_config.py",
                date=date, 
                time_window=time_window
                )      
            # Reload the updated config file
            importlib.reload(vs_config)
            print ("\n --------------------------------------------------------------------------")
            vs_main.main()

    
    
