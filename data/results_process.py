import pandas as pd
import numpy as np
import json
from scipy import stats

# Read the CSV file
df = pd.read_csv('data\data_2024-07-17_14-44-16.csv')

# Convert Timestamp to datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Load calibration coefficients
with open('calibration_coefficients.json', 'r') as f:
    calibration_coeffs = json.load(f)

# Function to identify steady states
def identify_steady_states(df, time_threshold=2, min_group_size=3):
    steady_states = []
    current_state = [0]
    for i in range(1, len(df)):
        time_diff = (df['Timestamp'].iloc[i] - df['Timestamp'].iloc[i-1]).total_seconds()
        if time_diff > time_threshold:
            if len(current_state) >= min_group_size:
                steady_states.append(current_state)
            current_state = [i]
        else:
            current_state.append(i)
    if len(current_state) >= min_group_size:
        steady_states.append(current_state)
    return steady_states

# Identify steady states
steady_states = identify_steady_states(df, time_threshold=1.5, min_group_size=2)

# Calculate statistics for each channel in each steady state
channels = df['Channel'].unique()
results = {channel: {'mean': [], 'std': []} for channel in channels}

for state in steady_states:
    state_data = df.iloc[state]
    for channel in channels:
        channel_data = state_data[state_data['Channel'] == channel]['Data']
        if not channel_data.empty:
            mean_value = channel_data.mean()
            std_value = channel_data.std()
            results[channel]['mean'].append(mean_value)
            results[channel]['std'].append(std_value)

# Apply calibration and create final results
calibrated_results = {channel: {'mean': [], 'std': []} for channel in channels}

for channel, values in results.items():
    if channel in calibration_coeffs:
        m = calibration_coeffs[channel]['m']
        b = calibration_coeffs[channel]['b']
        calibrated_means = [m * value + b for value in values['mean']]
        calibrated_stds = [m * value for value in values['std']]  # Standard deviation is scaled by m
        calibrated_results[channel]['mean'] = calibrated_means
        calibrated_results[channel]['std'] = calibrated_stds
    else:
        print(f"Warning: No calibration coefficient found for {channel}. Using raw values.")
        calibrated_results[channel] = values

# Print results
print("Calibrated Results:")
for channel, values in calibrated_results.items():
    print(f"{channel}:")
    for i in range(len(values['mean'])):
        print(f"  Steady State {i+1}: Mean = {values['mean'][i]:.6f}, Std Dev = {values['std'][i]:.6f}")
    print()

# Save results to a CSV file
result_df = pd.DataFrame({f"{channel}_mean": values['mean'] for channel, values in calibrated_results.items()})
result_df = result_df.join(pd.DataFrame({f"{channel}_std": values['std'] for channel, values in calibrated_results.items()}))
result_df.to_csv('calibrated_steady_state_results.csv', index=False)
print("Calibrated results saved to 'calibrated_steady_state_results.csv'")

# Calculate overall statistics
overall_stats = {}
for channel, values in calibrated_results.items():
    means = np.array(values['mean'])
    overall_mean = np.mean(means)
    overall_std = np.std(means)
    overall_stats[channel] = {'mean': overall_mean, 'std': overall_std}

# Print overall statistics
print("\nOverall Statistics:")
for channel, stats in overall_stats.items():
    print(f"{channel}: Mean = {stats['mean']:.6f}, Std Dev = {stats['std']:.6f}")

# Save overall statistics to a CSV file
overall_df = pd.DataFrame(overall_stats).T
overall_df.to_csv('overall_statistics.csv')
print("Overall statistics saved to 'overall_statistics.csv'")