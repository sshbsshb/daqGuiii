import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os

### pressure drop curve fitting with inlet and outlet pressure drop curve

def quadratic_fit(x, a, b, c):
    return a * x**2 + b * x + c

def read_pipe_test_data(file_path, flow_rate_col, p1_col, p2_col):
    df = pd.read_csv(file_path)
    df['pressure_drop'] = df[p1_col] - df[p2_col]
    return df[[flow_rate_col, 'pressure_drop']]

def read_cold_plate_data(file_path, flow_rate_col, p1_col, p2_col):
    df = pd.read_csv(file_path)
    df['pressure_drop'] = df[p1_col] - df[p2_col]
    return df[[flow_rate_col, 'pressure_drop', 'Nominal_Flow_Rate', 'Power']]

def select_highest_power_data(df):
    return df.loc[df.groupby('Nominal_Flow_Rate')['Power'].idxmax()]

def fit_and_plot(df, title):
    popt, _ = curve_fit(quadratic_fit, df.iloc[:, 0], df['pressure_drop'])
    
    x_fit = np.linspace(0, df.iloc[:, 0].max(), 100)
    y_fit = quadratic_fit(x_fit, *popt)
    
    plt.figure(figsize=(10, 6))
    plt.scatter(df.iloc[:, 0], df['pressure_drop'], label='Data')
    plt.plot(x_fit, y_fit, 'r-', label='Fitted Curve')
    plt.xlabel('Flow Rate (L/min)')
    plt.ylabel('Pressure Drop (Pa)')
    plt.title(f'{title}: Flow Rate vs Pressure Drop')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    print(f"{title} pressure drop equation: {popt[0]:.2f}x^2 + {popt[1]:.2f}x + {popt[2]:.2f}")
    return popt

def calculate_cold_plate_pressure_drop(flow_rate, popt_total, popt_pipes):
    return quadratic_fit(flow_rate, *popt_total) - quadratic_fit(flow_rate, *popt_pipes)

def plot_cold_plate_pressure_drop(x, y, title):
    plt.figure(figsize=(10, 6))
    plt.plot(x, y)
    plt.xlabel('Flow Rate (L/min)')
    plt.ylabel('Pressure Drop (Pa)')
    plt.title(title)
    plt.grid(True)
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
coldplate_test_name = 'calibrated_c04.csv'
pipe_test_name = 'processed_data_2024-08-15_17-27-14_pipe_test.csv'

coldplate_test_file = os.path.join('data', 'processed', coldplate_test_group, coldplate_test_name)
pipe_test_file = os.path.join('data', 'processed', pipe_test_name)

pipe_test = read_pipe_test_data(pipe_test_file, 'flow_rate_mean', 'p1_mean', 'p2_mean')
popt_pipes = fit_and_plot(pipe_test, "Pipe Test")

cold_plate = read_cold_plate_data(coldplate_test_file, 'Actual_Flow_Rate', 'Channel_106_mean', 'Channel_107_mean')
cold_plate_highest_power = select_highest_power_data(cold_plate)
popt_total = fit_and_plot(cold_plate_highest_power, "Cold Plate + Pipes (Highest Power)")

x_cp_alone = np.linspace(0, cold_plate_highest_power['Actual_Flow_Rate'].max(), 100)
y_cp_alone = [calculate_cold_plate_pressure_drop(flow, popt_total, popt_pipes) for flow in x_cp_alone]

plot_cold_plate_pressure_drop(x_cp_alone, y_cp_alone, 'Cold Plate Alone: Flow Rate vs Pressure Drop')

# Friction factor calculation (using assumed values)
length = 0.1  # m (example value)
diameter = 0.005  # m (example value)
rho = 997  # kg/m^3 (water at 25°C)
mu = 0.000891  # Pa·s (water at 25°C)

re_list, f_list = zip(*[calculate_friction_factor(flow, pressure, length, diameter, rho, mu) 
                        for flow, pressure in zip(x_cp_alone, y_cp_alone)])

# Remove NaN values before plotting
re_list, f_list = zip(*[(re, f) for re, f in zip(re_list, f_list) if not np.isnan(f)])

plot_friction_factor(re_list, f_list)