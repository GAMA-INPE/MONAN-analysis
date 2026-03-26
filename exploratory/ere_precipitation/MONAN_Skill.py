#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Script para gerar Skill Scores binarios do MONAN
# Contingencia em NetCDF e scores agregados em TXT
#
# Autor: Andre Lyra
#
# Uso:
# python MONAN_Skill.py 2025 12 01 00 120 1
#

import argparse
import datetime
import subprocess
import os
import xarray as xr
import numpy as np
from pathlib import Path

#OBS_REMAP_BASE = "/home2/eduardo.eras/workspace/NetCDFs/Remapped_30km/"
#OUTPUT_PATH =   "/home2/eduardo.eras/workspace/python/output/"
#NETCDF_PATH =   "/home2/eduardo.eras/workspace/NetCDFs/"
#NETCDF_MONAN_PATH = "/home2/eduardo.eras/workspace/python/output/"

# =====================================================
# Argumentos
# =====================================================
parser = argparse.ArgumentParser(
    description="Gera contingencia binaria e skill scores do MONAN.",
    formatter_class=argparse.RawTextHelpFormatter
)

parser.add_argument("ANO", type=str)
parser.add_argument("MES", type=str)
parser.add_argument("DIA", type=str)
parser.add_argument("HORA", type=str)
parser.add_argument("PRAZO_H", type=int)
parser.add_argument("P_LIMIAR", type=int)

# Argumentos dos caminhos de entrada e saída
parser.add_argument('NETCDF_PATH', type=str, help='Caminho base para os arquivos de comparação (NetCDF)')
parser.add_argument('OUTPUT_PATH', type=str, help='Caminho base para os arquivos de saída (imagens e NetCDF)')

args = parser.parse_args()

# Processamento dos caminhos de entrada e saída
NETCDF_PATH = Path(args.NETCDF_PATH)
OUTPUT_PATH = Path(args.OUTPUT_PATH)

data_ini = datetime.datetime(
    int(args.ANO),
    int(args.MES),
    int(args.DIA),
    int(args.HORA)
)

prazo_total = args.PRAZO_H

lead_times = range(24, prazo_total + 1, 24)

data_ini_str = data_ini.strftime("%Y%m%d%H")

anoMes = data_ini.strftime("%Y%m")

# Parametros
THRESHOLD_MM = args.P_LIMIAR

# Diretorio de saida
txt_dir = f"{OUTPUT_PATH}/Skill/Skill_txt_thr{int(THRESHOLD_MM)}mm/{anoMes}/{data_ini_str}"

os.makedirs(txt_dir, exist_ok=True)

# Regioes
sl_AMS = dict(lat=slice(-55, 20), lon=slice(275, 340))
sl_ACC = dict(lat=slice(-10, 35), lon=slice(242, 335))

regioes = {
    "GLB": {
        "slice": None,
        "txt": f"{txt_dir}/"
               f"Skill_scores_MONAN_GLB_{data_ini_str}_thr{int(THRESHOLD_MM)}mm.txt"
    },
    "AMS": {
        "slice": sl_AMS,
        "txt": f"{txt_dir}/"
               f"Skill_scores_MONAN_AMS_{data_ini_str}_thr{int(THRESHOLD_MM)}mm.txt"
    },
    "ACC": {
        "slice": sl_ACC,
        "txt": f"{txt_dir}/"
               f"Skill_scores_MONAN_ACC_{data_ini_str}_thr{int(THRESHOLD_MM)}mm.txt"
    }
}

# Valores de referencia ideais dos indices
SKILL_REF = {
    "ACC":  1.0,
    "POD":  1.0,
    "POFD": 0.0,
    "FAR":  0.0,
    "CSI":  1.0,
    "F1":   1.0,
}

# Funcoes
def remap_cdo(obs_nc, out_nc, ref_nc):
    if not os.path.exists(out_nc):
        subprocess.run(
            ["cdo", "-f", "nc", f"-remapcon,{ref_nc}", obs_nc, out_nc],
            check=True
        )


def contingencia_binaria(prev, obs, limiar):
    prev_evt = prev >= limiar
    obs_evt  = obs  >= limiar

# Hits H -> (previsto=1, observado=1)
# Misses M -> (previsto=0, observado=1)
# False Positive -> (previsto=1, observado=0)
# True Negative -> (previsto=0, observado=0)

    H = (prev_evt & obs_evt)
    M = (~prev_evt & obs_evt)
    F = (prev_evt & ~obs_evt)
    C = (~prev_evt & ~obs_evt)

    return H, M, F, C


def skill_agregado(H, M, F, C, slc=None):
    if slc is not None:
        H = H.sel(**slc)
        M = M.sel(**slc)
        F = F.sel(**slc)
        C = C.sel(**slc)

    Hn = H.sum().item()
    Mn = M.sum().item()
    Fn = F.sum().item()
    Cn = C.sum().item()

    total = Hn + Mn + Fn + Cn

    acc  = (Hn + Cn) / total if total > 0 else np.nan
    pod  = Hn / (Hn + Mn) if (Hn + Mn) > 0 else np.nan
    pofd = Fn / (Fn + Cn) if (Fn + Cn) > 0 else np.nan
    far  = Fn / (Hn + Fn) if (Hn + Fn) > 0 else np.nan
    csi  = Hn / (Hn + Mn + Fn) if (Hn + Mn + Fn) > 0 else np.nan
    f1   = (2 * Hn) / (2 * Hn + Fn + Mn) if (2 * Hn + Fn + Mn) > 0 else np.nan

    return acc, pod, pofd, far, csi, f1

for reg, info in regioes.items():
    if not os.path.exists(info["txt"]):
        with open(info["txt"], "w") as f:
            f.write("# Skill Scores MONAN\n")
            f.write(f"# Regiao = {reg}\n")
            f.write(f"# Threshold = {THRESHOLD_MM} mm / 24h\n")
            f.write(f"# Ciclo = {data_ini_str}\n\n")

            f.write("# Valores de referencia ideais\n")
            f.write(
                "# "
                f"ACC_best={SKILL_REF['ACC']}  "
                f"POD_best={SKILL_REF['POD']}  "
                f"POFD_best={SKILL_REF['POFD']}  "
                f"FAR_best={SKILL_REF['FAR']}  "
                f"CSI_best={SKILL_REF['CSI']}  "
                f"F1_best={SKILL_REF['F1']}\n\n"
            )

            header = (
                f"{'LEAD':^6}"
                f"{'REF':^8}"
                f"{'ACC':^8}"
                f"{'POD':^8}"
                f"{'POFD':^8}"
                f"{'FAR':^8}"
                f"{'CSI':^8}"
                f"{'F1':^8}\n"
            )
            f.write(header)
            f.write("-" * len(header) + "\n")

# =====================================================
# Loop de previsao
# =====================================================
for lead in lead_times:

    print(f"Processando lead time: {lead} h")

    data_fim = data_ini + datetime.timedelta(hours=lead)
    data_fim_str = data_fim.strftime("%Y%m%d%H")

    ciclo_str = data_ini_str

    monan_nc = (
        f"{OUTPUT_PATH}"
        f"/MONAN/{ciclo_str}/"
        f"MONAN_Precipitation_24h_acum_{data_ini_str}_{data_fim_str}_{lead:03d}h.nc"
    )

    gpm_nc = (
        f"{NETCDF_PATH}"
        f"/GPM_IMERG/{data_fim_str}00/"
        f"GPM_IMERG_Precipitation_24h_accum_{data_fim_str}00.nc"
    )

    gsmap_nc = (
        f"{NETCDF_PATH}"
        f"/GSMAP/{data_fim_str}00/"
        f"GSMAP_Precipitation_24h_accum_{data_fim_str}00.nc"
    )

    mswep_nc = (
        f"{NETCDF_PATH}"
        f"/MSWEP/{data_fim_str}00/"
        f"MSWEP_Precipitation_24h_accum_{data_fim_str}00.nc"
    )

    #gpm_remap   = gpm_nc.replace(".nc", "_MONAN_grid.nc")
    #gsmap_remap = gsmap_nc.replace(".nc", "_MONAN_grid.nc")
    #mswep_remap = mswep_nc.replace(".nc", "_MONAN_grid.nc")

    gpm_remap = (
        f"{NETCDF_PATH}"
        f"/Remapped_30km/GPM_IMERG/{data_fim_str}00/"
        f"GPM_IMERG_Precipitation_24h_accum_{data_fim_str}00_MONAN_30km.nc"
    )

    gsmap_remap = (
        f"{NETCDF_PATH}"
        f"/Remapped_30km/GSMAP/{data_fim_str}00/"
        f"GSMAP_Precipitation_24h_accum_{data_fim_str}00_MONAN_30km.nc"
    )

    mswep_remap = (
        f"{NETCDF_PATH}"
        f"/Remapped_30km/MSWEP/{data_fim_str}00/"
        f"MSWEP_Precipitation_24h_accum_{data_fim_str}00_MONAN_30km.nc"
    )

    os.makedirs(os.path.dirname(gpm_remap), exist_ok=True)
    os.makedirs(os.path.dirname(gsmap_remap), exist_ok=True)
    os.makedirs(os.path.dirname(mswep_remap), exist_ok=True)

    remap_cdo(gpm_nc, gpm_remap, monan_nc)
    remap_cdo(gsmap_nc, gsmap_remap, monan_nc)
    remap_cdo(mswep_nc, mswep_remap, monan_nc)

    monan = xr.open_dataset(monan_nc)["prec"]
    gpm   = xr.open_dataset(gpm_remap)["prec"]
    gsmap = xr.open_dataset(gsmap_remap)["prec"]
    mswep = xr.open_dataset(mswep_remap)["prec"]

    # Contingencia binaria
    H_gpm,   M_gpm,   F_gpm,   C_gpm   = contingencia_binaria(monan, gpm, THRESHOLD_MM)
    H_gsmap, M_gsmap, F_gsmap, C_gsmap = contingencia_binaria(monan, gsmap, THRESHOLD_MM)
    H_mswep, M_mswep, F_mswep, C_mswep = contingencia_binaria(monan, mswep, THRESHOLD_MM)

    # Escrita do TXT
    for reg, info in regioes.items():

       slc = info["slice"]
       txt_out = info["txt"]

       with open(txt_out, "a") as f:

          for ref, H, M, F_, C_ in [
            ("GPM",   H_gpm,   M_gpm,   F_gpm,   C_gpm),
            ("GSMAP", H_gsmap, M_gsmap, F_gsmap, C_gsmap),
            ("MSWEP", H_mswep, M_mswep, F_mswep, C_mswep),
          ]:
             acc, pod, pofd, far, csi, f1 = skill_agregado(H, M, F_, C_, slc)

             f.write(
                f"{str(lead).zfill(3):^6}"
                f"{ref:^8}"
                f"{acc:6.2f}"
                f"{pod:8.2f}"
                f"{pofd:8.2f}"
                f"{far:8.2f}"
                f"{csi:8.2f}"
                f"{f1:8.2f}\n"
             )
            
    # NetCDF de contingencia
    ds_out = xr.Dataset(
        {
            "H_GPM":    H_gpm.astype("int8"),
            "M_GPM":    M_gpm.astype("int8"),
            "F_GPM":    F_gpm.astype("int8"),
            "C_GPM":    C_gpm.astype("int8"),

            "H_GSMAP":  H_gsmap.astype("int8"),
            "M_GSMAP":  M_gsmap.astype("int8"),
            "F_GSMAP":  F_gsmap.astype("int8"),
            "C_GSMAP":  C_gsmap.astype("int8"),

            "H_MSWEP":  H_mswep.astype("int8"),
            "M_MSWEP":  M_mswep.astype("int8"),
            "F_MSWEP":  F_mswep.astype("int8"),
            "C_MSWEP":  C_mswep.astype("int8"),
        },
        coords={
            "lat": monan.lat,
            "lon": monan.lon
        },
        attrs={
            "threshold_mm": THRESHOLD_MM,
            "lead_time_h": lead,
            "descricao": "Contingencia binaria de precipitacao 24h MONAN"
        }
    )

    out_dir = Path(
        f"{OUTPUT_PATH}/precip_24h/CONTINGENCIA/{data_ini_str}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    ds_out.to_netcdf(
        out_dir / f"CONT_MONAN_{data_ini_str}_{lead:03d}h_thr{int(THRESHOLD_MM)}mm.nc",
        format="NETCDF4"
    )
