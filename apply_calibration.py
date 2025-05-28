import pyvisa as visa
import json
import time

# Load calibration data from JSON file
with open('calibration_coefficients_17_2.json', 'r') as f:
    calibration_data = json.load(f)

# Define the channels to calibrate
channels_to_calibrate = ['201', '202', '203', '208', '209', '210']

# Connect to DAQ970A
rm = visa.ResourceManager()
DAQ970A = rm.open_resource('USB0::0x2A8D::0x5101::MY58032659::0::INSTR')

# Set scale function for all specified channels
channel_list = ','.join(channels_to_calibrate)
DAQ970A.write(':CALCulate:SCALe:FUNCtion %s,(@%s)' % ('SCALe', channel_list))

# Apply calibration coefficients for each channel
for channel in channels_to_calibrate:
    channel_key = f'Channel_{channel}'
    
    if channel_key in calibration_data:
        m = calibration_data[channel_key]['m']  # slope (gain)
        b = calibration_data[channel_key]['b']  # intercept (offset)
        
        # Set gain (slope)
        DAQ970A.write(':CALCulate:SCALe:GAIN %G,(@%s)' % (m, channel))
        
        # Set offset (intercept)
        DAQ970A.write(':CALCulate:SCALe:OFFSet %G,(@%s)' % (b, channel))
        
        print(f'Channel {channel}: Gain = {m}, Offset = {b}')
    else:
        print(f'Warning: Channel {channel} not found in calibration data')

# Enable scaling
DAQ970A.write(':CALCulate:SCALe:STATe %d' % (1))

# Close connections
DAQ970A.close()
rm.close()

print('Calibration complete!')