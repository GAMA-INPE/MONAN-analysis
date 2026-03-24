#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Script para fazer as figuras dos Skill scores para um mes específico 
# Autor: Andre Lyra
# Uso: (Necessario ambiente python com bibliotecas carregadas)
# /lustre/projetos/monan_gam/andre.lyra/Scripts/Scripts_MONAN/python_env/bin/python Mean_Skill_score_MONAN_BAM_GFS.py

# Medias geradas com CDO no diretorio /lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/CONTIGENCIA/
# a partir do script Gera_monthly_sum_Skill.sh

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Gera Skill Scores a partir de contingencias mensais
# Tabelas TXT por dominio e figuras 3x3 por indice
#
# Autor: Andre Lyra
#

import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from pathlib import Path
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER


# ==========================================================
# PARAMETROS
# ==========================================================
ANO = 2026
MES = 1

PRAZO_INICIAL = 24
PRAZO_FINAL   = 120
PASSO_PRAZO   = 24

THRESHOLD_MM = 1.0   # 1.0 2.0 5.0 10.0 20.0 50.0

MODELOS = ["MONAN", "BAM", "GFS"]
REFERENCIAS = ["GPM", "GSMAP", "MSWEP"]

DIR_CONT = (
    "/lustre/projetos/monan_gam/andre.lyra/"
    "NetCDFs/precip_24h/CONTINGENCIA"
)

DIR_TXT = (
    "/pesq/share/monan/monan_gam/precip_24h/Skill/"
    f"Skill_txt_thr{int(THRESHOLD_MM)}mm/{ANO}{MES:02d}/{ANO}{MES:02d}_aggregated"
)

DIR_FIG = (
    ""
    "Skill_fig_mensal"
)

# ==========================================================
# DOMINIOS E FIGURAS
# ==========================================================
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
    "GLB": {"figsize": (16, 9)},
    "AMS": {"figsize": (14, 10)},
    "ACC": {"figsize": (15, 9)}
}

# ==========================================================
# INDICES
# ==========================================================
SKILL_REF = {
    "ACC":  1.0,
    "POD":  1.0,
    "POFD": 0.0,
    "FAR":  0.0,
    "CSI":  1.0,
    "F1":   1.0,
    "ETS":  1.0,
}

SKILL_PLOT = {
    "POD":  dict(vmin=0.0, vmax=1.0, cmap="YlGn"),
    "FAR":  dict(vmin=0.0, vmax=1.0, cmap="YlOrRd_r"),
    "CSI":  dict(vmin=0.0, vmax=1.0, cmap="PuBuGn"),
    "F1":   dict(vmin=0.0, vmax=1.0, cmap="GnBu"),
    "ETS":  dict(vmin=-0.2, vmax=0.6, cmap="RdYlGn"),
}

INDICES_ESPACIAIS = ["POD", "FAR", "CSI", "F1"]

# FUNCOES
def ajusta_longitude(da):
    if da.lon.min() < 0:
        da = da.assign_coords(lon=(da.lon + 360) % 360).sortby("lon")
    return da


def recorte_dominio(da, dominio):
    lat_min, lat_max = DOMINIOS[dominio]["lat"]
    lon_min, lon_max = DOMINIOS[dominio]["lon"]

    lat_slice = slice(lat_min, lat_max)
    if da.lat[0] > da.lat[-1]:
        lat_slice = slice(lat_max, lat_min)

    return da.sel(lat=lat_slice, lon=slice(lon_min, lon_max))


def skill_agregado(H, M, F, C):
    Hn = H.sum().item()
    Mn = M.sum().item()
    Fn = F.sum().item()
    Cn = C.sum().item()
    
    TP = Hn 
    FN = Mn
    FP = Fn
    TN = Cn

    Precision = TP/(TP+FP)
    Recall    = TP/(TP+FN)
    
    total = Hn + Mn + Fn + Cn

    acc  = (Hn + Cn) / total    if total > 0 else np.nan
    pod  = Hn / (Hn + Mn)       if (Hn + Mn) > 0 else np.nan
    pofd = Fn / (Fn + Cn)       if (Fn + Cn) > 0 else np.nan
    far  = Fn / (Hn + Fn)       if (Hn + Fn) > 0 else np.nan
    csi  = Hn / (Hn + Mn + Fn)  if (Hn + Mn + Fn) > 0 else np.nan
    
    f1   = (2 * Hn) / (2 * Hn + Fn + Mn)   if (2 * Hn + Fn + Mn) > 0 else np.nan
    
    f1new = 2 * ( (Precision * Recall) / (Precision + Recall) )
    
    f05= ( 1 + (0.5)**2 ) * ( (Precision * Recall) / ( (((0.5)**2)*Precision) + Recall) )
    
    He = ((Hn + Mn) * (Hn + Fn)) / total if total > 0 else np.nan
    ets = (Hn - He) / (Hn + Mn + Fn - He) if (Hn + Mn + Fn - He) > 0 else np.nan

    return acc, pod, pofd, far, csi, f1, f1new, f05, ets


def skill_spatial(H, M, F, C):
    pod = H / (H + M)
    far = F / (H + F)
    csi = H / (H + M + F)
    f1  = (2 * H) / (2 * H + F + M)

    total = H + M + F + C
    He = ((H + M) * (H + F)) / total
    ets = (H - He) / (H + M + F - He)

    return dict(POD=pod, FAR=far, CSI=csi, F1=f1, ETS=ets)

# Loop
for lead in range(PRAZO_INICIAL, PRAZO_FINAL + 1, PASSO_PRAZO):

    for dominio in DOMINIOS:

        fig_params = FIG_PARAMS[dominio]

        # TXT por modelo
        os.makedirs(DIR_TXT, exist_ok=True)

        txt_files = {}
        for modelo in MODELOS:
            txt_path = (
                f"{DIR_TXT}/Skill_{modelo}_{dominio}_"
                f"{ANO}{MES:02d}_thr{int(THRESHOLD_MM)}mm.txt"
            )
            txt_files[modelo] = txt_path

            if not os.path.exists(txt_path):
                with open(txt_path, "w") as f:
                    f.write("# Skill Scores mensais\n")
                    f.write(f"# Modelo = {modelo}\n")
                    f.write(f"# Regiao = {dominio}\n")
                    f.write(f"# Threshold = {THRESHOLD_MM} mm / 24h\n")
                    f.write(f"# Periodo = {ANO}{MES}\n\n")

                    f.write("# Valores de referencia ideais\n")
                    f.write(
                        "# "
                        f"ACC_best={SKILL_REF['ACC']}  "
                        f"POD_best={SKILL_REF['POD']}  "
                        f"POFD_best={SKILL_REF['POFD']}  "
                        f"FAR_best={SKILL_REF['FAR']}  "
                        f"CSI_best={SKILL_REF['CSI']}  "
                        f"F1_best={SKILL_REF['F1']}  "
                        f"F05_best={SKILL_REF['F1']}  "
                        f"ETS_best={SKILL_REF['ETS']}\n\n"
                    )
		    
                    header = (
                        f"{'LEAD':^6}"
                        f"{'REF':^8}"
                        f"{'ACC':^8}"
                        f"{'POD':^8}"
                        f"{'POFD':^8}"
                        f"{'FAR':^8}"
                        f"{'CSI':^8}"
                        f"{'F1':^8}"
                        f"{'F05':^8}"
                        f"{'ETS':^8}\n"
                    )
                    f.write(header)
                    f.write("-" * len(header) + "\n")


        # Leitura das contingencias
        dados = {}

        for modelo in MODELOS:

            nc = (
                f"{DIR_CONT}/"
                f"CONT_{modelo}_{ANO}{MES:02d}_sum_"
                f"{lead:03d}h_thr{int(THRESHOLD_MM)}mm.nc"
            )

            ds = xr.open_dataset(nc)

            dados[modelo] = {}

            for ref in REFERENCIAS:
                H = ajusta_longitude(ds[f"H_{ref}"])
                M = ajusta_longitude(ds[f"M_{ref}"])
                F = ajusta_longitude(ds[f"F_{ref}"])
                C = ajusta_longitude(ds[f"C_{ref}"])

                H = recorte_dominio(H, dominio)
                M = recorte_dominio(M, dominio)
                F = recorte_dominio(F, dominio)
                C = recorte_dominio(C, dominio)

                dados[modelo][ref] = dict(H=H, M=M, F=F, C=C)

        # TXT
        for modelo in MODELOS:
            with open(txt_files[modelo], "a") as f:
                for ref in REFERENCIAS:
                    H = dados[modelo][ref]["H"]
                    M = dados[modelo][ref]["M"]
                    F = dados[modelo][ref]["F"]
                    C = dados[modelo][ref]["C"]

                    acc, pod, pofd, far, csi, f1, f1new, f05, ets = skill_agregado(H, M, F, C)

                    f.write(
                        f"{str(lead).zfill(3):^6}"
                        f"{ref:^8}"
                        f"{acc:6.2f}"
                        f"{pod:8.2f}"
                        f"{pofd:8.2f}"
                        f"{far:8.2f}"
                        f"{csi:8.2f}"
                        f"{f1new:8.2f}"
                        f"{f05:8.2f}"
                        f"{ets:8.2f}\n"
                    )

        # FIGURAS 
        os.makedirs(DIR_FIG, exist_ok=True)

        for indice in INDICES_ESPACIAIS:

            cfg = SKILL_PLOT[indice]

            fig, axes = plt.subplots(
                nrows=3,
                ncols=3,
                figsize=fig_params["figsize"],
                subplot_kw={"projection": ccrs.PlateCarree()}
            )

            for i, modelo in enumerate(MODELOS):
                for j, ref in enumerate(REFERENCIAS):

                    ax = axes[i, j]

                    H = dados[modelo][ref]["H"]
                    M = dados[modelo][ref]["M"]
                    F = dados[modelo][ref]["F"]
                    C = dados[modelo][ref]["C"]

                    campo = skill_spatial(H, M, F, C)[indice]

                    im = ax.pcolormesh(
                        campo.lon,
                        campo.lat,
                        campo,
                        cmap=cfg["cmap"],
                        vmin=cfg["vmin"],
                        vmax=cfg["vmax"],
                        shading="auto"
                    )

                    ax.coastlines(resolution="110m", linewidth=0.8)
                    ax.add_feature(cfeature.BORDERS, linewidth=0.4)

                    gl = ax.gridlines(draw_labels=True, linewidth=0.3,
                                      linestyle=":", color="gray")
                    gl.top_labels = False
                    gl.right_labels = False
                    gl.xlabel_style = {"size": 8}
                    gl.ylabel_style = {"size": 8}
                    gl.xformatter = LONGITUDE_FORMATTER
                    gl.yformatter = LATITUDE_FORMATTER

                    ax.set_title(f"{modelo} x {ref}", fontsize=10)

            cbar = fig.colorbar(
                im,
                ax=axes,
                orientation="vertical",
                shrink=0.85,
                pad=0.02
            )

            fig.suptitle(
                f"{indice} mensal | {ANO}{MES:02d} | "
                f"F{lead:03d} | Thr {THRESHOLD_MM} mm | {dominio}",
                fontsize=15
            )

            fig.savefig(
                f"{DIR_FIG}/{indice}_{dominio}_{ANO}{MES:02d}_"
                f"p{lead:03d}h_thr{int(THRESHOLD_MM)}mm.png",
                dpi=300,
                bbox_inches="tight"
            )

            plt.close(fig)

