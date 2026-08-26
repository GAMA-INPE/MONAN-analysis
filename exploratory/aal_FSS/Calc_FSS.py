#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: André Lyra <andre.lyra@inpe.br>

"""
This script calculates the Fractions Skill Score (FSS) for 24-hour accumulated precipitation.

The calculation is performed for combinations of:
Models: MONAN, BAM, and GFS
References: GPM_IMERG, MSWEP, and GSMAP

Uses FSS_config.py for configuration, including paths, thresholds, window sizes, and domains.

Examples:
    python Calc_FSS.py --period 202601
    python Calc_FSS.py --period 202601 --models MONAN
    python Calc_FSS.py --period 202601 --models BAM GFS --references MSWEP GSMAP
    python Calc_FSS.py --period 202601 --domains AMS ACC
"""

import argparse
import csv
import calendar
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import xarray as xr
from scipy.ndimage import uniform_filter

from FSS_config import (
    BASE_PRECIP,
    OUTDIR_FSS,
    MODELOS,
    REFERENCIAS,
    THRESHOLDS,
    WINDOW_SIZES,
    PRAZOS,
    VAR_PREC,
    DOMINIOS,
    TARGET_GRID,
    REGRID_METHOD,
    USE_PRECOMPUTED_REMAPCON,
    PRECOMPUTED_REMAPCON_DIR,
)


EARTH_KM_PER_DEGREE = 111.32


def valida_configuracao_grade():
    if TARGET_GRID is not None and TARGET_GRID not in MODELOS:
        raise ValueError(
            "TARGET_GRID deve ser None ou um modelo presente em MODELOS. "
            f"Valor recebido: {TARGET_GRID!r}."
        )

    if REGRID_METHOD not in {"linear", "nearest"}:
        raise ValueError(
            "REGRID_METHOD deve ser 'linear' ou 'nearest'. "
            f"Valor recebido: {REGRID_METHOD!r}."
        )


def modo_grade():
    if TARGET_GRID is None:
        return "independent_grids"

    if USE_PRECOMPUTED_REMAPCON:
        return f"{TARGET_GRID}_grid_remapcon"

    return f"{TARGET_GRID}_grid"

def metodo_remapeamento():
    if TARGET_GRID is None:
        return "none"

    if USE_PRECOMPUTED_REMAPCON:
        return "remapcon"

    return REGRID_METHOD

def descricao_grade(modelo):
    if TARGET_GRID is None:
        return f"grade nativa do {modelo}"

    return f"grade comum do {TARGET_GRID}"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Calcula o FSS mensal para modelos e referências "
            "selecionados, usando grades independentes ou uma grade alvo."
        )
    )

    parser.add_argument(
        "--period",
        required=True,
        help="Período no formato YYYYMM, por exemplo 202601.",
    )

    parser.add_argument(
        "--models",
        nargs="+",
        default=["all"],
        help=(
            "Modelos a processar. Use MONAN BAM GFS ou all. "
            "Padrão: all."
        ),
    )

    parser.add_argument(
        "--references",
        nargs="+",
        default=["all"],
        help=(
            "Referências a processar. Use GPM_IMERG MSWEP GSMAP "
            "ou all. Padrão: all."
        ),
    )

    parser.add_argument(
        "--domains",
        nargs="+",
        default=["all"],
        help="Domínios a processar. Use GLB AMS ACC ou all. Padrão: all.",
    )

    return parser.parse_args()


def seleciona_opcoes(escolhas, disponiveis, nome):
    escolhas_upper = [item.upper() for item in escolhas]

    if "ALL" in escolhas_upper:
        return list(disponiveis)

    invalidas = [item for item in escolhas_upper if item not in disponiveis]

    if invalidas:
        raise ValueError(
            f"{nome} inválido(s): {invalidas}. "
            f"Opções disponíveis: {list(disponiveis)}"
        )

    return escolhas_upper


def interpreta_periodo(periodo):
    if len(periodo) != 6 or not periodo.isdigit():
        raise ValueError(
            f"Período inválido: {periodo}. Use o formato YYYYMM."
        )

    ano = int(periodo[:4])
    mes = int(periodo[4:])

    if mes < 1 or mes > 12:
        raise ValueError(f"Mês inválido no período {periodo}.")

    return ano, mes


def datas_validas_do_mes(ano, mes):
    ultimo_dia = calendar.monthrange(ano, mes)[1]

    return [
        datetime(ano, mes, dia, 0)
        for dia in range(1, ultimo_dia + 1)
    ]


# Locates the forecast file for a given model, valid date, and lead time.
# MONAN and BAM can be read from precomputed files remapped conservatively to the GFS grid or 
# from their native grids or interpolated in memory to the GFS grid. 
# GFS is always read from its native grid.
def caminho_previsao(modelo, data_valida, lead):

    data_inicial = data_valida - timedelta(hours=lead)

    init_str = data_inicial.strftime("%Y%m%d%H")
    valid_str = data_valida.strftime("%Y%m%d%H")
    lead_str = f"{lead:03d}h"

    nome_base = (
        f"{modelo}_Precipitation_24h_acum_"
        f"{init_str}_{valid_str}_{lead_str}"
    )

    if USE_PRECOMPUTED_REMAPCON and modelo in {"MONAN", "BAM"}:
        periodo_inicial = data_inicial.strftime("%Y%m")

        return (
            PRECOMPUTED_REMAPCON_DIR
            / periodo_inicial
            / modelo
            / init_str
            / f"{nome_base}_GFS_grid_remapcon.nc"
        )

    return (
        BASE_PRECIP
        / modelo
        / init_str
        / f"{nome_base}.nc"
    )


# Locates the reference file already remapped to the model's grid.
def caminho_referencia(referencia, modelo, data_valida):

    valid_str = data_valida.strftime("%Y%m%d%H%M")
    modelo_grade = TARGET_GRID if TARGET_GRID is not None else modelo

    return (
        BASE_PRECIP
        / referencia
        / valid_str
        / (
            f"{referencia}_Precipitation_24h_accum_"
            f"{valid_str}_{modelo_grade}_grid.nc"
        )
    )


# Normalizes coordinate names to 'lat' and 'lon'
def normaliza_nomes_coordenadas(da):
    renomear = {}

    if "latitude" in da.dims or "latitude" in da.coords:
        renomear["latitude"] = "lat"

    if "longitude" in da.dims or "longitude" in da.coords:
        renomear["longitude"] = "lon"

    if renomear:
        da = da.rename(renomear)

    if "lat" not in da.coords or "lon" not in da.coords:
        raise ValueError(
            "O campo não possui coordenadas lat/lon ou latitude/longitude."
        )

    if da["lat"].ndim != 1 or da["lon"].ndim != 1:
        raise ValueError(
            "Este script requer coordenadas unidimensionais de latitude "
            "e longitude."
        )

    return da


# Adjusts longitude to [0, 360), sorts coordinates, and removes duplicates, including 0/360.
def ajusta_longitude(da):

    lon_values = np.asarray(
        da["lon"].values,
        dtype="float64",
    )

    lon_values = np.mod(lon_values, 360.0)

    lon_values[np.isclose(
        lon_values,
        360.0,
        rtol=0.0,
        atol=1.0e-8,
    )] = 0.0

    da = da.assign_coords(lon=lon_values)
    da = da.sortby("lon")

    lon_values = np.asarray(
        da["lon"].values,
        dtype="float64",
    )
    lon_rounded = np.round(lon_values, decimals=8)

    _, unique_indices = np.unique(
        lon_rounded,
        return_index=True,
    )
    unique_indices = np.sort(unique_indices)

    if len(unique_indices) != len(lon_values):
        da = da.isel(lon=unique_indices)

    if not da.get_index("lon").is_unique:
        raise ValueError(
            "Longitude remains duplicated after normalization."
        )

    return da


# Prepares the precipitation field by opening the NetCDF
def prepara_precipitacao(path):

    with xr.open_dataset(path) as ds:
        if VAR_PREC not in ds:
            raise KeyError(
                f"Variável '{VAR_PREC}' não encontrada em {path}. "
                f"Variáveis disponíveis: {list(ds.data_vars)}"
            )

        da = ds[VAR_PREC].squeeze(drop=True).load()

    da = normaliza_nomes_coordenadas(da)

    if "_FillValue" in da.attrs:
        fill_value = da.attrs["_FillValue"]
        da = da.where(da != fill_value)

    if "missing_value" in da.attrs:
        missing_value = da.attrs["missing_value"]
        da = da.where(da != missing_value)

    da = da.where(np.isfinite(da))
    da = da.where(da >= 0.0)

    da = ajusta_longitude(da)
    da = da.sortby("lat")
    da = da.transpose("lat", "lon")

    return da


# Checks if two fields have the same grid.
def grades_iguais(campo_a, campo_b, atol=1.0e-6):
    mesma_forma = campo_a.shape == campo_b.shape

    mesmas_latitudes = (
        campo_a.sizes["lat"] == campo_b.sizes["lat"]
        and np.allclose(
            campo_a["lat"].values,
            campo_b["lat"].values,
            rtol=0.0,
            atol=atol,
            equal_nan=True,
        )
    )

    mesmas_longitudes = (
        campo_a.sizes["lon"] == campo_b.sizes["lon"]
        and np.allclose(
            campo_a["lon"].values,
            campo_b["lon"].values,
            rtol=0.0,
            atol=atol,
            equal_nan=True,
        )
    )

    return mesma_forma and mesmas_latitudes and mesmas_longitudes

# Interpolates the continuous field in memory before thresholding.
def interpola_para_grade_alvo(da, grade_alvo):
  
    if not da.get_index("lat").is_unique:
        raise ValueError(
            "Source latitude coordinates are not unique."
        )

    if not da.get_index("lon").is_unique:
        raise ValueError(
            "Source longitude coordinates are not unique."
        )

    if not grade_alvo.get_index("lat").is_unique:
        raise ValueError(
            "Target latitude coordinates are not unique."
        )

    if not grade_alvo.get_index("lon").is_unique:
        raise ValueError(
            "Target longitude coordinates are not unique."
        )

    if grades_iguais(da, grade_alvo):
        return da.assign_coords(
            lat=grade_alvo["lat"],
            lon=grade_alvo["lon"],
        )

    primeira_coluna = da.isel(lon=0).assign_coords(
        lon=float(da["lon"].isel(lon=0)) + 360.0
    )

    ultima_coluna = da.isel(lon=-1).assign_coords(
        lon=float(da["lon"].isel(lon=-1)) - 360.0
    )

    da_ciclico = xr.concat(
        [ultima_coluna, da, primeira_coluna],
        dim="lon",
    ).sortby("lon")

    if not da_ciclico.get_index("lon").is_unique:
        raise ValueError(
            "Cyclic longitude coordinates are not unique."
        )

    interpolado = da_ciclico.interp(
        lat=grade_alvo["lat"],
        lon=grade_alvo["lon"],
        method=REGRID_METHOD,
    )

    interpolado = interpolado.assign_coords(
        lat=grade_alvo["lat"],
        lon=grade_alvo["lon"],
    )

    return interpolado.transpose("lat", "lon")


# Confirms that the preparation left forecast and reference on the same grid.
def alinha_campos(fcst, obs):

    if not grades_iguais(fcst, obs):
        raise ValueError(
            "Previsão e referência não estão na mesma grade após a "
            f"preparação. Previsão={fcst.shape}; referência={obs.shape}."
        )

    obs = obs.assign_coords(
        lat=fcst["lat"],
        lon=fcst["lon"],
    )

    return fcst, obs


# Cuts the field to the specified domain.
def recorte_dominio(da, dominio):
    lat_min, lat_max = DOMINIOS[dominio]["lat"]
    lon_min, lon_max = DOMINIOS[dominio]["lon"]

    return da.sel(
        lat=slice(lat_min, lat_max),
        lon=slice(lon_min, lon_max),
    )


# Calculates the fraction of occurrence within the neighborhood.
# NaN values remain outside the denominator of the fraction.
def neighborhood_fraction(binary_da, window_size, periodic_lon=False):

    binary = binary_da.astype("float32")

    valid = xr.where(
        np.isfinite(binary),
        1.0,
        0.0,
    ).astype("float32")

    binary = binary.fillna(0.0).astype("float32")

    arr = binary.values
    mask = valid.values

    if periodic_lon:
        mode = ("nearest", "wrap")
    else:
        mode = ("constant", "constant")

    num = uniform_filter(
        arr,
        size=window_size,
        mode=mode,
        cval=0.0,
    )

    den = uniform_filter(
        mask,
        size=window_size,
        mode=mode,
        cval=0.0,
    )

    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(
            den > 0.0,
            num / den,
            np.nan,
        ).astype("float32")

    return xr.DataArray(
        frac,
        coords=binary_da.coords,
        dims=binary_da.dims,
    )


# Calculates latitude weights for area-weighted averaging.
def pesos_latitude(da):
    weights = np.cos(np.deg2rad(da["lat"]))

    return xr.DataArray(
        weights,
        coords={"lat": da["lat"]},
        dims=["lat"],
    )


# Computes the spatially weighted mean of a DataArray using latitude weights.
def media_ponderada_espacial(da, weights):
    return da.weighted(weights).mean(
        dim=("lat", "lon"),
        skipna=True,
    )


# Compute FSS for a single forecast and observation field at a given valid date
def calcula_fss_campo(
    fcst,
    obs,
    threshold,
    window_size,
    dominio,
):

    valid_mask = np.isfinite(fcst) & np.isfinite(obs)

    fcst_event = xr.where(
        valid_mask,
        fcst >= threshold,
        np.nan,
    )

    obs_event = xr.where(
        valid_mask,
        obs >= threshold,
        np.nan,
    )

    periodic_lon = dominio == "GLB"

    fcst_frac = neighborhood_fraction(
        fcst_event,
        window_size=window_size,
        periodic_lon=periodic_lon,
    )

    obs_frac = neighborhood_fraction(
        obs_event,
        window_size=window_size,
        periodic_lon=periodic_lon,
    )

    fbs = (fcst_frac - obs_frac) ** 2
    fbs_worst = fcst_frac ** 2 + obs_frac ** 2

    weights = pesos_latitude(fcst)

    fbs_mean = media_ponderada_espacial(fbs, weights)
    fbs_worst_mean = media_ponderada_espacial(
        fbs_worst,
        weights,
    )

    fbs_mean = float(fbs_mean.values)
    fbs_worst_mean = float(fbs_worst_mean.values)

    if (
        not np.isfinite(fbs_mean)
        or not np.isfinite(fbs_worst_mean)
        or fbs_worst_mean == 0.0
    ):
        return np.nan, np.nan, np.nan

    fss = 1.0 - (fbs_mean / fbs_worst_mean)

    return fss, fbs_mean, fbs_worst_mean


# Estimates the grid resolution and corresponding distance.
def estima_resolucao_grade(da):
    """
    A distância zonal é calculada na latitude mediana do domínio.
    A distância meridional é mais apropriada para comparar a escala
    aproximada das janelas entre as grades.
    """

    lat_values = np.asarray(da["lat"].values, dtype="float64")
    lon_values = np.asarray(da["lon"].values, dtype="float64")

    if lat_values.size < 2 or lon_values.size < 2:
        return {
            "grid_dlat_deg": np.nan,
            "grid_dlon_deg": np.nan,
            "grid_dy_km": np.nan,
            "grid_dx_km": np.nan,
            "representative_lat": np.nan,
        }

    dlat = float(np.nanmedian(np.abs(np.diff(lat_values))))
    dlon = float(np.nanmedian(np.abs(np.diff(lon_values))))
    representative_lat = float(np.nanmedian(lat_values))

    dy_km = EARTH_KM_PER_DEGREE * dlat
    dx_km = (
        EARTH_KM_PER_DEGREE
        * dlon
        * np.cos(np.deg2rad(representative_lat))
    )

    return {
        "grid_dlat_deg": dlat,
        "grid_dlon_deg": dlon,
        "grid_dy_km": dy_km,
        "grid_dx_km": dx_km,
        "representative_lat": representative_lat,
    }


# Creates accumulators for FSS and related statistics for all combinations of lead times, domains, thresholds, and window sizes.
def cria_acumuladores(dominios):
    acumuladores = {}

    for lead in PRAZOS:
        for dominio in dominios:
            for threshold in THRESHOLDS:
                for window_size in WINDOW_SIZES:
                    chave = (
                        int(lead),
                        dominio,
                        float(threshold),
                        int(window_size),
                    )

                    acumuladores[chave] = {
                        "fbs_sum": 0.0,
                        "fbs_worst_sum": 0.0,
                        "n_valid_days": 0,
                        "n_missing_pairs": 0,
                        "n_missing_forecast": 0,
                        "n_missing_reference": 0,
                        "n_processing_errors": 0,
                        "n_no_event_days": 0,
                        "grid_dlat_deg": np.nan,
                        "grid_dlon_deg": np.nan,
                        "grid_dy_km": np.nan,
                        "grid_dx_km": np.nan,
                        "representative_lat": np.nan,
                    }

    return acumuladores


# Updates the accumulators for missing forecast or reference files.
def atualiza_dias_ausentes(
    acumuladores,
    lead,
    dominios,
    forecast_missing,
    reference_missing,
):
    for dominio in dominios:
        for threshold in THRESHOLDS:
            for window_size in WINDOW_SIZES:
                chave = (
                    int(lead),
                    dominio,
                    float(threshold),
                    int(window_size),
                )

                acc = acumuladores[chave]
                acc["n_missing_pairs"] += 1

                if forecast_missing:
                    acc["n_missing_forecast"] += 1

                if reference_missing:
                    acc["n_missing_reference"] += 1


# Updates the accumulators for processing errors during FSS calculation.
def atualiza_erros_processamento(
    acumuladores,
    lead,
    dominios,
):
    for dominio in dominios:
        for threshold in THRESHOLDS:
            for window_size in WINDOW_SIZES:
                chave = (
                    int(lead),
                    dominio,
                    float(threshold),
                    int(window_size),
                )

                acumuladores[chave]["n_processing_errors"] += 1


# Calculates FSS for a combination of model, reference, and domain over a specified period.
def calcula_combinacao(
    periodo,
    modelo,
    referencia,
    dominios,
):
    ano, mes = interpreta_periodo(periodo)
    datas_validas = datas_validas_do_mes(ano, mes)

    linhas_diarias = []
    acumuladores = cria_acumuladores(dominios)

    print()
    print("=" * 80)
    print(
        f"Calculando FSS para {periodo}: "
        f"{modelo} vs {referencia}"
    )
    print(f"Modo de grade: {descricao_grade(modelo)}")
    if USE_PRECOMPUTED_REMAPCON:
        print("Remapeamento conservativo previamente realizado com CDO")
    elif TARGET_GRID is not None:
        print(f"Interpolação em memória: {REGRID_METHOD}")
    print("=" * 80)

    for lead in PRAZOS:
        print()
        print(f"Prazo {int(lead):03d} h")

        for data_valida in datas_validas:
            forecast_file = caminho_previsao(
                modelo=modelo,
                data_valida=data_valida,
                lead=int(lead),
            )

            reference_file = caminho_referencia(
                referencia=referencia,
                modelo=modelo,
                data_valida=data_valida,
            )

            forecast_missing = not forecast_file.exists()
            reference_missing = not reference_file.exists()

            if forecast_missing or reference_missing:
                atualiza_dias_ausentes(
                    acumuladores=acumuladores,
                    lead=int(lead),
                    dominios=dominios,
                    forecast_missing=forecast_missing,
                    reference_missing=reference_missing,
                )

                ausentes = []

                if forecast_missing:
                    ausentes.append("previsão")

                if reference_missing:
                    ausentes.append("referência")

                print(
                    f"  {data_valida:%Y%m%d%H}: "
                    f"arquivo ausente: {', '.join(ausentes)}"
                )
                continue

            try:
                fcst = prepara_precipitacao(forecast_file)
                obs = prepara_precipitacao(reference_file)

                if TARGET_GRID is not None and not USE_PRECOMPUTED_REMAPCON:
                    fcst = interpola_para_grade_alvo(
                        da=fcst,
                        grade_alvo=obs,
                    )

                fcst, obs = alinha_campos(fcst, obs)

                for dominio in dominios:
                    fcst_dom = recorte_dominio(fcst, dominio)
                    obs_dom = recorte_dominio(obs, dominio)

                    if fcst_dom.size == 0 or obs_dom.size == 0:
                        raise ValueError(
                            f"Campo vazio após recorte do domínio {dominio}."
                        )

                    resolucao = estima_resolucao_grade(fcst_dom)

                    for threshold in THRESHOLDS:
                        for window_size in WINDOW_SIZES:
                            fss, fbs, fbs_worst = calcula_fss_campo(
                                fcst=fcst_dom,
                                obs=obs_dom,
                                threshold=float(threshold),
                                window_size=int(window_size),
                                dominio=dominio,
                            )

                            chave = (
                                int(lead),
                                dominio,
                                float(threshold),
                                int(window_size),
                            )

                            acc = acumuladores[chave]

                            for campo, valor in resolucao.items():
                                acc[campo] = valor

                            window_lat_km = (
                                int(window_size)
                                * resolucao["grid_dy_km"]
                            )

                            window_lon_km = (
                                int(window_size)
                                * resolucao["grid_dx_km"]
                            )

                            status = "ok"

                            if np.isfinite(fss):
                                acc["fbs_sum"] += fbs
                                acc["fbs_worst_sum"] += fbs_worst
                                acc["n_valid_days"] += 1
                            else:
                                status = "no_event"
                                acc["n_no_event_days"] += 1

                            linhas_diarias.append({
                                "periodo": periodo,
                                "modelo": modelo,
                                "referencia": referencia,
                                "grid_mode": modo_grade(),
                                "target_grid": (
                                    TARGET_GRID
                                    if TARGET_GRID is not None
                                    else modelo
                                ),
                                "regrid_method": metodo_remapeamento(),
                                "dominio": dominio,
                                "valid_date": data_valida.strftime(
                                    "%Y%m%d%H"
                                ),
                                "lead": int(lead),
                                "threshold_mm": float(threshold),
                                "window_points": int(window_size),
                                "window_lat_km": window_lat_km,
                                "window_lon_km": window_lon_km,
                                "grid_dlat_deg": (
                                    resolucao["grid_dlat_deg"]
                                ),
                                "grid_dlon_deg": (
                                    resolucao["grid_dlon_deg"]
                                ),
                                "grid_dy_km": (
                                    resolucao["grid_dy_km"]
                                ),
                                "grid_dx_km": (
                                    resolucao["grid_dx_km"]
                                ),
                                "representative_lat": (
                                    resolucao["representative_lat"]
                                ),
                                "fss": fss,
                                "fbs": fbs,
                                "fbs_worst": fbs_worst,
                                "status": status,
                                "forecast_file": str(forecast_file),
                                "reference_file": str(reference_file),
                            })

                print(
                    f"  {data_valida:%Y%m%d%H}: processado"
                )

            except Exception as erro:
                atualiza_erros_processamento(
                    acumuladores=acumuladores,
                    lead=int(lead),
                    dominios=dominios,
                )

                print(
                    f"  Erro em {data_valida:%Y%m%d%H}, "
                    f"lead {int(lead):03d} h: {erro}"
                )

    linhas_mensais = []

    for chave, acc in acumuladores.items():
        lead, dominio, threshold, window_size = chave

        if (
            acc["n_valid_days"] > 0
            and acc["fbs_worst_sum"] > 0.0
        ):
            fss_mensal = 1.0 - (
                acc["fbs_sum"] / acc["fbs_worst_sum"]
            )
        else:
            fss_mensal = np.nan

        window_lat_km = (
            window_size * acc["grid_dy_km"]
            if np.isfinite(acc["grid_dy_km"])
            else np.nan
        )

        window_lon_km = (
            window_size * acc["grid_dx_km"]
            if np.isfinite(acc["grid_dx_km"])
            else np.nan
        )

        linhas_mensais.append({
            "periodo": periodo,
            "modelo": modelo,
            "referencia": referencia,
            "grid_mode": modo_grade(),
            "target_grid": (
                TARGET_GRID
                if TARGET_GRID is not None
                else modelo
            ),
            "regrid_method": metodo_remapeamento(),
            "dominio": dominio,
            "lead": lead,
            "threshold_mm": threshold,
            "window_points": window_size,
            "window_lat_km": window_lat_km,
            "window_lon_km": window_lon_km,
            "grid_dlat_deg": acc["grid_dlat_deg"],
            "grid_dlon_deg": acc["grid_dlon_deg"],
            "grid_dy_km": acc["grid_dy_km"],
            "grid_dx_km": acc["grid_dx_km"],
            "representative_lat": acc["representative_lat"],
            "fss": fss_mensal,
            "fbs_sum": acc["fbs_sum"],
            "fbs_worst_sum": acc["fbs_worst_sum"],
            "n_valid_days": acc["n_valid_days"],
            "n_missing_pairs": acc["n_missing_pairs"],
            "n_missing_forecast": acc["n_missing_forecast"],
            "n_missing_reference": acc["n_missing_reference"],
            "n_processing_errors": acc["n_processing_errors"],
            "n_no_event_days": acc["n_no_event_days"],
            "n_expected_days": len(datas_validas),
        })

        fss_texto = (
            f"{fss_mensal:.3f}"
            if np.isfinite(fss_mensal)
            else "nan"
        )

        print(
            f"{periodo} {modelo} vs {referencia} "
            f"{dominio} lead={lead:03d}h "
            f"thr={threshold:g}mm "
            f"window={window_size} "
            f"FSS={fss_texto} "
            f"n={acc['n_valid_days']}"
        )

    return linhas_diarias, linhas_mensais


# Saves the list of dictionaries to a CSV file.
def salva_csv(linhas, path):
    if not linhas:
        print(f"Nenhuma linha para salvar em {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    campos = list(linhas[0].keys())

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8",
    ) as arquivo:
        writer = csv.DictWriter(
            arquivo,
            fieldnames=campos,
        )
        writer.writeheader()
        writer.writerows(linhas)


# Main function to parse arguments and calculate FSS for selected combinations.
def main():
    args = parse_args()

    periodo = args.period
    interpreta_periodo(periodo)
    valida_configuracao_grade()

    modelos = seleciona_opcoes(
        args.models,
        MODELOS,
        "Modelo",
    )

    referencias = seleciona_opcoes(
        args.references,
        REFERENCIAS,
        "Referência",
    )

    dominios = seleciona_opcoes(
        args.domains,
        DOMINIOS.keys(),
        "Domínio",
    )

    for modelo in modelos:
        for referencia in referencias:
            linhas_diarias, linhas_mensais = calcula_combinacao(
                periodo=periodo,
                modelo=modelo,
                referencia=referencia,
                dominios=dominios,
            )

            if TARGET_GRID is None:
                outdir_combinacao = (
                    OUTDIR_FSS
                    / periodo
                    / modelo
                    / referencia
                )
            else:
                outdir_combinacao = (
                    OUTDIR_FSS
                    / modo_grade()
                    / periodo
                    / modelo
                    / referencia
                )

            csv_diario = (
                outdir_combinacao
                / (
                    f"FSS_daily_{modelo}_vs_"
                    f"{referencia}_{periodo}.csv"
                )
            )

            csv_mensal = (
                outdir_combinacao
                / (
                    f"FSS_monthly_{modelo}_vs_"
                    f"{referencia}_{periodo}.csv"
                )
            )

            salva_csv(
                linhas=linhas_diarias,
                path=csv_diario,
            )

            salva_csv(
                linhas=linhas_mensais,
                path=csv_mensal,
            )

            print()
            print(f"CSV diário salvo em: {csv_diario}")
            print(f"CSV mensal salvo em: {csv_mensal}")


if __name__ == "__main__":
    main()