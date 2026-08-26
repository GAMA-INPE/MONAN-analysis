#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calcula o Fractions Skill Score, FSS, mensal para MONAN Regional, WRF e MONAN Global
usando precipitação acumulada em 24 horas.

    limiares: 1, 2, 5, 10, 20 e 50 mm/24 h
    janelas: 1, 3, 5, 9, 15 e 25 pontos
    prazos: 24, 48, 72, 96 e 120 h

Uso:
    python Calc_FSS_MONAN_Regional_WRF.py --period 202607

    python Calc_FSS_MONAN_Regional_WRF.py \
        --period 202607 --references GPM_IMERG MSWEP

    python Calc_FSS_MONAN_Regional_WRF.py \
        --period 202607 --overwrite-remap

Requer:
    numpy, xarray, scipy, netCDF4 e CDO.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import xarray as xr
from scipy.ndimage import uniform_filter


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

BASE_PRECIP = Path(
    "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h"
)

BASE_NETCDF = Path(
    "/lustre/projetos/monan_gam/andre.lyra/NetCDFs"
)

OUTDIR_FSS = (
    BASE_PRECIP
    / "FSS_Regional_WRF"
    / "MONAN_Global_grid"
)

REMAP_CACHE = (
    BASE_PRECIP
    / "FSS_Regional_WRF_remapcon"
    / "MONAN_Global_grid"
)

MASK_GLOBAL_FILE = (
    BASE_NETCDF
    / "Masks"
    / "Mask_MONAN_Regional_domain_GLOBAL_grid.nc"
)

TARGET_MASK_FILE = (
    OUTDIR_FSS
    / "_metadata"
    / "Mask_REG_WRF_MASKED_MONAN_Global_grid.nc"
)

MODELS = (
    "MONAN_Regional",
    "WRF",
    "MONAN_Global",
)

# Apenas MONAN Regional e WRF definem a extensao espacial REG_WRF_MASKED.
# A inclusao do MONAN Global nao altera o dominio de verificacao.
DOMAIN_MODELS = (
    "MONAN_Regional",
    "WRF",
)

MODEL_REGRID_METHOD = {
    "MONAN_Regional": "remapcon",
    "WRF": "remapcon",
    "MONAN_Global": "native_target_grid",
}

REFERENCES = (
    "GPM_IMERG",
    "GSMAP",
    "MSWEP",
)

THRESHOLDS = (
    1.0,
    2.0,
    5.0,
    10.0,
    20.0,
    50.0,
)

WINDOW_SIZES = (
    1,
    3,
    5,
    9,
    15,
    25,
)

DEFAULT_LEADS = (
    24,
    48,
    72,
    96,
    120,
)

VAR_PREC = "prec"

DOMAIN = "REG_WRF_MASKED"

TARGET_GRID = "MONAN_Global_grid"

REGRID_METHOD = "remapcon"

EARTH_KM_PER_DEGREE = 111.32

REFERENCE_TEMPLATES = {
    "GPM_IMERG": (
        "GPM_IMERG_Precipitation_24h_accum_{valid}00.nc"
    ),
    "GSMAP": (
        "GSMAP_Precipitation_24h_accum_{valid}00.nc"
    ),
    "MSWEP": (
        "MSWEP_Precipitation_24h_accum_{valid}00.nc"
    ),
}


# =============================================================================
# ARGUMENTOS E TEMPO
# =============================================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Calcula FSS do MONAN Regional, WRF e MONAN Global "
            "na grade do MONAN Global."
        )
    )

    parser.add_argument(
        "--period",
        required=True,
        help=(
            "Período de validade YYYYMM, "
            "por exemplo 202607."
        ),
    )

    parser.add_argument(
        "--references",
        nargs="+",
        default=["all"],
        help=(
            "GPM_IMERG GSMAP MSWEP ou all."
        ),
    )

    parser.add_argument(
        "--leads",
        nargs="+",
        type=int,
        default=list(DEFAULT_LEADS),
        help=(
            "Prazos em horas. "
            "Padrão: 24 48 72 96 120."
        ),
    )

    parser.add_argument(
        "--overwrite-remap",
        action="store_true",
        help=(
            "Refaz os modelos remapeados "
            "para a grade do MONAN Global."
        ),
    )

    return parser.parse_args()


def parse_period(period):

    if len(period) != 6 or not period.isdigit():
        raise ValueError(
            f"Período inválido: {period}. "
            "Use YYYYMM."
        )

    year = int(period[:4])
    month = int(period[4:])

    if not 1 <= month <= 12:
        raise ValueError(
            f"Mês inválido: {period}."
        )

    return year, month


def valid_dates(year, month):
    """
    Retorna as datas finais dos acumulados de 24 h pertencentes ao mês.

     Exemplo para 202607:
        primeira validade: 2026070200
        última validade:   2026080100

    Portanto, julho contém 31 janelas de 24 h:
        2026070100 -> 2026070200
        ...
        2026073100 -> 2026080100
    """

    ndays = calendar.monthrange(
        year,
        month,
    )[1]

    first_start = datetime(
        year,
        month,
        1,
        0,
    )

    return [
        first_start
        + timedelta(days=day)
        for day in range(
            1,
            ndays + 1,
        )
    ]


def select_references(values):

    lookup = {
        item.upper(): item
        for item in REFERENCES
    }

    values_upper = [
        item.upper()
        for item in values
    ]

    if "ALL" in values_upper:
        return list(REFERENCES)

    invalid = [
        item
        for item in values_upper
        if item not in lookup
    ]

    if invalid:
        raise ValueError(
            f"Referências inválidas: {invalid}. "
            f"Opções: {list(REFERENCES)}"
        )

    return [
        lookup[item]
        for item in values_upper
    ]


def validate_leads(values):

    leads = sorted(
        set(
            int(item)
            for item in values
        )
    )

    invalid = [
        lead
        for lead in leads
        if lead not in DEFAULT_LEADS
    ]

    if invalid:
        raise ValueError(
            f"Prazos definidos: "
            f"{list(DEFAULT_LEADS)} h. "
            f"Inválidos: {invalid}"
        )

    return leads


# =============================================================================
# NOMES E CAMINHOS
# =============================================================================

def forecast_path(
    model,
    valid,
    lead,
):

    init = (
        valid
        - timedelta(hours=lead)
    )

    init_str = init.strftime(
        "%Y%m%d%H"
    )

    valid_str = valid.strftime(
        "%Y%m%d%H"
    )

    if model == "MONAN_Regional":

        name = (
            "MONAN_Regional_"
            "Precipitation_24h_acum_"
            f"{init_str}_"
            f"{valid_str}_"
            f"{lead:03d}h.nc"
        )

    elif model == "WRF":

        name = (
            "WRF_"
            "Precipitation_24h_acum_"
            f"{init_str}_"
            f"{valid_str}_"
            f"{lead:03d}h.nc"
        )

    elif model == "MONAN_Global":

        name = (
            "MONAN_"
            "Precipitation_24h_acum_"
            f"{init_str}_"
            f"{valid_str}_"
            f"{lead:03d}h.nc"
        )

    else:

        raise ValueError(
            f"Modelo não suportado: "
            f"{model}"
        )

    model_dir = (
        "MONAN"
        if model == "MONAN_Global"
        else model
    )

    return (
        BASE_PRECIP
        / model_dir
        / init_str
        / name
    )


def reference_original_path(
    reference,
    valid,
):

    valid_str = valid.strftime(
        "%Y%m%d%H"
    )

    name = (
        REFERENCE_TEMPLATES[
            reference
        ].format(
            valid=valid_str
        )
    )

    return (
        BASE_PRECIP
        / reference
        / f"{valid_str}00"
        / name
    )


def reference_monan_grid_path(
    reference,
    valid,
):

    original = (
        reference_original_path(
            reference,
            valid,
        )
    )

    return original.with_name(
        f"{original.stem}_"
        "MONAN_grid.nc"
    )


def remapped_model_path(
    model,
    valid,
    lead,
):

    init = (
        valid
        - timedelta(hours=lead)
    )

    init_str = init.strftime(
        "%Y%m%d%H"
    )

    valid_str = valid.strftime(
        "%Y%m%d%H"
    )

    name = (
        f"{model}_"
        "Precipitation_24h_acum_"
        f"{init_str}_"
        f"{valid_str}_"
        f"{lead:03d}h_"
        "MONAN_Global_grid.nc"
    )

    return (
        REMAP_CACHE
        / model
        / init_str
        / name
    )


# =============================================================================
# COORDENADAS, LEITURA E ALINHAMENTO
# =============================================================================

def coord_name(
    da,
    kind,
):

    names = list(
        dict.fromkeys(
            list(da.dims)
            + list(da.coords)
        )
    )

    lower = {
        str(name).lower(): name
        for name in names
    }

    if kind == "lat":

        exact = (
            "lat",
            "latitude",
            "y",
        )

        fragment = "lat"

    elif kind == "lon":

        exact = (
            "lon",
            "longitude",
            "x",
        )

        fragment = "lon"

    else:

        raise ValueError(
            kind
        )

    for candidate in exact:

        if candidate in lower:
            return lower[candidate]

    for name in names:

        if fragment in str(name).lower():
            return name

    raise ValueError(
        f"Coordenada {kind} "
        f"não encontrada em {names}"
    )


def standardize_lat_lon(da):

    lat_name = coord_name(
        da,
        "lat",
    )

    lon_name = coord_name(
        da,
        "lon",
    )

    rename = {}

    if lat_name != "lat":
        rename[lat_name] = "lat"

    if lon_name != "lon":
        rename[lon_name] = "lon"

    if rename:
        da = da.rename(rename)

    da = da.squeeze(
        drop=True
    )

    if (
        da["lat"].ndim != 1
        or da["lon"].ndim != 1
    ):

        raise ValueError(
            "Latitude e longitude "
            "devem ser unidimensionais."
        )

    lon = np.mod(
        np.asarray(
            da["lon"].values,
            dtype="float64",
        ),
        360.0,
    )

    lon[
        np.isclose(
            lon,
            360.0,
            atol=1.0e-8,
            rtol=0.0,
        )
    ] = 0.0

    da = (
        da
        .assign_coords(
            lon=lon
        )
        .sortby("lon")
        .sortby("lat")
    )

    lon_values = np.asarray(
        da["lon"].values,
        dtype="float64",
    )

    _, idx = np.unique(
        np.round(
            lon_values,
            8,
        ),
        return_index=True,
    )

    idx = np.sort(idx)

    if len(idx) != len(
        lon_values
    ):
        da = da.isel(
            lon=idx
        )

    if not da.get_index(
        "lat"
    ).is_unique:

        raise ValueError(
            "Latitude duplicada "
            "após padronização."
        )

    if not da.get_index(
        "lon"
    ).is_unique:

        raise ValueError(
            "Longitude duplicada "
            "após padronização."
        )

    return da.transpose(
        "lat",
        "lon",
    )


def get_bounds(da):

    return {
        "lat": (
            float(
                da.lat.min()
            ),
            float(
                da.lat.max()
            ),
        ),
        "lon": (
            float(
                da.lon.min()
            ),
            float(
                da.lon.max()
            ),
        ),
    }


def intersect_bounds(
    *items,
):

    lat_min = max(
        item["lat"][0]
        for item in items
    )

    lat_max = min(
        item["lat"][1]
        for item in items
    )

    lon_min = max(
        item["lon"][0]
        for item in items
    )

    lon_max = min(
        item["lon"][1]
        for item in items
    )

    if (
        lat_min >= lat_max
        or lon_min >= lon_max
    ):

        raise ValueError(
            "Não existe interseção "
            "espacial entre os domínios."
        )

    return {
        "lat": (
            lat_min,
            lat_max,
        ),
        "lon": (
            lon_min,
            lon_max,
        ),
    }


def crop(
    da,
    bounds,
):

    lat_min, lat_max = (
        bounds["lat"]
    )

    lon_min, lon_max = (
        bounds["lon"]
    )

    out = da.sel(
        lat=slice(
            lat_min,
            lat_max,
        ),
        lon=slice(
            lon_min,
            lon_max,
        ),
    )

    if (
        out.sizes.get(
            "lat",
            0,
        ) == 0
        or out.sizes.get(
            "lon",
            0,
        ) == 0
    ):

        raise ValueError(
            f"Recorte vazio: "
            f"{bounds}"
        )

    return out


def load_precip(
    path,
    bounds=None,
):

    with xr.open_dataset(
        path,
        engine="netcdf4",
        mask_and_scale=True,
    ) as ds:

        if VAR_PREC not in ds:

            raise KeyError(
                f"Variável "
                f"{VAR_PREC!r} "
                f"ausente em {path}. "
                f"Disponíveis: "
                f"{list(ds.data_vars)}"
            )

        da = standardize_lat_lon(
            ds[VAR_PREC]
        )

        if bounds is not None:

            da = crop(
                da,
                bounds,
            )

        da = da.load()

    da = da.where(
        np.isfinite(da)
    )

    # Valores negativos sao tratados como 0 mm.
    # NaN/missing reais permanecem como NaN.
    da = xr.where(
        da < 0.0,
        0.0,
        da,
    )

    return da.astype(
        "float32"
    )


def load_global_mask():

    if not MASK_GLOBAL_FILE.is_file():

        raise FileNotFoundError(
            f"Máscara não encontrada: "
            f"{MASK_GLOBAL_FILE}"
        )

    with xr.open_dataset(
        MASK_GLOBAL_FILE,
        engine="netcdf4",
    ) as ds:

        if "mask" not in ds:

            raise KeyError(
                "Variável 'mask' "
                f"ausente em "
                f"{MASK_GLOBAL_FILE}"
            )

        mask = (
            standardize_lat_lon(
                ds["mask"]
            )
            .load()
        )

    return xr.where(
        np.isfinite(mask)
        & (mask >= 0.5),
        1,
        0,
    ).astype(
        "int8"
    )


def same_grid(
    a,
    b,
    atol=1.0e-6,
):

    if a.shape != b.shape:
        return False

    return (
        np.allclose(
            a.lat.values,
            b.lat.values,
            rtol=0.0,
            atol=atol,
        )
        and np.allclose(
            a.lon.values,
            b.lon.values,
            rtol=0.0,
            atol=atol,
        )
    )


def force_target_grid(
    da,
    target,
):

    if not same_grid(
        da,
        target,
    ):

        raise ValueError(
            "Campo não coincide "
            "com a grade alvo "
            "do MONAN Global: "
            f"campo={da.shape}, "
            f"alvo={target.shape}"
        )

    return da.assign_coords(
        lat=target.lat,
        lon=target.lon,
    )


# =============================================================================
# GRADE ALVO E MÁSCARA COMUM
# =============================================================================

def find_representative_fields(
    period,
    leads,
):

    year, month = (
        parse_period(period)
    )

    dates = valid_dates(
        year,
        month,
    )

    found = {}

    for model in DOMAIN_MODELS:

        for lead in leads:

            for valid in dates:

                path = forecast_path(
                    model,
                    valid,
                    lead,
                )

                if path.is_file():

                    found[model] = (
                        load_precip(
                            path
                        )
                    )

                    break

            if model in found:
                break

        if model not in found:

            raise FileNotFoundError(
                "Arquivo representativo "
                f"de {model} "
                f"não encontrado em "
                f"{period}."
            )

    return found


def build_target_mask(
    period,
    leads,
):

    """
    Retorna um subconjunto exato
    da grade MONAN Global.
    """

    global_mask = (
        load_global_mask()
    )

    valid_bbox = (
        global_mask.where(
            global_mask == 1,
            drop=True,
        )
    )

    if valid_bbox.size == 0:

        raise ValueError(
            "A máscara Global "
            "do MONAN Regional "
            "está vazia."
        )

    representative = (
        find_representative_fields(
            period,
            leads,
        )
    )

    common_bounds = (
        intersect_bounds(
            get_bounds(
                valid_bbox
            ),
            get_bounds(
                representative[
                    "MONAN_Regional"
                ]
            ),
            get_bounds(
                representative[
                    "WRF"
                ]
            ),
        )
    )

    target = crop(
        global_mask,
        common_bounds,
    )

    target = target.where(
        target == 1,
        drop=True,
    )

    if target.size == 0:

        raise ValueError(
            "A área "
            "REG_WRF_MASKED "
            "ficou vazia."
        )

    target = xr.where(
        target == 1,
        1,
        0,
    ).astype(
        "int8"
    )

    target.name = "mask"

    target.attrs.update(
        {
            "long_name": (
                "REG_WRF_MASKED "
                "on MONAN Global grid"
            ),
            "domain": DOMAIN,
            "target_grid": (
                TARGET_GRID
            ),
            "source_mask": str(
                MASK_GLOBAL_FILE
            ),
        }
    )

    target.lat.attrs.update(
        {
            "units": (
                "degrees_north"
            ),
            "standard_name": (
                "latitude"
            ),
            "axis": "Y",
        }
    )

    target.lon.attrs.update(
        {
            "units": (
                "degrees_east"
            ),
            "standard_name": (
                "longitude"
            ),
            "axis": "X",
        }
    )

    return (
        target,
        get_bounds(target),
    )


def save_target_mask(
    target,
):

    TARGET_MASK_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if TARGET_MASK_FILE.is_file():

        with xr.open_dataset(
            TARGET_MASK_FILE,
            engine="netcdf4",
        ) as ds:

            old = (
                standardize_lat_lon(
                    ds["mask"]
                )
                .load()
            )

        same_values = (
            same_grid(
                old,
                target,
            )
            and np.array_equal(
                np.asarray(
                    old.values
                ),
                np.asarray(
                    target.values
                ),
            )
        )

        if not same_values:

            raise RuntimeError(
                "A máscara alvo existente "
                "difere da máscara calculada. "
                "Para não alterar domínio "
                "ou grade silenciosamente, "
                "revise: "
                f"{TARGET_MASK_FILE}"
            )

        return

    ds = target.to_dataset(
        name="mask"
    )

    ds.attrs.update(
        {
            "description": (
                "Target domain for "
                "MONAN Regional x WRF FSS. "
                "Exact subset of the "
                "MONAN Global grid."
            ),
            "domain": DOMAIN,
            "target_grid": (
                TARGET_GRID
            ),
        }
    )

    ds.to_netcdf(
        TARGET_MASK_FILE,
        format="NETCDF4",
        encoding={
            "mask": {
                "dtype": "int8",
                "_FillValue": None,
                "zlib": True,
            }
        },
    )


# =============================================================================
# REMAPEAMENTO DOS MODELOS
# =============================================================================

def remapcon(
    source,
    target,
    overwrite=False,
):

    if (
        target.is_file()
        and not overwrite
    ):
        return

    if not source.is_file():

        raise FileNotFoundError(
            "Arquivo fonte "
            f"ausente: {source}"
        )

    if not TARGET_MASK_FILE.is_file():

        raise FileNotFoundError(
            "Grade alvo "
            f"ausente: "
            f"{TARGET_MASK_FILE}"
        )

    if shutil.which(
        "cdo"
    ) is None:

        raise RuntimeError(
            "CDO não encontrado "
            "no PATH."
        )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cmd = [
        "cdo",
        "-O",
        "-f",
        "nc4",
        "-z",
        "zip4",
        (
            f"-remapcon,"
            f"{TARGET_MASK_FILE}"
        ),
        str(source),
        str(target),
    ]

    print(
        "Executando:",
        " ".join(cmd),
    )

    subprocess.run(
        cmd,
        check=True,
    )


def ensure_model_remap(
    model,
    valid,
    lead,
    overwrite=False,
):

    source = forecast_path(
        model,
        valid,
        lead,
    )

    # MONAN Global ja esta na grade alvo.
    # Nao aplicar remapcon sobre a propria grade.
    if model == "MONAN_Global":

        return source

    target = (
        remapped_model_path(
            model,
            valid,
            lead,
        )
    )

    remapcon(
        source,
        target,
        overwrite=overwrite,
    )

    return target


# =============================================================================
# FSS
# =============================================================================

def neighborhood_fraction(
    binary_da,
    window_size,
):

    binary = binary_da.astype(
        "float32"
    )

    valid = xr.where(
        np.isfinite(binary),
        1.0,
        0.0,
    ).astype(
        "float32"
    )

    binary = (
        binary
        .fillna(0.0)
        .astype("float32")
    )

    num = uniform_filter(
        binary.values,
        size=window_size,
        mode="constant",
        cval=0.0,
    )

    den = uniform_filter(
        valid.values,
        size=window_size,
        mode="constant",
        cval=0.0,
    )

    with np.errstate(
        invalid="ignore",
        divide="ignore",
    ):

        frac = np.where(
            den > 0.0,
            num / den,
            np.nan,
        ).astype(
            "float32"
        )

    return xr.DataArray(
        frac,
        coords=binary_da.coords,
        dims=binary_da.dims,
    )


def latitude_weights(da):

    return xr.DataArray(
        np.cos(
            np.deg2rad(
                da.lat
            )
        ),
        coords={
            "lat": da.lat
        },
        dims=("lat",),
    )


def weighted_spatial_mean(
    da,
    weights,
):

    value = da.weighted(
        weights
    ).mean(
        dim=(
            "lat",
            "lon",
        ),
        skipna=True,
    )

    return float(
        value.values
    )


def fss_from_fractions(
    fcst_frac,
    obs_frac,
    weights,
):

    fbs_field = (
        fcst_frac
        - obs_frac
    ) ** 2

    worst_field = (
        fcst_frac ** 2
        + obs_frac ** 2
    )

    fbs = (
        weighted_spatial_mean(
            fbs_field,
            weights,
        )
    )

    worst = (
        weighted_spatial_mean(
            worst_field,
            weights,
        )
    )

    if (
        not np.isfinite(fbs)
        or not np.isfinite(worst)
        or worst == 0.0
    ):

        return (
            np.nan,
            np.nan,
            np.nan,
        )

    return (
        1.0
        - fbs / worst,
        fbs,
        worst,
    )


def grid_resolution(da):

    lat = np.asarray(
        da.lat.values,
        dtype="float64",
    )

    lon = np.asarray(
        da.lon.values,
        dtype="float64",
    )

    dlat = float(
        np.nanmedian(
            np.abs(
                np.diff(lat)
            )
        )
    )

    dlon = float(
        np.nanmedian(
            np.abs(
                np.diff(lon)
            )
        )
    )

    rep_lat = float(
        np.nanmedian(lat)
    )

    dy_km = (
        EARTH_KM_PER_DEGREE
        * dlat
    )

    dx_km = (
        EARTH_KM_PER_DEGREE
        * dlon
        * np.cos(
            np.deg2rad(
                rep_lat
            )
        )
    )

    return {
        "grid_dlat_deg": dlat,
        "grid_dlon_deg": dlon,
        "grid_dy_km": dy_km,
        "grid_dx_km": dx_km,
        "representative_lat": (
            rep_lat
        ),
    }


# =============================================================================
# AMOSTRA TEMPORAL E CSV
# =============================================================================

def build_common_sample(
    period,
    reference,
    leads,
):

    year, month = (
        parse_period(period)
    )

    sample = {}

    audit = []

    for lead in leads:

        for valid in valid_dates(
            year,
            month,
        ):

            model_files = {
                model: forecast_path(
                    model,
                    valid,
                    lead,
                )
                for model in MODELS
            }

            model_exists = {
                model: path.is_file()
                for model, path
                in model_files.items()
            }

            ref_original = (
                reference_original_path(
                    reference,
                    valid,
                )
            )

            ref_monan = (
                reference_monan_grid_path(
                    reference,
                    valid,
                )
            )

            ref_exists = (
                ref_monan.is_file()
            )

            included = (
                all(
                    model_exists.values()
                )
                and ref_exists
            )

            sample[
                (
                    lead,
                    valid,
                )
            ] = {
                "included": included,
                "model_files": (
                    model_files
                ),
                "model_exists": (
                    model_exists
                ),
                "reference_original": (
                    ref_original
                ),
                "reference_monan": (
                    ref_monan
                ),
                "reference_exists": (
                    ref_exists
                ),
            }

            audit.append(
                {
                    "periodo": (
                        period
                    ),
                    "referencia": (
                        reference
                    ),
                    "valid_date": (
                        valid.strftime(
                            "%Y%m%d%H"
                        )
                    ),
                    "lead": lead,
                    "init_date": (
                        (
                            valid
                            - timedelta(
                                hours=lead
                            )
                        )
                        .strftime(
                            "%Y%m%d%H"
                        )
                    ),
                    "monan_regional_exists": (
                        model_exists[
                            "MONAN_Regional"
                        ]
                    ),
                    "wrf_exists": (
                        model_exists[
                            "WRF"
                        ]
                    ),
                    "monan_global_exists": (
                        model_exists[
                            "MONAN_Global"
                        ]
                    ),
                    "reference_monan_grid_exists": (
                        ref_exists
                    ),
                    "included_common_sample": (
                        included
                    ),
                    "monan_regional_file": str(
                        model_files[
                            "MONAN_Regional"
                        ]
                    ),
                    "wrf_file": str(
                        model_files[
                            "WRF"
                        ]
                    ),
                    "monan_global_file": str(
                        model_files[
                            "MONAN_Global"
                        ]
                    ),
                    "reference_original_file": str(
                        ref_original
                    ),
                    "reference_monan_grid_file": str(
                        ref_monan
                    ),
                }
            )

    return (
        sample,
        audit,
    )


def save_csv(
    rows,
    path,
):

    if not rows:

        print(
            "Nenhuma linha "
            f"para salvar: {path}"
        )

        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:

        writer = csv.DictWriter(
            stream,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def new_accumulators(
    leads,
):

    result = {}

    for model in MODELS:

        result[model] = {}

        for lead in leads:

            for threshold in THRESHOLDS:

                for window in WINDOW_SIZES:

                    result[
                        model
                    ][
                        (
                            lead,
                            threshold,
                            window,
                        )
                    ] = {
                        "fbs_sum": 0.0,
                        "worst_sum": 0.0,
                        "n_valid_days": 0,
                        "n_no_event_days": 0,
                        "n_processing_errors": 0,
                    }

    return result


# =============================================================================
# PROCESSAMENTO
# =============================================================================

def process_reference(
    period,
    reference,
    leads,
    target_mask,
    target_bounds,
    common_sample,
    overwrite_remap=False,
):

    year, month = (
        parse_period(period)
    )

    dates = valid_dates(
        year,
        month,
    )

    resolution = (
        grid_resolution(
            target_mask
        )
    )

    accum = (
        new_accumulators(
            leads
        )
    )

    daily = {
        model: []
        for model in MODELS
    }

    common_days = {
        lead: sum(
            common_sample[
                (
                    lead,
                    valid,
                )
            ]["included"]
            for valid in dates
        )
        for lead in leads
    }

    print(
        "\n"
        + "=" * 88
    )

    print(
        f"FSS {period}: "
        "MONAN Regional x WRF x MONAN Global "
        f"vs {reference} | "
        f"grade={TARGET_GRID} | "
        f"domínio={DOMAIN}"
    )

    print(
        "=" * 88
    )

    for lead in leads:

        print(
            f"\nPrazo "
            f"{lead:03d} h"
        )

        for valid in dates:

            info = (
                common_sample[
                    (
                        lead,
                        valid,
                    )
                ]
            )

            if not info[
                "included"
            ]:

                reasons = []

                if not info[
                    "model_exists"
                ][
                    "MONAN_Regional"
                ]:

                    reasons.append(
                        "MONAN Regional "
                        "ausente"
                    )

                if not info[
                    "model_exists"
                ][
                    "WRF"
                ]:

                    reasons.append(
                        "WRF ausente"
                    )

                if not info[
                    "model_exists"
                ][
                    "MONAN_Global"
                ]:

                    reasons.append(
                        "MONAN Global "
                        "ausente"
                    )

                if not info[
                    "reference_exists"
                ]:

                    reasons.append(
                        f"{reference} "
                        "_MONAN_grid "
                        "ausente"
                    )

                print(
                    f"  "
                    f"{valid:%Y%m%d%H}: "
                    "fora da amostra "
                    "comum, "
                    f"{', '.join(reasons)}"
                )

                continue

            try:

                remap_files = {
                    model: (
                        ensure_model_remap(
                            model,
                            valid,
                            lead,
                            overwrite=(
                                overwrite_remap
                            ),
                        )
                    )
                    for model in MODELS
                }

                model_fields = {
                    model: (
                        force_target_grid(
                            load_precip(
                                path,
                                target_bounds,
                            ),
                            target_mask,
                        )
                    )
                    for model, path
                    in remap_files.items()
                }

                obs = (
                    force_target_grid(
                        load_precip(
                            info[
                                "reference_monan"
                            ],
                            target_bounds,
                        ),
                        target_mask,
                    )
                )

                # Mesma mascara espacial para os tres modelos
                # e para a referencia na validade corrente.

                common_valid = (
                    (target_mask == 1)
                    & np.isfinite(
                        obs
                    )
                )

                for model in MODELS:

                    common_valid = (
                        common_valid
                        & np.isfinite(
                            model_fields[
                                model
                            ]
                        )
                    )

                npoints = int(
                    common_valid
                    .sum()
                    .item()
                )

                if npoints == 0:

                    raise ValueError(
                        "Nenhum ponto "
                        "espacial comum "
                        "válido."
                    )

                obs_common = obs.where(
                    common_valid
                )

                model_common = {
                    model: field.where(
                        common_valid
                    )
                    for model, field
                    in model_fields.items()
                }

                weights = (
                    latitude_weights(
                        obs_common
                    )
                )

                for threshold in THRESHOLDS:

                    obs_event = xr.where(
                        common_valid,
                        (
                            obs_common
                            >= threshold
                        ),
                        np.nan,
                    )

                    obs_fractions = {
                        window: (
                            neighborhood_fraction(
                                obs_event,
                                window,
                            )
                        )
                        for window
                        in WINDOW_SIZES
                    }

                    for model in MODELS:

                        fcst_event = xr.where(
                            common_valid,
                            (
                                model_common[
                                    model
                                ]
                                >= threshold
                            ),
                            np.nan,
                        )

                        for window in WINDOW_SIZES:

                            fcst_fraction = (
                                neighborhood_fraction(
                                    fcst_event,
                                    window,
                                )
                            )

                            (
                                fss,
                                fbs,
                                worst,
                            ) = (
                                fss_from_fractions(
                                    fcst_fraction,
                                    obs_fractions[
                                        window
                                    ],
                                    weights,
                                )
                            )

                            a = (
                                accum[
                                    model
                                ][
                                    (
                                        lead,
                                        threshold,
                                        window,
                                    )
                                ]
                            )

                            status = "ok"

                            if np.isfinite(
                                fss
                            ):

                                a[
                                    "fbs_sum"
                                ] += fbs

                                a[
                                    "worst_sum"
                                ] += worst

                                a[
                                    "n_valid_days"
                                ] += 1

                            else:

                                status = (
                                    "no_event"
                                )

                                a[
                                    "n_no_event_days"
                                ] += 1

                            daily[
                                model
                            ].append(
                                {
                                    "periodo": (
                                        period
                                    ),
                                    "modelo": (
                                        model
                                    ),
                                    "referencia": (
                                        reference
                                    ),
                                    "dominio": (
                                        DOMAIN
                                    ),
                                    "target_grid": (
                                        TARGET_GRID
                                    ),
                                    "regrid_method_model": (
                                        MODEL_REGRID_METHOD[
                                            model
                                        ]
                                    ),
                                    "reference_grid": (
                                        "existing_MONAN_grid"
                                    ),
                                    "valid_date": (
                                        valid.strftime(
                                            "%Y%m%d%H"
                                        )
                                    ),
                                    "init_date": (
                                        (
                                            valid
                                            - timedelta(
                                                hours=lead
                                            )
                                        )
                                        .strftime(
                                            "%Y%m%d%H"
                                        )
                                    ),
                                    "lead": (
                                        lead
                                    ),
                                    "accumulation_start": (
                                        (
                                            valid
                                            - timedelta(
                                                hours=24
                                            )
                                        )
                                        .strftime(
                                            "%Y%m%d%H"
                                        )
                                    ),
                                    "accumulation_end": (
                                        valid.strftime(
                                            "%Y%m%d%H"
                                        )
                                    ),
                                    "threshold_mm": (
                                        threshold
                                    ),
                                    "window_points": (
                                        window
                                    ),
                                    "window_lat_km": (
                                        window
                                        * resolution[
                                            "grid_dy_km"
                                        ]
                                    ),
                                    "window_lon_km": (
                                        window
                                        * resolution[
                                            "grid_dx_km"
                                        ]
                                    ),
                                    "grid_dlat_deg": (
                                        resolution[
                                            "grid_dlat_deg"
                                        ]
                                    ),
                                    "grid_dlon_deg": (
                                        resolution[
                                            "grid_dlon_deg"
                                        ]
                                    ),
                                    "grid_dy_km": (
                                        resolution[
                                            "grid_dy_km"
                                        ]
                                    ),
                                    "grid_dx_km": (
                                        resolution[
                                            "grid_dx_km"
                                        ]
                                    ),
                                    "representative_lat": (
                                        resolution[
                                            "representative_lat"
                                        ]
                                    ),
                                    "n_spatial_points": (
                                        npoints
                                    ),
                                    "fss": (
                                        fss
                                    ),
                                    "fbs": (
                                        fbs
                                    ),
                                    "fbs_worst": (
                                        worst
                                    ),
                                    "status": (
                                        status
                                    ),
                                    "forecast_original_file": str(
                                        info[
                                            "model_files"
                                        ][
                                            model
                                        ]
                                    ),
                                    "forecast_remap_file": str(
                                        remap_files[
                                            model
                                        ]
                                    ),
                                    "reference_file": str(
                                        info[
                                            "reference_monan"
                                        ]
                                    ),
                                    "mask_file": str(
                                        TARGET_MASK_FILE
                                    ),
                                }
                            )

                print(
                    f"  "
                    f"{valid:%Y%m%d%H}: "
                    "processado, "
                    f"{npoints} pontos"
                )

            except Exception as exc:

                for model in MODELS:

                    for threshold in THRESHOLDS:

                        for window in WINDOW_SIZES:

                            accum[
                                model
                            ][
                                (
                                    lead,
                                    threshold,
                                    window,
                                )
                            ][
                                "n_processing_errors"
                            ] += 1

                print(
                    f"  ERRO "
                    f"{valid:%Y%m%d%H}, "
                    f"lead "
                    f"{lead:03d} h: "
                    f"{exc}"
                )

    monthly = {
        model: []
        for model in MODELS
    }

    for model in MODELS:

        for (
            lead,
            threshold,
            window,
        ), a in accum[
            model
        ].items():

            if (
                a[
                    "n_valid_days"
                ] > 0
                and a[
                    "worst_sum"
                ] > 0.0
            ):

                fss_month = (
                    1.0
                    - (
                        a[
                            "fbs_sum"
                        ]
                        / a[
                            "worst_sum"
                        ]
                    )
                )

            else:

                fss_month = (
                    np.nan
                )

            monthly[
                model
            ].append(
                {
                    "periodo": (
                        period
                    ),
                    "modelo": (
                        model
                    ),
                    "referencia": (
                        reference
                    ),
                    "dominio": (
                        DOMAIN
                    ),
                    "target_grid": (
                        TARGET_GRID
                    ),
                    "regrid_method_model": (
                        MODEL_REGRID_METHOD[
                            model
                        ]
                    ),
                    "reference_grid": (
                        "existing_MONAN_grid"
                    ),
                    "lead": (
                        lead
                    ),
                    "threshold_mm": (
                        threshold
                    ),
                    "window_points": (
                        window
                    ),
                    "window_lat_km": (
                        window
                        * resolution[
                            "grid_dy_km"
                        ]
                    ),
                    "window_lon_km": (
                        window
                        * resolution[
                            "grid_dx_km"
                        ]
                    ),
                    "grid_dlat_deg": (
                        resolution[
                            "grid_dlat_deg"
                        ]
                    ),
                    "grid_dlon_deg": (
                        resolution[
                            "grid_dlon_deg"
                        ]
                    ),
                    "grid_dy_km": (
                        resolution[
                            "grid_dy_km"
                        ]
                    ),
                    "grid_dx_km": (
                        resolution[
                            "grid_dx_km"
                        ]
                    ),
                    "representative_lat": (
                        resolution[
                            "representative_lat"
                        ]
                    ),
                    "fss": (
                        fss_month
                    ),
                    "fbs_sum": (
                        a[
                            "fbs_sum"
                        ]
                    ),
                    "fbs_worst_sum": (
                        a[
                            "worst_sum"
                        ]
                    ),
                    "n_valid_days": (
                        a[
                            "n_valid_days"
                        ]
                    ),
                    "n_no_event_days": (
                        a[
                            "n_no_event_days"
                        ]
                    ),
                    "n_processing_errors": (
                        a[
                            "n_processing_errors"
                        ]
                    ),
                    "n_common_sample_days": (
                        common_days[
                            lead
                        ]
                    ),
                    "n_expected_days": (
                        len(dates)
                    ),
                    "common_lat_min": (
                        target_bounds[
                            "lat"
                        ][0]
                    ),
                    "common_lat_max": (
                        target_bounds[
                            "lat"
                        ][1]
                    ),
                    "common_lon_min": (
                        target_bounds[
                            "lon"
                        ][0]
                    ),
                    "common_lon_max": (
                        target_bounds[
                            "lon"
                        ][1]
                    ),
                    "mask_file": str(
                        TARGET_MASK_FILE
                    ),
                }
            )

    return (
        daily,
        monthly,
    )


# =============================================================================
# SAÍDAS E MAIN
# =============================================================================

def save_results(
    period,
    reference,
    daily,
    monthly,
):

    for model in MODELS:

        outdir = (
            OUTDIR_FSS
            / period
            / model
            / reference
        )

        daily_path = (
            outdir
            / (
                f"FSS_daily_"
                f"{model}_vs_"
                f"{reference}_"
                f"{period}_"
                f"{DOMAIN}_"
                f"{TARGET_GRID}.csv"
            )
        )

        monthly_path = (
            outdir
            / (
                f"FSS_monthly_"
                f"{model}_vs_"
                f"{reference}_"
                f"{period}_"
                f"{DOMAIN}_"
                f"{TARGET_GRID}.csv"
            )
        )

        save_csv(
            daily[model],
            daily_path,
        )

        save_csv(
            monthly[model],
            monthly_path,
        )

        print(
            f"CSV diário: "
            f"{daily_path}"
        )

        print(
            f"CSV mensal: "
            f"{monthly_path}"
        )


def main():

    args = parse_args()

    period = args.period

    parse_period(
        period
    )

    references = (
        select_references(
            args.references
        )
    )

    leads = (
        validate_leads(
            args.leads
        )
    )

    target_mask, target_bounds = (
        build_target_mask(
            period,
            leads,
        )
    )

    save_target_mask(
        target_mask
    )

    resolution = (
        grid_resolution(
            target_mask
        )
    )

    print(
        "\n"
        + "=" * 88
    )

    print(
        "CONFIGURAÇÃO DO FSS, "
        "MONAN REGIONAL x WRF x MONAN GLOBAL"
    )

    print(
        "=" * 88
    )

    print(
        f"Domínio:             "
        f"{DOMAIN}"
    )

    print(
        f"Grade alvo:          "
        f"{TARGET_GRID}"
    )

    print(
        f"Máscara alvo:        "
        f"{TARGET_MASK_FILE}"
    )

    print(
        "Tratamento das grades: "
        "MONAN Regional=remapcon; "
        "WRF=remapcon; "
        "MONAN Global=native_target_grid"
    )

    print(
        "Referências:          "
        "arquivos "
        "*_MONAN_grid.nc "
        "existentes"
    )

    print(
        "Limites:              "
        f"lat "
        f"{target_bounds['lat'][0]:.4f} "
        "a "
        f"{target_bounds['lat'][1]:.4f}; "
        f"lon "
        f"{target_bounds['lon'][0]:.4f} "
        "a "
        f"{target_bounds['lon'][1]:.4f}"
    )

    print(
        "Resolução detectada:  "
        f"dlat="
        f"{resolution['grid_dlat_deg']:.6f}°, "
        f"dlon="
        f"{resolution['grid_dlon_deg']:.6f}°"
    )

    print(
        f"Prazos:              "
        f"{leads}"
    )

    print(
        f"Limiares:            "
        f"{list(THRESHOLDS)} "
        "mm/24h"
    )

    print(
        f"Janelas:             "
        f"{list(WINDOW_SIZES)} "
        "pontos"
    )

    for reference in references:

        sample, audit = (
            build_common_sample(
                period,
                reference,
                leads,
            )
        )

        audit_path = (
            OUTDIR_FSS
            / "_metadata"
            / "common_samples"
            / period
            / (
                f"FSS_common_sample_"
                f"{reference}_"
                f"{period}.csv"
            )
        )

        save_csv(
            audit,
            audit_path,
        )

        print(
            "Amostra temporal "
            f"comum {reference}: "
            f"{audit_path}"
        )

        daily, monthly = (
            process_reference(
                period=period,
                reference=reference,
                leads=leads,
                target_mask=(
                    target_mask
                ),
                target_bounds=(
                    target_bounds
                ),
                common_sample=(
                    sample
                ),
                overwrite_remap=(
                    args.overwrite_remap
                ),
            )
        )

        save_results(
            period,
            reference,
            daily,
            monthly,
        )


if __name__ == "__main__":
    main()
