# -*- coding: utf-8 -*-
# Autor: 
# Andre Lyra
# Uso: (Necessario ambiente python com bibliotecas carregadas)
# /lustre/projetos/monan_gam/andre.lyra/Scripts/Scripts_MONAN/python_env/bin/python  MONAN_nc_24h_acum_newcolorbar.py 2025 12 01 00 120
# onde 120 eh o prazo de previsao em horas

import argparse
import datetime
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


parser = argparse.ArgumentParser(
        description="Gera acumulados de 24h para cada ciclo de previsao do MONAN.", 
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

data_inicio_base = datetime.datetime(
     int(args.ANO), 
     int(args.MES), 
     int(args.DIA), 
     int(args.HORA)
        )

data_inicial = f"{args.ANO}{args.MES}{args.DIA}{args.HORA}" 

delta_hora = datetime.timedelta(hours=0)
delta_dia = datetime.timedelta(hours=24)
num_dias = args.PRAZO_H // 24
    
print("\n" + "=" * 60)
print(f"PROCESSAMENTO DE {num_dias} PERIODOS DE 24 HORAS")
print("=" * 60)
    
  
pares_arquivos = []

# Loop para cada periodo de 24 horas
for i in range(num_dias):
    data_inicial_acumulo = data_inicio_base + (delta_dia * i) + (delta_hora * (i+1))
    data_final_acumulo = data_inicial_acumulo + delta_dia
    Fct=f"{((i+1)*24):03d}"   

    # Formato de data/hora esperado no nome do arquivo (YYYYMMDDHH)
    formato_data = '%Y%m%d%H'
    data_str_i = data_inicial_acumulo.strftime(formato_data)
    data_str_e = data_final_acumulo.strftime(formato_data)
    
# Montando nome dos arquivos
#    CAMINHO_BASE = "/lustre/projetos/monan_adm/monan/ecf_PREOPER/MONAN-WorkFlow-OPER/MONAN_PRE_OPER/MONAN/scripts_CD-CT/dataout/"
    CAMINHO_BASE = "/lustre/projetos/monan_adm/monan/ecf_PREOPER/MONAN-WorkFlow-OPER/MONAN_PRE_OPER/MONAN/scripts_CD-CT/dataout/flushout/"
    DIR_DATA = f"{data_inicial}/"
    PREFIXO_ARQ  = "MONAN_DIAG_G_POS_GFS_"
    SUFIXO_ARQ   = ".00.00.x5898242L55.nc" 
    nome_arquivo_i = f"{PREFIXO_ARQ}{data_inicial}_{data_str_i}{SUFIXO_ARQ}"
    nome_arquivo_e = f"{PREFIXO_ARQ}{data_inicial}_{data_str_e}{SUFIXO_ARQ}"
    
    # Monta o caminho completo
    caminho_completo_i = os.path.join(CAMINHO_BASE, DIR_DATA, nome_arquivo_i)
    caminho_completo_e = os.path.join(CAMINHO_BASE, DIR_DATA, nome_arquivo_e)

    pares_arquivos.append((caminho_completo_i, caminho_completo_e))

    # Imprimindo as datas de acumulo
    print(f"--- Acumulado {i+1} --- Previsao {Fct}h ---")
    print(f"Data Inicial: {data_inicial_acumulo.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data Final:   {data_final_acumulo.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Arquivo I: {caminho_completo_i}")
    print(f"Arquivo E: {caminho_completo_e}")
    
    print("=" * 60)
        
# Caminho dos arquivos (MONAN)
    arquivoi = caminho_completo_i
    arquivoe = caminho_completo_e
#    print(arquivoi)
#    print(arquivoe)

# Inicializa variaveis de referencia
    precip_soma = None
    lat = lon = None

    fi = xr.open_dataset(arquivoi, engine="netcdf4")
    fe = xr.open_dataset(arquivoe, engine="netcdf4")

# Soma das variaveis acumuladas
    vari = (fi["rainnc"].isel(Time=0) + fi["rainc"].isel(Time=0)).values
    vare = (fe["rainnc"].isel(Time=0) + fe["rainc"].isel(Time=0)).values

# Coordenadas geograficas (em graus)
    lat = (fi["latitude"].values)
    lon = (fi["longitude"].values)

#    print("Dimensoes de vari e vare:", vari.shape)

# Diferenca (chuva acumulada entre os dois tempos)
    prec_acum = ((vare - vari) ).squeeze()

# Calculando o Máximo Global
    prec_max = np.nanmax(prec_acum)
    mask_lat_AMS = (lat >= -55) & (lat <= 20)
    mask_lon_AMS = (lon >= 275) & (lon <= 340)
    prec_max_AMS = np.nanmax(prec_acum[np.ix_(mask_lat_AMS, mask_lon_AMS)])
    mask_lat_ACC = (lat >= -10) & (lat <= 35)
    mask_lon_ACC = (lon >= 242) & (lon <= 325)
    prec_max_ACC = np.nanmax(prec_acum[np.ix_(mask_lat_ACC, mask_lon_ACC)])
   
# Calculando a Média Global
    weights = np.cos(np.deg2rad(lat))    
    w2d = weights[:, None]                 
    mask = np.isfinite(prec_acum)
    num = np.nansum(prec_acum * w2d * mask)
    den = np.nansum(w2d * mask)
    prec_media = num / den   
    
    prec_sub = prec_acum[np.ix_(mask_lat_AMS, mask_lon_AMS)]
    lat_sub = lat[mask_lat_AMS]
    weights = np.cos(np.deg2rad(lat_sub))[:, None]
    num = np.nansum(prec_sub * weights)
    den = np.nansum(weights * np.isfinite(prec_sub))
    prec_media_AMS = num / den

    prec_sub = prec_acum[np.ix_(mask_lat_ACC, mask_lon_ACC)]
    lat_sub = lat[mask_lat_ACC]
    weights = np.cos(np.deg2rad(lat_sub))[:, None]
    num = np.nansum(prec_sub * weights)
    den = np.nansum(weights * np.isfinite(prec_sub))
    prec_media_ACC = num / den   
 
# Formatar os valores para inclusão no título
    max_str = f"Max: {prec_max:.2f} mm"
    media_str = f"Mean: {prec_media:.2f} mm"
    max_str_AMS = f"Max: {prec_max_AMS:.2f} mm"
    media_str_AMS = f"Mean: {prec_media_AMS:.2f} mm"
    max_str_ACC = f"Max: {prec_max_ACC:.2f} mm"
    media_str_ACC = f"Mean: {prec_media_ACC:.2f} mm" 
       
#    print("Shapes:", lon.shape, lat.shape, prec_acum.shape)

# Lista de Cores 
    cores_legenda_rgb = [
    (255, 255, 255),  # Branco
    (220, 220, 220),  # Cinza Claro
    (180, 180, 180),  # Cinza
    (20, 0, 150),     # Azul Marinho/Roxo
    (0, 0, 255),      # Azul
    (0, 100, 100),    # Verde Escuro/Azul Petróleo
    (0, 200, 0),      # Verde
    (150, 255, 0),    # Verde Limão/Ciano
    (255, 255, 0),    # Amarelo Claro
    (255, 220, 0),    # Amarelo Escuro/Ouro
    (255, 130, 0),    # Laranja
    (230, 25, 25),    # Vermelho Claro
    (100, 0, 0),      # Vermelho Escuro/Borgonha
    ]

    cores_normalizadas_matplotlib = []
    for r, g, b in cores_legenda_rgb:
        cores_normalizadas_matplotlib.append((r / 255.0, g / 255.0, b / 255.0))

# Criacao da colormap e os niveis (clevs)
    cmap = ListedColormap(cores_normalizadas_matplotlib)
    clevs = [0, 1, 2, 4, 6, 10, 15, 25, 35, 50, 75, 100, 150]
    clevs_full = clevs + [40]
    norm = BoundaryNorm(clevs, ncolors=len(clevs), extend='max')

# Projecao Cartopy
    proj = ccrs.PlateCarree()
    lon2d, lat2d = np.meshgrid(lon, lat)


##########################
# Plotagem Global
    fig = plt.figure(figsize=(10,5))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-180, 180, -90, 90], crs=ccrs.PlateCarree())

    plt_triang = ax.pcolormesh(
    lon2d, lat2d, prec_acum,
    cmap=cmap,
    norm=norm,
    shading='auto',
    transform=proj
    )

# Contornos de continentes e linhas costeiras
    ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.6)
    ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=0.4)
    ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='none', edgecolor='black', linewidth=0.2)

# Linhas de grade
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.bottom_labels = True
    gl.left_labels = True
    gl.xlines = False
    gl.ylines = False
    gl.xlocator = plt.FixedLocator(np.arange(-180, 181, 60))
    gl.ylocator = plt.FixedLocator(np.arange(-60, 61, 30))

# Barra de cores
    cbar = plt.colorbar(plt_triang, orientation='vertical', pad=0.1, aspect=50, boundaries=clevs, extend='max')
    cbar.set_label('(mm/day)')
    cbar.set_ticks(clevs)

# Titulo
    plt.title(
    f'MONAN {data_inicial}+{data_str_e} - 24h prec accum for {Fct}h \n' 
    f'Global - {max_str} | {media_str}', 
    fontsize=12
    )
# Salvar figura
    nome_arquivo = f"MONAN_24precacum_{data_inicial}_{data_str_e}_GLB.png"
    caminho_out = f"/pesq/share/monan/monan_gam/precip_24h/MONAN/{args.ANO}{args.MES}/{data_inicial}/"
    os.makedirs(caminho_out, exist_ok=True)
    plt.savefig(os.path.join(caminho_out, nome_arquivo), dpi=300, bbox_inches="tight")
    plt.close(fig)

##########################
# Plotagem América do Sul
    fig = plt.figure(figsize=(10,5))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-85, -20, -55, 20], crs=ccrs.PlateCarree())
    xticks = np.arange(-80, -19, 10)
    yticks = np.arange(-50, 21, 10)
    ax.set_xticks(xticks, crs=ccrs.PlateCarree())
    ax.set_yticks(yticks, crs=ccrs.PlateCarree())
    ax.xaxis.set_major_formatter(LongitudeFormatter(number_format='.0f'))
    ax.yaxis.set_major_formatter(LatitudeFormatter(number_format='.0f'))
    
    ax.tick_params(
    axis='both',
    which='major',
    direction='in',
    length=2,
    width=0.6,
    labelsize=8,
    top=True,
    right=True
    )
        
    plt_triang = ax.pcolormesh(
    lon2d, lat2d, prec_acum,
    cmap=cmap,
    norm=norm,
    shading='auto',
    transform=proj
    )

# Contornos de continentes e linhas costeiras
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

# Linhas de grade
    gl = ax.gridlines(
    draw_labels=True,
    linewidth=0.3,
    color='gray',
    alpha=0.5,
    linestyle='--'
    )

    gl.top_labels = False
    gl.right_labels = False
    gl.bottom_labels = False
    gl.left_labels = False
    gl.xlines = False
    gl.ylines = False
    gl.xlocator = plt.FixedLocator(np.arange(-180, 181, 10))
    gl.ylocator = plt.FixedLocator(np.arange(-60, 61, 10))
    gl.xlabel_style = {'size': 9}
    gl.ylabel_style = {'size': 9}

# Barra de cores
    cbar = plt.colorbar(plt_triang, orientation='vertical', pad=0.1, aspect=50, boundaries=clevs, extend='max')
    cbar.set_label('(mm/day)')
    cbar.set_ticks(clevs)

# Titulo
    plt.title(
    f'MONAN {data_inicial}+{data_str_e} - prec24h {Fct}h\n' 
    f'AMS - {max_str_AMS} | {media_str_AMS}', 
    fontsize=12
    )
# Salvar figura
    nome_arquivo = f"MONAN_24precacum_{data_inicial}_{data_str_e}_AMS.png"
    caminho_out = f"/pesq/share/monan/monan_gam/precip_24h/MONAN/{args.ANO}{args.MES}/{data_inicial}/"
    plt.savefig(os.path.join(caminho_out, nome_arquivo), dpi=300, bbox_inches="tight")
    plt.close(fig)


##########################
# Plotagem América Central e Caribe
    fig = plt.figure(figsize=(10,5))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-118, -35, -10, 35], crs=ccrs.PlateCarree())
    xticks = np.arange(-110, -35, 10)
    yticks = np.arange(-10, 36, 10)
    ax.set_xticks(xticks, crs=ccrs.PlateCarree())
    ax.set_yticks(yticks, crs=ccrs.PlateCarree())
    ax.xaxis.set_major_formatter(LongitudeFormatter(number_format='.0f'))
    ax.yaxis.set_major_formatter(LatitudeFormatter(number_format='.0f'))
    
    ax.tick_params(
    axis='both',
    which='major',
    direction='in',
    length=2,
    width=0.6,
    labelsize=8,
    top=True,
    right=True
    )
        
    plt_triang = ax.pcolormesh(
    lon2d, lat2d, prec_acum,
    cmap=cmap,
    norm=norm,
    shading='auto',
    transform=proj
    )

# Contornos de continentes e linhas costeiras
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

# Linhas de grade
    gl = ax.gridlines(
    draw_labels=True,
    linewidth=0.3,
    color='gray',
    alpha=0.5,
    linestyle='--'
    )

    gl.top_labels = False
    gl.right_labels = False
    gl.bottom_labels = False
    gl.left_labels = False
    gl.xlines = False
    gl.ylines = False
    gl.xlocator = plt.FixedLocator(np.arange(-180, 181, 10))
    gl.ylocator = plt.FixedLocator(np.arange(-60, 61, 10))
    gl.xlabel_style = {'size': 9}
    gl.ylabel_style = {'size': 9}

# Barra de cores
    cbar = plt.colorbar(plt_triang, orientation='vertical', pad=0.1, aspect=50, boundaries=clevs, extend='max')
    cbar.set_label('(mm/day)')
    cbar.set_ticks(clevs)

# Titulo
    plt.title(
    f'MONAN {data_inicial}+{data_str_e} - 24h prec accum for {Fct}h \n' 
    f'ACC - {max_str_ACC} | {media_str_ACC}', 
    fontsize=12
    )
# Salvar figura
    nome_arquivo = f"MONAN_24precacum_{data_inicial}_{data_str_e}_ACC.png"
    caminho_out = f"/pesq/share/monan/monan_gam/precip_24h/MONAN/{args.ANO}{args.MES}/{data_inicial}/"
    plt.savefig(os.path.join(caminho_out, nome_arquivo), dpi=300, bbox_inches="tight")
    plt.close(fig)


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

    prec_out = np.ascontiguousarray(prec_acum, dtype='float32')

    ds = xr.Dataset(
       {
        'prec': (['lat', 'lon'], prec_out)
       },
       coords={
        'lat': lat_da,
        'lon': lon_da
       }
    )

    encoding = {
       'prec': {
               'dtype': 'float32',
               '_FillValue': -999.0,
       }
    }


# Salva o arquivo NetCDF
    nome_arquivo = f"MONAN_Precipitation_24h_acum_{data_inicial}_{data_str_e}_{Fct}h.nc"
    caminho_netcdf = Path("/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/MONAN/") / data_inicial / nome_arquivo
    caminho_netcdf.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(caminho_netcdf, encoding=encoding, format='NETCDF4')
