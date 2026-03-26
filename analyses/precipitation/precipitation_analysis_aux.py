# -*- coding: utf-8 -*-
"""
precipitation_analysis_aux.py

Based on initial scripts developed by Andre Lyra (andre.lyra@inpe.br) and
based on the repository methodology proposed by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)
Last updated: March 2026 by Andre Lyra (andre.lyra@inpe.br)

Description
-----------
This module contains auxiliary functions for the MONAN 24 h accumulated precipitation analysis.

Usage
-----
- Import this module in scripts that are part of this specific analysis.
- Do not use this module for defining general-purpose functions.

Examples:
- from vertical_analysis_aux import setup_parser
or
- import vertical_analysis_aux as va_aux
  args = va_aux.setup_parser()

Acknowledgments
---------------
This file was created with the assistance of GitHub Copilot.    
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict

import numpy as np
import xarray as xr
from matplotlib.colors import BoundaryNorm, ListedColormap

import monan_analysis
import monan_analysis.config as monan_config
import monan_analysis.preprocess as monan_preprocess
import monan_analysis.utils as monan_utils

import precipitation_analysis_config as pa_config

try:
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
    from matplotlib.colors import BoundaryNorm
    HAS_PLOTTING = True
except Exception:
    HAS_PLOTTING = False


def log(message: str, level: int = 1) -> None:
    if pa_config.SEL_VERBOSE_LEVEL >= level:
        print(message, flush=True)



def get_cycle_datetime():
    return monan_utils.get_date_as_datetime(
        pa_config.YEAR,
        pa_config.MONTH,
        pa_config.DAY,
        pa_config.HOUR,
    )


def get_cycle_str() -> str:
    return monan_utils.get_date_as_YYYYMMDDHH_str(
        pa_config.YEAR,
        pa_config.MONTH,
        pa_config.DAY,
        pa_config.HOUR,
    )


def get_yearmonth_str() -> str:
    return monan_utils.get_date_as_YYYYMM_str(pa_config.YEAR, pa_config.MONTH)


def get_lead_times() -> list[int]:
    return list(range(pa_config.LEAD_STEP_H, pa_config.FORECAST_TOTAL_H + 1, pa_config.LEAD_STEP_H))


def get_output_tag() -> str:
    return get_cycle_str()


def create_folder_structure() -> None:
    cycle = get_output_tag()
    for folder in [
        pa_config.DIR_INPUT,
        pa_config.DIR_INPUT_RAW,
        pa_config.DIR_INPUT_INTERMEDIATE,
        pa_config.DIR_INPUT_PROCESSED,
        pa_config.DIR_OUTPUT,
        pa_config.DIR_OUTPUT_DATA,
        pa_config.DIR_OUTPUT_FIGS,
        pa_config.DIR_OUTPUT_TXT,
    ]:
        os.makedirs(folder, exist_ok=True)


# =================================================================================================
# Path and filename handling
# =================================================================================================
def _get_obs_base_dir(reference: str) -> str:
    mapping = {
        "GPM": pa_config.DIR_NETCDF_GPM_24H,
        "GSMAP": pa_config.DIR_NETCDF_GSMAP_24H,
        "MSWEP": pa_config.DIR_NETCDF_MSWEP_24H,
    }
    return mapping[reference]


def get_obs_filename(reference: str, valid_str: str) -> str:
    if reference == "GPM":
        return f"GPM_IMERG_Precipitation_24h_accum_{valid_str}00.nc"
    if reference == "GSMAP":
        return f"GSMAP_Precipitation_24h_accum_{valid_str}00.nc"
    if reference == "MSWEP":
        return f"MSWEP_Precipitation_24h_accum_{valid_str}00.nc"
    raise ValueError(f"Unsupported reference: {reference}")


def get_obs_filepath(reference: str, valid_str: str) -> str:
    base_dir = _get_obs_base_dir(reference)
    return os.path.join(base_dir, f"{valid_str}00", get_obs_filename(reference, valid_str))


def get_monan_24h_filename(cycle_str: str, valid_str: str, lead: int) -> str:
    return f"MONAN_Precipitation_24h_acum_{cycle_str}_{valid_str}_{lead:03d}h.nc"


def get_monan_24h_filepath(cycle_str: str, valid_str: str, lead: int) -> str:
    return os.path.join(pa_config.DIR_NETCDF_MONAN_24H, cycle_str, get_monan_24h_filename(cycle_str, valid_str, lead))


def build_file_dict_for_lead(lead: int) -> dict:
    cycle_dt = get_cycle_datetime()
    cycle_str = get_cycle_str()
    valid_dt = monan_utils.get_final_date_from_initial_date(cycle_dt, lead)
    valid_str = valid_dt.strftime(pa_config.DATE_FORMAT_STRING)

    file_dict = {
        "cycle_str": cycle_str,
        "yearmonth_str": get_yearmonth_str(),
        "valid_str": valid_str,
        "lead": lead,
        "monan_nc": get_monan_24h_filepath(cycle_str, valid_str, lead),
        "refs": {},
    }

    for reference in pa_config.OBS_REFERENCE_LIST:
        obs_nc = get_obs_filepath(reference, valid_str)
        remap_nc = obs_nc.replace(".nc", "_MONAN_grid.nc")
        file_dict["refs"][reference] = {"obs_nc": obs_nc, "remap_nc": remap_nc}

    return file_dict


def check_required_inputs(file_dict: dict) -> None:
    missing = []
    if not os.path.exists(file_dict["monan_nc"]):
        missing.append(file_dict["monan_nc"])
    for reference, ref_dict in file_dict["refs"].items():
        if not os.path.exists(ref_dict["obs_nc"]):
            missing.append(ref_dict["obs_nc"])
            log(f"Missing {reference} file: {ref_dict['obs_nc']}", level=0)
    if missing:
        raise FileNotFoundError("Required input files not found:\n" + "\n".join(missing))


# =================================================================================================
# MONAN 24 h accumulation generation
# =================================================================================================
def _get_flushout_filename(cycle_str: str, valid_str: str) -> str:
    return (
        f"{pa_config.MONAN_FILE_PREFIX}_{cycle_str}_{valid_str}.00.00."
        f"{pa_config.MONAN_GRID_STRING}{pa_config.MONAN_VERTICAL_LEVEL_STRING}.nc"
    )


def _get_flushout_filepath(cycle_str: str, valid_str: str) -> str:
    return os.path.join(pa_config.DIR_MONAN_PREOP, cycle_str, _get_flushout_filename(cycle_str, valid_str))


def build_monan_flushout_filepairs() -> list[dict]:
    cycle_dt = get_cycle_datetime()
    cycle_str = get_cycle_str()
    filepairs = []
    for lead in get_lead_times():
        end_dt = monan_utils.get_final_date_from_initial_date(cycle_dt, lead)
        start_dt = monan_utils.get_initial_date_from_final_date(end_dt, pa_config.ACCUM_WINDOW_H)
        start_str = start_dt.strftime(pa_config.DATE_FORMAT_STRING)
        end_str = end_dt.strftime(pa_config.DATE_FORMAT_STRING)
        filepairs.append(
            {
                "lead": lead,
                "start_str": start_str,
                "end_str": end_str,
                "start_file": _get_flushout_filepath(cycle_str, start_str),
                "end_file": _get_flushout_filepath(cycle_str, end_str),
                "output_nc": get_monan_24h_filepath(cycle_str, end_str, lead),
            }
        )
    return filepairs


# =================================================================================================
# IO, coordinates, subsetting, and statistics
# =================================================================================================
def get_lat_lon_names(da: xr.DataArray) -> tuple[str, str]:
    lat_candidates = ["lat", "latitude", "y"]
    lon_candidates = ["lon", "longitude", "x"]
    lat_name = next((name for name in lat_candidates if name in da.coords or name in da.dims), None)
    lon_name = next((name for name in lon_candidates if name in da.coords or name in da.dims), None)
    if lat_name is None or lon_name is None:
        raise ValueError("Latitude/longitude coordinate names could not be identified.")
    return lat_name, lon_name


def _normalize_precip_coords(da: xr.DataArray) -> xr.DataArray:
    lat_name, lon_name = get_lat_lon_names(da)
    rename_map = {}
    if lat_name != "lat":
        rename_map[lat_name] = "lat"
    if lon_name != "lon":
        rename_map[lon_name] = "lon"
    if rename_map:
        da = da.rename(rename_map)
    da = da.assign_coords(lon=((da["lon"] + 360.0) % 360.0)).sortby("lon")
    if float(da["lat"][0]) > float(da["lat"][-1]):
        da = da.sortby("lat")
    return da


def subset_domain(da: xr.DataArray, domain_name: str) -> xr.DataArray:
    domain_dict = pa_config.DOMAINS[domain_name]
    domain_slice = domain_dict["slice"]
    if domain_slice is None:
        return da
    return da.sel(lat=domain_slice["lat"], lon=domain_slice["lon"])


def _weighted_mean_2d(da: xr.DataArray) -> float:
    lat_rad = np.deg2rad(da["lat"])
    weights = xr.DataArray(np.cos(lat_rad), coords={"lat": da["lat"]}, dims=["lat"])
    return float(da.weighted(weights).mean(skipna=True).item())


def compute_domain_mean(da: xr.DataArray) -> float:
    return _weighted_mean_2d(_normalize_precip_coords(da))


def compute_bias(pred: xr.DataArray, obs: xr.DataArray) -> xr.DataArray:
    return pred - obs


def compute_abs_error(pred: xr.DataArray, obs: xr.DataArray) -> xr.DataArray:
    return np.abs(pred - obs)


def compute_sq_error(pred: xr.DataArray, obs: xr.DataArray) -> xr.DataArray:
    return (pred - obs) ** 2


def compute_rmse_field(pred: xr.DataArray, obs: xr.DataArray) -> xr.DataArray:
    return np.sqrt(compute_sq_error(pred, obs))


def save_precip_dataset(precip: xr.DataArray, output_nc: str, attrs: dict | None = None) -> None:
    os.makedirs(os.path.dirname(output_nc), exist_ok=True)
    ds = precip.to_dataset(name=pa_config.PRECIP_VAR_NAME)
    if attrs:
        ds.attrs.update(attrs)
    ds.to_netcdf(output_nc)


def open_precip_datasets(file_dict: dict) -> Dict[str, xr.DataArray]:
    data_dict = {"MONAN": _normalize_precip_coords(xr.open_dataset(file_dict["monan_nc"])[pa_config.PRECIP_VAR_NAME])}
    for reference, ref_dict in file_dict["refs"].items():
        ds = xr.open_dataset(ref_dict["remap_nc"])
        data_dict[reference] = _normalize_precip_coords(ds[pa_config.PRECIP_VAR_NAME])
    return data_dict


# =================================================================================================
# Plotting
# =================================================================================================
def _apply_map_features(ax, domain_name: str) -> None:
    domain_dict = pa_config.DOMAINS[domain_name]
    extent = domain_dict["extent"]
    if extent is not None:
        ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.set_xticks(domain_dict["xticks"], crs=ccrs.PlateCarree())
    ax.set_yticks(domain_dict["yticks"], crs=ccrs.PlateCarree())
    ax.xaxis.set_major_formatter(LongitudeFormatter())
    ax.yaxis.set_major_formatter(LatitudeFormatter())
    ax.set_xlabel("")
    ax.set_ylabel("")


def plot_map(
    data: xr.DataArray,
    title: str,
    output_filepath: str,
    domain_name: str,
    levels: list[float],
    cmap_name: str,
    extend: str,
    cbar_label: str,
) -> None:
    if not HAS_PLOTTING:
        log("Plotting skipped because matplotlib/cartopy are not available.", level=0)
        return

    os.environ["CARTOPY_USER_DATA_DIR"] = pa_config.DIR_CARTOPY_DATA
    domain_data = subset_domain(_normalize_precip_coords(data), domain_name)
    figsize = pa_config.FIGSIZE_GLOBAL if domain_name == "GLB" else pa_config.FIGSIZE_REGIONAL
    fig = plt.figure(figsize=figsize)
    ax = plt.axes(projection=ccrs.PlateCarree())
    norm = BoundaryNorm(levels, ncolors=plt.get_cmap(cmap_name).N, clip=False)
    im = domain_data.plot(
        ax=ax,
        transform=ccrs.PlateCarree(),
        cmap=cmap_name,
        norm=norm,
        add_colorbar=False,
    )
    _apply_map_features(ax, domain_name)
    ax.set_title(title)
    cbar = plt.colorbar(im, orientation="vertical", pad=0.04, aspect=35, extend=extend)
    cbar.set_label(cbar_label)
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    plt.savefig(output_filepath, dpi=pa_config.FIG_DPI, bbox_inches="tight")
    plt.close(fig)

def plot_bias_map_custom(data, title, output_filepath, domain_name):
    if not HAS_PLOTTING:
        log("Plotting skipped because matplotlib/cartopy are not available.", level=0)
        return

    os.environ["CARTOPY_USER_DATA_DIR"] = pa_config.DIR_CARTOPY_DATA

    plot_data = subset_domain(_normalize_precip_coords(data), domain_name)
    levels = pa_config.BIAS_LEVELS
    colors_rgb = pa_config.BIAS_COLORS_RGB
    cmap = ListedColormap([(r / 255, g / 255, b / 255) for r, g, b in colors_rgb])
    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=False)

    figsize = pa_config.FIGSIZE_GLOBAL if domain_name == "GLB" else pa_config.FIGSIZE_REGIONAL
    fig = plt.figure(figsize=figsize)
    ax = plt.axes(projection=ccrs.PlateCarree())

    im = plot_data.plot(
        ax=ax,
        transform=ccrs.PlateCarree(),
        cmap=cmap,
        norm=norm,
        add_colorbar=False,
    )

    _apply_map_features(ax, domain_name)
    ax.set_xlabel("")
    ax.set_ylabel("")

    cbar = plt.colorbar(
        im,
        ax=ax,
        orientation="vertical",
        pad=0.04,
        aspect=35,
        extend=pa_config.BIAS_EXTEND,
        ticks=pa_config.BIAS_LEVELS,
    )
    cbar.set_label(pa_config.BIAS_CBAR_LABEL)

    ax.set_title(title)

    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    plt.savefig(output_filepath, dpi=pa_config.FIG_DPI, bbox_inches="tight")
    plt.close(fig)

def plot_monan_accum_map_custom(
    data: xr.DataArray,
    title: str,
    output_filepath: str,
    domain_name: str,
) -> None:
    if not HAS_PLOTTING:
        log("Plotting skipped because matplotlib/cartopy are not available.", level=0)
        return

    os.environ["CARTOPY_USER_DATA_DIR"] = pa_config.DIR_CARTOPY_DATA

    plot_data = subset_domain(_normalize_precip_coords(data), domain_name)

    colors_rgb = pa_config.MONAN_ACCUM_COLORS_RGB
    levels = pa_config.MONAN_ACCUM_LEVELS

    cmap = ListedColormap([(r / 255, g / 255, b / 255) for r, g, b in colors_rgb])
    norm = BoundaryNorm(levels, ncolors=len(levels), extend="max")

    figsize = pa_config.FIGSIZE_GLOBAL if domain_name == "GLB" else pa_config.FIGSIZE_REGIONAL
    #fig = plt.figure(figsize=figsize)
    fig = plt.figure(figsize=(10, 5))
    ax = plt.axes(projection=ccrs.PlateCarree())

    if domain_name == "GLB":
        ax.set_extent([-180, 180, -90, 90], crs=ccrs.PlateCarree())

        lon_name, lat_name = "lon", "lat"
        lon2d, lat2d = np.meshgrid(plot_data[lon_name].values, plot_data[lat_name].values)

        im = ax.pcolormesh(
            lon2d,
            lat2d,
            plot_data.values,
            cmap=cmap,
            norm=norm,
            shading="auto",
            transform=ccrs.PlateCarree(),
        )

        ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.6)
        ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4)
        ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="none", edgecolor="black", linewidth=0.2)

        gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="gray", alpha=0.5, linestyle="--")
        gl.top_labels = False
        gl.right_labels = False
        gl.bottom_labels = True
        gl.left_labels = True
        gl.xlines = False
        gl.ylines = False
        gl.xlocator = plt.FixedLocator(np.arange(-180, 181, 60))
        gl.ylocator = plt.FixedLocator(np.arange(-60, 61, 30))

    else:
        _apply_map_features(ax, domain_name)

        if domain_name == "AMS":
            estados = cfeature.NaturalEarthFeature(
                category="cultural",
                name="admin_1_states_provinces_lines",
                scale="50m",
                facecolor="none",
            )
            ax.add_feature(estados, edgecolor="black", linewidth=0.4)

        if domain_name == "ACC":
            estados = cfeature.NaturalEarthFeature(
                category="cultural",
                name="admin_1_states_provinces_lines",
                scale="50m",
                facecolor="none",
            )
            ax.add_feature(estados, edgecolor="black", linewidth=0.4)

        ax.tick_params(
            axis="both",
            which="major",
            direction="in",
            length=2,
            width=0.6,
            labelsize=8,
            top=True,
            right=True,
        )

        lon2d, lat2d = np.meshgrid(plot_data["lon"].values, plot_data["lat"].values)

        im = ax.pcolormesh(
            lon2d,
            lat2d,
            plot_data.values,
            cmap=cmap,
            norm=norm,
            shading="auto",
            transform=ccrs.PlateCarree(),
        )

        ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.6)
        ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4)
        ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="none", edgecolor="black", linewidth=0.2)

        gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="gray", alpha=0.5, linestyle="--")
        gl.top_labels = False
        gl.right_labels = False
        gl.bottom_labels = False
        gl.left_labels = False
        gl.xlines = False
        gl.ylines = False
        gl.xlocator = plt.FixedLocator(np.arange(-180, 181, 10))
        gl.ylocator = plt.FixedLocator(np.arange(-60, 61, 10))
        gl.xlabel_style = {"size": 9}
        gl.ylabel_style = {"size": 9}

    cbar = plt.colorbar(
        im,
        orientation="vertical",
        pad=0.1,
        aspect=50,
        boundaries=levels,
        extend="max",
    )
    cbar.set_label(pa_config.MONAN_ACCUM_CBAR_LABEL)
    cbar.set_ticks(levels)

    ax.set_title(title, fontsize=12)

    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    plt.savefig(output_filepath, dpi=300, bbox_inches="tight")
    plt.close(fig)    

def get_monan_accum_title_and_stats(precip: xr.DataArray, domain_name: str, lead: int, valid_str: str) -> tuple[str, float, float]:
    domain_precip = subset_domain(_normalize_precip_coords(precip), domain_name)

    prec_max = float(np.nanmax(domain_precip.values))
    prec_mean = compute_domain_mean(domain_precip)

    max_str = f"Max: {prec_max:.2f} mm"
    mean_str = f"Mean: {prec_mean:.2f} mm"

    if domain_name == "GLB":
        title = (
            f"MONAN {get_cycle_str()}+{valid_str} - 24h prec accum for {lead:03d}h\n"
            f"Global - {max_str} | {mean_str}"
        )
    else:
        title = (
            f"MONAN {get_cycle_str()}+{valid_str} - prec24h {lead:03d}h\n"
            f"{domain_name} - {max_str} | {mean_str}"
        )

    return title, prec_max, prec_mean

# =================================================================================================
# Remapping, reusing monan_analysis.preprocess
# =================================================================================================
def remap_cdo(obs_nc: str, out_nc: str, ref_nc: str, overwrite: bool = False) -> None:
    if os.path.exists(out_nc) and not overwrite:
        log(f"Remapped file already exists: {out_nc}", level=2)
        return
    os.makedirs(os.path.dirname(out_nc), exist_ok=True)
    monan_preprocess.map_data_to_different_grid_with_cdo(ref_nc=ref_nc, input_nc=obs_nc, output_nc=out_nc)


def remap_observations_to_monan_grid(file_dict: dict) -> None:
    for reference, ref_dict in file_dict["refs"].items():
        log(f"Remapping {reference} to MONAN grid...", level=1)
        remap_cdo(
            obs_nc=ref_dict["obs_nc"],
            out_nc=ref_dict["remap_nc"],
            ref_nc=file_dict["monan_nc"],
            overwrite=pa_config.OVERWRITE_REMAP,
        )


# =================================================================================================
# MONAN accumulation generation
# =================================================================================================
def generate_monan_24h_accumulations() -> None:
    for pair in build_monan_flushout_filepairs():
        output_nc = pair["output_nc"]
        if os.path.exists(output_nc) and not pa_config.OVERWRITE_OUTPUTS:
            log(f"MONAN accumulated file already exists: {output_nc}", level=1)
            continue
        if not os.path.exists(pair["start_file"]) or not os.path.exists(pair["end_file"]):
            raise FileNotFoundError(
                f"Flushout files not found for lead {pair['lead']:03d} h:\n{pair['start_file']}\n{pair['end_file']}"
            )

        ds_start = xr.open_dataset(pair["start_file"], engine="netcdf4")
        ds_end = xr.open_dataset(pair["end_file"], engine="netcdf4")
        start_acc = ds_start[pa_config.MONAN_RAINNC_NAME].isel({pa_config.MONAN_TIME_DIM_NAME: 0}) + ds_start[
            pa_config.MONAN_RAINC_NAME
        ].isel({pa_config.MONAN_TIME_DIM_NAME: 0})
        end_acc = ds_end[pa_config.MONAN_RAINNC_NAME].isel({pa_config.MONAN_TIME_DIM_NAME: 0}) + ds_end[
            pa_config.MONAN_RAINC_NAME
        ].isel({pa_config.MONAN_TIME_DIM_NAME: 0})
        precip = _normalize_precip_coords((end_acc - start_acc).squeeze().rename(pa_config.PRECIP_VAR_NAME)).astype(
            "float32"
        )
        out_dir = os.path.join(
            pa_config.DIR_OUTPUT_DATA_MONAN,
            get_yearmonth_str(),
            get_cycle_str(),
            )
        os.makedirs(out_dir, exist_ok=True)

        out_nc_copy = os.path.join(
            out_dir,
            f"monan_{get_cycle_str()}_{pair['end_str']}_{pair['lead']:03d}h.nc",
        )

        save_precip_dataset(
            precip,
            out_nc_copy,
            attrs={
                "description": "MONAN 24 h accumulated precipitation",
            "cycle": get_cycle_str(),
                "lead_time_h": pair["lead"],
                "start_time": pair["start_str"],
                "end_time": pair["end_str"],
            },
        )

        if pa_config.RUN_PLOTTING:
            fig_dir = os.path.join(pa_config.DIR_OUTPUT_FIG_MONAN, get_yearmonth_str(), get_cycle_str())
            os.makedirs(fig_dir, exist_ok=True)

            for domain_name in pa_config.DOMAINS:
                title, _, _ = get_monan_accum_title_and_stats(
                    precip=precip,
                    domain_name=domain_name,
                    lead=pair["lead"],
                    valid_str=pair["end_str"],
                )

                out_fig = os.path.join(
                    fig_dir,
                    f"MONAN_24precacum_{get_cycle_str()}_{pair['end_str']}_{domain_name}.png",
                )

                plot_monan_accum_map_custom(
                    data=precip,
                    title=title,
                    output_filepath=out_fig,
                    domain_name=domain_name,
                )

# =================================================================================================
# Skill metrics
# =================================================================================================
def binary_contingency(pred: xr.DataArray, obs: xr.DataArray, threshold_mm: float) -> dict[str, int]:
    pred_event = pred >= threshold_mm
    obs_event = obs >= threshold_mm
    h = int(((pred_event) & (obs_event)).sum().item())
    m = int(((~pred_event) & (obs_event)).sum().item())
    f = int(((pred_event) & (~obs_event)).sum().item())
    c = int(((~pred_event) & (~obs_event)).sum().item())
    return {"H": h, "M": m, "F": f, "C": c}


def compute_skill_scores(h: int, m: int, f: int, c: int) -> dict[str, float]:
    total = h + m + f + c
    acc = (h + c) / total if total else np.nan
    pod = h / (h + m) if (h + m) else np.nan
    pofd = f / (f + c) if (f + c) else np.nan
    far = f / (h + f) if (h + f) else np.nan
    csi = h / (h + m + f) if (h + m + f) else np.nan
    f1 = 2 * h / (2 * h + f + m) if (2 * h + f + m) else np.nan
    return {"ACC": acc, "POD": pod, "POFD": pofd, "FAR": far, "CSI": csi, "F1": f1}


def initialize_skill_txt(file_dict: dict, threshold_mm: float) -> str:
    txt_dir = os.path.join(
        pa_config.DIR_OUTPUT_TXT_SKILL,
        file_dict["yearmonth_str"],
        file_dict["cycle_str"],
    )
    os.makedirs(txt_dir, exist_ok=True)

    txt_path = os.path.join(
        txt_dir,
        f"skill_{file_dict['cycle_str']}_thr{int(threshold_mm)}mm.txt"
    )

    if not os.path.exists(txt_path) or pa_config.OVERWRITE_OUTPUTS:
        with open(txt_path, "w", encoding="utf-8") as fobj:
            fobj.write("lead_h reference domain threshold_mm H M F C ACC POD POFD FAR CSI F1\n")
    return txt_path


def append_skill_txt(txt_path: str, lead: int, reference: str, domain_name: str, threshold_mm: float, scores: dict, cont: dict) -> None:
    with open(txt_path, "a", encoding="utf-8") as fobj:
        fobj.write(
            f"{lead:03d} {reference} {domain_name} {threshold_mm} {cont['H']} {cont['M']} {cont['F']} {cont['C']} "
            f"{scores['ACC']:.6f} {scores['POD']:.6f} {scores['POFD']:.6f} {scores['FAR']:.6f} {scores['CSI']:.6f} {scores['F1']:.6f}\n"
        )


# =================================================================================================
# Analysis runners
# =================================================================================================
def _save_metric_netcdf(metric_field, metric_name, reference, lead, file_dict):
    metric_dir_map = {
        "bias": pa_config.DIR_OUTPUT_DATA_BIAS,
        "mae": pa_config.DIR_OUTPUT_DATA_MAE,
        "sqerr": pa_config.DIR_OUTPUT_DATA_SQERR,
        "skill": pa_config.DIR_OUTPUT_DATA_SKILL,
        "monan": pa_config.DIR_OUTPUT_DATA_MONAN,
    }

    base_dir = metric_dir_map[metric_name]
    out_dir = os.path.join(base_dir, file_dict["yearmonth_str"], file_dict["cycle_str"])
    os.makedirs(out_dir, exist_ok=True)

    out_nc = os.path.join(
        out_dir,
        f"{metric_name}_{reference}_{file_dict['cycle_str']}_{lead:03d}h.nc"
    )
    save_precip_dataset(metric_field.rename(pa_config.PRECIP_VAR_NAME), out_nc)
    return out_nc


def run_bias_analysis(lead: int, file_dict: dict, data_dict: Dict[str, xr.DataArray]) -> None:
    monan = data_dict["MONAN"]
    for reference in pa_config.OBS_REFERENCE_LIST:
        obs = data_dict[reference]
        bias = compute_bias(monan, obs)
        _save_metric_netcdf(bias, "bias", reference, lead, file_dict)
        if pa_config.RUN_PLOTTING:
            legacy_dir = os.path.join(pa_config.DIR_OUTPUT_FIG_BIAS, get_yearmonth_str(), get_cycle_str())
            os.makedirs(legacy_dir, exist_ok=True)
            for domain_name in pa_config.DOMAINS:
                domain_bias = subset_domain(bias, domain_name)
                mean_bias = compute_domain_mean(subset_domain(bias, domain_name))
                ref_label = "GPM IMERG" if reference == "GPM" else reference
                title = (
                    f"Bias {lead:03d}h MONAN {get_cycle_str()} vs {ref_label}\n"
                    f"{domain_name}, Domain mean: {mean_bias:.2f} mm"
                )
                out_fig = os.path.join(legacy_dir, f"bias_MONAN_{reference}_{domain_name}_{lead:03d}h.png")
                plot_bias_map_custom(data=bias, title=title, output_filepath=out_fig, domain_name=domain_name)#                plot_map(domain_bias, title, out_fig, domain_name, pa_config.BIAS_LEVELS, pa_config.BIAS_CMAP_NAME, "both", "(mm)")


def run_mae_analysis(lead: int, file_dict: dict, data_dict: Dict[str, xr.DataArray]) -> None:
    monan = data_dict["MONAN"]
    for reference in pa_config.OBS_REFERENCE_LIST:
        obs = data_dict[reference]
        mae = compute_abs_error(monan, obs)
        _save_metric_netcdf(mae, "mae", reference, lead, file_dict)
        if pa_config.RUN_PLOTTING:
            legacy_dir = os.path.join(pa_config.DIR_OUTPUT_FIG_MAE, get_yearmonth_str(), get_cycle_str())
            os.makedirs(legacy_dir, exist_ok=True)
            for domain_name in pa_config.DOMAINS:
                domain_mae = subset_domain(mae, domain_name)
                mean_mae = compute_domain_mean(domain_mae)
                ref_label = "GPM IMERG" if reference == "GPM" else reference
                title = (
                    f"MAE {lead:03d}h MONAN {get_cycle_str()} vs {ref_label}\n"
                    f"{domain_name}, Domain mean: {mean_mae:.2f} mm"
                )
                out_fig = os.path.join(legacy_dir, f"mae_MONAN_{reference}_{domain_name}_{lead:03d}h.png")
                plot_map(domain_mae, title, out_fig, domain_name, pa_config.ABS_ERROR_LEVELS, pa_config.ABS_ERROR_CMAP_NAME, "max", "(mm)")


def run_squared_error_analysis(lead: int, file_dict: dict, data_dict: Dict[str, xr.DataArray]) -> None:
    monan = data_dict["MONAN"]
    for reference in pa_config.OBS_REFERENCE_LIST:
        obs = data_dict[reference]
        sqerr = compute_sq_error(monan, obs)
        _save_metric_netcdf(sqerr, "sqerr", reference, lead, file_dict)
        

def run_skill_analysis(lead: int, threshold_mm: float, file_dict: dict, data_dict: Dict[str, xr.DataArray]) -> None:
    monan = data_dict["MONAN"]
    txt_path = initialize_skill_txt(file_dict, threshold_mm) if pa_config.SAVE_SKILL_TXT else None
    for reference in pa_config.OBS_REFERENCE_LIST:
        obs = data_dict[reference]
        for domain_name in pa_config.DOMAINS:
            pred_dom = subset_domain(monan, domain_name)
            obs_dom = subset_domain(obs, domain_name)
            cont = binary_contingency(pred_dom, obs_dom, threshold_mm)
            scores = compute_skill_scores(cont["H"], cont["M"], cont["F"], cont["C"])
            if txt_path is not None:
                append_skill_txt(txt_path, lead, reference, domain_name, threshold_mm, scores, cont)
            if pa_config.SAVE_SKILL_NETCDF:
                score_vars = {name: xr.DataArray(value) for name, value in scores.items()}
                ds_out = xr.Dataset(score_vars)
                out_dir = os.path.join(
                    pa_config.DIR_OUTPUT_DATA_SKILL,
                    file_dict["yearmonth_str"],
                    file_dict["cycle_str"],
                )
                os.makedirs(out_dir, exist_ok=True)

                out_nc = os.path.join(
                    out_dir,
                    f"skill_{reference}_{domain_name}_{file_dict['cycle_str']}_{lead:03d}h_thr{int(threshold_mm)}mm.nc",
                )
                ds_out.to_netcdf(out_nc)


# =================================================================================================
# Copy config files for reproducibility
# =================================================================================================
def cp_config_files() -> None:
    out_dir = os.path.join(
        pa_config.DIR_OUTPUT_DATA_MONAN,
        get_yearmonth_str(),
        get_cycle_str(),
    )
    os.makedirs(out_dir, exist_ok=True)
    shutil.copy2(Path(__file__).with_name("precipitation_analysis_config.py"), out_dir)
    gen_config_package_dir = os.path.dirname(monan_analysis.__file__)
    shutil.copy2(os.path.join(gen_config_package_dir, "config.py"), out_dir)