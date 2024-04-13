import yaml

import time
import asyncio
from asyncio import Event

import dearpygui.dearpygui as dpg

from state import app_state
from gui_manager import GUIManager
from data_manager import AsyncDataManager
from equipment_manager import EquipmentManager
from schedule import ConstantIntervalSchedule, CsvSchedule


## GUI---realtime plot
def update_live_plot(data_manager):
    # Ensure there's data to plot
    if not data_manager.plot_deque:
        return

    # Assuming the plot and axes have been created previously, and we're just updating the series
    channels = {channel for _, _, channel, _ in data_manager.plot_deque}
    for channel in channels:
        data_x, data_y = zip(*[(dt.timestamp(), data) for dt, _, sid, data in data_manager.plot_deque if sid == channel])

        # Check for existing series; update if exists, else create
        series_tag = f"line_{channel}"
        if not dpg.does_item_exist(series_tag):
            # Assuming 'y_axis' is the tag for your Y axis where series should be added
            dpg.add_line_series(list(data_x), list(data_y), parent="y_axis", label=channel, tag=series_tag)
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

## stop entire system after long time as a precaution
async def overall_time_limit_reached(data_manager, overall_time_limit, gui_manager):
    await asyncio.sleep(overall_time_limit) #config['overall_time_limit']
    # Here, you could stop data acquisition and plotting
    print("Overall time limit reached. Stopping...")
    # Optionally save data here or trigger any cleanup routines
    gui_manager.start_stop_action("Stop")
    asyncio.create_task(data_manager.save_data())
    # return the start button

## add async tasks
async def task_monitor(data_manager, eqpt_manager, gui_manager):
    tasks = []
    while True:
        if app_state.is_running():
            if not tasks:
                # print("Starting tasks")
                try:
                    data_manager.reset_data()
                    # dpg.delete_item("y_axis", children_only=True, slot=1) # can not delete plot..
                    tasks.extend([
                        asyncio.create_task(eqpt.start()) for eqpt in eqpt_manager.equipment_list
                    ])
                    tasks.append(asyncio.create_task(live_plot_updater(data_manager)))
                    tasks.append(asyncio.create_task(update_progress_marker()))
                    tasks.append(asyncio.create_task(data_manager.periodically_update_dataframe()))
                    tasks.append(asyncio.create_task(overall_time_limit_reached(data_manager, eqpt_manager.config['overall_time_limit'], gui_manager)))
                except Exception as e:
                    print(f"Error starting tasks: {e}")
        else:
            if tasks:
                print("Stopping tasks")
                try:
                    await eqpt_manager.stop_equipment()
                    # asyncio.create_task(eqpt_manager.stop_equipment())
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks.clear()
                except Exception as e:
                    print(f"Error stopping tasks: {e}")
        await asyncio.sleep(0.5)

## config file
def load_config(filename):
    """Load configuration from a YAML file."""
    with open(filename, 'r') as file:
        return yaml.safe_load(file)

## main logic
async def main():
        # Initial setup
    config = load_config('config.yaml')
    data_manager = AsyncDataManager()
    eqpt_manager = EquipmentManager(config)
    eqpt_manager.load_equipment(data_manager)
    await eqpt_manager.initialize_equipment()

    gui_manager = GUIManager(eqpt_manager, data_manager)
    gui_manager.setup()

    # Start monitoring tasks based on app_state
    asyncio.create_task(task_monitor(data_manager, eqpt_manager, gui_manager))

    # Start rendering in a non-blocking way
    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()
        await asyncio.sleep(0.016)  # Roughly 60 FPS

    dpg.destroy_context()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Caught keyboard interrupt. Exiting...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        dpg.destroy_context()

