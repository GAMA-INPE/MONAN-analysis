# Plot_Series_Heatmap_skill_score_MONAN_BAM_GFS.py
#
# Purpose
# -------
# This script reads monthly aggregated skill score tables (TXT files)
# generated from contingency statistics and produces diagnostic plots
# for forecast verification analysis.
#
# The script generates:
#   1) Skill score vs lead time curves (per threshold)
#   2) Skill score vs precipitation threshold curves (per lead time)
#   3) Heatmaps (Lead time × Threshold) for spatial visualization
#   4) Combined comparison plots (models × references)
#
# Input
# -----
# Aggregated TXT files produced by:
#   Mean_Skill_score_MONAN_BAM_GFS.py
#
# Output
# ------
# Figures saved in:
#   ./Skill_fig_mensal/
#       ├── skill_vs_lead/
#       ├── skill_vs_threshold/
#       └── heatmap_lead_threshold/
#
# Configurable Parameters
# -----------------------
# PERIODO         → YYYYMM (analysis month)
# REGIAO_ANALISE  → GLB, AMS, or ACC
# METRICAS_PRINCIPAIS → Skill indices to analyze
#
# Notes
# -----
# This script performs statistical visualization only.
# It does not recompute skill scores or read NetCDF data.
#
# Author: Original implementation by Andre Lyra

import argparse
from pathlib import Path
import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.ticker as mticker

# ==========================================================
# ARGUMENTOS
# ==========================================================

parser = argparse.ArgumentParser(
    description="Gera figuras de bias medio para um mes especifico.",
    formatter_class=argparse.RawTextHelpFormatter
)

parser.add_argument("ANO", type=str)
parser.add_argument("MES", type=str)
parser.add_argument('REGION', type=str, choices=["GLB", "AMS", "ACC"], help='Região geográfica para análise (GLB, AMS ou ACC)')
parser.add_argument('ANALYSIS_NAME', type=str, help='Nome do conjunto de analises (ex: monthly_means, 10_days_means, etc.)')
parser.add_argument('OUTPUT_PATH', type=str, help='Caminho base para os arquivos de saída (imagens e NetCDF)')

args = parser.parse_args()

ANO = int(args.ANO)
MES = int(args.MES)
REGIAO_ANALISE = args.REGION
ANALYSIS_NAME = args.ANALYSIS_NAME
OUTPUT_PATH = Path(args.OUTPUT_PATH)

# Input / Output directories and parameters
#BASE_SKILL_DIR = "/home2/eduardo.eras/workspace/python/output/Skill/10_days"
BASE_SKILL_DIR = f"{OUTPUT_PATH}/Skill/{ANALYSIS_NAME}"
BASE_OUT_DIR = BASE_SKILL_DIR + "/Skill_fig_mensal"

PERIODO = str(ANO) + str(MES)

REFERENCIAS = ["GPM", "GSMAP", "MSWEP"]
METRICAS_PRINCIPAIS = ["ETS", "CSI", "POD", "F1", "F05"]

os.makedirs(BASE_OUT_DIR, exist_ok=True)

#DIR_21 = f"/pesq/share/monan/monan_gam/precip_24h/Skill/"
DIR_21 = f"{BASE_OUT_DIR}/skill_vs_lead"
DIR_22 = f"{BASE_OUT_DIR}/skill_vs_threshold"
DIR_23 = f"{BASE_OUT_DIR}/heatmap_lead_threshold"

os.makedirs(DIR_21, exist_ok=True)
os.makedirs(DIR_22, exist_ok=True)
os.makedirs(DIR_23, exist_ok=True)

CORES_MODELO = {
    "MONAN": "red",
    "BAM": "green",
    "GFS": "black"
}

ESTILO_REF = {
    "GPM":   {"linestyle": "-",  "marker": "o"},
    "GSMAP": {"linestyle": "--", "marker": "s"},
    "MSWEP": {"linestyle": ":",  "marker": "^"}
}

ORDEM_MODELOS = ["MONAN", "BAM", "GFS"]

# Leitura da tabelas txt
arquivos = glob.glob(
    f"{BASE_SKILL_DIR}/Skill_txt_thr*/{PERIODO}/{PERIODO}_aggregated/Skill_*.txt")

#Debug output to verify files being read
print("Searching in:", BASE_SKILL_DIR)
print("PERIODO:", PERIODO)
print("Number of TXT files found:", len(arquivos))

#for a in arquivos[:5]:
#    print("  →", a)

##################################################

registros = []

for arq in arquivos:
    nome = os.path.basename(arq)

    m = re.match(
        r"Skill_(\w+)_(\w+)_" + PERIODO + r"_thr(\d+)mm.txt",
        nome
    )
    if not m:
        continue

    modelo = m.group(1)
    regiao = m.group(2)
    threshold = int(m.group(3))

    with open(arq) as f:
        linhas = f.readlines()

    for i, l in enumerate(linhas):
        if l.strip().startswith("LEAD"):
            inicio = i + 2
            break

    for l in linhas[inicio:]:
        if not l.strip():
            continue

        p = l.split()
        lead = int(p[0])
        ref = p[1]

        metricas = {
            "ACC":  float(p[2]),
            "POD":  float(p[3]),
            "POFD": float(p[4]),
            "FAR":  float(p[5]),
            "CSI":  float(p[6]),
            "F1":   float(p[7]),
            "F05":  float(p[8]),
            "ETS":  float(p[9]),
        }

        for metrica, valor in metricas.items():
            registros.append({
                "modelo": modelo,
                "regiao": regiao,
                "referencia": ref,
                "threshold_mm": threshold,
                "lead_h": lead,
                "metrica": metrica,
                "valor": valor,
                "periodo": PERIODO
            })

df = pd.DataFrame(registros)

# Skill versus prazo
for metrica in METRICAS_PRINCIPAIS:
    print(f"\nSkill versus prazo - Processing metric: {metrica}")
    for ref in REFERENCIAS:
        for thr in sorted(df.threshold_mm.unique()):
            DIR_21_thr=f"{DIR_21}/Skill_fig_thr{thr}mm/{PERIODO}"
            os.makedirs(DIR_21_thr, exist_ok=True)
            dfp = df[
                (df.metrica == metrica) &
                (df.threshold_mm == thr) &
                (df.regiao == REGIAO_ANALISE) &
                (df.referencia == ref)
            ]

            if dfp.empty:
                continue

            plt.figure(figsize=(8, 5))

            for modelo, d in sorted(
                dfp.groupby("modelo"),
                key=lambda x: ORDEM_MODELOS.index(x[0])
            ):
                plt.plot(
                    d.lead_h,
                    d.valor,
                    marker="o",
                    color=CORES_MODELO.get(modelo, "gray"),
                    label=modelo
                )
                #plt.plot(d.lead_h, d.valor, marker="o", label=modelo)
            
            leads = sorted(dfp.lead_h.unique())
            plt.xticks(leads)
            
            plt.xlabel("Lead time (h)")
            plt.ylabel(metrica)
            plt.gca().yaxis.set_major_formatter(
                mticker.FormatStrFormatter("%.2f")
            )
            plt.title(
                f"{metrica} versus lead time | thr {thr} mm | "
                f"{REGIAO_ANALISE} | {ref}"
            )
            plt.legend()
            plt.grid(True)

            out = (
                f"{DIR_21_thr}/{metrica}_vs_lead_thr{thr}mm_"
                f"{REGIAO_ANALISE}_{ref}.png"
            )
            plt.savefig(out, dpi=150, bbox_inches="tight")
            plt.close()

# Skill versus limiar
for metrica in METRICAS_PRINCIPAIS:
    print(f"\nSkill versus limiar - Processing metric: {metrica}")
    for ref in REFERENCIAS:
        for lead in sorted(df.lead_h.unique()):
            dfp = df[
                (df.metrica == metrica) &
                (df.lead_h == lead) &
                (df.regiao == REGIAO_ANALISE) &
                (df.referencia == ref)
            ]

            if dfp.empty:
                continue

            plt.figure(figsize=(8, 5))
            
            thresholds = sorted(dfp.threshold_mm.unique())
            xpos = np.arange(len(thresholds))
            
            for modelo, d in sorted(
                dfp.groupby("modelo"),
                key=lambda x: ORDEM_MODELOS.index(x[0])
            ):
                d = d.sort_values("threshold_mm")
                x = [thresholds.index(t) for t in d.threshold_mm]
                plt.plot(
                    x,
                    d.valor,
                    marker="o",
                    color=CORES_MODELO.get(modelo, "gray"),
                    label=modelo
                )
                #plt.plot(d.threshold_mm, d.valor, marker="o", label=modelo)
       
            plt.xticks(xpos, thresholds)
           
            plt.xlabel("Threshold (mm / 24 h)")
            plt.ylabel(metrica)
            plt.gca().yaxis.set_major_formatter(
                mticker.FormatStrFormatter("%.2f")
            )
            plt.title(
                f"{metrica} versus threshold | lead {lead} h | "
                f"{REGIAO_ANALISE} | {ref}"
            )
            plt.legend()
            plt.grid(True)

            out = (
                f"{DIR_22}/{metrica}_vs_threshold_lead{lead}h_"
                f"{REGIAO_ANALISE}_{ref}.png"
            )
            plt.savefig(out, dpi=150, bbox_inches="tight")
            plt.close()

# Heatmaps 
for metrica in METRICAS_PRINCIPAIS:
    print(f"\nHeatmaps - Processing metric: {metrica}")
    # DataFrame global da métrica para o domínio
    dfm_all = df[
        (df.metrica == metrica) &
        (df.regiao == REGIAO_ANALISE)
    ]

    if dfm_all.empty:
        continue

    # Limites globais da barra de cores
    vmin = dfm_all.valor.min()
    vmax = dfm_all.valor.max()

    # Opcional, arredondar o vmax para facilitar comparação visual
    vmax = np.ceil(vmax * 10) / 10
    vmin = 0.0

    for ref in REFERENCIAS:
        dfm = dfm_all[dfm_all.referencia == ref]

        if dfm.empty:
            continue

        for modelo in dfm.modelo.unique():

            dfp = dfm[dfm.modelo == modelo]

            tabela = dfp.pivot_table(
                index="lead_h",
                columns="threshold_mm",
                values="valor"
            )

            plt.figure(figsize=(8, 6))

            im = plt.imshow(
                tabela,
                origin="lower",
                aspect="auto",
                vmin=vmin,
                vmax=vmax
            )

            plt.colorbar(im, label=metrica)

            plt.xticks(range(len(tabela.columns)), tabela.columns)
            plt.yticks(range(len(tabela.index)), tabela.index)

            plt.xlabel("Precipitation threshold (mm / 24 h)")
            plt.ylabel("Lead time (h)")
            plt.title(
                f"{metrica} Heatmap | {modelo} | {REGIAO_ANALISE} | {ref}"
            )

            # Escrita dos valores
            for i, lead in enumerate(tabela.index):
                for j, thr in enumerate(tabela.columns):
                    valor = tabela.loc[lead, thr]
                    if np.isfinite(valor):
                        plt.text(
                            j,
                            i,
                            f"{valor:.2f}",
                            ha="center",
                            va="center",
                            fontsize=14,
                            color="white" if valor < (vmin + vmax) / 2 else "black"
                        )

            out = (
                f"{DIR_23}/heatmap_{metrica}_{modelo}_"
                f"{REGIAO_ANALISE}_{ref}.png"
            )

            plt.savefig(out, dpi=150, bbox_inches="tight")
            plt.close()


# Skill versus limiar com todas as referências
for metrica in METRICAS_PRINCIPAIS:
    print(f"\nSkill versus limiar com todas as referências - Processing metric: {metrica}")
    for lead in sorted(df.lead_h.unique()):

        dfp = df[
            (df.metrica == metrica) &
            (df.lead_h == lead) &
            (df.regiao == REGIAO_ANALISE)
        ]

        if dfp.empty:
            continue

        plt.figure(figsize=(9, 6))

        for modelo in dfp.modelo.unique():
            for ref in REFERENCIAS:
                d = dfp[
                    (dfp.modelo == modelo) &
                    (dfp.referencia == ref)
                ].sort_values("threshold_mm")

                if d.empty:
                    continue
    
                thresholds = sorted(dfp.threshold_mm.unique())
                xpos = np.arange(len(thresholds))
                x = [thresholds.index(t) for t in d.threshold_mm]

                plt.plot(
                    x,
                    d.valor,
                    color=CORES_MODELO.get(modelo, "gray"),
                    linestyle=ESTILO_REF[ref]["linestyle"],
                    marker=ESTILO_REF[ref]["marker"],
                    label=f"{modelo} {ref}"
                )

        plt.xticks(xpos, thresholds)
	
        plt.xlabel("Precipitation threshold (mm / 24 h)")
        plt.ylabel(metrica)
        plt.gca().yaxis.set_major_formatter(
            mticker.FormatStrFormatter("%.2f")
        )
        plt.title(
            f"{metrica} vs threshold | lead {lead} h | "
            f"{REGIAO_ANALISE}"
        )

        plt.legend(ncol=3, fontsize=9)
        plt.grid(True)

        out = (
            f"{BASE_OUT_DIR}/skill_vs_threshold/"
            f"{metrica}_vs_threshold_all_models_refs_"
            f"lead{lead}h_{REGIAO_ANALISE}.png"
        )
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()

print("\nFim do Script.\n")