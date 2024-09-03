import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os

### pressure drop curve fitting with inlet and outlet pressure curves separately

def quadratic_fit(x, a, b, c):
    return a * x**2 + b * x + c

def read_data(file_path):
    return pd.read_csv(file_path)

def fit_pressure_curve(flow_rates, pressures):
    popt, _ = curve_fit(quadratic_fit, flow_rates, pressures)
    return popt

def r_squared(x, y, popt):
    residuals = y - quadratic_fit(x, *popt)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    return 1 - (ss_res / ss_tot)

def plot_pressure_fits(df, p1_fit, p2_fit, title, flow_col, p1_col, p2_col):
    plt.figure(figsize=(12, 8))
    
    # Scatter plot of all data points
    plt.scatter(df[flow_col], df[p1_col], label='Inlet Pressure')
    plt.scatter(df[flow_col], df[p2_col], label='Outlet Pressure')
    
    # Generate points for the fitted curve between 0.5 and 2.5 L/min
    x_fit = np.linspace(df[flow_col].min(), df[flow_col].max(), 100)
    y1_fit = quadratic_fit(x_fit, *p1_fit)
    y2_fit = quadratic_fit(x_fit, *p2_fit)
    
    plt.plot(x_fit, y1_fit, 'r-', label='Inlet Fit')
    plt.plot(x_fit, y2_fit, 'b-', label='Outlet Fit')
    
    r2_p1 = r_squared(df[flow_col], df[p1_col], p1_fit)
    r2_p2 = r_squared(df[flow_col], df[p2_col], p2_fit)
    
    plt.xlabel('Flow Rate (L/min)')
    plt.ylabel('Pressure (Pa)')
    plt.title(f"{title}\nInlet R² = {r2_p1:.4f}, Outlet R² = {r2_p2:.4f}")
    plt.legend()
    plt.grid(True)
    plt.xlim(0, 2.75)  # Set x-axis limit to show a bit more than the fitted range
    plt.show()
    
    print(f"Inlet fit: P = {p1_fit[0]:.2f}x² + {p1_fit[1]:.2f}x + {p1_fit[2]:.2f}")
    print(f"Outlet fit: P = {p2_fit[0]:.2f}x² + {p2_fit[1]:.2f}x + {p2_fit[2]:.2f}")

def calculate_pressure_drop(flow_rate, p1_fit, p2_fit):
    return quadratic_fit(flow_rate, *p1_fit) - quadratic_fit(flow_rate, *p2_fit)

def plot_pressure_drop(x, y, title):
    plt.figure(figsize=(10, 6))
    plt.plot(x, y)
    plt.xlabel('Flow Rate (L/min)')
    plt.ylabel('Pressure Drop (Pa)')
    plt.title(title)
    plt.grid(True)
    plt.xlim(0.5, 2.5)  # Limit x-axis to the specified range
    plt.show()

def calculate_friction_factor(flow_rate, pressure_drop, length, diameter, rho, mu):
    area = np.pi * (diameter/2)**2
    velocity = (flow_rate / 60000) / area
    reynolds = rho * velocity * diameter / mu
    
    if velocity < 1e-6:
        friction = np.nan
    else:
        friction = pressure_drop * 2 * diameter / (length * rho * velocity**2)
    
    return reynolds, friction

def plot_friction_factor(re, f):
    plt.figure(figsize=(10, 6))
    plt.scatter(re, f)
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('Reynolds Number')
    plt.ylabel('Friction Factor')
    plt.title('Cold Plate: Friction Factor vs Reynolds Number')
    plt.grid(True)
    plt.show()


# Main execution
coldplate_test_group = 'uniform'
coldplate_test_name = 'calibrated_cc5.csv'
pipe_test_name = 'processed_data_2024-08-15_17-27-14_pipe_test.csv'

coldplate_test_file = os.path.join('data', 'processed', coldplate_test_group, coldplate_test_name)
pipe_test_file = os.path.join('data', 'processed', pipe_test_name)

# Process pipe test data
pipe_test = read_data(pipe_test_file)
pipe_p1_fit = fit_pressure_curve(pipe_test['flow_rate_mean'], pipe_test['p1_mean'])
pipe_p2_fit = fit_pressure_curve(pipe_test['flow_rate_mean'], pipe_test['p2_mean'])
plot_pressure_fits(pipe_test, pipe_p1_fit, pipe_p2_fit, "Pipe Test: Pressure vs Flow Rate", 'flow_rate_mean', 'p1_mean', 'p2_mean')

# Process cold plate data
cold_plate = read_data(coldplate_test_file)
cold_plate_highest_power = cold_plate.loc[cold_plate.groupby('Nominal_Flow_Rate')['Power'].idxmax()]
cp_p1_fit = fit_pressure_curve(cold_plate_highest_power['Actual_Flow_Rate'], cold_plate_highest_power['Channel_106_mean'])
cp_p2_fit = fit_pressure_curve(cold_plate_highest_power['Actual_Flow_Rate'], cold_plate_highest_power['Channel_107_mean'])
plot_pressure_fits(cold_plate_highest_power, cp_p1_fit, cp_p2_fit, "Cold Plate + Pipes: Pressure vs Flow Rate", 'Actual_Flow_Rate', 'Channel_106_mean', 'Channel_107_mean')

# Calculate and plot pressure drops
x_flow = np.linspace(0.5, 2.5, 100)  # Limit to the specified range
y_pipe_drop = [calculate_pressure_drop(flow, pipe_p1_fit, pipe_p2_fit) for flow in x_flow]
y_total_drop = [calculate_pressure_drop(flow, cp_p1_fit, cp_p2_fit) for flow in x_flow]
y_cp_drop = [total - pipe for total, pipe in zip(y_total_drop, y_pipe_drop)]

plot_pressure_drop(x_flow, y_pipe_drop, 'Pipe: Flow Rate vs Pressure Drop')
plot_pressure_drop(x_flow, y_total_drop, 'Cold Plate + Pipes: Flow Rate vs Pressure Drop')
plot_pressure_drop(x_flow, y_cp_drop, 'Cold Plate Alone: Flow Rate vs Pressure Drop')

# Friction factor calculation (using assumed values)
length = 0.1  # m (example value)
diameter = 0.005  # m (example value)
rho = 997  # kg/m^3 (water at 25°C)
mu = 0.000891  # Pa·s (water at 25°C)

re_list, f_list = zip(*[calculate_friction_factor(flow, pressure, length, diameter, rho, mu) 
                        for flow, pressure in zip(x_flow, y_cp_drop)])

# Remove NaN values before plotting
re_list, f_list = zip(*[(re, f) for re, f in zip(re_list, f_list) if not np.isnan(f)])

plot_friction_factor(re_list, f_list)

# Save nominal flow rates and pressure drops to CSV
results_df = pd.DataFrame({
    'Flow_Rate': x_flow,
    'Pipe_Pressure_Drop': y_pipe_drop,
    'Total_Pressure_Drop': y_total_drop,
    'Cold_Plate_Pressure_Drop': y_cp_drop
})

# Round the flow rates to 2 decimal places to get nominal flow rates
results_df['Nominal_Flow_Rate'] = results_df['Flow_Rate'].round(2)

# Group by nominal flow rate and calculate mean pressure drops
grouped_results = results_df.groupby('Nominal_Flow_Rate').agg({
    'Pipe_Pressure_Drop': 'mean',
    'Total_Pressure_Drop': 'mean',
    'Cold_Plate_Pressure_Drop': 'mean'
}).reset_index()

# Save to CSV
output_file = os.path.join('data', 'processed', f'{coldplate_test_name}_pressure_drops.csv')
grouped_results.to_csv(output_file, index=False)
print(f"Results saved to {output_file}")