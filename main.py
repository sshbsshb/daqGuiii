import yaml
import importlib
import time
import asyncio
from asyncio import Event

import dearpygui.dearpygui as dpg

from state import app_state
from gui_manager import GUIManager
from datamanager import AsyncDataManager
from schedule import ConstantIntervalSchedule, CsvSchedule

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






# ## main GUI
# async def setup_dpg(equipment_list):
#     dpg.create_context()

#     with dpg.theme() as disabled_theme:
#         with dpg.theme_component(dpg.mvButton, enabled_state=False):
#             dpg.add_theme_color(dpg.mvThemeCol_Text, (100, 100, 100), category=dpg.mvThemeCat_Core)
#     dpg.bind_theme(disabled_theme)

#     with dpg.window(label="Data Visualization", tag="main_window"):
#         # Create a group for the live plot
#         with dpg.group(horizontal=True, ):
#             dpg.add_text("Equipment connected and press start ----->")
#             dpg.add_button(label="Start", width=75, callback=start_stop_handler, tag="start_stop_button")
#             dpg.add_button(label="Save", width=75,  callback=save_handler, tag="save_button")
#         with dpg.group(horizontal=False):
#             setup_live_plot()

#         with dpg.group(horizontal=False):
#             setup_progress_plot(equipment_list)
#     # dpg.show_metrics()
#     dpg.set_exit_callback(on_attempt_to_close)
#     dpg.create_viewport(title='Monitoring Dashboard', width=1024, height=850, disable_close=True)
#     dpg.setup_dearpygui()
#     dpg.show_viewport()
#     dpg.set_primary_window("main_window", True)

async def task_monitor(data_manager, equipment_list):
    tasks = []
    while True:
        if app_state.is_running():
            if not tasks:
                print("Starting tasks")
                try:
                    tasks.extend([
                        asyncio.create_task(eqpt.start()) for eqpt in equipment_list
                    ])
                    tasks.append(asyncio.create_task(live_plot_updater(data_manager)))
                    tasks.append(asyncio.create_task(update_progress_marker()))
                    tasks.append(asyncio.create_task(data_manager.periodically_update_dataframe()))
                except Exception as e:
                    print(f"Error starting tasks: {e}")
        else:
            if tasks:
                print("Stopping tasks")
                try:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks.clear()
                except Exception as e:
                    print(f"Error stopping tasks: {e}")
        await asyncio.sleep(1)

## main logic
async def main():
    gui_manager = GUIManager(equipment_list, data_manager)
    gui_manager.setup()



    # Start monitoring tasks based on app_state
    asyncio.create_task(task_monitor(data_manager, equipment_list))

    # Start rendering in a non-blocking way
    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()
        await asyncio.sleep(0.016)  # Roughly 60 FPS
    # await setup_dpg(equipment_list)
    # # Start rendering in a non-blocking way
    # while dpg.is_dearpygui_running():
    #     dpg.render_dearpygui_frame()
    #     await asyncio.sleep(0.016)  # Roughly 60 FPS

    dpg.destroy_context()

if __name__ == "__main__":
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

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Caught keyboard interrupt. Exiting...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        dpg.destroy_context()

