#!/bin/bash

module load eccodes/2.40.0
module load libfabric/1.22.0

export ECCODES_DEFINITION_PATH=/p/app/eccodes/2.40.0/share/eccodes/definitions

mkdir -p "$HOME/libfix_netcdf"

ln -sf /opt/cray/pe/netcdf-hdf5parallel/4.9.0.15/CRAYCLANG/18.0/lib/libnetcdf.so.19 \
      "$HOME/libfix_netcdf/libnetcdf.so.18"

export LD_LIBRARY_PATH="$HOME/libfix_netcdf:/opt/cray/pe/netcdf-hdf5parallel/4.9.0.15/CRAYCLANG/18.0/lib:/opt/cray/libfabric/1.22.0/lib64:${LD_LIBRARY_PATH:-}"


# Configuration
BASE_IN="/oper/dados/modelo/bam/TQ0666L064/brutos"

ANO="2026"
MES="07"

DIR_OUT="/lustre/projetos/monan_gam/andre.lyra/NetCDFs/vert_struct/BAM/${ANO}${MES}"

mkdir -p "${DIR_OUT}"

# Period
DATA_INI="${ANO}-${MES}-01"
DATA_FIM="$(date -d "${DATA_INI} +1 month -1 day" +%F)"


fix_bam_coordinates() {

    NCFILE="$1"

    python - "${NCFILE}" <<'PY'

import sys
import numpy as np
from netCDF4 import Dataset

ncfile = sys.argv[1]

with Dataset(ncfile, "r+") as nc:

    nx = len(nc.dimensions["longitude"])
    ny = len(nc.dimensions["latitude"])

    lon = 0.0 + 0.18 * np.arange(nx, dtype=np.float32)

    # BAM raw GRIB uses reversed Y ordering, as indicated by "options yrev"
    lat = 89.91 - 0.18 * np.arange(ny, dtype=np.float32)

    nc.variables["longitude"][:] = lon
    nc.variables["latitude"][:] = lat

    print(f"Coordinates fixed: {ncfile}")
    print(f"  longitude: {lon[0]:.2f} -> {lon[-1]:.2f}")
    print(f"  latitude : {lat[0]:.2f} -> {lat[-1]:.2f}")

PY
}

# Loop over dates and forecast leads
data="${DATA_INI}"

while [[ "${data}" < "$(date -d "${DATA_FIM} +1 day" +%F)" ]]; do

  ymd=$(date -d "${data}" +%Y%m%d)

  for HH in 00; do

    CICLO="${ymd}${HH}"

    for LEAD in 24 48 72 96 120; do

        FHHH="f$(printf '%03d' ${LEAD})"

        # --------------------------------------------------------
        # Calculate valid date corresponding to forecast lead
        # --------------------------------------------------------
        VALID=$(date -u -d \
          "${ymd:0:4}-${ymd:4:2}-${ymd:6:2} ${HH}:00 UTC +${LEAD} hours" \
          +%Y%m%d%H)

        DD="${ymd:6:2}"

        DIR_DIA="${BASE_IN}/${ANO}/${MES}/${DD}/${HH}"

        ARQ_IN="${DIR_DIA}/GPOSNMC${CICLO}${VALID}P.fct.TQ0666L064.grb"


        # --------------------------------------------------------
        # Output files
        # --------------------------------------------------------
        OUT_NC_LEVS="${DIR_OUT}/BAM_${FHHH}_levels_${CICLO}.nc"
        OUT_NC_SFC="${DIR_OUT}/BAM_${FHHH}_surface_${CICLO}.nc"

        TMP_GRIB_LEVS="${DIR_OUT}/tmp_${FHHH}_levels_${CICLO}.grb"
        TMP_GRIB_SFC="${DIR_OUT}/tmp_${FHHH}_surface_${CICLO}.grb"
        
        # Check input
        if [[ ! -s "${ARQ_IN}" ]]; then
          echo "File not found: ${ARQ_IN}"
          continue
        fi

        echo
        echo "============================================================"
        echo "Cycle : ${CICLO}"
        echo "Lead  : ${FHHH}"
        echo "Valid : ${VALID}"
        echo "Input : ${ARQ_IN}"
        echo "============================================================"

        # Pressure levels
        grib_copy \
          -w shortName=temp/umes/zgeo/uvel/vvel,typeOfLevel=isobaricInhPa,level=925/850/700/500/400/250/100,stepRange=${LEAD} \
          "${ARQ_IN}" \
          "${TMP_GRIB_LEVS}"

        if [[ -s "${TMP_GRIB_LEVS}" ]]; then

          grib_to_netcdf \
            -o "${OUT_NC_LEVS}" \
            "${TMP_GRIB_LEVS}"

          fix_bam_coordinates "${OUT_NC_LEVS}"

          echo "Created: ${OUT_NC_LEVS}"

        else

          echo "WARNING: No pressure-level variables found"

        fi


        # Surface
        grib_copy \
          -w shortName=pslc/psnm,stepRange=${LEAD} \
          "${ARQ_IN}" \
          "${TMP_GRIB_SFC}"

        if [[ -s "${TMP_GRIB_SFC}" ]]; then

          grib_to_netcdf \
            -o "${OUT_NC_SFC}" \
            "${TMP_GRIB_SFC}"
          
          fix_bam_coordinates "${OUT_NC_SFC}"

          echo "Created: ${OUT_NC_SFC}"

        else

          echo "WARNING: No surface variables found"

        fi


        # Cleanup
        rm -f "${TMP_GRIB_LEVS}" "${TMP_GRIB_SFC}"

    done
  done

  data="$(date -d "${data} +1 day" +%F)"

done