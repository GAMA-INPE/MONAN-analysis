#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plota os resultados mensais do Fractions Skill Score, FSS, para
MONAN Regional, WRF e MONAN Global na grade comum do MONAN Global.

O script gera:
    1. Um heatmap individual para cada limiar.
    2. Um painel 2 x 3 com os seis limiares e uma unica barra de cores.

Exemplos:
    python Plot_FSS_MONAN_Regional_WRF.py --period 202607

    python Plot_FSS_MONAN_Regional_WRF.py \
        --period 202607 \
        --models MONAN_Regional

    python Plot_FSS_MONAN_Regional_WRF.py \
        --period 202607 \
        --references GPM_IMERG MSWEP

    python Plot_FSS_MONAN_Regional_WRF.py \
        --period 202607 \
        --skip-individual
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm


# =============================================================================
# CONFIGURACAO
# =============================================================================

BASE_PRECIP = Path(
    "/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h"
)

OUTDIR_FSS = (
    BASE_PRECIP
    / "FSS_Regional_WRF"
    / "MONAN_Global_grid"
)

OUTDIR_FIG_BASE = Path(
    "/pesq/share/monan/monan_gam/precip_24h/FSS_MONAN_Regional"
) 

MODELS = (
    "MONAN_Regional",
    "WRF",
    "MONAN_Global",
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

DOMAIN = "REG_WRF_MASKED"

TARGET_GRID = "MONAN_Global_grid"

REGRID_METHOD = "remapcon"

MODEL_LABELS = {
    "MONAN_Regional": "MONAN Regional",
    "WRF": "WRF",
    "MONAN_Global": "MONAN Global",
}

REFERENCE_LABELS = {
    "GPM_IMERG": "GPM IMERG",
    "GSMAP": "GSMaP",
    "MSWEP": "MSWEP",
}

LEVELS = np.arange(
    0.0,
    1.05,
    0.05,
)

CMAP = plt.get_cmap(
    "RdYlGn",
    len(LEVELS) - 1,
)

NORM = BoundaryNorm(
    LEVELS,
    ncolors=CMAP.N,
    clip=True,
)


# =============================================================================
# ARGUMENTOS
# =============================================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Plota os heatmaps mensais de FSS para "
            "MONAN Regional, WRF e MONAN Global na grade do MONAN Global."
        )
    )

    parser.add_argument(
        "--period",
        required=True,
        help=(
            "Periodo no formato YYYYMM, "
            "por exemplo 202607."
        ),
    )

    parser.add_argument(
        "--models",
        nargs="+",
        default=["all"],
        help=(
            "MONAN_Regional, WRF, MONAN_Global ou all. "
            "Padrao: all."
        ),
    )

    parser.add_argument(
        "--references",
        nargs="+",
        default=["all"],
        help=(
            "GPM_IMERG, GSMAP, MSWEP ou all. "
            "Padrao: all."
        ),
    )

    parser.add_argument(
        "--skip-individual",
        action="store_true",
        help=(
            "Nao gera os heatmaps individuais."
        ),
    )

    parser.add_argument(
        "--skip-panel",
        action="store_true",
        help=(
            "Nao gera o painel 2 x 3."
        ),
    )

    return parser.parse_args()


def select_options(
    choices,
    available,
    name,
):

    lookup = {
        item.upper(): item
        for item in available
    }

    choices_upper = [
        item.upper()
        for item in choices
    ]

    if "ALL" in choices_upper:
        return list(
            available
        )

    invalid = [
        item
        for item in choices_upper
        if item not in lookup
    ]

    if invalid:
        raise ValueError(
            f"{name} invalido(s): {invalid}. "
            f"Opcoes disponiveis: "
            f"{list(available)}"
        )

    return [
        lookup[item]
        for item in choices_upper
    ]


# =============================================================================
# CAMINHOS E VALIDACAO
# =============================================================================

def monthly_csv_path(
    period,
    model,
    reference,
):

    filename = (
        f"FSS_monthly_"
        f"{model}_vs_"
        f"{reference}_"
        f"{period}_"
        f"{DOMAIN}_"
        f"{TARGET_GRID}.csv"
    )

    return (
        OUTDIR_FSS
        / period
        / model
        / reference
        / filename
    )


def figure_directory(
    period,
):

    return (
        OUTDIR_FIG_BASE
        / period
    )


def grid_description(
    model,
):

    if model == "MONAN_Global":

        return (
            "MONAN Global native target grid (~0.1 deg)"
        )

    return (
        "common MONAN Global grid (~0.1 deg), "
        "conservative remapping"
    )


def validate_dataframe(
    df,
    csv_file,
    model,
):

    required_columns = {
        "periodo",
        "modelo",
        "referencia",
        "dominio",
        "target_grid",
        "regrid_method_model",
        "lead",
        "threshold_mm",
        "window_points",
        "window_lat_km",
        "fss",
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "CSV sem colunas obrigatorias: "
            f"{sorted(missing)}\n"
            f"Arquivo: {csv_file}"
        )

    domains = set(
        df["dominio"]
        .dropna()
        .astype(str)
        .unique()
    )

    if domains != {DOMAIN}:
        raise ValueError(
            "Dominio inesperado no CSV. "
            f"Esperado: {DOMAIN}. "
            f"Encontrado: {sorted(domains)}. "
            f"Arquivo: {csv_file}"
        )

    target_grids = set(
        df["target_grid"]
        .dropna()
        .astype(str)
        .unique()
    )

    if target_grids != {TARGET_GRID}:
        raise ValueError(
            "Grade alvo inesperada no CSV. "
            f"Esperada: {TARGET_GRID}. "
            f"Encontrada: {sorted(target_grids)}. "
            f"Arquivo: {csv_file}"
        )

    methods = set(
        df["regrid_method_model"]
        .dropna()
        .astype(str)
        .unique()
    )

    expected_method = (
        MODEL_REGRID_METHOD[
            model
        ]
    )

    if methods != {expected_method}:
        raise ValueError(
            "Metodo de tratamento da grade inesperado no CSV. "
            f"Esperado para {model}: {expected_method}. "
            f"Encontrado: {sorted(methods)}. "
            f"Arquivo: {csv_file}"
        )


# =============================================================================
# HEATMAP
# =============================================================================

def draw_step_boundary(
    ax,
    z_values,
    threshold=0.5,
    color="black",
    linewidth=0.75,
):
    """
    Desenha uma linha em degraus na fronteira entre celulas abaixo
    e acima do valor limite.
    """

    valid = np.isfinite(
        z_values
    )

    if not np.any(
        valid
    ):
        return

    mask = np.zeros_like(
        z_values,
        dtype=bool,
    )

    mask[
        valid
    ] = (
        z_values[
            valid
        ]
        >= threshold
    )

    ny, nx = mask.shape

    x_edges = np.arange(
        nx + 1
    )

    y_edges = np.arange(
        ny + 1
    )

    for i in range(
        ny
    ):

        for j in range(
            nx - 1
        ):

            if not (
                valid[i, j]
                and valid[i, j + 1]
            ):
                continue

            if (
                mask[i, j]
                != mask[i, j + 1]
            ):

                x = x_edges[
                    j + 1
                ]

                y0 = y_edges[i]
                y1 = y_edges[
                    i + 1
                ]

                ax.plot(
                    [x, x],
                    [y0, y1],
                    color=color,
                    linewidth=linewidth,
                    linestyle="--",
                )

    for i in range(
        ny - 1
    ):

        for j in range(
            nx
        ):

            if not (
                valid[i, j]
                and valid[i + 1, j]
            ):
                continue

            if (
                mask[i, j]
                != mask[i + 1, j]
            ):

                y = y_edges[
                    i + 1
                ]

                x0 = x_edges[j]
                x1 = x_edges[
                    j + 1
                ]

                ax.plot(
                    [x0, x1],
                    [y, y],
                    color=color,
                    linewidth=linewidth,
                    linestyle="--",
                )


def prepare_table(
    df,
    threshold,
):

    subset = df[
        (
            df["dominio"]
            == DOMAIN
        )
        & np.isclose(
            df[
                "threshold_mm"
            ].astype(float),
            float(threshold),
        )
    ].copy()

    if subset.empty:
        return (
            None,
            None,
        )

    duplicates = subset.duplicated(
        subset=[
            "window_points",
            "lead",
        ],
        keep=False,
    )

    if duplicates.any():
        duplicated_rows = subset.loc[
            duplicates,
            [
                "window_points",
                "lead",
                "threshold_mm",
            ],
        ]

        raise ValueError(
            "Foram encontradas combinacoes "
            "duplicadas de window_points x lead:\n"
            f"{duplicated_rows}"
        )

    table = subset.pivot(
        index="window_points",
        columns="lead",
        values="fss",
    )

    table = (
        table
        .sort_index()
        .sort_index(
            axis=1
        )
    )

    scale_km = (
        subset
        .groupby(
            "window_points"
        )[
            "window_lat_km"
        ]
        .median()
        .reindex(
            table.index
        )
    )

    return (
        table,
        scale_km,
    )


def neighborhood_labels(
    table,
    scale_km,
):

    labels = []

    for window_size in table.index:

        km = scale_km.loc[
            window_size
        ]

        if np.isfinite(
            km
        ):

            labels.append(
                f"{int(window_size)} pts\n"
                f"~{km:.0f} km"
            )

        else:

            labels.append(
                f"{int(window_size)} pts"
            )

    return labels


def draw_heatmap(
    ax,
    table,
    scale_km,
    show_title=True,
    title=None,
):

    z_values = table.values.astype(
        float
    )

    ny, nx = (
        z_values.shape
    )

    x_edges = np.arange(
        nx + 1
    )

    y_edges = np.arange(
        ny + 1
    )

    x_centers = (
        np.arange(nx)
        + 0.5
    )

    y_centers = (
        np.arange(ny)
        + 0.5
    )

    im = ax.pcolormesh(
        x_edges,
        y_edges,
        z_values,
        cmap=CMAP,
        norm=NORM,
        shading="flat",
    )

    valid = z_values[
        np.isfinite(
            z_values
        )
    ]

    if (
        valid.size > 0
        and np.nanmin(
            valid
        ) < 0.5
        and np.nanmax(
            valid
        ) >= 0.5
    ):

        draw_step_boundary(
            ax=ax,
            z_values=z_values,
            threshold=0.5,
        )

    ax.set_xticks(
        x_centers
    )

    ax.set_xticklabels(
        [
            f"{int(value):03d}"
            for value
            in table.columns
        ]
    )

    ax.set_yticks(
        y_centers
    )

    ax.set_yticklabels(
        neighborhood_labels(
            table=table,
            scale_km=scale_km,
        )
    )

    ax.set_xlim(
        0,
        nx,
    )

    ax.set_ylim(
        0,
        ny,
    )

    ax.set_xlabel(
        "Lead time (h)"
    )

    ax.set_ylabel(
        "Neighbourhood size\n"
        "(MONAN Global grid; "
        "approx. meridional scale)"
    )

    if (
        show_title
        and title
    ):

        ax.set_title(
            title
        )

    return im


# =============================================================================
# FIGURAS
# =============================================================================

def save_individual_heatmap(
    df,
    period,
    model,
    reference,
    threshold,
    outdir,
):

    table, scale_km = (
        prepare_table(
            df=df,
            threshold=threshold,
        )
    )

    if (
        table is None
        or table.empty
    ):

        print(
            "Sem dados para "
            f"{model} vs {reference}, "
            f"threshold "
            f"{threshold:g} mm."
        )

        return

    fig, ax = plt.subplots(
        figsize=(
            10,
            5.5,
        ),
        constrained_layout=True,
    )

    model_label = (
        MODEL_LABELS[
            model
        ]
    )

    reference_label = (
        REFERENCE_LABELS[
            reference
        ]
    )

    title = (
        f"FSS | "
        f"{model_label} vs "
        f"{reference_label} | "
        f"{period} | "
        f"Threshold {threshold:g} mm | "
        f"{DOMAIN}"
    )

    im = draw_heatmap(
        ax=ax,
        table=table,
        scale_km=scale_km,
        show_title=True,
        title=title,
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
        boundaries=LEVELS,
        ticks=np.arange(
            0.0,
            1.01,
            0.1,
        ),
        spacing="proportional",
    )

    cbar.set_label(
        "FSS"
    )

    outpng = (
        outdir
        / (
            f"FSS_heatmap_"
            f"{model}_vs_"
            f"{reference}_"
            f"{DOMAIN}_"
            f"{period}_"
            f"thr"
            f"{int(threshold)}mm.png"
        )
    )

    fig.savefig(
        outpng,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    print(
        f"Figura salva em: "
        f"{outpng}"
    )


def save_panel(
    df,
    period,
    model,
    reference,
    outdir,
):

    fig, axes = plt.subplots(
        nrows=2,
        ncols=3,
        figsize=(
            19,
            10,
        ),
        constrained_layout=True,
    )

    last_im = None
    n_panels = 0

    for ax, threshold in zip(
        axes.flat,
        THRESHOLDS,
    ):

        table, scale_km = (
            prepare_table(
                df=df,
                threshold=threshold,
            )
        )

        if (
            table is None
            or table.empty
        ):

            ax.set_visible(
                False
            )

            continue

        last_im = draw_heatmap(
            ax=ax,
            table=table,
            scale_km=scale_km,
            show_title=True,
            title=(
                f"Threshold: "
                f"{threshold:g} mm"
            ),
        )

        n_panels += 1

    if n_panels == 0:

        plt.close(
            fig
        )

        print(
            "Sem dados para o painel "
            f"{model} vs {reference}."
        )

        return

    model_label = (
        MODEL_LABELS[
            model
        ]
    )

    reference_label = (
        REFERENCE_LABELS[
            reference
        ]
    )

    fig.suptitle(
        f"FSS | "
        f"{model_label} vs "
        f"{reference_label} | "
        f"{period} | "
        f"{DOMAIN} | "
        f"{grid_description(model)}",
        fontsize=16,
    )

    cbar = fig.colorbar(
        last_im,
        ax=axes.ravel().tolist(),
        boundaries=LEVELS,
        ticks=np.arange(
            0.0,
            1.01,
            0.1,
        ),
        spacing="proportional",
        fraction=0.025,
        pad=0.02,
    )

    cbar.set_label(
        "FSS"
    )

    outpng = (
        outdir
        / (
            f"FSS_"
            f"{model}_vs_"
            f"{reference}_"
            f"{DOMAIN}_"
            f"{period}.png"
        )
    )

    fig.savefig(
        outpng,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    print(
        f"Painel salvo em: "
        f"{outpng}"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    args = parse_args()

    models = select_options(
        args.models,
        MODELS,
        "Modelo",
    )

    references = (
        select_options(
            args.references,
            REFERENCES,
            "Referencia",
        )
    )

    period = (
        args.period
    )

    outdir = (
        figure_directory(
            period
        )
    )

    outdir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\n"
        + "=" * 88
    )

    print(
        "PLOTAGEM DO FSS, "
        "MONAN REGIONAL x WRF x MONAN GLOBAL"
    )

    print(
        "=" * 88
    )

    print(
        f"Periodo:              "
        f"{period}"
    )

    print(
        f"Dominio:              "
        f"{DOMAIN}"
    )

    print(
        f"Grade:                "
        f"{TARGET_GRID}"
    )

    print(
        "Tratamento das grades: "
        "Regional/WRF=remapcon; "
        "MONAN Global=native_target_grid"
    )

    print(
        f"Modelos:              "
        f"{models}"
    )

    print(
        f"Referencias:          "
        f"{references}"
    )

    print(
        f"Saida:                "
        f"{outdir}"
    )

    for model in models:

        for reference in references:

            csv_file = (
                monthly_csv_path(
                    period=period,
                    model=model,
                    reference=reference,
                )
            )

            if not csv_file.is_file():

                print(
                    "Arquivo nao encontrado: "
                    f"{csv_file}"
                )

                continue

            print(
                "\nLendo: "
                f"{csv_file}"
            )

            df = pd.read_csv(
                csv_file
            )

            validate_dataframe(
                df,
                csv_file,
                model,
            )

            if not args.skip_individual:

                for threshold in THRESHOLDS:

                    save_individual_heatmap(
                        df=df,
                        period=period,
                        model=model,
                        reference=reference,
                        threshold=float(
                            threshold
                        ),
                        outdir=outdir,
                    )

            if not args.skip_panel:

                save_panel(
                    df=df,
                    period=period,
                    model=model,
                    reference=reference,
                    outdir=outdir,
                )


if __name__ == "__main__":
    main()
