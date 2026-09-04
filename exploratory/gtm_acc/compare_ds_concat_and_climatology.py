import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# Function to plot zgeo map for a specific month
def plot_zgeo_map(ds1_filepath, ds2_filepath, month, level=50000, output_dir="./"):
    """
    Reads two datasets, extracts zgeo for a specific month, and saves the maps.

    Parameters:
        ds1_filepath (str): Filepath for the first dataset.
        ds2_filepath (str): Filepath for the second dataset.
        month (int): Month to extract (1-12).
        level (int): Pressure level to extract (default: 50000 Pa).
        output_dir (str): Directory to save the output figures.
    """
    # Load datasets
    ds1 = xr.open_dataset(ds1_filepath)
    ds2 = xr.open_dataset(ds2_filepath)

    print (ds1.coords)
    print (ds2.coords)
    ds2 = get_era5_in_monan_format(ds2, gfs_to_monan_var_dict={})
    print ("after conversion:")
    print ("monan:")
    print (ds1.coords)
    print ("era5:")
    print (ds2.coords)

    # Extract zgeo for the specified month and level
    zgeo_ds1 = ds1['zgeo'].sel(Time=ds1['Time'].dt.month == month, level=level).mean(dim='Time')
    zgeo_ds2 = ds2['zgeo'].sel(Time=ds2['Time'].dt.month == month, level=level).mean(dim='Time')

    # Plot and save the first dataset
    plt.figure(figsize=(12, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_global()
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, edgecolor='black', facecolor='lightgray')

    zgeo_ds1.plot(ax=ax, transform=ccrs.PlateCarree(), cmap='viridis', cbar_kwargs={'label': 'Geopotential Height (m)'})
    plt.title(f"Zgeo Map (Dataset 1) - Month: {month}")
    output_file_ds1 = f"{output_dir}/zgeo_map_dataset1_month_{month}.png"
    plt.savefig(output_file_ds1, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_file_ds1}")

    # Plot and save the second dataset
    plt.figure(figsize=(12, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_global()
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, edgecolor='black', facecolor='lightgray')

    zgeo_ds2.plot(ax=ax, transform=ccrs.PlateCarree(), cmap='viridis', cbar_kwargs={'label': 'Geopotential Height (m)'})
    plt.title(f"Zgeo Map (Dataset 2) - Month: {month}")
    output_file_ds2 = f"{output_dir}/zgeo_map_dataset2_month_{month}.png"
    plt.savefig(output_file_ds2, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_file_ds2}")

    # Save converted ds2 to a new NetCDF file
    ds2.to_netcdf(f"/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/mon/nc_climatology/climatology_in_monan_format.nc")

def get_era5_in_monan_format(ds_era5, gfs_to_monan_var_dict):
    # Sort by latitude
    ds_era5 = ds_era5.sortby('latitude')

    # Convert longitude from -180 -> 180 to 0 -> 360
    #ds_era5 = ds_era5.assign_coords(longitude=(ds_era5.longitude + 360) % 360)

    ds_era5['longitude'] = (ds_era5['longitude'] + 180) % 360

    # Sort by level
    ds_era5 = ds_era5.sortby('level', ascending=False)
    
    print ("ds_era5 coords after sorting and longitude conversion:")
    print (ds_era5.coords)

    # Rename time variable and coord from time to Time
    ds_era5_in_monan_format = ds_era5.rename({'time': 'Time'})

    return ds_era5_in_monan_format

# Example usage
if __name__ == "__main__":
    # Replace with the paths to your datasets
    ds1_gfs_filepath = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/results/old/input/processed/prediction_gfs_concat_date_from_2026070100_to_2026070200_time_window_120.nc"
    ds2_era5_filepath = "/lustre/projetos/monan_atm/guilherme.mendonca/scratch/data/ERA5/mon/nc_climatology/climatology.nc"

    # Specify the month to plot (e.g., January = 1)
    month = 7

    output_dir = "./output_figures"

    # Call the function to plot zgeo maps
    plot_zgeo_map(ds1_gfs_filepath, ds2_era5_filepath, month,  output_dir=output_dir)