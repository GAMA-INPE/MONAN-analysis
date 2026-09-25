#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate period-aggregated precipitation skill-score TXT tables for CTL and NEW.

Reads aggregated H/M/F/C fields directly from NetCDF files in:
    output/<EXPERIMENT>/aggregated/<PERIOD>/data/Skill/

Scores are recomputed from cos(latitude)-weighted contingency totals.

"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import xarray as xr


REFERENCES = ("GPM", "GSMAP", "MSWEP")
EXPERIMENTS = (
    ("MONAN_CTL_AMS_CAR", "CTL"),
    ("MONAN_NEW_AMS_CAR", "NEW"),
)

DEFAULT_LEADS = (24, 48, 72, 96, 120)
DEFAULT_THRESHOLDS = (1.0, 2.0, 5.0, 10.0, 20.0, 50.0)

REGION_ANALYSIS = "REG"
REGION_DESCRIPTION = "full common REG grid used by CTL and NEW verification"


def parse_cycle(cycle):
    return datetime.strptime(cycle, "%Y%m%d%H")


def threshold_label(threshold):
    if float(threshold).is_integer():
        return str(int(threshold))
    return f"{threshold:g}".replace(".", "p")


def skill_input_path(base_dir, experiment, period, reference, lead, threshold):
    thr = threshold_label(threshold)
    return (
        base_dir
        / "output"
        / experiment
        / "aggregated"
        / period
        / "data"
        / "Skill"
        / f"skill_{reference}_{REGION_ANALYSIS}_{period}_{lead:03d}h_thr{thr}mm.nc"
    )


def output_file_path(base_dir, period, experiment_label, threshold):
    thr = threshold_label(threshold)
    out_dir = (
        base_dir
        / "output"
        / "period_comparison_summary"
        / period
        / f"Skill_txt_thr{thr}mm"
        / f"{period}"
    )
    return out_dir / f"Skill_{experiment_label}_{REGION_ANALYSIS}_{period}_thr{thr}mm.txt"


def standardize_lat_lon(da):
    rename = {}
    if "latitude" in da.dims or "latitude" in da.coords:
        rename["latitude"] = "lat"
    if "longitude" in da.dims or "longitude" in da.coords:
        rename["longitude"] = "lon"
    if rename:
        da = da.rename(rename)

    da = da.squeeze(drop=True)

    if "lat" not in da.coords or "lon" not in da.coords:
        raise ValueError(f"Expected lat/lon coordinates; found {list(da.coords)}")

    if da["lat"].ndim != 1 or da["lon"].ndim != 1:
        raise ValueError("Expected regular one-dimensional lat/lon coordinates.")

    if da["lat"].size > 1 and float(da["lat"][0]) > float(da["lat"][-1]):
        da = da.sortby("lat")

    if float(da["lon"].min()) < 0.0:
        da = da.assign_coords(lon=(da["lon"] + 360.0) % 360.0).sortby("lon")

    return da


def load_contingencies(path):
    if not path.exists():
        raise FileNotFoundError(path)

    contingency = {}
    with xr.open_dataset(path) as ds:
        for name in ("H", "M", "F", "C"):
            if name not in ds:
                raise KeyError(
                    f"Variable {name} not found in {path}. "
                    f"Available: {list(ds.data_vars)}"
                )
            contingency[name] = standardize_lat_lon(ds[name].load()).astype("float64")

    ref = contingency["H"]
    for name in ("M", "F", "C"):
        try:
            xr.align(ref, contingency[name], join="exact", copy=False)
        except ValueError as exc:
            raise ValueError(f"Grid mismatch among contingency fields in {path}") from exc

    return contingency


def weighted_sum(da):
    weights = xr.DataArray(
        np.cos(np.deg2rad(da["lat"])),
        coords={"lat": da["lat"]},
        dims=("lat",),
    )
    value = (da.fillna(0.0) * weights).sum(
        dim=("lat", "lon"),
        skipna=True,
    )
    return float(value.item())


def safe_divide(num, den):
    return num / den if den > 0.0 else np.nan


def skill_aggregated(H, M, F, C):
    Hn = weighted_sum(H)
    Mn = weighted_sum(M)
    Fn = weighted_sum(F)
    Cn = weighted_sum(C)

    total = Hn + Mn + Fn + Cn

    acc = safe_divide(Hn + Cn, total)
    pod = safe_divide(Hn, Hn + Mn)
    pofd = safe_divide(Fn, Fn + Cn)
    far = safe_divide(Fn, Hn + Fn)
    csi = safe_divide(Hn, Hn + Mn + Fn)

    f1 = safe_divide(2.0 * Hn, 2.0 * Hn + Mn + Fn)
    f05 = safe_divide(1.25 * Hn, 1.25 * Hn + 0.25 * Mn + Fn)
    f2 = safe_divide(5.0 * Hn, 5.0 * Hn + 4.0 * Mn + Fn)

    expected_hits = (
        ((Hn + Mn) * (Hn + Fn)) / total
        if total > 0.0 else np.nan
    )

    ets = safe_divide(
        Hn - expected_hits,
        Hn + Mn + Fn - expected_hits,
    )

    return {
        "ACC": acc,
        "POD": pod,
        "POFD": pofd,
        "FAR": far,
        "CSI": csi,
        "F1": f1,
        "F05": f05,
        "F2": f2,
        "ETS": ets,
    }


def format_score(value):
    if np.isfinite(value):
        return f"{value:8.3f}"
    return f"{'nan':>8}"


def write_txt(path, experiment_label, experiment_name, start_cycle, end_cycle,
              period, threshold, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        f.write("# Period-aggregated precipitation skill scores\n")
        f.write(f"# Experiment = {experiment_label} ({experiment_name})\n")
        f.write(f"# Region = {REGION_ANALYSIS} ({REGION_DESCRIPTION})\n")
        f.write(f"# Threshold = {threshold:g} mm / 24 h\n")
        f.write(f"# Initialization cycles = {start_cycle} .. {end_cycle}\n")
        f.write("# Temporal aggregation = summed H/M/F/C over initialization cycles\n")
        f.write("# Spatial aggregation = cos(latitude)-weighted H/M/F/C totals\n")
        f.write("# Scores recomputed from aggregated contingencies; daily scores are not averaged.\n")
        f.write("# F2 = 5H/(5H+4M+F); F05 = 1.25H/(1.25H+0.25M+F)\n\n")

        header = (
            f"{'LEAD':^6}{'REF':^8}{'ACC':^8}{'POD':^8}{'POFD':^8}"
            f"{'FAR':^8}{'CSI':^8}{'F1':^8}{'F05':^8}{'F2':^8}{'ETS':^8}\n"
        )
        f.write(header)
        f.write("-" * 86 + "\n")

        for row in sorted(rows, key=lambda x: (x["lead"], REFERENCES.index(x["reference"]))):
            s = row["scores"]
            f.write(
                f"{row['lead']:03d}".center(6)
                + f"{row['reference']:^8}"
                + format_score(s["ACC"])
                + format_score(s["POD"])
                + format_score(s["POFD"])
                + format_score(s["FAR"])
                + format_score(s["CSI"])
                + format_score(s["F1"])
                + format_score(s["F05"])
                + format_score(s["F2"])
                + format_score(s["ETS"])
                + "\n"
            )

    print(f"TXT saved: {path}")


def process_threshold(base_dir, period, start_cycle, end_cycle, threshold, leads, strict):
    rows_by_exp = {label: [] for _, label in EXPERIMENTS}

    for lead in leads:
        print("=" * 78)
        print(f"Skill | {period} | F{lead:03d} | threshold={threshold:g} mm")

        for experiment, label in EXPERIMENTS:
            for reference in REFERENCES:
                path = skill_input_path(
                    base_dir, experiment, period, reference, lead, threshold
                )

                try:
                    cont = load_contingencies(path)
                    scores = skill_aggregated(
                        cont["H"], cont["M"], cont["F"], cont["C"]
                    )

                    rows_by_exp[label].append(
                        {
                            "lead": lead,
                            "reference": reference,
                            "scores": scores,
                        }
                    )

                    print(
                        f"  {label:3s} x {reference:5s}: "
                        f"CSI={scores['CSI']:.3f} "
                        f"F1={scores['F1']:.3f} "
                        f"F2={scores['F2']:.3f} "
                        f"ETS={scores['ETS']:.3f}"
                    )

                except Exception as exc:
                    if strict:
                        raise
                    print(
                        f"  WARNING: {label} x {reference}, "
                        f"F{lead:03d}, threshold={threshold:g}: {exc}"
                    )

    for experiment, label in EXPERIMENTS:
        rows = rows_by_exp[label]
        if not rows:
            continue

        out = output_file_path(
            base_dir, period, label, threshold
        )

        write_txt(
            out,
            label,
            experiment,
            start_cycle,
            end_cycle,
            period,
            threshold,
            rows,
        )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-cycle", required=True)
    parser.add_argument("--end-cycle", required=True)
    parser.add_argument("--leads", nargs="+", type=int, default=DEFAULT_LEADS)
    parser.add_argument("--thresholds", nargs="+", type=float, default=DEFAULT_THRESHOLDS)
    parser.add_argument(
        "--base-dir",
        default=str(Path(__file__).resolve().parent),
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    start = parse_cycle(args.start_cycle)
    end = parse_cycle(args.end_cycle)
    if end < start:
        raise ValueError("end-cycle must be >= start-cycle.")

    base_dir = Path(args.base_dir).resolve()
    period = f"{args.start_cycle}_{args.end_cycle}"

    print("=" * 80)
    print("Period-aggregated skill-score TXT generation")
    print(f"Start cycle: {args.start_cycle}")
    print(f"End cycle:   {args.end_cycle}")
    print(f"Leads: {tuple(args.leads)}")
    print(f"Thresholds: {tuple(args.thresholds)}")
    print("Method: aggregated H/M/F/C -> cos(latitude) spatial totals -> scores")
    print("=" * 80)

    for threshold in args.thresholds:
        process_threshold(
            base_dir,
            period,
            args.start_cycle,
            args.end_cycle,
            threshold,
            tuple(args.leads),
            args.strict,
        )


if __name__ == "__main__":
    main()


