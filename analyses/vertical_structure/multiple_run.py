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
    #===============================================================================================
    # Concatenate resulting datasets to prepare for calculations
    #===============================================================================================
    print ("\n ==========================================================================")
    print ("\n Concatenating resulting datasets to prepare for calculations...")
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        print (f"\n Time window: {time_window}")
        # First, concatenate datasets for statistical metrics calculated for each date
        print (f"\n Stats datasets... {time_window}")
        vs_aux.concatenate_stats_datasets(date_list=DATES_TO_ANALYZE, time_window=time_window)
        # Second, concatenate datasets for the variables analyzed for each date (they will be used
        # to calculate metrics that involve time averages)
        print (f"\n Vars datasets... {time_window}")
        vs_aux.concatenate_var_datasets(date_list=DATES_TO_ANALYZE, time_window=time_window)

    #===============================================================================================
    # Calculate metrics across all dates for each time window
    #===============================================================================================
    print ("\n Calculating mean metrics across all dates for each time window...")
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        print (f"\n Time window: {time_window}")
        # First, mean of metrics that can be calculated for each time instant independently
        # (e.g., bias, relative error)
        vs_aux.calculate_mean_single_time_metrics(time_window=time_window)
        # Second, metrics that require multiple time instants for their definition
        # (e.g., RMSE, anomaly correlation coefficient)
        vs_aux.calculate_multi_time_metrics(time_window=time_window)
    #===============================================================================================
    # Plot mean values of stats metrics across all dates for each time window
    #===============================================================================================
    print ("\n Plotting mean values of stats metrics across all dates for each time window...")
    for time_window in vs_config.TIME_WINDOWS_TO_ANALYZE:
        print (f"\n Time window: {time_window}")
        vs_aux.plot_mean_metrics(time_window=time_window)
    print ("\n ==========================================================================")

