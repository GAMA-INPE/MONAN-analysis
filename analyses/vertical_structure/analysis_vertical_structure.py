# -*- coding: utf-8 -*-
"""
Based on a script by Andre Lyra (andre.lyra@inpe.br)
Last update: Feb 2026 by Guilherme Torres Mendonça (guilherme.mendonca@inpe.br)

Description
-----------
Takes in data from MONAN and from GFS and performs an analysis of the vertical structure of MONAN.

Steps:
1. Read data from MONAN and from GFS
2. Preprocess data
3. Calculate statistics
4. Plot and save results

Input
-----
- ds_monan (xr.Dataset): netcdf file containing MONAN data
- ds_gfs (xr.Dataset): netcdf file containing GFS data

Output
------
- RMSE values
- Analysis maps

Main variables
--------------
- RMSE (float64): root mean square error
"""

if __name__ == "__main__":
    # read MONAN data
    read_monan_data()

    # read GFS data
    read_gfs_data()

    # preprocess data
    preprocess()

    # plot results
    plot()

    # save output
    save_output()
