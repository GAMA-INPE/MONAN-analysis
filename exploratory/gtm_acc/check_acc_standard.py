import xarray as xr
import monan_analysis.preprocess as preprocess
import monan_analysis.stats as stats
import monan_analysis.utils as utils

# Relevant filepaths
DIR_MONAN_PREOP = "/lustre/projetos/ioper/models/MONAN-WorkFlow-OPER/MONAN_PRE_OPER/posTMP"
DIR_GFS_ANALYSIS = "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/vert_struct/GFS"
DIR_GFS = "/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/GFS"
DIR_CARTOPY_DATA = "/lustre/projetos/monan_gam/andre.lyra/cartopy"
DIR_OUTPUT = f"/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/results/test_acc_standard_gfs_vs_gfs_analysis/output"
DIR_OUTPUT_FIGS = f"{DIR_OUTPUT}/figs"
DIR_OUTPUT_DATA = f"{DIR_OUTPUT}/data"
DIR_INPUT = f"/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/results/test_acc_standard_gfs_vs_gfs_analysis/input"
DIR_INPUT_INTERMEDIATE = f"{DIR_INPUT}/intermediate"
DIR_INPUT_PROCESSED = f"{DIR_INPUT}/processed"
DIR_INPUT_RAW = f"{DIR_INPUT}/raw"
FILEPATH_CLIMATOLOGY = f"/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/mon/nc_climatology/climatology_in_monan_format.nc"
# Other relevant input
PREDICTION_MODEL = "gfs"
REFERENCE_DATA = "gfs_analysis"
DATE_INIT = "2026070100"
DATE_FINAL = "2026070200"
TIME_WINDOW = "120"


def get_prediction_ref_concat_filepath(time_window):
    prediction_concat_filepath = f"{DIR_INPUT_PROCESSED}/prediction_{PREDICTION_MODEL}_concat_date_from_{DATE_INIT}_to_{DATE_FINAL}_time_window_{time_window}.nc"
    ref_concat_filepath = f"{DIR_INPUT_PROCESSED}/ref_{REFERENCE_DATA}_concat_date_from_{DATE_INIT}_to_{DATE_FINAL}_time_window_{TIME_WINDOW}.nc"
    return prediction_concat_filepath, ref_concat_filepath

def apply_pressure_level_mask_in_ref_and_prediction(ds_ref, ds_prediction, APPLY_PRESSURE_LEVEL_VALIDITY_MASK=True):
        # Apply pressure-level validity mask based on GFS and MONAN surface pressure
    if APPLY_PRESSURE_LEVEL_VALIDITY_MASK:
        if "surface_pressure" not in ds_ref:
            raise ValueError(
                "APPLY_PRESSURE_LEVEL_VALIDITY_MASK is True, but "
                "'surface_pressure' was not found in the preprocessed GFS dataset."
            )

        if "surface_pressure" not in ds_prediction:
            raise ValueError(
                "APPLY_PRESSURE_LEVEL_VALIDITY_MASK is True, but "
                "'surface_pressure' was not found in the preprocessed MONAN dataset."
            )
        
        # Obtain validity masks for reference dataset
        valid_ref_pressure_level_mask = preprocess.apply_pressure_level_validity_mask(
            ds=ds_ref,
            pressure_level=ds_ref["level"],
            surface_pressure_var="surface_pressure"
        )

        # Obtain validity masks for prediction dataset
        valid_prediction_pressure_level_mask = preprocess.apply_pressure_level_validity_mask(
            ds=ds_prediction,
            pressure_level=ds_prediction["level"],
            surface_pressure_var="surface_pressure"
        )

        # Obtain validity mask considering both datasets
        valid_pressure_level_mask = (
            valid_ref_pressure_level_mask
            & valid_prediction_pressure_level_mask
        )

        # Remove surface_pressure before applying the mask to avoid expanding
        # this 2D/3D field to all pressure levels during ds.where()
        ds_ref = ds_ref.drop_vars("surface_pressure")
        ds_prediction = ds_prediction.drop_vars("surface_pressure")

        # Apply the same combined validity mask to reference and prediction
        ds_ref = ds_ref.where(valid_pressure_level_mask)
        ds_prediction = ds_prediction.where(valid_pressure_level_mask)

    else:
        # Avoid calculating RMSE or ACC for surface_pressure if it exists in the dataset
        ds_ref = ds_ref.drop_vars("surface_pressure", errors="ignore")
        ds_prediction = ds_prediction.drop_vars("surface_pressure", errors="ignore")

# Construct filepaths for concatenated variable datasets
time_window = "120"
var_prediction_concat_filepath, var_ref_concat_filepath = get_prediction_ref_concat_filepath(time_window)
# Read concatenated variable datasets
ds_var_prediction_concat = xr.open_dataset(var_prediction_concat_filepath, engine="netcdf4")
ds_var_ref_concat = xr.open_dataset(var_ref_concat_filepath, engine="netcdf4")

print ("prediction concat:")
print (ds_var_prediction_concat)
print (len(ds_var_prediction_concat.latitude))
print (len(ds_var_prediction_concat.longitude))
print (ds_var_prediction_concat["zgeo"].mean(dim="Time").sel(level="50000"))
print (ds_var_prediction_concat["zgeo"].mean(dim="Time", keep_attrs=True).sel(level="50000"))

print ("ref concat:")
print (ds_var_ref_concat)
print (len(ds_var_ref_concat.latitude))
print (len(ds_var_ref_concat.longitude))
print (ds_var_ref_concat["zgeo"].mean(dim="Time").sel(level="50000"))

# Read mapped climatology
#ds_climatology = xr.open_dataset(vs_config.DIR_INPUT_PROCESSED+f"/climatology_mapped_to_ref_{vs_config.REFERENCE_DATA}.nc", engine="netcdf4")
ds_climatology = xr.open_dataset(FILEPATH_CLIMATOLOGY, engine="netcdf4")

print ("climatology:")
print (len(ds_climatology.latitude))
print (len(ds_climatology.longitude))
print (ds_climatology.Time)
print (ds_climatology["zgeo"].sel(level="50000", Time="20200701"))

# get month for calculation
month = utils.get_MM_str_from_YYYYMMDDHH_str(date_string=DATE_INIT)

print (month)

ds_acc = stats.anomaly_correlation_coefficient_standard(
    var="zgeo", 
    predictions=ds_var_prediction_concat,
    observations=ds_var_ref_concat,
    climatology=ds_climatology,
    month_MM = "07"
)

print (ds_acc.sel(level="50000"))