import pandas as pd
import matplotlib.pyplot as plt

# Dir with input data
input_dir = "/lustre/projetos/monan_atm/guilherme.mendonca/MONAN-analysis/analyses/vertical_structure/results/output/data"

# Define list of forecast days
list_of_forecast_days = ["024", "048", "072", "096", "120", "144", "168", "192", "216", "240"]

acc_list = []
for forecast_day in list_of_forecast_days:
    # Read csv containing acc value
    acc_df = pd.read_csv(f"{input_dir}/date_2026060100_time_window_{forecast_day}/anomaly_correlation_coefficient_standard_date_2026060100_time_window_{forecast_day}.csv")
    acc_list.append(acc_df["mean"].values[3])

# plot forecast day vs acc
plt.figure(figsize=(10, 6))
plt.plot(list_of_forecast_days, acc_list, marker='o')
plt.title("Anomaly Correlation Coefficient (ACC) vs Forecast Hour - GFS")
plt.xlabel("Forecast Hour")
plt.ylabel("Anomaly Correlation Coefficient (ACC)")
plt.grid()
plt.savefig(f"output_figures/acc_curve_gfs.png", dpi=300)