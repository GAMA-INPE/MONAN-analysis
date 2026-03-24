#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Script para fazer as figuras de Bias medios para um mes específico 
# Autor: Andre Lyra
# Uso: (Necessario ambiente python com bibliotecas carregadas)
# /lustre/projetos/monan_gam/andre.lyra/Scripts/Scripts_MONAN/python_env/bin/python Mean_Bias_MONAN_BAM_GFS.py

# Medias geradas com CDO no diretorio /lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/Bias/
# a partir do script Gera_monthly_mean_Bias.sh

import os
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

# ==========================================================
# PARAMETROS
# ==========================================================

ANO  = 2026
MES  = 1

PRAZO_INICIAL = 24
PRAZO_FINAL   = 120
PASSO_PRAZO   = 24

DOMINIO_ATIVO = "GLB"    # GLB, AMS ou ACC

VMIN = -10
VMAX =  10
CMAP = "RdBu"

DOMINIOS = {
    "GLB": {
        "lat": (-90, 90),
        "lon": (0, 360)
    },
    "AMS": {
        "lat": (-55, 20),
        "lon": (275, 340)
    },
    "ACC": {
        "lat": (-10, 35),
        "lon": (242, 335)
    }
}

FIG_PARAMS = {
    "GLB": {
        "figsize": (16, 9),
        "hspace": 0.18,
        "wspace": 0.15
    },
    "AMS": {
        "figsize": (14, 10),
        "hspace": 0.22,
        "wspace": 0.15
    },
    "ACC": {
        "figsize": (15, 9),
        "hspace": 0.20,
        "wspace": 0.15
    }
}
DIR_NETCDF = (
    "/lustre/projetos/monan_gam/andre.lyra/"
    "NetCDFs/precip_24h/Bias"
)

DIR_SAIDA = (
    "/pesq/share/monan/monan_gam/"
    "precip_24h/Bias"
)

# ==========================================================
# FUNCOES
# ==========================================================
def calcula_bias_medio(da, dominio):
    da_sub = da.sel(
        lat=DOMINIOS[dominio]["lat"],
        lon=DOMINIOS[dominio]["lon"]
    )
    return float(da_sub.mean(skipna=True))
    
def plot_bias_mensal(ano, mes, lead):

    ds_gfs = xr.open_dataset(
        f"{DIR_NETCDF}/Bias_GFS_Prec_{ano}{mes:02d}_mean_{lead:03d}h.nc"
    )

    ds_bam = xr.open_dataset(
        f"{DIR_NETCDF}/Bias_BAM_Prec_{ano}{mes:02d}_mean_{lead:03d}h.nc"
    )

    ds_monan = xr.open_dataset(
        f"{DIR_NETCDF}/Bias_MONAN_Prec_{ano}{mes:02d}_mean_{lead:03d}h.nc"
    )

    models = [
        ("MONAN", ds_monan, ["bias_monangpm", "bias_monangsmap", "bias_monanmswep"]),
        ("BAM",   ds_bam,   ["bias_bamgpm",   "bias_bamgsmap",   "bias_bammswep"]),
        ("GFS",   ds_gfs,   ["bias_gfsgpm",   "bias_gfsgsmap",   "bias_gfsmswep"])
    ]

    obs_names = ["GPM", "GSMAP", "MSWEP"]

    proj = ccrs.PlateCarree()

    fig_params = FIG_PARAMS[DOMINIO_ATIVO]

    fig, axes = plt.subplots(
       nrows=3,
       ncols=3,
       figsize=fig_params["figsize"],
       subplot_kw={"projection": proj},
       gridspec_kw={
           "hspace": fig_params["hspace"],
           "wspace": fig_params["wspace"]
       }
    )

    for i, (model_name, ds, var_list) in enumerate(models):
        for j, var in enumerate(var_list):

            ax = axes[i, j]
            da = ds[var].squeeze()

            lat_name = [d for d in da.dims if "lat" in d.lower()][0]
            lon_name = [d for d in da.dims if "lon" in d.lower() or d.lower() == "x"][0]

            dom = DOMINIOS[DOMINIO_ATIVO]

            if da[lon_name].min() < 0:
                da = (
                    da.assign_coords(
                        {lon_name: (da[lon_name] + 360) % 360}
                    )
                    .sortby(lon_name)
                )

            lat_min, lat_max = dom["lat"]
            lon_min, lon_max = dom["lon"]

            if da[lat_name][0] > da[lat_name][-1]:
                lat_slice = slice(lat_max, lat_min)
            else:
                lat_slice = slice(lat_min, lat_max)

            sub = da.sel(
                {
                    lat_name: lat_slice,
                    lon_name: slice(lon_min, lon_max)
                }
            )

            bias_med = float(sub.mean(skipna=True))
            
            im = ax.pcolormesh(
                sub[lon_name],
                sub[lat_name],
                sub,
                transform=ccrs.PlateCarree(),
                cmap=CMAP,
                vmin=VMIN,
                vmax=VMAX,
                shading="auto"
            )

            ax.coastlines(resolution="110m", linewidth=0.8)
            ax.add_feature(cfeature.BORDERS, linewidth=0.4)

            gl = ax.gridlines(
                draw_labels=True,
                linewidth=0.3,
                color="gray",
                alpha=0.5,
                linestyle=":"
            )

            gl.top_labels = False
            gl.right_labels = False

#            if i != 2:
#                gl.bottom_labels = False
#            if j != 0:
#                gl.left_labels = False

            gl.xlabel_style = {"size": 8}
            gl.ylabel_style = {"size": 8}
            gl.xformatter = LONGITUDE_FORMATTER
            gl.yformatter = LATITUDE_FORMATTER

            ax.set_title(
                f"{model_name} - {obs_names[j]} "
                f"(Bias: {bias_med:.2f} mm)",
                fontsize=10,
                pad=4
            )

    cbar = fig.colorbar(
        im,
        ax=axes,
        orientation="vertical",
        shrink=0.85,
        pad=0.018
    )

    cbar.ax.tick_params(labelsize=12)

    fig.suptitle(
        f"Monthly Mean 24 h Precipitation Bias (mm) | "
        f"{ano}{mes:02d} | F{lead:03d}",
        fontsize=16,
        y=0.96
    )

#    plt.subplots_adjust(top=0.92, bottom=0.06)

    nome_fig = f"{ano}{mes:02d}/{ano}{mes:02d}_mean/BIAS_{ano}{mes:02d}_{DOMINIO_ATIVO}_p{lead:03d}h.png"
    fig_dir = f"{DIR_SAIDA}/{ano}{mes:02d}/{ano}{mes:02d}_mean"
    os.makedirs(fig_dir, exist_ok=True)
    plt.savefig(
        os.path.join(fig_dir, nome_fig),
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    ds_gfs.close()
    ds_bam.close()
    ds_monan.close()


# ==========================================================
# LOOP 
# ==========================================================

if __name__ == "__main__":

    for lead in range(PRAZO_INICIAL, PRAZO_FINAL + 1, PASSO_PRAZO):
        print(f"Gerando figura para prazo {lead:03d} h - {DOMINIO_ATIVO}")
        plot_bias_mensal(ANO, MES, lead)


