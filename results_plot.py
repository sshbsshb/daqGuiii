
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler

# Read the results
df = pd.read_csv('calibrated_steady_state_results.csv')

# Set the names of the steady states
steady_state_names = ['Initial', 'Initial2', 'Heating', 'Cooling', 'Final', 'Final2']  # Adjust this list as needed

# Get all available channel names
all_channels = [col.replace('_mean', '') for col in df.columns if col.endswith('_mean')]

# Select which channels to plot and their display names
channels_to_plot = {
    'Channel_101': 'Temperature 1',
    'Channel_102': 'Temperature 2',
    'Channel_103': 'Temperature 3',
    'Channel_201': 'Pressure 1',
    'Channel_202': 'Pressure 2'
}
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 10,
    "axes.linewidth": 1,
    "axes.labelsize": 12,
    "xtick.major.width": 1,
    "ytick.major.width": 1,
})

# Create a figure with adjusted size and tight layout
fig, ax = plt.subplots(figsize=(10, 6), dpi=300, constrained_layout=True)

# Define a color cycle inspired by Nature magazine style
nature_colors = ['#4878CF', '#6ACC65', '#D65F5F', '#B47CC7', '#C4AD66', '#77BEDB']
plt.rcParams['axes.prop_cycle'] = cycler(color=nature_colors)

# Define markers
markers = ['o', 's', '^', 'D', 'v', 'p']

# Plot lines and points for each selected channel
for i, (channel, display_name) in enumerate(channels_to_plot.items()):
    means = df[f'{channel}_mean']
    stds = df[f'{channel}_std']
    
    # Plot the line
    ax.plot(steady_state_names, means, '--', alpha=0.7, lw=1.5)
    
    # Plot the points with error bars
    ax.errorbar(steady_state_names, means, yerr=stds, fmt=markers[i % len(markers)], 
                label=display_name, capsize=4, capthick=1, markersize=6, 
                elinewidth=1, markeredgewidth=1)

# Customize the plot
ax.set_xlabel('Steady State', fontweight='bold')
ax.set_ylabel('Calibrated Value', fontweight='bold')
ax.set_title('Steady State Results for Selected Channels', fontsize=14, fontweight='bold')

# Adjust y-axis limits to give some padding
y_min = df[[f'{ch}_mean' for ch in channels_to_plot.keys()]].min().min()
y_max = df[[f'{ch}_mean' for ch in channels_to_plot.keys()]].max().max()
ax.set_ylim(y_min - 0.1 * (y_max - y_min), y_max + 0.1 * (y_max - y_min))

# Improve tick label size
ax.tick_params(axis='both', which='major', labelsize=10)

# Add legend with a semi-transparent background
legend = ax.legend(title='Channels', loc='center left', bbox_to_anchor=(1, 0.5),
                   fontsize=10, title_fontsize=11)
legend.get_frame().set_alpha(0.7)

# Remove top and right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Save the plot
plt.savefig('steady_state_results_plot.png', dpi=300, bbox_inches='tight')
print("Plot saved as 'steady_state_results_plot.png'")

# Display the plot
plt.show()