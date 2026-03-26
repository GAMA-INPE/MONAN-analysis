# -*- coding: utf-8 -*-
"""
precipitation_analysis_main.py

Based on initial scripts developed by Andre Lyra (andre.lyra@inpe.br) and
based on the repository methodology proposed by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last updated: March 2026 by Andre Lyra (andre.lyra@inpe.br)

Description
-----------
This script controls the execution of the precipitation evaluation analysis. 

Steps:
1. Read data from MONAN 
2. Preprocess data
3. Calculate statistics
4. Plot and save results

Input
-----
- ds_monan (xr.Dataset): netcdf file containing MONAN data
- ds_observations (xr.Dataset): netcdf files containing observation data (GPM IMERG, GSMaP, and MSWEP)

Output
------
- Remapped observational files on the MONAN grid
- NetCDF files containing precipitation fields and statistical metrics
- Figures for precipitation and error diagnostics
- Text files with categorical skill scores tables

Usage
-----
- 

"""

import precipitation_analysis_aux as pa_aux
import precipitation_analysis_config as pa_config


def main() -> None:
    pa_aux.log("Initializing folder structure...", level=0)
    pa_aux.create_folder_structure()

    if pa_config.GENERATE_MONAN_24H_ACCUM:
        pa_aux.log("Generating MONAN 24 h accumulated precipitation files...", level=0)
        pa_aux.generate_monan_24h_accumulations()

    lead_times = pa_aux.get_lead_times()
    pa_aux.log(f"Configured leads: {lead_times}", level=1)

    for lead in lead_times:
        pa_aux.log("=" * 80, level=0)
        pa_aux.log(f"Processing lead {lead:03d} h", level=0)

        file_dict = pa_aux.build_file_dict_for_lead(lead)
        pa_aux.check_required_inputs(file_dict)

        if pa_config.RUN_REMAP:
            pa_aux.remap_observations_to_monan_grid(file_dict)

        data_dict = pa_aux.open_precip_datasets(file_dict)

        if "bias" in pa_config.STATS_METRICS_TO_ANALYZE:
            pa_aux.log(f"Running bias analysis for lead {lead:03d} h...", level=1)
            pa_aux.run_bias_analysis(lead=lead, file_dict=file_dict, data_dict=data_dict)

        if "mae" in pa_config.STATS_METRICS_TO_ANALYZE:
            pa_aux.log(f"Running MAE analysis for lead {lead:03d} h...", level=1)
            pa_aux.run_mae_analysis(lead=lead, file_dict=file_dict, data_dict=data_dict)

        if "sqerr" in pa_config.STATS_METRICS_TO_ANALYZE:
            pa_aux.log(f"Running squared error analysis for lead {lead:03d} h...", level=1)
            pa_aux.run_squared_error_analysis(lead=lead, file_dict=file_dict, data_dict=data_dict)

        if "skill" in pa_config.STATS_METRICS_TO_ANALYZE:
            for threshold in pa_config.SKILL_THRESHOLDS_MM:
                pa_aux.log(
                    f"Running skill analysis for lead {lead:03d} h and threshold {threshold} mm...",
                    level=1,
                )
                pa_aux.run_skill_analysis(
                    lead=lead,
                    threshold_mm=threshold,
                    file_dict=file_dict,
                    data_dict=data_dict,
                )

    pa_aux.log("Copying config files to output directory...", level=0)
    pa_aux.cp_config_files()
    pa_aux.log("Done.", level=0)


if __name__ == "__main__":
    main()
