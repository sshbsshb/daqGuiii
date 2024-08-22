import os
import pandas as pd
import numpy as np
import json
import re
from scipy import stats

def extract_config(filename):
    # Try to match the pattern for both 'cc' and 'c0', 'c1', 'c2', etc.
    # This pattern now accounts for both hyphen and underscore before the config
    match = re.search(r'[_-]((?:cc|c\d+))(?:[_-]|\.)', filename)
    if match:
        return match.group(1)
    else:
        print(f"Warning: Could not extract configuration from filename: {filename}")
        return 'unknown'

def process_csv_file(file_path, calibration_coeffs):
    # Extract configuration from filename
    file_name = os.path.basename(file_path)
    config = extract_config(file_name)

    # Read the CSV file
    df = pd.read_csv(file_path)

    # Convert Timestamp to datetime
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])

    # Group data by Timestamp
    grouped = df.groupby('Timestamp')

    # Identify steady states
    steady_states = identify_steady_states(grouped)

    # Calculate statistics for each channel in each steady state
    channels = df['Channel'].unique()
    results = {channel: {'raw_data': []} for channel in channels}

    for state in steady_states:
        state_data = pd.concat(state)
        for channel in channels:
            channel_data = state_data[state_data['Channel'] == channel]['Data']
            if not channel_data.empty:
                results[channel]['raw_data'].append(channel_data.tolist())

    # Apply calibration and calculate statistics
    calibrated_results = {channel: {'mean': [], 'std': []} for channel in channels}

    for channel, values in results.items():
        if channel in calibration_coeffs:
            m = calibration_coeffs[channel]['m']
            b = calibration_coeffs[channel]['b']
            for raw_data in values['raw_data']:
                calibrated_data = [m * value + b for value in raw_data]
                calibrated_results[channel]['mean'].append(np.mean(calibrated_data))
                calibrated_results[channel]['std'].append(np.std(calibrated_data))
        else:
            print(f"Warning: No calibration coefficient found for {channel}. Using raw values.")
            for raw_data in values['raw_data']:
                calibrated_results[channel]['mean'].append(np.mean(raw_data))
                calibrated_results[channel]['std'].append(np.std(raw_data))

    # Create result DataFrame
    result_df = pd.DataFrame({f"{channel}_mean": values['mean'] for channel, values in calibrated_results.items()})
    result_df = result_df.join(pd.DataFrame({f"{channel}_std": values['std'] for channel, values in calibrated_results.items()}))

    # Add flow rate information
    flow_rates = [2.5, 2.0, 1.5, 1.0, 0.88]
    result_df['Nominal_Flow_Rate'] = np.repeat(flow_rates, 9)  # 9 power levels for each flow rate

    # Add power level information
    power_levels = list(range(0, 18, 2))  # [0, 2, 4, 6, 8, 10, 12, 14, 16]
    result_df['Power'] = power_levels * 5  # 5 flow rates

    # Add actual flow rate (assuming it's in Channel_108_mean)
    result_df['Actual_Flow_Rate'] = result_df['Channel_108_mean']

    return result_df, config

def identify_steady_states(grouped, time_threshold=3):
    steady_states = []
    current_state = []
    prev_time = None
    
    for time, group in grouped:
        if prev_time is not None:
            time_diff = (time - prev_time).total_seconds()
            if time_diff > time_threshold:
                if current_state:
                    steady_states.append(current_state)
                current_state = [group]
            else:
                current_state.append(group)
        else:
            current_state.append(group)
        prev_time = time
    
    if current_state:
        steady_states.append(current_state)
    
    return steady_states

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Load calibration coefficients
with open('data/calibration_coefficients.json', 'r') as f:
    calibration_coeffs = json.load(f)

# Specify the folder containing CSV files
data_folder = 'data'
file_group = 'uniform'
file_folder = os.path.join(data_folder, file_group)
save_folder = 'processed'
base_save_path = os.path.join(data_folder, save_folder, file_group)
ensure_dir(base_save_path)

# Process all CSV files in the folder
for filename in os.listdir(file_folder):
    if filename.endswith('.csv'):
        file_path = os.path.join(file_folder, filename)
        print(f"Processing {filename}...")

        result_df, config = process_csv_file(file_path, calibration_coeffs)

        # Save results to CSV files
        save_name = f'calibrated_{config}.csv'
        full_save_path = os.path.join(base_save_path, save_name)
        
        result_df.to_csv(full_save_path, index=False)

        print(f"Calibrated results saved to '{full_save_path}'")

        print(f"Finished processing {filename}\n")

print("All files processed.")