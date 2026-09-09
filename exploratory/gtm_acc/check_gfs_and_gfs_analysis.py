import xarray as xr

ds_gfs_analysis = xr.open_dataset("/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/results/input/intermediate/ref_gfs_analysis_in_monan_format_date_2026060100_time_window_120.nc")
ds_gfs = xr.open_dataset("/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/results/input/intermediate/prediction_gfs_in_monan_format_date_2026060100_time_window_120.nc")

print (ds_gfs_analysis)

print (ds_gfs)