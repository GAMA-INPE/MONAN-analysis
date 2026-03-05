#!/bin/bash

# Uso:
# ./Gera_MAE_montage.sh 2025120100 120
# onde 120 eh o prazo de previsao em horas

DATA_INI=$1
PRAZO_MAX=$2
OUTPUT_PATH=$3

echo "Montagem de figuras para: "$DATA_INI" "$PRAZO_MAX  

DATA_INI_EPOCH=$(date -u -d "${DATA_INI:0:4}-${DATA_INI:4:2}-${DATA_INI:6:2} ${DATA_INI:8:2}:00:00" +%s)

BASE_MONAN="${OUTPUT_PATH}/MONAN/${DATA_INI:0:4}${DATA_INI:4:2}/${DATA_INI}"
BASE_BIAS="${OUTPUT_PATH}/MAE/${DATA_INI:0:4}${DATA_INI:4:2}/${DATA_INI}"

DIR_TRAB=$(pwd)
DIR_OUT="${OUTPUT_PATH}/MAE/${DATA_INI:0:4}${DATA_INI:4:2}/${DATA_INI}/"

DOMINIOS=("GLB" "AMS" "ACC")

SIZE="800x600"

for dom in "${DOMINIOS[@]}"; do

for prazo in $(seq 24 24 ${PRAZO_MAX}); do

    PRAZO3=$(printf "%03d" ${prazo})

    DATA_FIM=$(date -u -d "@$((DATA_INI_EPOCH + prazo*3600))" +%Y%m%d%H)

    echo "Processando prazo ${PRAZO3}h"

    # Arquivos de entrada
    IMG_MONAN="${BASE_MONAN}/MONAN_24precacum_${DATA_INI}_${DATA_FIM}_${dom}.png"
    IMG_GPM="${BASE_BIAS}/MAE_MONAN_GPM_${dom}_${PRAZO3}h.png"
    IMG_GSMAP=${BASE_BIAS}/"MAE_MONAN_GSMAP_${dom}_${PRAZO3}h.png"
    IMG_MSWEP=${BASE_BIAS}/"MAE_MONAN_MSWEP_${dom}_${PRAZO3}h.png"

    # Arquivos temp
    TMP1="tmp_monan_${PRAZO3}.png"
    TMP2="tmp_gpm_${PRAZO3}.png"
    TMP3="tmp_gsmap_${PRAZO3}.png"
    TMP4="tmp_mswep_${PRAZO3}.png"

    # Arquivo de saida
    OUT="MAE_MONAN_${dom}_${PRAZO3}.png"

    # Padroniza 
    convert ${IMG_MONAN} \
    -trim \
    -bordercolor white \
    -border 50x50 \
    -background white \
    -gravity center \
    +repage \
	"${TMP1}"

    convert ${IMG_GPM} \
    -trim \
    -bordercolor white \
    -border 50x50 \
    -background white \
    -gravity center \
    +repage \
        "${TMP2}"

    convert ${IMG_GSMAP} \
    -trim \
    -bordercolor white \
    -border 50x50 \
    -background white \
    -gravity center \
    +repage \
        "${TMP3}"

    convert ${IMG_MSWEP} \
    -trim \
    -bordercolor white \
    -border 50x50 \
    -background white \
    -gravity center \
    +repage \
        "${TMP4}"

    # Montagem 2x2
    montage \
        ${TMP1} ${TMP2} ${TMP3} ${TMP4} \
        -tile 2x2 \
        -geometry +1+1 \
        -background white \
        ${DIR_OUT}${OUT}

    # Remove temporários
    rm -f ${TMP1} ${TMP2} ${TMP3} ${TMP4}
    rm -f ${IMG_GPM} ${IMG_GSMAP} ${IMG_MSWEP}
done

done
