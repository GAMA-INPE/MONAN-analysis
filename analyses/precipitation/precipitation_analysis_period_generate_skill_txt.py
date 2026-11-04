#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate period-aggregated precipitation skill-score TXT tables for experiments.

Reads aggregated H/M/F/C fields directly from NetCDF files in:
    output/<EXPERIMENT>/aggregated/<PERIOD>/data/Skill/

Scores are recomputed from cos(latitude)-weighted contingency totals.

Usage:  python precipitation_analysis_period_generate_skill_txt.py --start-cycle YYYYMMDDHH --end-cycle YYYYMMDDHH
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import xarray as xr

from precipitation_analysis_config import (
    DOMAINS_CONFIG as DOMAIN_CONFIG,
)

REFERENCES = ("GPM", "GSMAP", "MSWEP")

EXPERIMENTS = {
    "P1_v1.4.4": {
        "label": "Global v1.4.4",
        "source_domain": "GLB",
    },
#    "P1_v1.4.4_Reg": {
#        "label": "Regional v1.4.4",
#        "source_domain": "REG",
#    },
    "P1_v2.0.0-rc": {
        "label": "Global v2.0.0-rc",
        "source_domain": "GLB",
    },
}

DEFAULT_LEADS = (24, 48, 72, 96, 120, 144, 168, 192, 216, 240)

DEFAULT_THRESHOLDS = (1.0, 2.0, 5.0, 10.0, 20.0, 50.0)

DOMAIN = "GLB"  # "GLB", "AMS", "ACC", or "REG"

SOURCE_DOMAINS = {
    config["source_domain"]
    for config in EXPERIMENTS.values()
}

if not SOURCE_DOMAINS.issubset({"GLB", "REG"}):
    raise ValueError(
        f"Unsupported source domains: {SOURCE_DOMAINS}"
    )

COMPARISON_DOMAIN = (
    "REG" if "REG" in SOURCE_DOMAINS else DOMAIN
)

DOMAIN_INFO = DOMAIN_CONFIG[COMPARISON_DOMAIN].copy()

COMPARISON_NAME = "_vs_".join(EXPERIMENTS.keys())

SPATIAL_METHOD = (
    "native_mask_nn"
    if "REG" in SOURCE_DOMAINS
    else "native"
)


def skill_summary_root(base_dir, period):
    return (
        base_dir
        / "output"
        / "period_comparison_summary"
        / period
        / COMPARISON_NAME
        / SPATIAL_METHOD
    )

def parse_cycle(cycle):
    return datetime.strptime(cycle, "%Y%m%d%H")


def threshold_label(threshold):
    if float(threshold).is_integer():
        return str(int(threshold))
    return f"{threshold:g}".replace(".", "p")


def skill_input_path(base_dir, experiment, period, reference, lead, threshold):
    thr = threshold_label(threshold)
    source_domain = EXPERIMENTS[experiment]["source_domain"]

    return (
        base_dir
        / "output"
        / experiment
        / "aggregated"
        / period
        / "data"
        / "Skill"
        / (
            f"skill_{reference}_{source_domain}_"
            f"{period}_{lead:03d}h_thr{thr}mm.nc"
        )
    )

def validate_domain_configuration():

    if DOMAIN not in DOMAIN_CONFIG:
        raise ValueError(
            f"Invalid DOMAIN={DOMAIN!r}. "
            f"Available: {list(DOMAIN_CONFIG)}"
        )

    if (
        COMPARISON_DOMAIN == "REG"
        and "REG" not in SOURCE_DOMAINS
        and DOMAIN_INFO.get("comparison_extent") is None
    ):
        raise ValueError(
            "Global-only comparison with DOMAIN='REG' "
            "requires REG comparison_extent."
        )

    print(f"Source domains: {SOURCE_DOMAINS}")
    print(f"Comparison domain: {COMPARISON_DOMAIN}")

def determine_comparison_extent(paths):
    """
    Determine the comparison geographic extent.

    Global-only:
        GLB/AMS/ACC preserve the existing domain slices.
        REG uses comparison_extent.

    With REG experiments:
        Use the intersection of regional grid bounds,
        optionally limited by comparison_extent.
    """

    if "REG" not in SOURCE_DOMAINS:

        if COMPARISON_DOMAIN != "REG":
            return None

        extent = DOMAIN_INFO.get("comparison_extent")

        if extent is None:
            raise ValueError(
                "DOMAIN='REG' requires comparison_extent "
                "when all experiments are global."
            )

        return list(extent)

    bounds = []

    for experiment, path in paths.items():

        if EXPERIMENTS[experiment]["source_domain"] != "REG":
            continue

        with xr.open_dataset(path) as ds:

            lat_name = (
                "lat" if "lat" in ds.coords else "latitude"
            )
            lon_name = (
                "lon" if "lon" in ds.coords else "longitude"
            )

            lat = np.asarray(
                ds[lat_name].values,
                dtype="float64",
            )
            lon = np.asarray(
                ds[lon_name].values,
                dtype="float64",
            )

        if lat.ndim != 1 or lon.ndim != 1:
            raise ValueError(
                f"Expected regular 1-D grid in {path}"
            )

        if (
            not np.isfinite(lat).all()
            or not np.isfinite(lon).all()
        ):
            raise ValueError(
                f"Invalid coordinates in {path}"
            )

        lon_plot = ((lon + 180.0) % 360.0) - 180.0

        if np.ptp(lon_plot) > 180.0:
            raise ValueError(
                f"Regional grid crosses longitude seam: {path}"
            )

        bounds.append([
            float(lon_plot.min()),
            float(lon_plot.max()),
            float(lat.min()),
            float(lat.max()),
        ])

    if not bounds:
        raise ValueError(
            "No regional grid found for comparison."
        )

    extent = [
        max(b[0] for b in bounds),
        min(b[1] for b in bounds),
        max(b[2] for b in bounds),
        min(b[3] for b in bounds),
    ]

    requested = DOMAIN_INFO.get("comparison_extent")

    if requested is not None:
        extent = [
            max(extent[0], requested[0]),
            min(extent[1], requested[1]),
            max(extent[2], requested[2]),
            min(extent[3], requested[3]),
        ]

    if extent[0] >= extent[1] or extent[2] >= extent[3]:
        raise ValueError(
            f"No common regional extent: {bounds}"
        )

    return extent

def output_file_path(base_dir, period, experiment, threshold):
    thr = threshold_label(threshold)

    out_dir = (
        skill_summary_root(base_dir, period)
        / f"Skill_txt_thr{thr}mm"
        / period
    )

    return out_dir / (
        f"Skill_{experiment}_{COMPARISON_DOMAIN}_"
        f"{period}_thr{thr}mm.txt"
    )

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

def subset_comparison_extent(da, extent):
    """
    Crop a field to geographic extent.

    Longitude coordinates are expected in 0..360.
    No remapping is performed.
    """

    if extent is None:
        return da

    west, east, south, north = extent

    if float(da.lat[0]) > float(da.lat[-1]):
        da = da.sortby("lat")

    da = da.sel(lat=slice(south, north))

    west360 = west % 360.0
    east360 = east % 360.0

    if east - west >= 360.0:
        pass

    elif west360 <= east360:
        da = da.sel(
            lon=slice(west360, east360)
        )

    else:
        da = da.where(
            (da.lon >= west360)
            | (da.lon <= east360),
            drop=True,
        )

    if (
        da.sizes.get("lat", 0) == 0
        or da.sizes.get("lon", 0) == 0
    ):
        raise ValueError(
            f"Empty spatial subset for extent={extent}"
        )

    return da

def subset_analysis_domain(da, extent=None):
    """
    Select analysis domain without remapping.

    Global-only comparisons preserve GLB/AMS/ACC
    domain slices from the existing configuration.

    REG comparisons use the common bounding extent.
    """

    if (
        "REG" not in SOURCE_DOMAINS
        and COMPARISON_DOMAIN in ("GLB", "AMS", "ACC")
    ):

        if COMPARISON_DOMAIN == "GLB":
            return da

        domain_slice = DOMAIN_CONFIG[
            COMPARISON_DOMAIN
        ]["slice"]

        if domain_slice is None:
            raise ValueError(
                f"Missing slice for {COMPARISON_DOMAIN}"
            )

        lat_bounds = domain_slice["lat"]

        lat_min, lat_max = sorted((
            lat_bounds.start,
            lat_bounds.stop,
        ))

        if float(da.lat[0]) > float(da.lat[-1]):
            da = da.sortby("lat")

        sub = da.sel(
            lat=slice(lat_min, lat_max),
            lon=domain_slice["lon"],
        )

        if (
            sub.sizes.get("lat", 0) == 0
            or sub.sizes.get("lon", 0) == 0
        ):
            raise ValueError(
                f"Empty subset for {COMPARISON_DOMAIN}"
            )

        return sub

    if extent is None:
        raise ValueError(
            "A comparison extent is required for REG."
        )

    return subset_comparison_extent(da, extent)

def load_contingencies(path, extent=None):

    if not path.exists():
        raise FileNotFoundError(path)

    contingency = {}

    with xr.open_dataset(path) as ds:

        for name in ("H", "M", "F", "C", "VALID"):

            if name not in ds:
                raise KeyError(
                    f"Variable {name} not found in {path}. "
                    f"Available: {list(ds.data_vars)}"
                )

            field = standardize_lat_lon(ds[name])

            field = subset_analysis_domain(
                field,
                extent=extent,
            )

            contingency[name] = (
                field.load().astype("float64")
            )

    ref = contingency["H"]

    for name in ("M", "F", "C", "VALID"):

        try:
            xr.align(
                ref,
                contingency[name],
                join="exact",
                copy=False,
            )

        except ValueError as exc:
            raise ValueError(
                f"Grid mismatch among contingency "
                f"fields in {path}"
            ) from exc

    return contingency


def mask_for_common_coverage(contingencies):
    """
    Apply approximate common valid footprint.

    VALID > 0 determines data availability.

    Only Boolean masks are transferred between grids
    using nearest neighbor. H/M/F/C are not remapped.
    """

    if "REG" not in SOURCE_DOMAINS:
        return contingencies

    validity = {}

    for experiment, valid in validity.items():
        valid_cases = contingencies[experiment]["VALID"].where(valid)

        print(
            f"  {experiment}: "
            f"valid_cells={int(valid.sum().item())}, "
            f"VALID_min={float(valid_cases.min(skipna=True).item()):.0f}, "
            f"VALID_max={float(valid_cases.max(skipna=True).item()):.0f}"
        )

    for experiment, cont in contingencies.items():

        valid = (
            np.isfinite(cont["VALID"])
            & (cont["VALID"] > 0)
        )

        for name in ("H", "M", "F", "C"):
            valid = valid & np.isfinite(cont[name])

        validity[experiment] = valid

    common_masks = {}

    for experiment, target_mask in validity.items():

        common = target_mask.copy()

        for other_experiment, other_mask in validity.items():

            if experiment == other_experiment:
                continue

            if (
                target_mask.lat.equals(other_mask.lat)
                and target_mask.lon.equals(other_mask.lon)
            ):
                matched = other_mask

            else:
                matched = (
                    other_mask.astype("float32")
                    .interp(
                        lat=target_mask.lat,
                        lon=target_mask.lon,
                        method="nearest",
                        kwargs={"fill_value": 0.0},
                    )
                    > 0.5
                )

            common = common & matched

        n_valid = int(common.sum().item())

        print(
            f"  Common mask: {experiment}, "
            f"valid grid cells={n_valid}"
        )

        if n_valid == 0:
            raise ValueError(
                f"No common valid cells for {experiment}"
            )

        common_masks[experiment] = common

    for experiment, cont in contingencies.items():

        common = common_masks[experiment]

        for name in ("H", "M", "F", "C"):
            cont[name] = cont[name].where(common)

        cont["VALID"] = cont["VALID"].where(common)

    return contingencies


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
        source_domain = EXPERIMENTS[experiment_name]["source_domain"]
        f.write(f"# Region = {COMPARISON_DOMAIN}\n")
        f.write(f"# Source domain = {source_domain}\n")
        if "REG" in SOURCE_DOMAINS:
            f.write(
                "# Spatial comparison method = native verification "
                "grids with approximate common validity mask "
                "transferred by nearest neighbor\n"
            )
            f.write(
                "# Temporal caveat = VALID > 0 does not guarantee "
                "identical valid initialization cycles at each cell\n"
            )
        else:
            f.write(
                "# Spatial comparison method = original global "
                "verification grids and configured domain slice\n"
            )
        f.write(
            f"# Comparison ID = {COMPARISON_NAME}\n"
        )
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

def process_threshold(
    base_dir,
    period,
    start_cycle,
    end_cycle,
    threshold,
    leads,
    strict,
):

    rows_by_exp = {
        experiment: []
        for experiment in EXPERIMENTS
    }

    for lead in leads:

        print("=" * 78)
        print(
            f"Skill | {period} | F{lead:03d} | "
            f"threshold={threshold:g} mm"
        )

        for reference in REFERENCES:

            paths = {
                experiment: skill_input_path(
                    base_dir,
                    experiment,
                    period,
                    reference,
                    lead,
                    threshold,
                )
                for experiment in EXPERIMENTS
            }

            try:

                # Verify all input files before processing
                missing = [
                    str(path)
                    for path in paths.values()
                    if not path.exists()
                ]

                if missing:
                    raise FileNotFoundError(
                        "Missing input files:\n"
                        + "\n".join(missing)
                    )

                # Determine the common comparison extent
                extent = determine_comparison_extent(paths)

                print(
                    f"  Reference: {reference}, "
                    f"domain: {COMPARISON_DOMAIN}, "
                    f"extent: {extent}"
                )

                group_scores = {}

                if "REG" in SOURCE_DOMAINS:

                    # Mixed or regional comparison:
                    # load all fields after spatial cropping
                    contingencies = {
                        experiment: load_contingencies(
                            path,
                            extent=extent,
                        )
                        for experiment, path in paths.items()
                    }

                    # Apply approximate common footprint
                    contingencies = mask_for_common_coverage(
                        contingencies
                    )

                    # Calculate scores on each verification grid
                    for experiment, cont in contingencies.items():

                        group_scores[experiment] = skill_aggregated(
                            cont["H"],
                            cont["M"],
                            cont["F"],
                            cont["C"],
                        )

                    del contingencies

                else:

                    # Global-only comparison:
                    # preserve original domain selection
                    # and process one experiment at a time
                    for experiment, path in paths.items():

                        cont = load_contingencies(
                            path,
                            extent=extent,
                        )

                        group_scores[experiment] = skill_aggregated(
                            cont["H"],
                            cont["M"],
                            cont["F"],
                            cont["C"],
                        )

                        del cont

            except Exception as exc:

                if strict:
                    raise

                print(
                    f"  WARNING: skipped reference={reference}, "
                    f"lead={lead:03d}, "
                    f"threshold={threshold:g}: {exc}"
                )

                continue

            # Save results only after all experiments succeed
            for experiment, scores in group_scores.items():

                label = EXPERIMENTS[experiment]["label"]

                rows_by_exp[experiment].append({
                    "lead": lead,
                    "reference": reference,
                    "scores": scores,
                })

                print(
                    f"  {label} x {reference}: "
                    f"CSI={scores['CSI']:.3f} "
                    f"F1={scores['F1']:.3f} "
                    f"F2={scores['F2']:.3f} "
                    f"ETS={scores['ETS']:.3f}"
                )

    # Write one TXT per experiment
    for experiment, rows in rows_by_exp.items():

        if not rows:
            print(
                f"WARNING: no results for {experiment}"
            )
            continue

        label = EXPERIMENTS[experiment]["label"]

        out = output_file_path(
            base_dir,
            period,
            experiment,
            threshold,
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
    validate_domain_configuration()

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
    print(f"Source domains: {SOURCE_DOMAINS}")
    print(f"Comparison domain: {COMPARISON_DOMAIN}")
    print(f"Comparison name: {COMPARISON_NAME}")
    print(f"Spatial method: {SPATIAL_METHOD}")
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


