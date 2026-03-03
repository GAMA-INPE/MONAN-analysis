#!/bin/bash

module load eccodes/2.40.0
module load libfabric/1.22.0

export ECCODES_DEFINITION_PATH=/p/app/eccodes/2.40.0/share/eccodes/definitions
mkdir -p "$HOME/libfix_netcdf"
ln -sf /opt/cray/pe/netcdf-hdf5parallel/4.9.0.15/CRAYCLANG/18.0/lib/libnetcdf.so.19 \
      "$HOME/libfix_netcdf/libnetcdf.so.18"

export LD_LIBRARY_PATH="$HOME/libfix_netcdf:/opt/cray/pe/netcdf-hdf5parallel/4.9.0.15/CRAYCLANG/18.0/lib:/opt/cray/libfabric/1.22.0/lib64:${LD_LIBRARY_PATH:-}"

WGRIB2="/p/app/wgrib2/3.8.0/bin/wgrib2"
BASE_IN="/p/projetos/monan_adm/monan/CIs/GFS"

ANO="2026"
MES="02"

DIR_OUT="/lustre/projetos/monan_gam/andre.lyra/Scripts/Scripts_GFS_levelsvar/GFS_NETCDF_struct/${ANO}${MES}"
mkdir -p "${DIR_OUT}"

# Selectcting variables and levels for analysis time (anl)
REG_VARS_LEVS=":(TMP|SPFH|HGT|UGRD|VGRD):"
REG_LEVS=":(925|850|700|500|400|250|100) mb:"
REG_VARS_SFC=":(PRMSL|PRES):"
REG_SFC=":(surface|mean sea level):"
REG_STEP=":anl:"

DATA_INI="${ANO}-${MES}-01"
DATA_FIM="$(date -d "${DATA_INI} +1 month -1 day" +%F)"

data="${DATA_INI}"
while [[ "${data}" < "$(date -d "${DATA_FIM} +1 day" +%F)" ]]; do
  ymd=$(date -d "${data}" +%Y%m%d)

for HH in 00 12; do

  CICLO="${ymd}${HH}"  

  DIR_DIA="${BASE_IN}/${ANO}/${ANO}${MES}${ymd:6:2}${HH}"
  ARQ_IN="${DIR_DIA}/gfs.t${HH}z.pgrb2.0p25.f000.${CICLO}.grib2"

  OUT_NC_LEVS="${DIR_OUT}/GFS_anl_levels_${CICLO}.nc"
  OUT_NC_SFC="${DIR_OUT}/GFS_anl_surface_${CICLO}.nc"

  TMP_GRIB_LEVS="${DIR_OUT}/tmp_levels_${CICLO}.grib2"
  TMP_GRIB_SFC="${DIR_OUT}/tmp_surface_${CICLO}.grib2"

  if [[ ! -s "${ARQ_IN}" ]]; then
    echo "File not found: ${ARQ_IN}"
    continue
  fi

  echo "Processing ${ARQ_IN}"
  echo "Output ${OUT_NC_LEVS}"
  echo "Output ${OUT_NC_SFC}"

  "${WGRIB2}" "${ARQ_IN}" \
    -match "${REG_VARS_LEVS}" \
    -match "${REG_LEVS}" \
    -match "${REG_STEP}" \
    -grib "${TMP_GRIB_LEVS}"

  grib_to_netcdf -o "${OUT_NC_LEVS}" "${TMP_GRIB_LEVS}"

  "${WGRIB2}" "${ARQ_IN}" \
    -match "${REG_VARS_SFC}" \
    -match "${REG_SFC}" \
    -match "${REG_STEP}" \
    -grib "${TMP_GRIB_SFC}"

  grib_to_netcdf -o "${OUT_NC_SFC}" "${TMP_GRIB_SFC}"

  rm -f "${TMP_GRIB_LEVS}" "${TMP_GRIB_SFC}"
done 

  data="$(date -d "${data} +1 day" +%F)"
done

