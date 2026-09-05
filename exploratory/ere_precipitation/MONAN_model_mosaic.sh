#!/bin/bash

# Gather the output path and analysis names from command line arguments
OUTPUT_PATH="$1"
shift

# Output directory
OUTPUT_DIR=${OUTPUT_PATH}compare

# Create output directory if it doesn't exist
mkdir -p ${OUTPUT_DIR}

# Metrics to process
METRICS=("POD" "CSI" "ETS" "F1" "F05")

for METRIC in "${METRICS[@]}"; do

    # Title for the mosaic
    TITLE="${METRIC} - South America and Global"

    # Initialize an array to hold the tile image paths
    TILES=()

    for analysis in "$@"; do
        # Set the analysis name for this iteration
        ANALYSIS_NAME="$analysis"
        
        # Data directory where the heatmap images are stored
        DATA_DIR=${OUTPUT_PATH}Skill/${ANALYSIS_NAME}/Skill_fig_mensal/heatmap_lead_threshold/

        # Add the corresponding heatmap images to the TILES array
        TILES+=("${DATA_DIR}heatmap_${METRIC}_${ANALYSIS_NAME}_AMS_MSWEP.png")
        TILES+=("${DATA_DIR}heatmap_${METRIC}_${ANALYSIS_NAME}_GLB_MSWEP.png")
        
    done

    for file in "${TILES[@]}"; do
        if [ ! -f "$file" ]; then
            echo "Error: File $file not found!"
            exit 1
        else
            echo "Found file: $file"
        fi
    done

    # Output file for this mosaic
    OUTPUT_FILE="${OUTPUT_DIR}/compare_${METRIC}_MSWEP.png"

    # Create the mosaic using montage (ImageMagick)
    montage "${TILES[@]}" -tile 2x3 -geometry +5+5 -title "${TITLE}" -pointsize 24 "${OUTPUT_FILE}"
    echo "Mosaic saved: ${OUTPUT_FILE}"

done