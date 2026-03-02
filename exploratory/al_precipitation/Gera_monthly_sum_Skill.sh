#!/bin/bash

DIR_BASE=/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h/CONTINGENCIA
ANO=2026
MES=01
THR=thr50mm

INI_VALID=${ANO}${MES}0100
ULT_DIA=$(date -u -d "${ANO}-${MES}-01 +1 month -1 day" +%d)
FIM_VALID=${ANO}${MES}${ULT_DIA}23

mkdir -p listas_medias

for PRAZO in 24 48 72 96 120; do

  PRAZO3=$(printf "%03d" ${PRAZO})

  LISTA="listas_medias/arquivos_cont_${ANO}${MES}_${PRAZO3}h_${THR}.txt"
  : > ${LISTA}

  INI_ROD=$(date -u -d "${INI_VALID:0:8} ${INI_VALID:8:2} -${PRAZO} hours" +%Y%m%d%H)
  FIM_ROD=$(date -u -d "${FIM_VALID:0:8} ${FIM_VALID:8:2} -${PRAZO} hours" +%Y%m%d%H)
  INI_NEXT=$(date -u -d "${INI_ROD:0:6}01 +1 month" +%Y%m)

  for D in \
    ${DIR_BASE}/${INI_ROD:0:4}${INI_ROD:4:2}??00 \
    ${DIR_BASE}/${INI_NEXT}??00
  do
    DATA_ROD=$(basename ${D})

    DATA_VALID=$(date -u -d "${DATA_ROD:0:8} ${DATA_ROD:8:2} +${PRAZO} hours" +%Y%m%d%H)

    if [ "${DATA_VALID}" -ge "${INI_VALID}" ] && [ "${DATA_VALID}" -le "${FIM_VALID}" ]; then

      ARQ="${DIR_BASE}/${DATA_ROD}/CONT_MONAN_${DATA_ROD}_${PRAZO3}h_${THR}.nc"
      echo "${ARQ}"
      
      if [ -f "${ARQ}" ]; then
        echo "${ARQ}" >> ${LISTA}
      fi

    fi
  done

  NARQ=$(wc -l < ${LISTA})
  echo "Ano ${ANO}, mes ${MES}, prazo ${PRAZO}h, total de arquivos: ${NARQ}"

  cdo enssum $(cat ${LISTA}) \
    ${DIR_BASE}/CONT_MONAN_${ANO}${MES}_sum_${PRAZO3}h_${THR}.nc

done

