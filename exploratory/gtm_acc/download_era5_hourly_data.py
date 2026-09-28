#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified script for downloading hourly ERA5 pressure-level and surface data for obtaining 
climatologies. Supports global and regional data.

The script automatically handles downloading data for specified date ranges and timesteps.

Adapted from download_era5_data.py by:
   Danilo Couto de Souza
   Universidade de São Paulo (USP)
   São Paulo, Brazil
   danilo.oceano@gmail.com
"""

import os
import cdsapi
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Create the CDSAPI client
client = cdsapi.Client()

def download_era5_hourly_pressure_data(year, time, var_list, pressure_level_list, area,
                                             target_filename):
    """
    Download hourly pressure-level data from ERA5 for specific date, time, var_list, 
    pressure_level_list and area.
    """
    # Dataset definition
    dataset = "reanalysis-era5-pressure-levels"
    # Request definition
    request = {
        'product_type': ['reanalysis'],
        'variable': var_list,
        'year': [str(year)],
        'month': [f"{m:02d}" for m in range(1, 13)],
        'day': [f"{d:02d}" for d in range(1, 32)],
        'time': [time],
        'pressure_level': pressure_level_list,
        'area': area,
        'format': 'grib',
        'download_format': 'unarchived'
    }

    print(f"Request details: {request}")
    client.retrieve(dataset, request).download(target_filename)
    print(f"Downloaded pressure data: {target_filename}")

def generate_hourly_time_steps(start_date, end_date):
    time_steps = []
    current_date = start_date
    while current_date <= end_date:
        time_steps.append(current_date.strftime('%Y-%m-%d-%H'))
        current_date += timedelta(days=1)  # Increment by one day
    return time_steps

def download_for_time_range(start_year, end_year, hour, area, output_dir, var_list, pl_list):
    """
    Downloads hourly data for all years within given time range.
    """

    # Loop through each time step and download data
    for year in range(start_year, end_year + 1):
        target_filename_pl = f'{output_dir}/era5_hourly_pl_{year}.grib'
        if os.path.exists(target_filename_pl):
            print(f"File already exists: {target_filename_pl}. Skipping download.")
        else:
            download_era5_hourly_pressure_data(
                year=year, 
                time=hour,
                var_list=var_list, 
                pressure_level_list=pl_list, 
                area=area,
                target_filename=target_filename_pl
            )

if __name__ == "__main__":
    # Data setup
    start_year = 1991
    end_year = 1992
    hour = "00:00"
    # Download area
    area = [-90, -180, 90, 180]  # Example area [South, West, North, East]
    # List of variables for download
    var_list = ["geopotential"]
    # List of pressure levels for download
    pl_list = ["500"]
## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
## !!!!!!!!!!! ATENCAO: DIRETORIO PARA SALVAR OS DADOS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! !!!!!!!!!!!
## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    output_dir = '/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/hourly/grib'  # Output directory
## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    download_for_time_range(
        start_year=start_year, 
        end_year=end_year,  
        hour=hour,
        area=area, 
        output_dir=output_dir,
        var_list=var_list,
        pl_list=pl_list
        )
