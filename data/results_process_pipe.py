import json
import pandas as pd
import numpy as np
import os
from glob import glob

# Load calibration coefficients
with open('data/calibration_coefficients.json', 'r') as f:
    calibration_coeffs = json.load(f)

# Function to apply calibration
def apply_calibration(value, channel):
    m = calibration_coeffs[channel]['m']
    b = calibration_coeffs[channel]['b']
    return m * value + b

# Function to process data for a single file
def process_file(file_path):
    # Read CSV file
    df = pd.read_csv(file_path)
    
    # Extract relevant channels
    channels = ['Channel_106', 'Channel_107', 'Channel_108']
    data = {channel: df[df['Channel'] == channel]['Data'].values for channel in channels}
    
    # Apply calibration
    for channel in channels:
        data[channel] = apply_calibration(data[channel], channel)
    
    # Create DataFrame with processed data
    processed_df = pd.DataFrame({
        'p1': data['Channel_106'],
        'p2': data['Channel_107'],
        'flow_rate': data['Channel_108']
    })
    
    return processed_df

# Function to calculate statistics for each flow rate
def calculate_stats(df, flow_rates):
    stats = []
    for flow_rate in flow_rates:
        # Find data points close to the target flow rate
        mask = (df['flow_rate'] >= flow_rate - 0.1) & (df['flow_rate'] <= flow_rate + 0.1)
        subset = df[mask]
        
        if len(subset) > 0:
            stats.append({
                'flow_rate': flow_rate,
                'p1_mean': subset['p1'].mean(),
                'p1_std': subset['p1'].std(),
                'p2_mean': subset['p2'].mean(),
                'p2_std': subset['p2'].std(),
                'flow_rate_mean': subset['flow_rate'].mean(),
                'flow_rate_std': subset['flow_rate'].std(),
                'sample_count': len(subset)
            })
    
    return pd.DataFrame(stats)

# Main processing
flow_rates = [0.85, 1.0, 1.5, 2.0, 2.5]

# Find all pipe test data files
data_files = glob('data/*pipe_test.csv')

for file_path in data_files:
    # Process file
    processed_df = process_file(file_path)
    
    # Calculate statistics
    stats_df = calculate_stats(processed_df, flow_rates)
    
    # # Create processed folder if it doesn't exist
    # os.makedirs('processed', exist_ok=True)
    
    # Save processed data
    output_file = os.path.join('data', 'processed', f'processed_{os.path.basename(file_path)}')
    stats_df.to_csv(output_file, index=False)
    print(f"Processed data saved to {output_file}")

print("All files processed successfully.")