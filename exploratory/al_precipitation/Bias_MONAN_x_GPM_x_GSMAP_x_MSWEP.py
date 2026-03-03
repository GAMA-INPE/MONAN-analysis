#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Script para gerar MAE (Mean absolute Error) do MONAN em relação a GPM, GSMAP e MSWEP
# Autor: Andre Lyra
#
# Uso: (Necessario ambiente python e cdo)
# /lustre/projetos/monan_gam/andre.lyra/Scripts/Scripts_MONAN/python_env/bin/python Bias_MONAN_x_GPM_x_GSMAP_x_MSWEP.py 2025 12 01 00 120
# onde 120 eh o prazo de previsao em horas

import argparse
import datetime
import subprocess

import os
os.environ["CARTOPY_DATA_DIR"] = "/lustre/projetos/monan_gam/andre.lyra/cartopy"

import sys
import xarray as xr
import numpy as np
import glob
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
import matplotlib.ticker as mticker
from matplotlib.colors import Normalize
from matplotlib import cm
from matplotlib.colors import ListedColormap, BoundaryNorm 
from pathlib import Path

# module load cdo/2.5.4

parser = argparse.ArgumentParser(
        description="Gera Bias para cada ciclo de previsao do MONAN.", 
        formatter_class=argparse.RawTextHelpFormatter 
    )

# Argumentos da data inicial
parser.add_argument('ANO', type=str, help='Ano de inicializacao (Ex: 2025)')
parser.add_argument('MES', type=str, help='Mes de inicializacao (Ex: 12)')
parser.add_argument('DIA', type=str, help='Dia de inicializacao (Ex: 01)')
parser.add_argument('HORA', type=str, help='Hora de inicializacao (Ex: 00)')

# Argumento do prazo total
parser.add_argument('PRAZO_H', type=int, help='Prazo total da previsao em horas (Ex: 72, 120)')

args = parser.parse_args()

data_ini = datetime.datetime(
    int(args.ANO),
    int(args.MES),
    int(args.DIA),
    int(args.HORA)
)
prazo_total = args.PRAZO_H

lead_times = range(24, prazo_total + 1, 24)

# Loop de previsao
for lead in lead_times:
    print("=" * 60)

    data_fim = data_ini + datetime.timedelta(hours=lead)
    data_ini_obs = data_fim - datetime.timedelta(hours=24)

    ciclo_str = data_ini.strftime("%Y%m%d%H")
    data_ini_mod_str = data_ini.strftime("%Y%m%d%H")
    data_fim_mod_str = data_fim.strftime("%Y%m%d%H")
    data_fim_obs_str = data_fim.strftime("%Y%m%d%H")

# Caminhos dos arquivos
    monan_nc = (
        f"/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/"
        f"MONAN/{ciclo_str}/"
        f"MONAN_Precipitation_24h_acum_"
        f"{data_ini_mod_str}_{data_fim_mod_str}_{lead:03d}h.nc"
    )

    gpm_nc = (
        f"/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/"
        f"GPM_IMERG/{data_fim_obs_str}00/"
        f"GPM_IMERG_Precipitation_24h_accum_{data_fim_obs_str}00.nc"
    )

    gsmap_nc = (
        f"/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/"
        f"GSMAP/{data_fim_obs_str}00/"
        f"GSMAP_Precipitation_24h_accum_{data_fim_obs_str}00.nc"
    )

    mswep_nc = (
        f"/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/"
        f"MSWEP/{data_fim_obs_str}00/"
        f"MSWEP_Precipitation_24h_accum_{data_fim_obs_str}00.nc"
    )

    print("Model file:", monan_nc)
    print("GPM file:", gpm_nc)
    print("GSMAP file:", gsmap_nc)
    print("MSWEP file:", mswep_nc)

# Diretorio de saida das figuras
    fig_dir = f"/pesq/share/monan/monan_gam/precip_24h/Bias/{args.ANO}{args.MES}/{ciclo_str}/"
    os.makedirs(fig_dir, exist_ok=True)

# Funcao para o CDO
    def remap_cdo(obs_nc, out_nc, ref_nc):
        if not os.path.exists(out_nc):
            cmd = [
                "cdo",
                "-f", "nc",
                f"-remapcon,{ref_nc}",
                obs_nc,
                out_nc
            ]
            subprocess.run(cmd, check=True)
            print(f"Remapeado: {out_nc}")
        else:
            print(f"Arquivo ja existe: {out_nc}")

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


# Ajuste se o nome da variavel for diferente
    var_monan = "prec"
    var_gpm = "prec"
    var_gsmap = "prec"
    var_mswep = "prec"

    monan = ds_monan[var_monan]
    gpm = ds_gpm[var_gpm]
    gsmap = ds_gsmap[var_gsmap]
    mswep = ds_mswep[var_mswep]

    lat = ds_monan["lat"]
    lon = ds_monan["lon"]

# Diferencas
    diff_monan_gpm = monan - gpm
    diff_monan_gsmap = monan - gsmap
    diff_monan_mswep = monan - mswep

    abs_diff_monan_gpm = np.abs(monan - gpm)
    abs_diff_monan_gsmap = np.abs(monan - gsmap)
    abs_diff_monan_mswep = np.abs(monan - mswep)

# Calculando as medias 
    diff_med_gpm = np.nanmean(diff_monan_gpm)
    diff_med_gpm_AMS =  np.nanmean(diff_monan_gpm.sel(lat=slice(-55, 20),lon=slice(275, 340)))
    diff_med_gpm_ACC =  np.nanmean(diff_monan_gpm.sel(lat=slice(-10, 35),lon=slice(242, 335)))

    diff_med_gsmap = np.nanmean(diff_monan_gsmap)
    diff_med_gsmap_AMS =  np.nanmean(diff_monan_gsmap.sel(lat=slice(-55, 20),lon=slice(275, 340)))
    diff_med_gsmap_ACC =  np.nanmean(diff_monan_gsmap.sel(lat=slice(-10, 35),lon=slice(242, 335)))

    diff_med_mswep = np.nanmean(diff_monan_mswep)
    diff_med_mswep_AMS =  np.nanmean(diff_monan_mswep.sel(lat=slice(-55, 20),lon=slice(275, 340)))
    diff_med_mswep_ACC =  np.nanmean(diff_monan_mswep.sel(lat=slice(-10, 35),lon=slice(242, 335)))

    abs_diff_med_gpm = np.nanmean(abs_diff_monan_gpm)
    abs_diff_med_gpm_AMS =  np.nanmean(abs_diff_monan_gpm.sel(lat=slice(-55, 20),lon=slice(275, 340)))
    abs_diff_med_gpm_ACC =  np.nanmean(abs_diff_monan_gpm.sel(lat=slice(-10, 35),lon=slice(242, 335)))

    abs_diff_med_gsmap = np.nanmean(abs_diff_monan_gsmap)
    abs_diff_med_gsmap_AMS =  np.nanmean(abs_diff_monan_gsmap.sel(lat=slice(-55, 20),lon=slice(275, 340)))
    abs_diff_med_gsmap_ACC =  np.nanmean(abs_diff_monan_gsmap.sel(lat=slice(-10, 35),lon=slice(242, 335)))

    abs_diff_med_mswep = np.nanmean(abs_diff_monan_mswep)
    abs_diff_med_mswep_AMS =  np.nanmean(abs_diff_monan_mswep.sel(lat=slice(-55, 20),lon=slice(275, 340)))
    abs_diff_med_mswep_ACC =  np.nanmean(abs_diff_monan_mswep.sel(lat=slice(-10, 35),lon=slice(242, 335)))
    
# Formatar os valores para inclus?o no t?tulo
    media_str_gpm = f"MAE: {abs_diff_med_gpm:.2f} mm, Bias: {diff_med_gpm:.2f} mm"
    media_str_gpm_AMS = f"MAE: {abs_diff_med_gpm_AMS:.2f} mm, Bias: {diff_med_gpm_AMS:.2f} mm"
    media_str_gpm_ACC = f"MAE: {abs_diff_med_gpm_ACC:.2f} mm, Bias: {diff_med_gpm_ACC:.2f} mm"

    media_str_gsmap = f"MAE: {abs_diff_med_gsmap:.2f} mm, Bias: {diff_med_gsmap:.2f} mm"
    media_str_gsmap_AMS = f"MAE: {abs_diff_med_gsmap_AMS:.2f} mm, Bias: {diff_med_gsmap_AMS:.2f} mm"
    media_str_gsmap_ACC = f"MAE: {abs_diff_med_gsmap_ACC:.2f} mm, Bias: {diff_med_gsmap_ACC:.2f} mm"

    media_str_mswep = f"MAE: {abs_diff_med_mswep:.2f} mm, Bias: {diff_med_mswep:.2f} mm"
    media_str_mswep_AMS = f"MAE: {abs_diff_med_mswep_AMS:.2f} mm, Bias: {diff_med_mswep_AMS:.2f} mm"
    media_str_mswep_ACC = f"MAE: {abs_diff_med_mswep_ACC:.2f} mm, Bias: {diff_med_mswep_ACC:.2f} mm"

# Escala
    colors_rgb = [
#    (90, 0, 0)            # 25
    (130, 0, 0),      # 20
    (192, 3, 0),      # 15
    (225, 18, 0),     # 12
    (255, 96, 2),     # 9
    (255, 193, 60),   # 6
    (255, 251, 190),  # 3
    (255, 255, 255),  # 0
    (179, 230, 249),  # -3
    (150, 200, 249),  # -6
    (75, 155, 244),   # -9
    (36, 116, 241),   # -12
    (25, 90, 234),    # -15
    (0,  45, 220),    # -20        
#    (0,  25, 200),        # -25
    ]

    levels = [ -25, -20, -15, -12, -9, -6, -3, 3, 6, 9, 12, 15, 20, 25]
    cmap = ListedColormap( [(r/255, g/255, b/255) for r, g, b in colors_rgb] )
    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)


# ===============================
# Funcao de plot Global
# ===============================
    def plot_diff(data, titulo, nome_fig):
       fig = plt.figure(figsize=(10,5))
       ax = plt.axes(projection=ccrs.PlateCarree())

       im = data.plot(
       ax=ax,
       transform=ccrs.PlateCarree(),
       cmap=cmap,
       norm=norm,
       add_colorbar=False
       )

       ax.set_xticks(np.arange(-180, 180+1 , 60), crs=ccrs.PlateCarree())
       ax.set_yticks(np.arange(-60, 60, 30), crs=ccrs.PlateCarree())      
       ax.xaxis.set_major_formatter(LongitudeFormatter())
       ax.yaxis.set_major_formatter(LatitudeFormatter())
       ax.set_xlabel("")
       ax.set_ylabel("")
       ax.coastlines()
       ax.set_title(titulo) 

       cbar = plt.colorbar(im, orientation='vertical', pad=0.1, aspect=50, boundaries=levels, extend='both')
       cbar.set_label('(mm)')
       cbar.set_ticks( [-20, -15, -12, -9, -6, -3, 3, 6, 9, 12, 15, 20])                 

       plt.savefig(os.path.join(fig_dir, nome_fig), dpi=300, bbox_inches="tight")
       plt.close()
       print(f"Figura salva: {nome_fig}")

# Plot e salvamento Global
    plot_diff(
    diff_monan_gpm,
    f"Bias {lead:03d}h MONAN vs GPM IMERG \n Global - {media_str_gpm}",
    f"diff_MONAN_GPM_GLB_{lead:03d}h.png"
    )

    plot_diff(
    diff_monan_gsmap,
    f"Bias {lead:03d}h MONAN vs GSMAP \n Global - {media_str_gsmap}",
    f"diff_MONAN_GSMAP_GLB_{lead:03d}h.png"
    )

    plot_diff(
    diff_monan_mswep,
    f"Bias {lead:03d}h MONAN vs MSWEP \n Global - {media_str_mswep}",
    f"diff_MONAN_MSWEP_GLB_{lead:03d}h.png"
    )
    
    
# ===============================
# Funcao de plot AMS
# ===============================
    def plot_diff_AMS(data, titulo, nome_fig):
       fig = plt.figure(figsize=(10,5))
       ax = plt.axes(projection=ccrs.PlateCarree())

       im = data.plot(
       ax=ax,
       transform=ccrs.PlateCarree(),
       cmap=cmap,
       norm=norm, 
       add_colorbar=False
       )

       ax.set_xticks(np.arange(-180, 180+1 , 10), crs=ccrs.PlateCarree())
       ax.set_yticks(np.arange(-60, 60, 10), crs=ccrs.PlateCarree())      
       ax.xaxis.set_major_formatter(LongitudeFormatter())
       ax.yaxis.set_major_formatter(LatitudeFormatter())
       ax.set_xlabel("")
       ax.set_ylabel("")
       ax.coastlines()
       ax.set_title(titulo) 
       ax.set_extent([-85, -20, -55, 20], crs=ccrs.PlateCarree())
       xticks = np.arange(-80, -19, 10)
       yticks = np.arange(-50, 21, 10)

       ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.6)
       ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=0.4)
       ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='none', edgecolor='black', linewidth=0.2)
       estados = cfeature.NaturalEarthFeature(
       category='cultural',
       name='admin_1_states_provinces_lines',
       scale='50m',
       facecolor='none'
       )
       ax.add_feature(estados, edgecolor='black', linewidth=0.4)
       
       cbar = plt.colorbar(im, orientation='vertical', pad=0.1, aspect=50, boundaries=levels, extend='both')
       cbar.set_label('(mm)')
       cbar.set_ticks( [-20, -15, -12, -9, -6, -3, 3, 6, 9, 12, 15, 20])           
       
       plt.savefig(os.path.join(fig_dir, nome_fig), dpi=300, bbox_inches="tight")
       plt.close()
       print(f"Figura salva: {nome_fig}")

# Plot e salvamento AMS
    plot_diff_AMS(
    diff_monan_gpm,
    f"Bias {lead:03d}h MONAN {data_ini_mod_str} vs GPM IMERG \n AMS - {media_str_gpm_AMS}",
    f"diff_MONAN_GPM_AMS_{lead:03d}h.png"
    )

    plot_diff_AMS(
    diff_monan_gsmap,
    f"Bias {lead:03d}h MONAN {data_ini_mod_str} vs GSMAP \n AMS - {media_str_gsmap_AMS}",
    f"diff_MONAN_GSMAP_AMS_{lead:03d}h.png"
    )

    plot_diff_AMS(
    diff_monan_mswep,
    f"Bias {lead:03d}h MONAN {data_ini_mod_str} vs MSWEP \n AMS - {media_str_mswep_AMS}",
    f"diff_MONAN_MSWEP_AMS_{lead:03d}h.png"
    )


# ===============================
# Funcao de plot ACC
# ===============================
    def plot_diff_AMS(data, titulo, nome_fig):
       fig = plt.figure(figsize=(10,5))
       ax = plt.axes(projection=ccrs.PlateCarree())

       im = data.plot(
       ax=ax,
       transform=ccrs.PlateCarree(),
       cmap=cmap,
       norm=norm,
       add_colorbar=False
       )

       ax.set_xticks(np.arange(-180, 180+1 , 10), crs=ccrs.PlateCarree())
       ax.set_yticks(np.arange(-60, 60, 10), crs=ccrs.PlateCarree())      
       ax.xaxis.set_major_formatter(LongitudeFormatter())
       ax.yaxis.set_major_formatter(LatitudeFormatter())
       ax.set_xlabel("")
       ax.set_ylabel("")
       ax.coastlines()
       ax.set_title(titulo) 
       ax.set_extent([-118, -35, -10, 35], crs=ccrs.PlateCarree())
       xticks = np.arange(-110, -35, 10)
       yticks = np.arange(-10, 36, 10)


       ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.6)
       ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=0.4)
       ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='none', edgecolor='black', linewidth=0.2)
       estados = cfeature.NaturalEarthFeature(
       category='cultural',
       name='admin_1_states_provinces_lines',
       scale='50m',
       facecolor='none'
       )
       ax.add_feature(estados, edgecolor='black', linewidth=0.4)
   
       cbar = plt.colorbar(im, orientation='vertical', pad=0.1, aspect=50, boundaries=levels, extend='both')
       cbar.set_label('(mm)')
       cbar.set_ticks( [-20, -15, -12, -9, -6, -3, 3, 6, 9, 12, 15, 20])             
   
       plt.savefig(os.path.join(fig_dir, nome_fig), dpi=300, bbox_inches="tight")
       plt.close()
       print(f"Figura salva: {nome_fig}")

# Plot e salvamento ACC
    plot_diff_AMS(
    diff_monan_gpm,
    f"Bias {lead:03d}h MONAN {data_ini_mod_str} vs GPM IMERG \n ACC - {media_str_gpm_ACC}",
    f"diff_MONAN_GPM_ACC_{lead:03d}h.png"
    )

    plot_diff_AMS(
    diff_monan_gsmap,
    f"Bias {lead:03d}h MONAN {data_ini_mod_str} vs GSMAP \n ACC - {media_str_gsmap_ACC}",
    f"diff_MONAN_GSMAP_ACC_{lead:03d}h.png"
    )

    plot_diff_AMS(
    diff_monan_mswep,
    f"Bias {lead:03d}h MONAN {data_ini_mod_str} vs MSWEP \n ACC - {media_str_mswep_ACC}",
    f"diff_MONAN_MSWEP_ACC_{lead:03d}h.png"
    )


# Salvando o arquivo NetCDF
    lat_da = xr.DataArray(
       lat,
       dims=['lat'],
       attrs={
        'units': 'degrees_north',
        'long_name': 'Latitude',
        '_CoordinateAxisType': 'Lat',
        'axis': 'Y'
       }
    )

    lon_da = xr.DataArray(
       lon,
       dims=['lon'],
       attrs={
        'units': 'degrees_east',
        'long_name': 'Longitude',
        '_CoordinateAxisType': 'Lon',
        'axis': 'X'
       }
    )

# Arrays de saída
    diff_monan_gpm_out   = np.ascontiguousarray(diff_monan_gpm,   dtype='float32')
    diff_monan_gsmap_out = np.ascontiguousarray(diff_monan_gsmap, dtype='float32')
    diff_monan_mswep_out = np.ascontiguousarray(diff_monan_mswep, dtype='float32')

# Dataset com múltiplas variáveis
    ds = xr.Dataset(
    {
        'bias_monangpm':   (['lat', 'lon'], diff_monan_gpm_out),
        'bias_monangsmap': (['lat', 'lon'], diff_monan_gsmap_out),
        'bias_monanmswep': (['lat', 'lon'], diff_monan_mswep_out),
    },
    coords={
        'lat': lat_da,
        'lon': lon_da
    }
    )

# Encoding para todas as variáveis
    encoding = {
    'bias_monangpm': {
        'dtype': 'float32',
        '_FillValue': -999.0,
    },
    'bias_monangsmap': {
        'dtype': 'float32',
        '_FillValue': -999.0,
    },
    'bias_monanmswep': {
        'dtype': 'float32',
        '_FillValue': -999.0,
    }
    }


# Salva o arquivo NetCDF
    nome_arquivo = f"Bias_MONAN_Prec_{data_ini_mod_str}_{lead:03d}h.nc"
    caminho_netcdf = Path("/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/Bias/") / data_ini_mod_str / nome_arquivo
    caminho_netcdf.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(caminho_netcdf, encoding=encoding, format='NETCDF4')  
    print(f"Netcdf: {caminho_netcdf}")
    

# Roda o script para recortar e juntar as figuras
subprocess.run(
    ["bash", "Gera_bias_montage.sh", f"{data_ini_mod_str}", f"{prazo_total}"],
    check=True
)  
