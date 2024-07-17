import os
import json
import pandas as pd
import numpy as np
from scipy import stats

def process_calibration_file(file_path):
    # Extract reference value from filename
    reference_value = float(file_path.split('_')[-1].split('.')[0])
    
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Channels to process
    channels = ['Channel_101', 'Channel_102', 'Channel_103'] + [f'Channel_{i}' for i in range(201, 211)]
    
    calibration_data = {}
    
    for channel in channels:
        channel_data = df[df['Channel'] == channel]['Data']
        if not channel_data.empty:
            # Calculate mean of channel data
            channel_mean = channel_data.mean()
            
            calibration_data[channel] = (channel_mean, reference_value)
    
    return calibration_data

# Directory containing calibration files
cal_directory = "data/cal"

all_calibration_data = {}

# Traverse all files in the calibration directory
for filename in os.listdir(cal_directory):
    if filename.endswith(".csv"):
        file_path = os.path.join(cal_directory, filename)
        calibration_data = process_calibration_file(file_path)
        
        for channel, data in calibration_data.items():
            if channel not in all_calibration_data:
                all_calibration_data[channel] = []
            all_calibration_data[channel].append(data)

# Calculate final calibration coefficients (mx + b)
final_coefficients = {}
for channel, data_points in all_calibration_data.items():
    x = [point[0] for point in data_points]  # Measured values
    y = [point[1] for point in data_points]  # Reference values
    
    # Perform linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    
    final_coefficients[channel] = {"m": slope, "b": intercept}

# Load existing coefficients if the file exists
json_file = "calibration_coefficients.json"
if os.path.exists(json_file):
    with open(json_file, 'r') as f:
        existing_coefficients = json.load(f)
    # Update existing coefficients with new ones
    existing_coefficients.update(final_coefficients)
    final_coefficients = existing_coefficients

# Save the coefficients to a JSON file
with open(json_file, 'w') as f:
    json.dump(final_coefficients, f, indent=4)

print(f"Calibration coefficients have been saved to '{json_file}'")

# Print the final calibration coefficients
print("\nFinal Calibration Coefficients (mx + b):")
for channel, coeff in final_coefficients.items():
    print(f"{channel}: m = {coeff['m']:.6f}, b = {coeff['b']:.6f}")