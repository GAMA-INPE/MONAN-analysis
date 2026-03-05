#!/bin/bash

############################################################
# Script to compute mean Bias over an arbitrary date range #
# Usage:                                                   # 
# ./media_periodo.sh 2025112600 2025123023                 #
#                                                          #
# Arguments:                                               #
#   $1 - Start valid datetime (YYYYMMDDHH)                 #
#   $2 - End valid datetime   (YYYYMMDDHH)                 #
#   $3 - Process to average: "bias", "rmse" ou "skill"     #
#   $4 - Output path for the monthly mean files            #
#   $5 - Analysis name (e.g., "monthly_means")             #
#   $6 - Threshold for skill score (e.g., 1.0)             #
############################################################

# Capture input arguments
INI_VALID=$1
FIM_VALID=$2
PROCESSO=$3
OUTPUT_PATH=$4
ANALYSIS_NAME=$5
THRESHOLD=$6

ANO=${INI_VALID:0:4}
MES=${INI_VALID:4:2}

# Define DIR_BASE based on the requested process type
if [ ${PROCESSO} == "bias" ]; then
    DIR_BASE=${OUTPUT_PATH}Bias
elif [ ${PROCESSO} == "rmse" ]; then
    DIR_BASE=${OUTPUT_PATH}precip_24h/RMSE
elif [ ${PROCESSO} == "skill" ]; then
    DIR_BASE=${OUTPUT_PATH}precip_24h/CONTINGENCIA
    THR=thr${THRESHOLD}mm
else
    echo "Processo desconhecido: ${PROCESSO}. Use 'bias', 'rmse' ou 'skill'."
    exit 1
fi

# Output directory
OUTPUT_DIR=${OUTPUT_PATH}${ANALYSIS_NAME}

echo "Dir base: $DIR_BASE"
echo "Output dir: $OUTPUT_DIR"


mkdir -p ${OUTPUT_DIR}

#load CDO module for data manipulation
module load cdo

# Base directory where the bias output files are stored

# Create directory to store file lists
mkdir -p listas_medias

if [ ${PROCESSO} == "skill" ]; then
    echo "Processo: ${PROCESSO}, limiar: ${THR}"
    # Loop over forecast lead times
    for PRAZO in 24 48 72 96 120; do
    
        # Format lead time as three digits (e.g. 024)
        PRAZO3=$(printf "%03d" ${PRAZO})

        # Path to the list file that will contain all matching netCDF paths
        LISTA="listas_medias/arquivos_cont_${INI_VALID}_${FIM_VALID}_${PRAZO3}h_${THR}.txt"

        # Clear the file if it already exists
        : > ${LISTA}
    
        # Loop over ALL run directories in DIR_BASE
        # (assuming they are named with the pattern YYYYMMDDHH)
        for D in ${DIR_BASE}/??????????; do

            # Extract the directory name (which is the run timestamp)
            DATA_ROD=$(basename ${D})

            # Compute valid datetime for this run + lead
            DATA_VALID=$(date -u -d "${DATA_ROD:0:8} ${DATA_ROD:8:2} +${PRAZO} hours" +%Y%m%d%H)
            echo "Processando rodada ${DATA_ROD}, prazo ${PRAZO}h, data válida ${DATA_VALID}"
            
            # Only consider runs whose valid time lies within the requested month
            if [ "${DATA_VALID}" -ge "${INI_VALID}" ] && \
            [ "${DATA_VALID}" -le "${FIM_VALID}" ]; then

                # Construct expected NetCDF filename
                ARQ="${DIR_BASE}/${DATA_ROD}/CONT_MONAN_${DATA_ROD}_${PRAZO3}h_${THR}.nc"

                if [ -f "${ARQ}" ]; then
                    # If the file exists, append it to the list to be averaged later
                    echo "${ARQ}" >> ${LISTA}
                else
                    # Otherwise warn the user about the missing file
                    echo "Arquivo não encontrado: ${ARQ}"
                fi

            fi
        done

        # Count how many files were collected for this lead time
        NARQ=$(wc -l < ${LISTA})
        echo "Ano ${ANO}, mes ${MES}, prazo ${PRAZO}h, total de arquivos: ${NARQ}"

        # Use CDO to compute the ensemble mean of all the collected files
        cdo enssum $(cat ${LISTA}) ${OUTPUT_DIR}/CONT_MONAN_${ANO}${MES}_sum_${PRAZO3}h_${THR}.nc

    done
else
    echo "Processo: ${PROCESSO}"
        for PRAZO in 24 48 72 96 120; do
    
        # Format lead time as three digits (e.g. 024)
        PRAZO3=$(printf "%03d" ${PRAZO})

        # Path to the list file that will contain all matching netCDF paths
        if [ ${PROCESSO} == "bias" ]; then
            LISTA="listas_medias/arquivos_media_${INI_VALID}_${FIM_VALID}_${PRAZO}h.txt"
        elif [ ${PROCESSO} == "rmse" ]; then
            LISTA="listas_medias/arquivos_media_RMSE_MAE_${INI_VALID}_${FIM_VALID}_${PRAZO}h.txt"
        fi

        # Clear the file if it already exists
        : > ${LISTA}
    
        # Loop over ALL run directories in DIR_BASE
        # (assuming they are named with the pattern YYYYMMDDHH)
        for D in ${DIR_BASE}/??????????; do

            # Extract the directory name (which is the run timestamp)
            DATA_ROD=$(basename ${D})

            # Compute valid datetime for this run + lead
            DATA_VALID=$(date -u -d "${DATA_ROD:0:8} ${DATA_ROD:8:2} +${PRAZO} hours" +%Y%m%d%H)
            echo "Processando rodada ${DATA_ROD}, prazo ${PRAZO}h, data válida ${DATA_VALID}"
            
            # Only consider runs whose valid time lies within the requested month
            if [ "${DATA_VALID}" -ge "${INI_VALID}" ] && \
            [ "${DATA_VALID}" -le "${FIM_VALID}" ]; then

                # Construct expected NetCDF filename
                if [ ${PROCESSO} == "bias" ]; then
                    ARQ="${DIR_BASE}/${DATA_ROD}/Bias_MONAN_Prec_${DATA_ROD}_${PRAZO3}h.nc"
                elif [ ${PROCESSO} == "rmse" ]; then
                    ARQ="${DIR_BASE}/${DATA_ROD}/RMSE_MONAN_Prec_${DATA_ROD}_${PRAZO3}h.nc"
                fi

                if [ -f "${ARQ}" ]; then
                    # If the file exists, append it to the list to be averaged later
                    echo "${ARQ}" >> ${LISTA}
                else
                    # Otherwise warn the user about the missing file
                    echo "Arquivo não encontrado: ${ARQ}"
                fi

            fi
        done

        # Count how many files were collected for this lead time
        NARQ=$(wc -l < ${LISTA})
        echo "Ano ${ANO}, mes ${MES}, prazo ${PRAZO}h, total de arquivos: ${NARQ}"

        # Use CDO to compute the ensemble mean of all the collected files
        if [ ${PROCESSO} == "bias" ]; then
            cdo ensmean $(cat ${LISTA}) ${OUTPUT_DIR}/Bias_MONAN_Prec_${ANO}${MES}_mean_${PRAZO3}h.nc
        elif [ ${PROCESSO} == "rmse" ]; then
            cdo ensmean $(cat ${LISTA}) ${OUTPUT_DIR}/RMSE_MAE_MONAN_Prec_${ANO}${MES}_mean_${PRAZO3}h.nc
        fi

    done
fi

