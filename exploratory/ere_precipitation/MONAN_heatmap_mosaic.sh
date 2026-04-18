#!/bin/bash

OUTPUT_PATH=$1
ANALYSIS_NAME=$2

# Output directory
OUTPUT_DIR=${OUTPUT_PATH}mosaic_${ANALYSIS_NAME}
# Data directory where the heatmap images are stored
DATA_DIR=${OUTPUT_PATH}Skill/${ANALYSIS_NAME}/Skill_fig_mensal/heatmap_lead_threshold/

echo "Dir base: $OUTPUT_PATH"
echo "Analysis name: $ANALYSIS_NAME"
echo "Output dir: $OUTPUT_DIR"
echo "Data dir: $DATA_DIR"

# Create output directory if it doesn't exist
mkdir -p ${OUTPUT_DIR}

METRICS=("CSI" "ETS" "F1" "F05" "POD")

for METRIC in "${METRICS[@]}"; do

    # Output file name
    OUTPUT_FILE=${OUTPUT_DIR}/mosaic_${METRIC}_${ANALYSIS_NAME}.png
    # Title for the mosaic
    TITLE="${METRIC} - South America and Global - ${ANALYSIS_NAME}"
    
    # Matrix layout:
    # A1 A2
    # B1 B2
    # C1 C2

    A1="${DATA_DIR}heatmap_${METRIC}_MONAN_AMS_MSWEP.png"
    A2="${DATA_DIR}heatmap_${METRIC}_MONAN_GLB_MSWEP.png"
    B1="${DATA_DIR}heatmap_${METRIC}_BAM_AMS_MSWEP.png"
    B2="${DATA_DIR}heatmap_${METRIC}_BAM_GLB_MSWEP.png"
    C1="${DATA_DIR}heatmap_${METRIC}_GFS_AMS_MSWEP.png"
    C2="${DATA_DIR}heatmap_${METRIC}_GFS_GLB_MSWEP.png"

    echo "*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*"
    echo "Processing metric: $METRIC"
    echo "Output file: $OUTPUT_FILE"
    echo "*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*"

    # Check if all input files exist
    for file in $A1 $A2 $B1 $B2 $C1 $C2; do
        if [ ! -f "$file" ]; then
            echo "Error: File $file not found!"
            exit 1
        else
            echo "Found file: $file"
        fi
    done

    # Create the mosaic using montage (ImageMagick)
    montage $A1 $A2 $B1 $B2 $C1 $C2 -tile 2x3 -geometry +5+5 -title "${TITLE}" -pointsize 24 ${OUTPUT_FILE}
done





