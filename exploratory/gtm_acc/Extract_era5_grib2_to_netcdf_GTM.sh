#!/bin/bash

module load cdo

# Define source and destination directories
SOURCE_DIR="/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/mon/grib"  # Replace with the folder containing GRIB files
DEST_DIR="/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/mon/nc"  # Replace with the folder for NetCDF files

# Create the destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Loop through all GRIB files in the source directory
for grib_file in "$SOURCE_DIR"/*.grib; do
    # Extract the base filename without extension
    base_name=$(basename "$grib_file" .grib)
    
    # Define the output NetCDF file path
    nc_file="$DEST_DIR/$base_name.nc"
    
    # Convert GRIB to NetCDF using cdo
    cdo -f nc copy "$grib_file" "$nc_file"
    
    # Check if the conversion was successful
    if [ $? -eq 0 ]; then
        echo "Converted: $grib_file -> $nc_file"
    else
        echo "Failed to convert: $grib_file"
    fi
done
