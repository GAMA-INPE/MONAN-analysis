#!/bin/bash

module load cdo

# Define input and output directories
INPUT_DIR="/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/mon/nc"  # Replace with the directory containing the ERA5 files
OUTPUT_DIR="/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/mon/nc_climatology"  # Replace with the directory for processed files
CLIMATOLOGY_FILE="$OUTPUT_DIR/climatology.nc"
CLIMATOLOGY_FILE_TEMP="$OUTPUT_DIR/climatology_temp.nc"
CONCATENATED_FILE="$OUTPUT_DIR/zgeo_concatenated.nc"

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Temporary directory for intermediate files
TEMP_DIR="$OUTPUT_DIR/temp"
mkdir -p "$TEMP_DIR"

# Loop through all files and convert geopotential to geopotential height
for file in "$INPUT_DIR"/era5_pl_??????15.nc; do
    # Extract the base filename
    base_name=$(basename "$file")
    
    # Define the output file path for geopotential height
    temp_file="$TEMP_DIR/$base_name"
    
    # Convert geopotential (z) to geopotential height (zgeo)
    # Formula: zgeo = z / g (where g = 9.80665 m/s²)
    cdo expr,'zgeo=var129/9.80665' "$file" "$temp_file"
    
    # Check if the conversion was successful
    if [ $? -eq 0 ]; then
        echo "Processed: $file -> $temp_file"
    else
        echo "Failed to process: $file"
        exit 1
    fi
done

# Concatenate all zgeo files into a single file
cdo mergetime "$TEMP_DIR"/era5_pl_??????15.nc "$CONCATENATED_FILE"

# Check if concatenation was successful
if [ $? -eq 0 ]; then
    echo "Files concatenated successfully: $CONCATENATED_FILE"
else
    echo "Failed to concatenate files"
    exit 1
fi

# Compute the monthly climatology over the 30 years
cdo ymonmean "$CONCATENATED_FILE" "$CLIMATOLOGY_FILE_TEMP"

# Check if climatology computation was successful
if [ $? -eq 0 ]; then
    echo "Monthly climatology computed successfully: $CLIMATOLOGY_FILE_TEMP"
else
    echo "Failed to compute monthly climatology"
    exit 1
fi

# Change the dimension name from plev to level
cdo chname,plev,level,lat,latitude,lon,longitude,time,Time "$CLIMATOLOGY_FILE_TEMP" "$CLIMATOLOGY_FILE"

if [ $? -eq 0 ]; then
    echo "plev changed to level successfully: $CLIMATOLOGY_FILE"
else
    echo "Failed to change plev to level"
    exit 1
fi

# Clean up temporary files
#rm -rf "$TEMP_DIR"

echo "All processing complete."
