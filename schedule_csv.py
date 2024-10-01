import csv
import matplotlib.pyplot as plt

def create_pump_schedule(speeds, stabilization_time, heater_stable_time, record_time):
    schedule = []
    current_time = 0
    for i, speed in enumerate(speeds):
        if i == 0:
            # Initial ramp-up
            ramp_time = 10 if speed == 3.17 else 30
            steps = 8
            for step in range(steps):
                intermediate_speed = 1 + (speed - 1) * (step) / steps
                schedule.append((current_time + ramp_time * step / steps, round(intermediate_speed, 2)))
            current_time += ramp_time
        else:
            # Ramp to next speed
            prev_speed = speeds[i-1]
            ramp_time = 7
            steps = 5
            for step in range(steps):
                intermediate_speed = prev_speed + (speed - prev_speed) * (step) / steps
                schedule.append((current_time + ramp_time * step / steps, round(intermediate_speed, 2)))
            current_time += ramp_time

        # Stabilization at new speed
        schedule.append((current_time, speed))
        if i > 0:
            current_time += stabilization_time

        # Hold speed for heater cycle and DAQ recording
        if i < len(speeds) - 1:
            heater_cycle_time = len(heater_voltages) * ( heater_stable_time + record_time)  # (600s + 100s) * number of voltages
            current_time += heater_cycle_time

    # Add final entries
    schedule.append((current_time+heater_cycle_time, 3.2))
    # schedule.append((current_time + 10, 1))
    return schedule

def create_heater_schedule(voltages, pump_speeds, stabilization_time, heater_stable_time, record_time):
    schedule = []
    daq_schedule = []
    current_time = 30  # Start after initial pump ramp
    now_speed = pump_speeds[0]
    for i, speed in enumerate(pump_speeds):

        for voltage in voltages:
            schedule.append((current_time, voltage))
            if now_speed !=speed:
                now_speed = speed
                current_time += stabilization_time + 7  # Add time for stabilization and ramp
            current_time += heater_stable_time  # Heater runs for 600s
            daq_schedule.append(current_time)
            current_time += record_time  # Time for DAQ recording
            
    schedule.append((current_time, 0))  # shutdown heater !!!!
    return schedule, daq_schedule

def create_daq_schedule(daq_value, heater_schedule):
    return [(time, daq_value) for time in heater_schedule]

def write_csv(filename, schedule):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['time', 'value'])
        for time, value in schedule:
            writer.writerow([time, value])

def plot_schedules(pump_schedule, heater_schedule, daq_schedule):
    plt.figure(figsize=(14, 8))
    
    pump_times, pump_values = zip(*pump_schedule)
    heater_times, heater_values = zip(*heater_schedule)
    daq_times, daq_values = zip(*daq_schedule)
    
    plt.step(pump_times, pump_values, where='post', label='Pump Speed', linewidth=2)
    plt.step(heater_times, heater_values, where='post', label='Heater Voltage', linewidth=2)
    
    # Add vertical lines for DAQ trigger times
    for daq_time in daq_times:
        plt.axvline(x=daq_time, color='r', linestyle='--', alpha=0.5, linewidth=1)
    
    # Add a single entry to the legend for DAQ triggers
    plt.axvline(x=0, color='r', linestyle='--', alpha=0.5, linewidth=1, label='DAQ Trigger')
    
    plt.xlabel('Time (s)')
    plt.ylabel('Value')
    plt.title('Pump, Heater, and DAQ Schedules')
    plt.legend()
    plt.grid(True)
    
    # Adjust x-axis to show more tick marks
    plt.xticks(range(0, int(max(pump_times[-1], heater_times[-1], daq_times[-1])) + 1, 1000))
    
    plt.tight_layout()
    plt.savefig('schedule_plot.png', dpi=300)
    plt.close()

# Define parameters
pump_speeds = [3.24, 2.59, 1.83, 1.18, 0.59]
heater_voltages = [14, 16, 18]
daq_value = 60
stabilization_time = 1000  # Can be changed as needed
heater_stable_time = 1000
record_time = 100

# Create schedules
pump_schedule = create_pump_schedule(pump_speeds, stabilization_time, heater_stable_time, record_time)
heater_schedule, daq_schedule = create_heater_schedule(heater_voltages, pump_speeds, stabilization_time, heater_stable_time, record_time)
daq_schedule = create_daq_schedule(daq_value, daq_schedule)

# Write schedules to CSV files
write_csv('schedule_pump.csv', pump_schedule)
write_csv('schedule_heater.csv', heater_schedule)
write_csv('schedule_daq.csv', daq_schedule)

# Plot schedules
plot_schedules(pump_schedule, heater_schedule, daq_schedule)

print("CSV files and plot have been generated successfully.")