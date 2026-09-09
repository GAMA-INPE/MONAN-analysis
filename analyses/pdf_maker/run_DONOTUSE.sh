#!/bin/bash

# Extract configurations from pdf_maker_config.py
DIR_INPUT=$(grep "DIR_INPUT" pdf_maker_config.py | cut -d '"' -f 2)
FILENAME_INPUT=$(grep "FILENAME_INPUT" pdf_maker_config.py | cut -d '"' -f 2)

# Check if the variables are set
if [[ -z "$DIR_INPUT" || -z "$FILENAME_INPUT" ]]; then
  echo "Error: Could not read configurations from pdf_maker_config.py"
  exit 1
fi

# Run the Python script with the extracted configurations
python3 pdf_maker_main.py --input-dir "$DIR_INPUT" --input-file "$FILENAME_INPUT"