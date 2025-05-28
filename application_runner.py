# In application_runner.py
import asyncio
from gui_manager import GUIManager
from equipment_manager import EquipmentManager
from data_manager import AsyncDataManager
from state import app_state

import dearpygui.dearpygui as dpg

class ApplicationRunner:
    def __init__(self, config, loop_instance):
        self.config = config
        self.loop = loop_instance
        self.data_manager = AsyncDataManager()
        self.eqpt_manager = EquipmentManager(self.config, self.data_manager)
        self.gui_manager = GUIManager(self.eqpt_manager, self.data_manager, self)

    def get_loop(self): # Method for GUIManager to access the loop
        return self.loop
    
    async def run(self):
        self.gui_manager.setup()
        orchestrator_task = self.loop.create_task(self.batch_orchestrator())

        try:
            while dpg.is_dearpygui_running():
                dpg.render_dearpygui_frame()
                await asyncio.sleep(0.016) # Keep yielding to the event loop
        finally:
            print("ApplicationRunner: DPG render loop exited or error occurred.")
            # Ensure orchestrator_task is handled if DPG closes unexpectedly
            if not orchestrator_task.done():
                print("ApplicationRunner: Cancelling batch_orchestrator due to DPG exit.")
                orchestrator_task.cancel()
                try:
                    await orchestrator_task # Allow cancellation to be processed
                except asyncio.CancelledError:
                    print("ApplicationRunner: batch_orchestrator successfully cancelled.")

            # Further cleanup if app_state indicates running (e.g., forceful DPG close)
            if app_state.is_running():
                 print("ApplicationRunner: App was running during DPG exit. Signaling stop.")
                 app_state.stop()
                 # The task_monitor (if active) should see app_state.stop() and clean up.
                 # Give it a moment.
                 await asyncio.sleep(1.0)

            # Final DPG context destruction
            if dpg.get_dearpygui_version(): # Check if DPG context might still exist
                try:
                    if dpg.is_dearpygui_running(): # Should be false, but check
                        dpg.stop_dearpygui()
                    dpg.destroy_context()
                    print("ApplicationRunner: DearPyGui context destroyed.")
                except Exception as e_dpg:
                    print(f"ApplicationRunner: Error destroying DPG context: {e_dpg}")
            print("ApplicationRunner: Run method finished.")

    async def batch_orchestrator(self):
        for i in range(app_state.batch_total_runs):
            app_state.batch_current_run = i + 1
            
            # Ensure app_state is stopped before preparing the next batch
            # This is important if a previous batch was stopped, app_state.stop() was called.
            if app_state.is_running(): # Should ideally be false here
                app_state.stop() 
                # Wait for task_monitor of previous run to complete its cleanup if it was running
                await asyncio.sleep(0.5) # Adjust as needed for tasks to fully stop

            print(f"Preparing Batch {app_state.batch_current_run} of {app_state.batch_total_runs}")

            if dpg.is_dearpygui_running():
                self.gui_manager.update_batch_display()
                # prepare_for_new_run enables Start button, sets label to "Start"
                self.gui_manager.prepare_for_new_run() 
                dpg.set_value("info_text", f"Batch {app_state.batch_current_run} ready. Press Start.")
            else:
                print("GUI not running. Exiting batch orchestrator.")
                break

            self.data_manager.reset_data()
            await self.eqpt_manager.initialize_equipment()

            print(f"Batch {app_state.batch_current_run} ready. Waiting for Start signal...")

            # Wait for the Start button to be pressed (app_state.is_running() becomes True)
            while not app_state.is_running() and dpg.is_dearpygui_running():
                await asyncio.sleep(0.1) # Check periodically

            if not dpg.is_dearpygui_running():
                print(f"GUI closed while waiting to start Batch {app_state.batch_current_run}.")
                break
            
            if not app_state.is_running() or not app_state.is_running(): # If GUI closed AND app_state didn't become true
                print(f"Start not triggered for Batch {app_state.batch_current_run}. Exiting batch loop.")
                break
            
            # app_state.is_running() is now True, proceed with the batch
            print(f"Start signal received for Batch {app_state.batch_current_run}. Starting tasks...")
            if dpg.is_dearpygui_running():
                dpg.set_value("info_text", f"Running Batch {app_state.batch_current_run}...")
            
            monitor_task = self.loop.create_task(self.task_monitor())

            # Wait for this batch to complete (app_state.is_running() becomes False via Stop button or time limit)
            while app_state.is_running() and dpg.is_dearpygui_running():
                await asyncio.sleep(0.2)
            
            # Batch has been signaled to stop (or GUI closed)
            if not dpg.is_dearpygui_running() and not monitor_task.done():
                print(f"GUI closed during Batch {app_state.batch_current_run} execution. Cancelling tasks.")
                monitor_task.cancel()
                # Wait for monitor_task to acknowledge cancellation and clean up
                await asyncio.gather(monitor_task, return_exceptions=True) 
                print(f"Batch {app_state.batch_current_run} interrupted by GUI closure.")
                break # Exit batch loop

            # If monitor_task is still running (e.g. app_state.stop() was called, but task_monitor is cleaning up)
            if not monitor_task.done():
                 await monitor_task # Wait for task_monitor to finish its cleanup
            
            print(f"Batch {app_state.batch_current_run} processing finished.")
            # Save data after the batch is fully processed and tasks are stopped
            await self.data_manager.save_data() # Using the simplified save_data from previous step

            if not dpg.is_dearpygui_running(): # Check again if GUI closed during save or cleanup
                print("GUI closed during batch wrap-up.")
                break

            if app_state.batch_current_run < app_state.batch_total_runs:
                print("Current batch finished. Next batch will require 'Start' press.")
                # The GUI will be set to "Batch X+1 ready. Press Start." at the beginning of the next iteration.
                await asyncio.sleep(0.5) # Brief pause
            
            if not dpg.is_dearpygui_running():
                break
        
        # After all batches or if loop was broken
        if dpg.is_dearpygui_running():
            final_message = ""
            if app_state.batch_current_run == app_state.batch_total_runs and not app_state.is_running():
                final_message = f"All {app_state.batch_total_runs} batches completed."
            elif not dpg.is_dearpygui_running() or app_state.is_running(): # Interrupted or still running (shouldn't be)
                final_message = "Batch sequence ended or was interrupted."
            else: # Should be covered by the first condition if all batches ran
                final_message = "Batch sequence completed."

            print(final_message)
            dpg.set_value("batch_info_text", final_message)
            dpg.set_value("info_text", "All operations complete. Press Save if desired.") # Changed message
            if dpg.does_item_exist("start_stop_button"):
                dpg.configure_item("start_stop_button", label="Done", enabled=False)
            if dpg.does_item_exist("save_button"):
                 dpg.enable_item("save_button") # Ensure Save is enabled at the very end
        else:
            print("Batch orchestrator finished due to GUI closure.")


    async def task_monitor(self):
        # (task_monitor code remains largely the same as in the previous detailed answer)
        # It correctly starts tasks when app_state.is_running() is true
        # and stops them when app_state.is_running() becomes false.
        tasks = []
        try:
            # This loop ensures that if task_monitor is somehow entered when app_state is false,
            # it will try to clean up (if tasks exist) or exit.
            while True: 
                if app_state.is_running():
                    if not tasks: 
                        print(f"Starting tasks for Batch {app_state.batch_current_run}")
                        try:
                            self.gui_manager.reset_progress_marker_start_time()
                            tasks.extend([
                                self.loop.create_task(eqpt.start()) for eqpt in self.eqpt_manager.equipment_list
                            ])
                            tasks.append(self.loop.create_task(self.gui_manager.live_plot_updater()))
                            tasks.append(self.loop.create_task(self.gui_manager.update_progress_marker()))
                            tasks.append(self.loop.create_task(self.data_manager.periodically_update_dataframe()))
                            tasks.append(self.loop.create_task(self.overall_time_limit_reached()))
                        except Exception as e:
                            print(f"Error starting tasks for Batch {app_state.batch_current_run}: {e}")
                            app_state.stop() 
                else: 
                    if tasks:
                        print(f"Stopping tasks for Batch {app_state.batch_current_run}")
                        try:
                            await self.eqpt_manager.stop_equipment()
                            for task in tasks:
                                if not task.done(): # Check if task is not already done
                                    task.cancel()
                            await asyncio.gather(*tasks, return_exceptions=True)
                            tasks.clear()
                            print(f"Tasks for Batch {app_state.batch_current_run} stopped.")
                        except Exception as e:
                            print(f"Error stopping tasks for Batch {app_state.batch_current_run}: {e}")
                        finally:
                            return # Exit task_monitor as current batch processing is done/stopped
                    else:
                        # If app_state is not running and no tasks, means batch is over or never started properly.
                        return 
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            print(f"Task monitor for Batch {app_state.batch_current_run} was cancelled.")
            if tasks:
                try:
                    await self.eqpt_manager.stop_equipment()
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                except Exception as e:
                    print(f"Error during task_monitor cancellation cleanup: {e}")
            raise 

    async def overall_time_limit_reached(self):
        time_limit = self.eqpt_manager.config.get('overall_time_limit', 86400)
        try:
            await asyncio.sleep(time_limit)
            if app_state.is_running():
                print(f"Overall time limit for Batch {app_state.batch_current_run} reached. Stopping batch...")
                # This will set app_state.stop(), effectively ending the current batch.
                # The GUI button label change is handled by start_stop_action.
                self.gui_manager.start_stop_action("Stop") 
        except asyncio.CancelledError:
            print(f"Overall time limit task for Batch {app_state.batch_current_run} cancelled.")
            raise