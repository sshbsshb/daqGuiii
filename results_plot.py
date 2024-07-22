import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler

# Color palettes inspired by ggsci, including Futurama and Tron Legacy
color_palettes = {
    'npg': ['#E64B35', '#4DBBD5', '#00A087', '#3C5488', '#F39B7F', '#8491B4', '#91D1C2', '#DC0000', '#7E6148', '#B09C85'],
    'aaas': ['#3B4992', '#EE0000', '#008B45', '#631879', '#008280', '#BB0021', '#5F559B', '#A20056', '#808180', '#1B1919'],
    'nejm': ['#BC3C29', '#0072B5', '#E18727', '#20854E', '#7876B1', '#6F99AD', '#FFDC91', '#EE4C97'],
    'lancet': ['#00468B', '#ED0000', '#42B540', '#0099B4', '#925E9F', '#FDAF91', '#AD002A', '#ADB6B6', '#1B1919'],
    'jama': ['#374E55', '#DF8F44', '#00A1D5', '#B24745', '#79AF97', '#6A6599', '#80796B'],
    'jco': ['#0073C2', '#EFC000', '#868686', '#CD534C', '#7AA6DC', '#003C67', '#8F7700', '#3B3B3B', '#A73030', '#4A6990'],
    'futurama': ['#FF6F00', '#C71000', '#008EA0', '#8A4198', '#5A9599', '#FF6348', '#84D7E1', '#FF95A8', '#3D3B25', '#ADE2D0'],
    'tron': ['#FF410D', '#6EE2FF', '#F7C530', '#95CC5E', '#D0DFE6', '#F79D1E', '#748AA6']
}

# Read the results
df = pd.read_csv('calibrated_steady_state_results.csv')

# Set the names of the steady states
steady_state_names = ['Initial', 'Heating1', 'Heating2', 'Heating3', 'Heating4', 'Heating5', 'Heating6', 'Cooling', 'Final']

# Select which channels to plot and their display names
channels_to_plot = {
    'Channel_101': 'Temperature 1',
    'Channel_102': 'Temperature 2',
    'Channel_103': 'Temperature 3',
    'Channel_201': 'Pressure 1',
    'Channel_202': 'Pressure 2'
}

# Define a list of distinct markers
markers = ['o', 's', '^', 'D', 'v', 'p', 'h', '8', '*', 'H']

# Function to create and save plot
def create_plot(chosen_palette):
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)

    # Set the color cycle to the chosen palette
    ax.set_prop_cycle(cycler('color', color_palettes[chosen_palette]))

    # Set background color for Tron Legacy style
    if chosen_palette == 'tron':
        ax.set_facecolor('#0C141F')
        fig.patch.set_facecolor('#0C141F')
        text_color = 'white'
    else:
        ax.set_facecolor('white')
        fig.patch.set_facecolor('white')
        text_color = 'black'

    plt.rcParams['text.color'] = text_color
    plt.rcParams['axes.labelcolor'] = text_color
    plt.rcParams['xtick.color'] = text_color
    plt.rcParams['ytick.color'] = text_color

    # Plot lines and points for each selected channel
    for i, (channel, display_name) in enumerate(channels_to_plot.items()):
        means = df[f'{channel}_mean']
        stds = df[f'{channel}_std']
        
        color = color_palettes[chosen_palette][i % len(color_palettes[chosen_palette])]
        marker = markers[i % len(markers)]
        
        # Plot the line
        ax.plot(steady_state_names, means, '--', alpha=0.7, lw=2, color=color)
        
        # Plot the points with error bars
        ax.errorbar(steady_state_names, means, yerr=stds, fmt=marker, 
                    label=f'{display_name}', capsize=4, capthick=1, markersize=8, 
                    elinewidth=1, markeredgewidth=1, color=color) # ({marker})

    # Customize the plot
    ax.set_xlabel('Steady State', fontweight='bold', fontsize=12)
    ax.set_ylabel('Calibrated Value', fontweight='bold', fontsize=12)
    ax.set_title(f'Steady State Results', fontsize=16, fontweight='bold') # (Palette: {chosen_palette})

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')

    # Adjust y-axis limits to give some padding
    y_min = df[[f'{ch}_mean' for ch in channels_to_plot.keys()]].min().min()
    y_max = df[[f'{ch}_mean' for ch in channels_to_plot.keys()]].max().max()
    y_range = y_max - y_min
    ax.set_ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)

    # Improve tick label size
    ax.tick_params(axis='both', which='major', labelsize=10)

    # Add legend inside the plot
    legend = ax.legend(title='Channels', loc='upper left', fontsize=10, title_fontsize=11)
    legend.get_frame().set_alpha(0.7)
    if chosen_palette == 'tron':
        legend.get_frame().set_facecolor('#0C141F')
        legend.get_frame().set_edgecolor('white')
    for text in legend.get_texts():
        text.set_color(text_color)
    legend.get_title().set_color(text_color)

    # Add a box around the plot
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(text_color)

    # Adjust layout and save the plot
    plt.tight_layout()
    plt.savefig(f'steady_state_results_plot', dpi=300, bbox_inches='tight') #_{chosen_palette}.png
    print(f"Plot saved as 'steady_state_results.png'") #_plot_{chosen_palette}

    plt.close()

# Create plots for all palettes
# for palette in color_palettes.keys():
#     create_plot(palette)

create_plot('futurama')
print("All plots have been created and saved.")