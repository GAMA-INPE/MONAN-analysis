#!/bin/bash

module load eccodes/2.40.0
module load libfabric/1.22.0

export ECCODES_DEFINITION_PATH=/p/app/eccodes/2.40.0/share/eccodes/definitions

mkdir -p "$HOME/libfix_netcdf"

ln -sf /opt/cray/pe/netcdf-hdf5parallel/4.9.0.15/CRAYCLANG/18.0/lib/libnetcdf.so.19 \
      "$HOME/libfix_netcdf/libnetcdf.so.18"

export LD_LIBRARY_PATH="$HOME/libfix_netcdf:/opt/cray/pe/netcdf-hdf5parallel/4.9.0.15/CRAYCLANG/18.0/lib:/opt/cray/libfabric/1.22.0/lib64:${LD_LIBRARY_PATH:-}"

WGRIB2="/p/app/wgrib2/3.8.0/bin/wgrib2"

# Configuration
BASE_IN="/p/projetos/ioper/data/external/gfs_0p25"

ANO="2025"
MES="05"

DIR_OUT="/lustre/projetos/monan_gam/andre.lyra/NetCDFs/vert_struct/GFS_teste/${ANO}${MES}"

mkdir -p "${DIR_OUT}"

# Variables and levels
REG_VARS_LEVS=":(TMP|SPFH|HGT|UGRD|VGRD):"
REG_LEVS=":(925|850|700|500|400|250|100) mb:"

REG_VARS_SFC=":(PRMSL|PRES):"
REG_SFC=":(surface|mean sea level):"

# Period
DATA_INI="${ANO}-${MES}-01"
DATA_FIM="$(date -d "${DATA_INI} +1 month -1 day" +%F)"

data="${DATA_INI}"

while [[ "${data}" < "$(date -d "${DATA_FIM} +1 day" +%F)" ]]; do

    ymd=$(date -d "${data}" +%Y%m%d)

    for HH in 00; do

        CICLO="${ymd}${HH}"

        DIR_DIA="${BASE_IN}/${ANO}/${MES}/${ymd:6:2}/${HH}"

        for LEAD in anl 24 48 72 96 120 144 168 192 216 240; do

            # Analysis
            if [[ "${LEAD}" == "anl" ]]; then

                FHHH="anl"

                ARQ_IN="${DIR_DIA}/gfs.t${HH}z.pgrb2.0p25.anl.${CICLO}.grib2"

                OUT_NC_LEVS="${DIR_OUT}/GFS_anl_levels_${CICLO}.nc"
                OUT_NC_SFC="${DIR_OUT}/GFS_anl_surface_${CICLO}.nc"

                REG_STEP=":anl:"

            # Forecast
            else

                FHHH="f$(printf '%03d' "${LEAD}")"

                ARQ_IN="${DIR_DIA}/gfs.t${HH}z.pgrb2.0p25.${FHHH}.${CICLO}.grib2"

                OUT_NC_LEVS="${DIR_OUT}/GFS_${FHHH}_levels_${CICLO}.nc"
                OUT_NC_SFC="${DIR_OUT}/GFS_${FHHH}_surface_${CICLO}.nc"

                REG_STEP=":${LEAD} hour fcst:"

            fi

            TMP_GRIB_LEVS="${DIR_OUT}/tmp_${FHHH}_levels_${CICLO}.grib2"
            TMP_GRIB_SFC="${DIR_OUT}/tmp_${FHHH}_surface_${CICLO}.grib2"

            if [[ ! -s "${ARQ_IN}" ]]; then
                echo "File not found: ${ARQ_IN}"
                continue
            fi

            echo
            echo "============================================================"
            echo "Cycle : ${CICLO}"
            echo "Lead  : ${FHHH}"
            echo "Input : ${ARQ_IN}"
            echo "============================================================"

            # Pressure levels
            "${WGRIB2}" "${ARQ_IN}" \
                -match "${REG_VARS_LEVS}" \
                -match "${REG_LEVS}" \
                -match "${REG_STEP}" \
                -grib "${TMP_GRIB_LEVS}"

            if [[ -s "${TMP_GRIB_LEVS}" ]]; then
                grib_to_netcdf \
                    -o "${OUT_NC_LEVS}" \
                    "${TMP_GRIB_LEVS}"

                echo "Created: ${OUT_NC_LEVS}"
            else
                echo "WARNING: No pressure-level variables found"
            fi

            # Surface
            "${WGRIB2}" "${ARQ_IN}" \
                -match "${REG_VARS_SFC}" \
                -match "${REG_SFC}" \
                -match "${REG_STEP}" \
                -grib "${TMP_GRIB_SFC}"

            if [[ -s "${TMP_GRIB_SFC}" ]]; then
                grib_to_netcdf \
                    -o "${OUT_NC_SFC}" \
                    "${TMP_GRIB_SFC}"

                echo "Created: ${OUT_NC_SFC}"
            else
                echo "WARNING: No surface variables found"
            fi

            rm -f "${TMP_GRIB_LEVS}" "${TMP_GRIB_SFC}"

        done

    done

    data="$(date -d "${data} +1 day" +%F)

done
