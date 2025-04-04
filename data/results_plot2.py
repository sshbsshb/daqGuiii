import pandas as pd
import os
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from itertools import cycle
from sklearn.cluster import KMeans

# Constants and configurations
DATA_FOLDER = 'data'
SAVE_FOLDER = 'processed'
FILE_GROUP = 'uniform'
FIG_FILE = 'figure'
BASE_SAVE_PATH = os.path.join(DATA_FOLDER, SAVE_FOLDER, FILE_GROUP)
HEATER_CHANNELS = ['Channel_201_mean', 'Channel_202_mean', 'Channel_203_mean', 
                   'Channel_208_mean', 'Channel_209_mean', 'Channel_210_mean']
COLORS = plt.cm.tab20(np.linspace(0, 1, 20))
MARKERS = ['o', 's', 'D', '^', 'v', '<', '>', 'p', '*', 'h', 'H', '+', 'x', 'd', '|', '_']

# def assign_flow_group(flow):
#     # Define nominal flow rates as a list or a more complex structure if your settings vary widely
#     nominal_rates = [0.5, 0.9, 1.6, 2.0, 2.6]  # Example nominal rates

#     # Round the flow to the nearest 0.1
#     rounded_flow = round(flow, 1)

#     # Find the closest nominal rate
#     closest_nominal = min(nominal_rates, key=lambda x: abs(x - rounded_flow))

#     # Check if the rounded flow is within ±0.1 of the closest nominal rate
#     if abs(rounded_flow - closest_nominal) <= 0.19:
#         return closest_nominal
#     else:
#         return None  # or handle as needed for flows that do not fit any group

def find_nominal_rates(flow_data, n_clusters):
    # Reshape flow data for clustering (sklearn expects a 2D array)
    flow_data_reshaped = np.array(flow_data).reshape(-1, 1)
    
    # Apply k-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(flow_data_reshaped)
    
    # Get the cluster centers (nominal rates)
    nominal_rates = kmeans.cluster_centers_.flatten()
    
    return sorted(nominal_rates)

def assign_flow_group(flow, nominal_rates):
    # Find the closest nominal rate
    closest_nominal = min(nominal_rates, key=lambda x: abs(x - flow))
    
    # Define a tolerance within which flow rate is considered part of the nominal group
    tolerance = 0.1
    
    if abs(flow - closest_nominal) <= tolerance:
        return closest_nominal
    else:
        return None

def process_csv(file_path):
    df = pd.read_csv(file_path)
    nominal_rates = find_nominal_rates(df['Actual_Flow_Rate'], n_clusters=5)  # Adjust n_clusters based on expected number of nominal rates

    # df['Flow_Group'] = df['Channel_108_mean'].apply(assign_flow_group)
    df['Flow_Group'] = df['Actual_Flow_Rate'].apply(lambda x: assign_flow_group(x, nominal_rates))
    config = os.path.basename(file_path).split('_')[1].split('.')[0]
    highest_power_data = df.iloc[8::9]
    
    results = []
    for _, row in highest_power_data.iterrows():
        result = {
            'Configuration': config,
            'Flow_Rate': row['Flow_Group'],
            'Actual_Flow_Rate': row['Channel_108_mean']
        }
        for channel in HEATER_CHANNELS:
            result[channel] = row[channel]
            std_channel = channel.replace('_mean', '_std')
            if std_channel in row:
                result[std_channel] = row[std_channel]
        results.append(result)
    
    return results

def plot_temp_vs_flow_power(df, config, channel):
    plt.figure(figsize=(15, 10))
    power_levels = sorted(df['Power'].unique())
    color_cycle = cycle(COLORS)
    marker_cycle = cycle(MARKERS)
    
    for power in power_levels:
        power_data = df[(df['Configuration'] == config) & (df['Power'] == power)]
        color = next(color_cycle)
        marker = next(marker_cycle)
        
        x = power_data['Actual_Flow_Rate']
        y = power_data[channel]
        yerr = power_data[channel.replace('_mean', '_std')]
        
        plt.errorbar(x, y, yerr=yerr, 
                     marker=marker, linestyle='-', linewidth=2, markersize=8,
                     label=f'{power}W', color=color, capsize=5, capthick=2, elinewidth=1)
    plt.ylim(30, 60)
    plt.xlabel('Actual Flow Rate (L/min)', fontsize=12)
    plt.ylabel('Temperature (°C)', fontsize=12)
    plt.title(f'{channel} Temperature vs Flow Rate for Configuration {config}', fontsize=14)
    plt.legend(title='Power', fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.7)
    # plt.gca().invert_xaxis()
    plt.tight_layout()
    save_path = os.path.join(FIG_FILE, f'{channel}_vs_flow_power_config_{config}_with_error.png')
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()

def plot_highest_power_temps(result_df):
    for config in result_df['Configuration'].unique():
        plt.figure(figsize=(15, 10))
        config_data = result_df[result_df['Configuration'] == config]
        
        for i, channel in enumerate(HEATER_CHANNELS):
            std_channel = channel.replace('_mean', '_std')
            if std_channel in config_data.columns:
                plt.errorbar(config_data['Actual_Flow_Rate'], config_data[channel], 
                             yerr=config_data[std_channel],
                             color=COLORS[i], marker=MARKERS[i], linestyle='-', linewidth=2, markersize=8,
                             label=channel, capsize=5, capthick=2, elinewidth=1)
            else:
                plt.plot(config_data['Actual_Flow_Rate'], config_data[channel], 
                         color=COLORS[i], marker=MARKERS[i], linestyle='-', linewidth=2, markersize=8,
                         label=channel)
        plt.ylim(30, 60)
        plt.xlabel('Actual Flow Rate (L/min)', fontsize=12)
        plt.ylabel('Temperature (°C)', fontsize=12)
        plt.title(f'Heater Temperatures vs Actual Flow Rate for Configuration {config} (at 16W)', fontsize=14)
        plt.legend(fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.7)
        # plt.gca().invert_xaxis()
        plt.tight_layout()
        save_path = os.path.join(FIG_FILE, f'temperatures_vs_actual_flow_rate_16W_config_{config}.png')
        plt.savefig(save_path)
        plt.close()

def plot_channel_203_all_configs(result_df):
    plt.figure(figsize=(15, 10))

    for i, config in enumerate(result_df['Configuration'].unique()):
        config_data = result_df[result_df['Configuration'] == config]
        if 'Channel_203_std' in config_data.columns:
            plt.errorbar(config_data['Actual_Flow_Rate'], config_data['Channel_203_mean'], 
                         yerr=config_data['Channel_203_std'],
                         color=COLORS[i], marker=MARKERS[i], linestyle='-', linewidth=2, markersize=8,
                         label=f'Config {config}', capsize=5, capthick=2, elinewidth=1)
        else:
            plt.plot(config_data['Actual_Flow_Rate'], config_data['Channel_203_mean'], 
                     color=COLORS[i], marker=MARKERS[i], linestyle='-', linewidth=2, markersize=8,
                     label=f'Config {config}')
    plt.ylim(30, 60)
    plt.xlabel('Actual Flow Rate (L/min)', fontsize=12)
    plt.ylabel('Temperature (°C)', fontsize=12)
    plt.title('Channel 203 Temperature vs Actual Flow Rate for All Configurations (at 16W)', fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    # plt.gca().invert_xaxis()
    plt.tight_layout()
    save_path = os.path.join(FIG_FILE, 'channel203_all_configs_16W.png')
    plt.savefig(save_path)
    plt.close()

def plot_channel_all_configs(result_df, channel_name='202'):
    plt.figure(figsize=(15, 10))

    for i, config in enumerate(result_df['Configuration'].unique()):
        config_data = result_df[result_df['Configuration'] == config]
        if f'Channel_{channel_name}_std' in config_data.columns:
            plt.errorbar(config_data['Actual_Flow_Rate'], config_data[f'Channel_{channel_name}_mean'], 
                         yerr=config_data[f'Channel_{channel_name}_std'],
                         color=COLORS[i], marker=MARKERS[i], linestyle='-', linewidth=2, markersize=8,
                         label=f'Config {config}', capsize=5, capthick=2, elinewidth=1)
        else:
            plt.plot(config_data['Actual_Flow_Rate'], config_data[f'Channel_{channel_name}_mean'], 
                     color=COLORS[i], marker=MARKERS[i], linestyle='-', linewidth=2, markersize=8,
                     label=f'Config {config}')
    plt.ylim(30, 60)
    plt.xlabel('Actual Flow Rate (L/min)', fontsize=12)
    plt.ylabel('Temperature (°C)', fontsize=12)
    plt.title(f'Channel_{channel_name} Temperature vs Actual Flow Rate for All Configurations (at 16W)', fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    # plt.gca().invert_xaxis()
    plt.tight_layout()
    save_path = os.path.join(FIG_FILE, f'Channel_{channel_name}_all_configs_16W.png')
    plt.savefig(save_path)
    plt.close()

def main():
    # Process highest power data
    csv_files = glob.glob(f'{BASE_SAVE_PATH}\\calibrated_*.csv')
    all_results = []
    for file in csv_files:
        all_results.extend(process_csv(file))

    result_df = pd.DataFrame(all_results)
    result_df = result_df.sort_values(['Configuration', 'Flow_Rate'], ascending=[True, False])

    print(result_df)
    save_path = os.path.join(FIG_FILE, 'highest_power_temperatures.csv')
    result_df.to_csv(save_path, index=False)
    print("Results saved to 'highest_power_temperatures.csv'")

    # Load full dataset
    full_data = pd.DataFrame()
    for file in csv_files:
        df = pd.read_csv(file)
        config = os.path.basename(file).split('_')[1].split('.')[0]
        df['Configuration'] = config
        full_data = pd.concat([full_data, df], ignore_index=True)

    # Generate plots
    for config in full_data['Configuration'].unique():
        for channel in HEATER_CHANNELS:
            plot_temp_vs_flow_power(full_data, config, channel)

    plot_highest_power_temps(result_df)
    # plot_channel_203_all_configs(result_df)
    for name in [201, 202, 203, 208, 209, 210]:
        plot_channel_all_configs(result_df, channel_name=f'{name}')

    print("All plots have been updated with error bars and saved as PNG files in the current directory.")

if __name__ == "__main__":
    main()