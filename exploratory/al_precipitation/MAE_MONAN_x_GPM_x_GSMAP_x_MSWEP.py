#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Script para gerar MAE (Mean absolute Error) do MONAN em relação a GPM, GSMAP e MSWEP
# Tambem escreve um netcdf com o erro absoluto e o quadrado da diferença para futuro calculo do RMSE
# Autor: Andre Lyra
#
# Uso: (Necessario ambiente python e cdo)
# /lustre/projetos/monan_gam/andre.lyra/Scripts/Scripts_MONAN/python_env/bin/python \
# MAE_MONAN_x_GPM_x_GSMAP_x_MSWEP.py 2025 12 01 00 120
#

import argparse
import datetime
import subprocess
import os
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
from matplotlib.colors import BoundaryNorm
from pathlib import Path

os.environ["CARTOPY_DATA_DIR"] = "/lustre/projetos/monan_gam/andre.lyra/cartopy"

# Argumentos
parser = argparse.ArgumentParser(
    description="Gera RMSE do MONAN para cada ciclo de previsao.",
    formatter_class=argparse.RawTextHelpFormatter
)

parser.add_argument("ANO", type=str)
parser.add_argument("MES", type=str)
parser.add_argument("DIA", type=str)
parser.add_argument("HORA", type=str)
parser.add_argument("PRAZO_H", type=int)

args = parser.parse_args()

data_ini = datetime.datetime(
    int(args.ANO),
    int(args.MES),
    int(args.DIA),
    int(args.HORA)
)

prazo_total = args.PRAZO_H
lead_times = range(24, prazo_total + 1, 24)

# Funcoes 
def remap_cdo(obs_nc, out_nc, ref_nc):
    if not os.path.exists(out_nc):
        subprocess.run(
            ["cdo", "-f", "nc", f"-remapcon,{ref_nc}", obs_nc, out_nc],
            check=True
        )

def rmse_medio(diff):
    return np.sqrt(np.nanmean(diff**2))

def correlacao_espacial(a, b):
    a_flat = a.values.flatten()
    b_flat = b.values.flatten()
    mask = np.isfinite(a_flat) & np.isfinite(b_flat)
    return np.corrcoef(a_flat[mask], b_flat[mask])[0, 1]

# Escala de RMSE
levels = [0, 2, 4, 6, 8, 10, 15, 20, 30, 40, 50]
cmap = plt.cm.YlOrRd
norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

# Funcoes de plot
def plot_rmse(data, titulo, nome_fig, extent=None):
    fig = plt.figure(figsize=(10, 5))
    ax = plt.axes(projection=ccrs.PlateCarree())

    im = data.plot(
        ax=ax,
        transform=ccrs.PlateCarree(),
        cmap=cmap,
        norm=norm,
        add_colorbar=False
    )

    ax.coastlines()
    ax.set_title(titulo)
    
    if extent is None:
        ax.set_xticks(np.arange(-180, 181, 60), crs=ccrs.PlateCarree())
        ax.set_yticks(np.arange(-60, 61, 30), crs=ccrs.PlateCarree())

    else: 
        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.set_xticks(np.arange(-180, 181, 10), crs=ccrs.PlateCarree())
        ax.set_yticks(np.arange(-60, 61, 10), crs=ccrs.PlateCarree())
    
    ax.xaxis.set_major_formatter(LongitudeFormatter())
    ax.yaxis.set_major_formatter(LatitudeFormatter())
    ax.set_xlabel("")
    ax.set_ylabel("")
   
    if extent is not None:
        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4)
        ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="none", edgecolor="black", linewidth=0.2)
        estados = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lines',
        scale='50m',
        facecolor='none'
        )
        ax.add_feature(estados, edgecolor='black', linewidth=0.4)
    
    cbar = plt.colorbar(
        im,
        orientation="vertical",
        pad=0.1,
        aspect=50,
        boundaries=levels,
        extend="max"
    )
    cbar.set_label("(mm)")

    plt.savefig(nome_fig, dpi=300, bbox_inches="tight")
    plt.close()

# Loop de previsao
for lead in lead_times:

    data_fim = data_ini + datetime.timedelta(hours=lead)

    ciclo_str = data_ini.strftime("%Y%m%d%H")
    data_ini_str = data_ini.strftime("%Y%m%d%H")
    data_fim_str = data_fim.strftime("%Y%m%d%H")

# Caminhos dos arquivos
    monan_nc = (
        f"/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/"
        f"MONAN/{ciclo_str}/"
        f"MONAN_Precipitation_24h_acum_{data_ini_str}_{data_fim_str}_{lead:03d}h.nc"
    )

    gpm_nc = (
        f"/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/"
        f"GPM_IMERG/{data_fim_str}00/"
        f"GPM_IMERG_Precipitation_24h_accum_{data_fim_str}00.nc"
    )

    gsmap_nc = (
        f"/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/"
        f"GSMAP/{data_fim_str}00/"
        f"GSMAP_Precipitation_24h_accum_{data_fim_str}00.nc"
    )

    mswep_nc = (
        f"/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/"
        f"MSWEP/{data_fim_str}00/"
        f"MSWEP_Precipitation_24h_accum_{data_fim_str}00.nc"
    )

# Regrid
    gpm_remap = gpm_nc.replace(".nc", "_MONAN_grid.nc")
    gsmap_remap = gsmap_nc.replace(".nc", "_MONAN_grid.nc")
    mswep_remap = mswep_nc.replace(".nc", "_MONAN_grid.nc")

    remap_cdo(gpm_nc, gpm_remap, monan_nc)
    remap_cdo(gsmap_nc, gsmap_remap, monan_nc)
    remap_cdo(mswep_nc, mswep_remap, monan_nc)

# Leitura dos NetCDF
    ds_monan = xr.open_dataset(monan_nc)
    ds_gpm = xr.open_dataset(gpm_remap)
    ds_gsmap = xr.open_dataset(gsmap_remap)
    ds_mswep = xr.open_dataset(mswep_remap)

    monan = ds_monan["prec"]
    gpm = ds_gpm["prec"]
    gsmap = ds_gsmap["prec"]
    mswep = ds_mswep["prec"]

    lat = ds_monan["lat"]
    lon = ds_monan["lon"]

    diff_gpm = monan - gpm
    diff_gsmap = monan - gsmap
    diff_mswep = monan - mswep

    sqerr_gpm = diff_gpm**2
    sqerr_gsmap = diff_gsmap**2
    sqerr_mswep = diff_mswep**2
    
    abs_err_gpm = np.abs(diff_gpm)
    abs_err_gsmap = np.abs(diff_gsmap)
    abs_err_mswep = np.abs(diff_mswep)

# Diretorio de saida das figuras
    fig_dir = f"/pesq/share/monan/monan_gam/precip_24h/MAE/{args.ANO}{args.MES}/{ciclo_str}/"
    os.makedirs(fig_dir, exist_ok=True)

# ===============================
# Funcao de plot Global
# ===============================
    corr_gpm = correlacao_espacial(monan, gpm)
    corr_gsmap = correlacao_espacial(monan, gsmap)
    corr_mswep = correlacao_espacial(monan, mswep)

    rmse_med_gpm = rmse_medio(diff_gpm)
    rmse_med_gsmap = rmse_medio(diff_gsmap)
    rmse_med_mswep = rmse_medio(diff_mswep)

    plot_rmse(
        abs_err_gpm,
        f"MAE {lead:03d}h MONAN vs GPM IMERG\nGlobal - Corr={corr_gpm:.2f} RMSE={rmse_med_gpm:.2f} mm",
        os.path.join(fig_dir, f"MAE_MONAN_GPM_GLB_{lead:03d}h.png")
    )

    plot_rmse(
        abs_err_gsmap,
        f"MAE {lead:03d}h MONAN vs GSMAP\nGlobal - Corr={corr_gsmap:.2f} RMSE={rmse_med_gsmap:.2f} mm",
        os.path.join(fig_dir, f"MAE_MONAN_GSMAP_GLB_{lead:03d}h.png")
    )

    plot_rmse(
        abs_err_mswep,
        f"MAE {lead:03d}h MONAN vs MSWEP\nGlobal - Corr={corr_mswep:.2f} RMSE={rmse_med_mswep:.2f} mm",
        os.path.join(fig_dir, f"MAE_MONAN_MSWEP_GLB_{lead:03d}h.png")
    )

# ===============================
# Funcao de plot AMS
# ==============================
    sl_AMS = dict(lat=slice(-55, 20), lon=slice(275, 340))

    plot_rmse(
        abs_err_gpm.sel(**sl_AMS),
        f"MAE {lead:03d}h MONAN vs GPM IMERG\nAMS - Corr={correlacao_espacial(monan.sel(**sl_AMS), gpm.sel(**sl_AMS)):.2f} "
        f"RMSE={rmse_medio(diff_gpm.sel(**sl_AMS)):.2f} mm",
        os.path.join(fig_dir, f"MAE_MONAN_GPM_AMS_{lead:03d}h.png"),
        extent=[-85, -20, -55, 20]
    )

    plot_rmse(
        abs_err_gsmap.sel(**sl_AMS),
        f"MAE {lead:03d}h MONAN vs GSMAP\nAMS = Corr={correlacao_espacial(monan.sel(**sl_AMS), gsmap.sel(**sl_AMS)):.2f} "
        f"RMSE={rmse_medio(diff_gsmap.sel(**sl_AMS)):.2f} mm",
        os.path.join(fig_dir, f"MAE_MONAN_GSMAP_AMS_{lead:03d}h.png"),
        extent=[-85, -20, -55, 20]
    )

    plot_rmse(
        abs_err_mswep.sel(**sl_AMS),
        f"MAE {lead:03d}h MONAN vs MSWEP\nAMS - Corr={correlacao_espacial(monan.sel(**sl_AMS), mswep.sel(**sl_AMS)):.2f} "
        f"RMSE={rmse_medio(diff_mswep.sel(**sl_AMS)):.2f} mm",
        os.path.join(fig_dir, f"MAE_MONAN_MSWEP_AMS_{lead:03d}h.png"),
        extent=[-85, -20, -55, 20]
    )

# ===============================
# Funcao de plot ACC
# ==============================
    sl_ACC = dict(lat=slice(-10, 35), lon=slice(242, 335))

    plot_rmse(
        abs_err_gpm.sel(**sl_ACC),
        f"MAE {lead:03d}h MONAN vs GPM IMERG\nACC - Corr={correlacao_espacial(monan.sel(**sl_ACC), gpm.sel(**sl_ACC)):.2f} "
        f"RMSE={rmse_medio(diff_gpm.sel(**sl_ACC)):.2f} mm",
        os.path.join(fig_dir, f"MAE_MONAN_GPM_ACC_{lead:03d}h.png"),
        extent=[-118, -35, -10, 35]
    )

    plot_rmse(
        abs_err_gsmap.sel(**sl_ACC),
        f"MAE {lead:03d}h MONAN vs GSMAP\nACC - Corr={correlacao_espacial(monan.sel(**sl_ACC), gsmap.sel(**sl_ACC)):.2f} "
        f"RMSE={rmse_medio(diff_gsmap.sel(**sl_ACC)):.2f} mm",
        os.path.join(fig_dir, f"MAE_MONAN_GSMAP_ACC_{lead:03d}h.png"),
        extent=[-118, -35, -10, 35]
    )

    plot_rmse(
        abs_err_mswep.sel(**sl_ACC),
        f"MAE {lead:03d}h MONAN vs MSWEP\nACC - Corr={correlacao_espacial(monan.sel(**sl_ACC), mswep.sel(**sl_ACC)):.2f} "
        f"RMSE={rmse_medio(diff_mswep.sel(**sl_ACC)):.2f} mm",
        os.path.join(fig_dir, f"MAE_MONAN_MSWEP_ACC_{lead:03d}h.png"),
        extent=[-118, -35, -10, 35]
    )


# Salvando o arquivo NetCDF
    ds_out = xr.Dataset(
        {
            "abs_err_monangpm":   (("lat", "lon"), abs_err_gpm.data),
            "sqerr_monangpm":     (("lat", "lon"), sqerr_gpm.data),

            "abs_err_monangsmap": (("lat", "lon"), abs_err_gsmap.data),
            "sqerr_monangsmap":   (("lat", "lon"), sqerr_gsmap.data),

            "abs_err_monanmswep": (("lat", "lon"), abs_err_mswep.data),
            "sqerr_monanmswep":   (("lat", "lon"), sqerr_mswep.data),
        },
        coords={
            "lat": monan.lat.data,
            "lon": monan.lon.data,
        },
    )

    out_dir = Path(
        f"/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/RMSE/{data_ini_str}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    ds_out.to_netcdf(
        out_dir / f"RMSE_MONAN_Prec_{data_ini_str}_{lead:03d}h.nc",
        format="NETCDF4"
    )


# Roda o script para recortar e juntar as figuras
subprocess.run(
    ["bash", "Gera_MAE_montage.sh", f"{data_ini_str}", f"{prazo_total}"],
    check=True
)
