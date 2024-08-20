import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Data Loading and Preprocessing
df = pd.read_csv('data\\processed\\1.0-2mm\\calibrated_c0.csv')

# 2. Examining Flow Rates
print("Unique flow rates:")
print(df['Channel_108_mean'].unique())

# Function to assign flow rate groups
def assign_flow_group(flow):
    if 0.85 <= flow < 0.95:
        return 0.88
    elif 0.95 <= flow < 1.3:
        return 1.0
    elif 1.3 <= flow < 1.8:
        return 1.5
    elif 1.8 <= flow < 2.3:
        return 2.0
    elif 2.3 <= flow <= 2.6:
        return 2.5
    else:
        return None

# Assign flow rate groups
df['Flow_Group'] = df['Channel_108_mean'].apply(assign_flow_group)

# 3. Calculating Pressure Difference
df['Pressure_Difference'] = df['Channel_106_mean'] - df['Channel_107_mean']

# 4. Analyzing Heater Temperatures
heater_channels = ['Channel_201_mean', 'Channel_202_mean', 'Channel_203_mean', 
                   'Channel_208_mean', 'Channel_209_mean', 'Channel_210_mean']

# Identify power levels (assuming they increase monotonically for each flow rate)
df['Power_Level'] = df.groupby('Flow_Group').cumcount()

# 5. Visualizing the Results
plt.figure(figsize=(15, 10))

for channel in heater_channels:
    for flow_group in df['Flow_Group'].unique():
        flow_data = df[df['Flow_Group'] == flow_group]
        plt.scatter(flow_data['Channel_108_mean'], flow_data[channel], label=f'{channel} at ~{flow_group} L/min')

plt.xlabel('Actual Flow Rate (L/min)')
plt.ylabel('Temperature (°C)')
plt.title('Heater Temperatures vs Actual Flow Rate')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True)
plt.tight_layout()
plt.show()

# Pressure Difference vs Actual Flow Rate
plt.figure(figsize=(10, 6))
for power_level in df['Power_Level'].unique():
    power_data = df[df['Power_Level'] == power_level]
    plt.scatter(power_data['Channel_108_mean'], power_data['Pressure_Difference'], label=f'Power Level {power_level}')

plt.xlabel('Actual Flow Rate (L/min)')
plt.ylabel('Pressure Difference (units)')
plt.title('Pressure Difference vs Actual Flow Rate at Different Power Levels')
plt.legend()
plt.grid(True)
plt.show()

# Summary Statistics
summary = df.groupby('Flow_Group')[heater_channels + ['Pressure_Difference', 'Channel_108_mean']].agg(['mean', 'std', 'min', 'max'])
print(summary)

# Plot actual flow rates over measurements
plt.figure(figsize=(10, 6))
for flow_group in df['Flow_Group'].unique():
    group_data = df[df['Flow_Group'] == flow_group]
    plt.scatter(range(len(group_data)), group_data['Channel_108_mean'], label=f'~{flow_group} L/min')

plt.xlabel('Measurement Index')
plt.ylabel('Actual Flow Rate (L/min)')
plt.title('Actual Flow Rates Over Measurements')
plt.legend()
plt.grid(True)
plt.show()

# Plot temperatures for each heater channel
plt.figure(figsize=(15, 10))
for channel in heater_channels:
    plt.scatter(df['Channel_108_mean'], df[channel], label=channel)

plt.xlabel('Actual Flow Rate (L/min)')
plt.ylabel('Temperature (°C)')
plt.title('Heater Temperatures vs Actual Flow Rate')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True)
plt.tight_layout()
plt.show()