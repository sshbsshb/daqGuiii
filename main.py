import yaml
import importlib
from schedule import ConstantIntervalSchedule, CsvSchedule
import asyncio
from asyncio import Event
from datamanager import AsyncDataManager
import dearpygui.dearpygui as dpg
import time
from state import app_state


## config file
def load_config(filename):
    with open(filename, 'r') as file:
        return yaml.safe_load(file)

### GUI---realtime plot
def update_live_plot(data_manager):
    # Ensure there's data to plot
    if not data_manager.plot_deque:
        return

    # Assuming the plot and axes have been created previously, and we're just updating the series
    sensor_ids = {sensor_id for _, sensor_id, _ in data_manager.plot_deque}
    for sensor_id in sensor_ids:
        data_x, data_y = zip(*[(dt.timestamp(), data) for dt, sid, data in data_manager.plot_deque if sid == sensor_id])

        # Check for existing series; update if exists, else create
        series_tag = f"line_{sensor_id}"
        if not dpg.does_item_exist(series_tag):
            # Assuming 'y_axis' is the tag for your Y axis where series should be added
            dpg.add_line_series(list(data_x), list(data_y), parent="y_axis", label=sensor_id, tag=series_tag)
        else:
            dpg.configure_item(series_tag, x=list(data_x), y=list(data_y))
        dpg.fit_axis_data("y_axis")
        dpg.fit_axis_data("x_axis")

async def live_plot_updater(data_manager):
    while app_state.is_running():
        update_live_plot(data_manager)
        dpg.render_dearpygui_frame()
        await asyncio.sleep(1/30)  # Update at roughly 30 FPS

async def update_progress_marker():
    start_time = time.time()
    while app_state.is_running():
        current_time = time.time() - start_time
        if dpg.does_item_exist("progress_marker"):
            dpg.configure_item("progress_marker", x=[current_time])
        else:
            print("Progress marker does not exist yet.")
        await asyncio.sleep(1)

### GUI---run live plot
def setup_live_plot():
    with dpg.plot(label="Sensor Data", width=1024, height=600, tag="sensor_plot"):
        dpg.add_plot_legend()
        # Note: Removed direct series creation from here, it will be handled dynamically
        dpg.add_plot_axis(dpg.mvXAxis, label="Time", time=True, tag="x_axis")
        dpg.add_plot_axis(dpg.mvYAxis, label="Data", tag="y_axis")

### GUI---run progress plot---only for step plot
def transform_for_step_plot(schedule_data):
    """
    Transform schedule data for a hold-last-value (step) curve.
    Each point is duplicated with the next point's timestamp to create a step effect.
    """
    step_data = []
    for i, (time, value) in enumerate(schedule_data):
        if i < len(schedule_data) - 1:
            # Duplicate the current point with the next point's timestamp
            next_time = schedule_data[i + 1][0]
            step_data.append((time, value))
            step_data.append((next_time, value))
        else:
            # Last point, just append
            step_data.append((time, value))
    return step_data
### GUI---run progress plot
def setup_progress_plot(equipment_list):
    try:
        with dpg.plot(label="Progress", width=1024, height=200, tag="pro_plot"):
            dpg.add_plot_legend()
            x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Overall Time (s)")
            y_axis_p = dpg.add_plot_axis(dpg.mvYAxis, label="Value")
            # Assuming x_axis and y_axis are correctly set up
            dpg.add_vline_series([0], parent=x_axis, label="Current Progress", tag="progress_marker")
            for equipment in equipment_list:
                if isinstance(equipment.schedule, CsvSchedule):
                    # times, values = zip(*equipment.schedule.schedule_data)
                    # dpg.add_line_series(times, values, parent=y_axis_p, label=equipment.name)
                    # Transform the original schedule data for a step plot
                    step_data = transform_for_step_plot(equipment.schedule.schedule_data)
                    times, values = zip(*step_data)
                    dpg.add_line_series(times, values, parent=y_axis_p, label=equipment.name)
    except Exception as e:
        print(f"Error while creating progress plot: {e}")

### GUI---Start button
def start_stop_handler(sender, app_data, user_data):
    current_label = dpg.get_item_label(sender)
    # data_manager, equipment_list = user_data
    
    if current_label == "Start":
        dpg.set_item_label(sender, "Stop")
        # Trigger tasks start
        app_state.start()
    else:
        dpg.set_item_label(sender, "Start")
        # Signal tasks to stop
        app_state.stop()

## main GUI
async def setup_dpg(data_manager, equipment_list):
    dpg.create_context()
    with dpg.window(label="Data Visualization", tag="main_window"):
        # Create a group for the live plot
        with dpg.group(horizontal=False):
            dpg.add_button(label="Start", callback=start_stop_handler, tag="start_stop_button")#, user_data=(data_manager, equipment_list))
        with dpg.group(horizontal=False):
            setup_live_plot()
        # Some spacing between plots (optional)
        # dpg.add_spacer(height=2)
        # Create a group for the progress plot

        with dpg.group(horizontal=False):
            setup_progress_plot(equipment_list)

    dpg.create_viewport(title='Monitoring Dashboard', width=1024, height=850)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)

async def shutdown(tasks):
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

async def task_monitor(data_manager, equipment_list):
    tasks = []
    while True:
        if app_state.is_running():
            # Ensure tasks are not already running
            if not tasks:  # Assuming `tasks` is accessible and used to track running tasks
                print("Starting tasks")
                tasks.extend([
                    asyncio.create_task(eqpt.start()) for eqpt in equipment_list
                ])
                tasks.append(asyncio.create_task(live_plot_updater(data_manager)))
                tasks.append(asyncio.create_task(update_progress_marker()))
                tasks.append(asyncio.create_task(data_manager.periodically_update_dataframe(interval=6)))
                # Add other tasks as needed
        else:
            if tasks:
                print("Stopping tasks")
                for task in tasks:
                    task.cancel()
                tasks.clear()
        await asyncio.sleep(1)  # Check every second

    # try:
    #     await asyncio.gather(*tasks)
    # except asyncio.CancelledError:
    #     # Handle task cancellation here if necessary
    #     await shutdown(tasks)
    #     print("Tasks canceled")

## main logic
async def main():
    # Initial setup
    data_manager = AsyncDataManager()

    config = load_config('config.yaml')
    equipment_list = []
 
    for eq_config in config['equipment']:
        # Example for determining which schedule to use based on config
        if 'sample_rate' in eq_config['specific_parameters']:
            schedule = ConstantIntervalSchedule(1/eq_config['specific_parameters']['sample_rate'])
        elif 'schedule_csv' in eq_config['specific_parameters']:
            schedule = CsvSchedule(eq_config['specific_parameters']['schedule_csv'])
        else:
            schedule = None

        # Dynamic class loading based on the equipment type
        module_path = f"equipment.{eq_config['connection'].lower()}.{eq_config['class'].lower()}"
        module = importlib.import_module(module_path)
        class_ = getattr(module, eq_config['class'])
        equipment_instance = class_(name=eq_config['name'], config=eq_config, schedule=schedule, data_manager=data_manager)
        equipment_list.append(equipment_instance)

    # Start monitoring tasks based on app_state
    asyncio.create_task(task_monitor(data_manager, equipment_list))

    await setup_dpg(data_manager, equipment_list)
    # Start Dear PyGui's rendering in a non-blocking way
    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()
        await asyncio.sleep(0.016)  # Roughly 60 FPS

    dpg.destroy_context()

if __name__ == "__main__":

    try:
        asyncio.run(main())
    except KeyboardInterrupt:

        print("Caught keyboard interrupt. Exiting...")
    finally:
        dpg.destroy_context()

