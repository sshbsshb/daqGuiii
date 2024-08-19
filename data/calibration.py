import os
import json
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

def process_calibration_file(file_path):
    reference_value = float(file_path.split('_')[-1].split('.')[0])
    df = pd.read_csv(file_path)
    channels = ['Channel_101', 'Channel_102', 'Channel_103'] + [f'Channel_{i}' for i in range(201, 211)]
    calibration_data = {}
    for channel in channels:
        channel_data = df[df['Channel'] == channel]['Data']
        if not channel_data.empty:
            channel_mean = channel_data.mean()
            calibration_data[channel] = (channel_mean, reference_value)
    return calibration_data

def plot_calibration(channel, data_points, slope, intercept, r_squared):
    x = [point[0] for point in data_points]  # Measured values
    y = [point[1] for point in data_points]  # Reference values

    plt.figure(figsize=(10, 6))
    plt.scatter(x, y, color='blue', label='Calibration Points')
    
    # Calculate points for the fitted line
    x_line = np.array([min(x), max(x)])
    y_line = slope * x_line + intercept
    plt.plot(x_line, y_line, color='red', label='Fitted Line')

    plt.xlabel('Measured Value')
    plt.ylabel('Reference Value')
    plt.title(f'Calibration Plot for {channel}')
    plt.legend(loc="lower right")
    plt.grid(True)

    # Add equation and R-squared to the plot
    equation = f'y = {slope:.4f}x + {intercept:.4f}'
    r_squared_text = f'R² = {r_squared:.4f}'
    plt.text(0.05, 0.95, equation + '\n' + r_squared_text, transform=plt.gca().transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.savefig(f'calibration_plot_{channel}.png')
    plt.close()

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

# Calculate final calibration coefficients (mx + b) and plot
final_coefficients = {}
for channel, data_points in all_calibration_data.items():
    x = [point[0] for point in data_points]  # Measured values
    y = [point[1] for point in data_points]  # Reference values
    
    # Perform linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_squared = r_value ** 2
    
    final_coefficients[channel] = {"m": slope, "b": intercept, "R2": r_squared}

    # Plot calibration data and fitted line
    plot_calibration(channel, data_points, slope, intercept, r_squared)

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
print("\nFinal Calibration Coefficients (mx + b) and R-squared:")
for channel, coeff in final_coefficients.items():
    print(f"{channel}: m = {coeff['m']:.6f}, b = {coeff['b']:.6f}, R² = {coeff['R2']:.6f}")

print("\nCalibration plots have been saved as 'calibration_plot_Channel_XXX.png'")