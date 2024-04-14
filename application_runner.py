import asyncio
from gui_manager import GUIManager
from equipment_manager import EquipmentManager
from data_manager import AsyncDataManager
from state import app_state

import dearpygui.dearpygui as dpg

class ApplicationRunner:
    def __init__(self, config):
        self.config = config
        self.data_manager = AsyncDataManager()
        self.eqpt_manager = EquipmentManager(self.config, self.data_manager)
        self.gui_manager = GUIManager(self.eqpt_manager, self.data_manager)

    async def run(self):
        # Initial setup
        await self.eqpt_manager.initialize_equipment()
        self.gui_manager.setup()

        # Start monitoring tasks based on app_state
        asyncio.create_task(self.task_monitor())

        # Start rendering in a non-blocking way
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
            await asyncio.sleep(0.016)  # Roughly 60 FPS

        dpg.destroy_context()

    async def task_monitor(self):
        tasks = []
        while True:
            if app_state.is_running():
                if not tasks:
                    print("Starting tasks")
                    try:
                        self.data_manager.reset_data()
                        # dpg.delete_item("y_axis", children_only=True, slot=1) # can not delete plot..
                        tasks.extend([
                            asyncio.create_task(eqpt.start()) for eqpt in self.eqpt_manager.equipment_list
                        ])
                        tasks.append(asyncio.create_task(self.gui_manager.live_plot_updater()))
                        tasks.append(asyncio.create_task(self.gui_manager.update_progress_marker()))
                        tasks.append(asyncio.create_task(self.data_manager.periodically_update_dataframe()))
                        tasks.append(asyncio.create_task(self.overall_time_limit_reached()))
                    except Exception as e:
                        print(f"Error starting tasks: {e}")
            else:
                if tasks:
                    print("Stopping tasks")
                    try:
                        await self.eqpt_manager.stop_equipment()
                        # asyncio.create_task(eqpt_manager.stop_equipment())
                        for task in tasks:
                            task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)
                        tasks.clear()
                    except Exception as e:
                        print(f"Error stopping tasks: {e}")
            await asyncio.sleep(0.5)

    async def overall_time_limit_reached(self):
        await asyncio.sleep(self.eqpt_manager.config['overall_time_limit'])
        # Here, you could stop data acquisition and plotting
        print("Overall time limit reached. Stopping...")
        # Optionally save data here or trigger any cleanup routines
        self.gui_manager.start_stop_action("Stop")
        await self.data_manager.save_data()
        # return the start button