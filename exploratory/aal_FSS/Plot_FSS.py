#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plota os resultados mensais do Fractions Skill Score, FSS.

O script gera:
    1. Um heatmap individual para cada limiar.
    2. Um painel 3 x 2 com os seis limiares e uma única barra de cores.

Exemplos:
    python Plot_FSS.py --period 202601
    python Plot_FSS.py --period 202601 --models MONAN
    python Plot_FSS.py --period 202601 --references MSWEP GSMAP
    python Plot_FSS.py --period 202601 --domains AMS
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm

from FSS_config import (
    OUTDIR_FSS,
    MODELOS,
    REFERENCIAS,
    THRESHOLDS,
    DOMINIOS,
    TARGET_GRID,
    REGRID_METHOD,
    USE_PRECOMPUTED_REMAPCON,
)

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = Path("/pesq/share/monan/monan_gam/precip_24h/")
OUTDIR_FIG_BASE = OUT_DIR / "FSS"
#OUTDIR_FIG_BASE = SCRIPT_DIR / "Fig_FSS"

LEVELS = np.arange(0.0, 1.05, 0.05)
CMAP = plt.get_cmap("RdYlGn", len(LEVELS) - 1)
NORM = BoundaryNorm(
    LEVELS,
    ncolors=CMAP.N,
    clip=True,
)


def valida_configuracao_grade():
    if TARGET_GRID is not None and TARGET_GRID not in MODELOS:
        raise ValueError(
            "TARGET_GRID deve ser None ou um modelo presente em MODELOS. "
            f"Valor recebido: {TARGET_GRID!r}."
        )

    if (
        TARGET_GRID is not None
        and not USE_PRECOMPUTED_REMAPCON
        and REGRID_METHOD not in {"linear", "nearest"}
    ):
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


def descricao_grade():
    if TARGET_GRID is None:
        return "independent model grids"

    if USE_PRECOMPUTED_REMAPCON:
        return f"common {TARGET_GRID} grid, conservative remapping"

    return f"common {TARGET_GRID} grid, {REGRID_METHOD} interpolation"


def diretorio_csv(periodo, modelo, referencia):
    if TARGET_GRID is None:
        return OUTDIR_FSS / periodo / modelo / referencia

    return (
        OUTDIR_FSS
        / modo_grade()
        / periodo
        / modelo
        / referencia
    )


def diretorio_figuras(periodo):
    if TARGET_GRID is None:
        return OUTDIR_FIG_BASE / periodo

    return OUTDIR_FIG_BASE / modo_grade() / periodo


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Plota os heatmaps mensais de FSS para modelos, "
            "referências e domínios selecionados."
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
        help="Modelos a plotar ou all. Padrão: all.",
    )

    parser.add_argument(
        "--references",
        nargs="+",
        default=["all"],
        help="Referências a plotar ou all. Padrão: all.",
    )

    parser.add_argument(
        "--domains",
        nargs="+",
        default=["all"],
        help="Domínios a plotar ou all. Padrão: all.",
    )

    parser.add_argument(
        "--skip-individual",
        action="store_true",
        help="Não gera os heatmaps individuais.",
    )

    parser.add_argument(
        "--skip-panel",
        action="store_true",
        help="Não gera o painel 3 x 2.",
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


def draw_step_boundary(
    ax,
    z_values,
    threshold=0.5,
    color="black",
    linewidth=0.75,
):
    """
    Desenha uma linha em degraus na fronteira entre células abaixo
    e acima do valor limite.
    """

    valid = np.isfinite(z_values)

    if not np.any(valid):
        return

    mask = np.zeros_like(z_values, dtype=bool)
    mask[valid] = z_values[valid] >= threshold

    ny, nx = mask.shape
    x_edges = np.arange(nx + 1)
    y_edges = np.arange(ny + 1)

    for i in range(ny):
        for j in range(nx - 1):
            if not (
                valid[i, j]
                and valid[i, j + 1]
            ):
                continue

            if mask[i, j] != mask[i, j + 1]:
                x = x_edges[j + 1]
                y0 = y_edges[i]
                y1 = y_edges[i + 1]

                ax.plot(
                    [x, x],
                    [y0, y1],
                    color=color,
                    linewidth=linewidth,
                    linestyle="--",
                )

    for i in range(ny - 1):
        for j in range(nx):
            if not (
                valid[i, j]
                and valid[i + 1, j]
            ):
                continue

            if mask[i, j] != mask[i + 1, j]:
                y = y_edges[i + 1]
                x0 = x_edges[j]
                x1 = x_edges[j + 1]

                ax.plot(
                    [x0, x1],
                    [y, y],
                    color=color,
                    linewidth=linewidth,
                    linestyle="--",
                )


def prepara_tabela(
    df,
    dominio,
    threshold,
):
    subset = df[
        (df["dominio"] == dominio)
        & np.isclose(
            df["threshold_mm"].astype(float),
            float(threshold),
        )
    ].copy()

    if subset.empty:
        return None, None

    tabela = subset.pivot(
        index="window_points",
        columns="lead",
        values="fss",
    )

    tabela = tabela.sort_index().sort_index(axis=1)

    escala_km = (
        subset.groupby("window_points")["window_lat_km"]
        .median()
        .reindex(tabela.index)
    )

    return tabela, escala_km


def rotulos_vizinhanca(tabela, escala_km):
    labels = []

    for window_size in tabela.index:
        km = escala_km.loc[window_size]

        if np.isfinite(km):
            labels.append(
                f"{int(window_size)} pts\n~{km:.0f} km"
            )
        else:
            labels.append(f"{int(window_size)} pts")

    return labels


def desenha_heatmap(
    ax,
    tabela,
    escala_km,
    mostrar_titulo=True,
    titulo=None,
):
    z_values = tabela.values.astype(float)
    ny, nx = z_values.shape

    x_edges = np.arange(nx + 1)
    y_edges = np.arange(ny + 1)

    x_centers = np.arange(nx) + 0.5
    y_centers = np.arange(ny) + 0.5

    im = ax.pcolormesh(
        x_edges,
        y_edges,
        z_values,
        cmap=CMAP,
        norm=NORM,
        shading="flat",
    )

    valid = z_values[np.isfinite(z_values)]

    if (
        valid.size > 0
        and np.nanmin(valid) < 0.5
        and np.nanmax(valid) >= 0.5
    ):
        draw_step_boundary(
            ax=ax,
            z_values=z_values,
            threshold=0.5,
        )

    ax.set_xticks(x_centers)
    ax.set_xticklabels(
        [f"{int(value):03d}" for value in tabela.columns]
    )

    ax.set_yticks(y_centers)
    ax.set_yticklabels(
        rotulos_vizinhanca(
            tabela=tabela,
            escala_km=escala_km,
        )
    )

    ax.set_xlim(0, nx)
    ax.set_ylim(0, ny)

    ax.set_xlabel("Lead time (h)")
    ax.set_ylabel(
        "Neighbourhood size\n"
        f"({descricao_grade()}; meridional scale)"
    )

    if mostrar_titulo and titulo:
        ax.set_title(titulo)

    return im


def salva_heatmap_individual(
    df,
    periodo,
    modelo,
    referencia,
    dominio,
    threshold,
    outdir,
):
    tabela, escala_km = prepara_tabela(
        df=df,
        dominio=dominio,
        threshold=threshold,
    )

    if tabela is None or tabela.empty:
        print(
            f"Sem dados para {modelo} vs {referencia}, "
            f"{dominio}, threshold {threshold:g} mm."
        )
        return

    fig, ax = plt.subplots(
        figsize=(10, 5.5),
        constrained_layout=True,
    )

    titulo = (
        f"FSS | {modelo} vs {referencia} | "
        f"{periodo} | Thr {threshold:g} mm | {dominio} | "
        f"{descricao_grade()}"
    )

    im = desenha_heatmap(
        ax=ax,
        tabela=tabela,
        escala_km=escala_km,
        mostrar_titulo=True,
        titulo=titulo,
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
        boundaries=LEVELS,
        ticks=np.arange(0.0, 1.01, 0.1),
        spacing="proportional",
    )
    cbar.set_label("FSS")

    outpng = (
        outdir
        / (
            f"FSS_heatmap_{modelo}_vs_{referencia}_"
            f"{dominio}_{periodo}_thr{int(threshold)}mm.png"
        )
    )

    fig.savefig(
        outpng,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    print(f"Figura salva em: {outpng}")


def salva_painel(
    df,
    periodo,
    modelo,
    referencia,
    dominio,
    outdir,
):
    fig, axes = plt.subplots(
        nrows=2,
        ncols=3,
        figsize=(19, 10),
        constrained_layout=True,
    )

    ultimo_im = None
    n_paineis = 0

    for ax, threshold in zip(
        axes.flat,
        THRESHOLDS,
    ):
        tabela, escala_km = prepara_tabela(
            df=df,
            dominio=dominio,
            threshold=threshold,
        )

        if tabela is None or tabela.empty:
            ax.set_visible(False)
            continue

        ultimo_im = desenha_heatmap(
            ax=ax,
            tabela=tabela,
            escala_km=escala_km,
            mostrar_titulo=True,
            titulo=f"Threshold: {threshold:g} mm",
        )

        n_paineis += 1

    if n_paineis == 0:
        plt.close(fig)
        print(
            f"Sem dados para o painel {modelo} vs "
            f"{referencia}, {dominio}."
        )
        return

    fig.suptitle(
        f"FSS | {modelo} vs {referencia} | "
        f"{periodo} | {dominio} | {descricao_grade()}",
        fontsize=16,
    )

    cbar = fig.colorbar(
        ultimo_im,
        ax=axes.ravel().tolist(),
        boundaries=LEVELS,
        ticks=np.arange(0.0, 1.01, 0.1),
        spacing="proportional",
        fraction=0.025,
        pad=0.02,
    )
    cbar.set_label("FSS")

#    fig.text(
#        0.5,
#        0.005,
#        (
#            "Approximate kilometre values use the median meridional "
#            "grid spacing of each model within the domain."
#        ),
#        ha="center",
#        fontsize=9,
#    )

    outpng = (
        outdir
        / (
            f"FSS_{modelo}_vs_{referencia}_"
            f"{dominio}_{periodo}.png"
        )
    )

    fig.savefig(
        outpng,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    print(f"Painel salvo em: {outpng}")


def main():
    args = parse_args()
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

    periodo = args.period

    for modelo in modelos:
        for referencia in referencias:
            csv_file = (
                diretorio_csv(
                    periodo=periodo,
                    modelo=modelo,
                    referencia=referencia,
                )
                / (
                    f"FSS_monthly_{modelo}_vs_"
                    f"{referencia}_{periodo}.csv"
                )
            )

            if not csv_file.exists():
                print(f"Arquivo não encontrado: {csv_file}")
                continue

            df = pd.read_csv(csv_file)

            outdir = diretorio_figuras(periodo)
            outdir.mkdir(
                parents=True,
                exist_ok=True,
            )

            for dominio in dominios:
                if not args.skip_individual:
                    for threshold in THRESHOLDS:
                        salva_heatmap_individual(
                            df=df,
                            periodo=periodo,
                            modelo=modelo,
                            referencia=referencia,
                            dominio=dominio,
                            threshold=float(threshold),
                            outdir=outdir,
                        )

                if not args.skip_panel:
                    salva_painel(
                        df=df,
                        periodo=periodo,
                        modelo=modelo,
                        referencia=referencia,
                        dominio=dominio,
                        outdir=outdir,
                    )


if __name__ == "__main__":
    main()