#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified script for downloading monthly mean ERA5 pressure-level and surface data for obtaining 
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

def download_era5_monthly_mean_pressure_data(date, time, var_list, pressure_level_list, area,
                                             target_filename):
    """
    Download monthly-mean, pressure-level data from ERA5 for specific date, time, var_list, 
    pressure_level_list and area.
    """
    # Dataset definition
    dataset = "reanalysis-era5-pressure-levels-monthly-means"
    # Convert date to string format
    date = pd.to_datetime(date).strftime('%Y-%m-%d %H:%M')
    # Request definition
    request = {
        'product_type': ['monthly_averaged_reanalysis'],
        'variable': var_list,
        'year': [date[:4]],
        'month': [date[5:7]],
        'day': [date[8:10]],
        'time': [time],
        'pressure_level': pressure_level_list,
        'area': area,
        'format': 'grib',
        'download_format': 'unarchived'
    }

    print(f"Request details: {request}")
    client.retrieve(dataset, request).download(target_filename)
    print(f"Downloaded pressure data: {target_filename}")

def generate_monthly_time_steps(start_date, end_date):
    time_steps = []
    current_date = start_date
    while current_date <= end_date:
        time_steps.append(current_date.strftime('%Y-%m-%d'))  # Only include the date
        current_date += relativedelta(months=1)
    return time_steps

def download_for_time_range(start_date, end_date, area, output_dir, var_list, pl_list):
    """
    Downloads monthly data for all time steps within a given date range.
    """
    # Generate monthly time steps
    time_steps = generate_monthly_time_steps(start_date, end_date)
    # Loop through each time step and download data
    for date in time_steps:
        target_filename_pl = f'{output_dir}/era5_pl_{date.replace("-", "")}.grib'
        if os.path.exists(target_filename_pl):
            print(f"File already exists: {target_filename_pl}. Skipping download.")
        else:
            download_era5_monthly_mean_pressure_data(
                date=date, 
                time="00:00",  # Fixed time for monthly mean data
                var_list=var_list, 
                pressure_level_list=pl_list, 
                area=area,
                target_filename=target_filename_pl
            )

if __name__ == "__main__":
    # Data setup
    start_date = datetime.strptime('1991-01-15 00:00', '%Y-%m-%d %H:%M') # Simulation start date
    end_date = datetime.strptime('2020-12-15 00:00', '%Y-%m-%d %H:%M') # Simulation end date
    # Download area
    area = [-90, -180, 90, 180]  # Example area [South, West, North, East]
    # List of variables for download
    var_list = ["geopotential"]
    # List of pressure levels for download
    pl_list = ["500"]
## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
## !!!!!!!!!!! ATENCAO: DIRETORIO PARA SALVAR OS DADOS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! !!!!!!!!!!!
## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    output_dir = '/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/mon'  # Output directory
## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    download_for_time_range(
        start_date=start_date, 
        end_date=end_date,  
        area=area, 
        output_dir=output_dir,
        var_list=var_list,
        pl_list=pl_list
        )
