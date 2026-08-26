#!/usr/bin/env bash
# Author: André Lyra <andre.lyra@inpe.br>

set -u
set -o pipefail

# Remap 24-hour accumulated precipitation from MONAN and BAM to the GFS grid
# using first-order conservative remapping with CDO.

BASE_DIR="/lustre/projetos/monan_gam/andre.lyra/NetCDFs/precip_24h"
PERIOD="${1:-202601}"
OUTPUT_ROOT="${BASE_DIR}/MONAN_BAM_common_grid_GFS/remapcon_GFS/${PERIOD}"

TARGET_REFERENCE="${BASE_DIR}/GFS/2026010100/GFS_Precipitation_24h_acum_2026010100_2026010200_024h.nc"
TARGET_GRID="${OUTPUT_ROOT}/GFS_grid.txt"
MONAN_WEIGHTS="${OUTPUT_ROOT}/weights_MONAN_to_GFS_remapcon.nc"
BAM_WEIGHTS="${OUTPUT_ROOT}/weights_BAM_to_GFS_remapcon.nc"
LOG_FILE="${OUTPUT_ROOT}/remap_${PERIOD}.log"

LEADS=(024 048 072 096 120 144 168 192 216 240)
OVERWRITE="${OVERWRITE:-false}"

mkdir -p "${OUTPUT_ROOT}"
: > "${LOG_FILE}"

log() {
    printf '%s\n' "$*" | tee -a "${LOG_FILE}"
}

if ! command -v cdo >/dev/null 2>&1; then
    log "ERRO: CDO nao encontrado no PATH."
    exit 1
fi

if [[ ! -f "${TARGET_REFERENCE}" ]]; then
    log "ERRO: arquivo de referencia da grade do GFS nao encontrado:"
    log "${TARGET_REFERENCE}"
    exit 1
fi

log "Periodo: ${PERIOD}"
log "Grade alvo: ${TARGET_REFERENCE}"
log "Saida: ${OUTPUT_ROOT}"

# O arquivo de grade e criado diretamente a partir do GFS indicado.
cdo -s griddes "${TARGET_REFERENCE}" > "${TARGET_GRID}"

declare -A WEIGHTS
WEIGHTS[MONAN]="${MONAN_WEIGHTS}"
WEIGHTS[BAM]="${BAM_WEIGHTS}"

# Each model needs its own weights file, as MONAN and BAM have different source grids.
# The weights are reused for the month.
for model in MONAN BAM; do
    sample=""
    for cycle_dir in "${BASE_DIR}/${model}/${PERIOD}"??00; do
        [[ -d "${cycle_dir}" ]] || continue
        for lead in "${LEADS[@]}"; do
            candidates=("${cycle_dir}"/"${model}"_Precipitation_24h_acum_*_"${lead}"h.nc)
            if [[ -f "${candidates[0]}" ]]; then
                sample="${candidates[0]}"
                break 2
            fi
        done
    done

    if [[ -z "${sample}" ]]; then
        log "ERRO: nenhum arquivo ${model} encontrado para ${PERIOD}."
        exit 1
    fi

    if [[ ! -f "${WEIGHTS[${model}]}" || "${OVERWRITE}" == "true" ]]; then
        log "Gerando pesos conservativos de ${model} para a grade do GFS."
        cdo -L -s gencon,"${TARGET_GRID}" "${sample}" "${WEIGHTS[${model}]}" \
            2>&1 | tee -a "${LOG_FILE}"
        status=${PIPESTATUS[0]}
        if (( status != 0 )); then
            log "ERRO: falha ao gerar os pesos de ${model}."
            exit "${status}"
        fi
    else
        log "Reutilizando pesos de ${model}: ${WEIGHTS[${model}]}"
    fi
done

n_monan=0
n_bam=0
n_skipped=0
n_missing=0
n_errors=0

for model in MONAN BAM; do
    for cycle_dir in "${BASE_DIR}/${model}/${PERIOD}"??00; do
        [[ -d "${cycle_dir}" ]] || continue
        cycle="$(basename "${cycle_dir}")"

        for lead in "${LEADS[@]}"; do
            input_files=("${cycle_dir}"/"${model}"_Precipitation_24h_acum_*_"${lead}"h.nc)

            if [[ ! -f "${input_files[0]}" ]]; then
                log "AUSENTE: ${model} ciclo=${cycle} lead=${lead}h"
                ((n_missing+=1))
                continue
            fi

            if (( ${#input_files[@]} != 1 )); then
                log "ERRO: mais de um arquivo ${model} para ciclo=${cycle} lead=${lead}h"
                ((n_errors+=1))
                continue
            fi

            input_file="${input_files[0]}"
            output_dir="${OUTPUT_ROOT}/${model}/${cycle}"
            output_name="$(basename "${input_file}" .nc)_GFS_grid_remapcon.nc"
            output_file="${output_dir}/${output_name}"
            mkdir -p "${output_dir}"

            if [[ -f "${output_file}" && "${OVERWRITE}" != "true" ]]; then
                log "PULANDO existente: ${output_file}"
                ((n_skipped+=1))
                continue
            fi

            log "REMAP ${model}: ciclo=${cycle} lead=${lead}h"
            cdo -L -s -f nc4c -z zip_4 \
                remap,"${TARGET_GRID}","${WEIGHTS[${model}]}" \
                "${input_file}" "${output_file}" \
                2>&1 | tee -a "${LOG_FILE}"
            status=${PIPESTATUS[0]}

            if (( status == 0 )); then
                if [[ "${model}" == "MONAN" ]]; then
                    ((n_monan+=1))
                else
                    ((n_bam+=1))
                fi
            else
                log "ERRO no remapeamento: ${input_file}"
                rm -f "${output_file}"
                ((n_errors+=1))
            fi
        done
    done
done

log ""
log "Summary of remapping:"
log "MONAN remapped: ${n_monan}"
log "BAM remapped: ${n_bam}"
log "Files skipped: ${n_skipped}"
log "Files missing: ${n_missing}"
log "Errors: ${n_errors}"

if (( n_errors > 0 )); then
    exit 2
fi

log "Remap completed successfully"
