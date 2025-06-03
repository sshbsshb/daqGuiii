# In gui_manager.py
import dearpygui.dearpygui as dpg
from state import app_state
from schedule import ConstantIntervalSchedule, CsvSchedule
import asyncio
import time

class GUIManager:
    def __init__(self, eqpt_manager, data_manager, app_runner_instance):
        self.eqpt_manager = eqpt_manager
        self.data_manager = data_manager
        self.app_runner = app_runner_instance
        self.progress_marker_start_time = 0 # For progress plot

    def setup(self):
        dpg.create_context()
        with dpg.theme() as disabled_theme:
            with dpg.theme_component(dpg.mvButton, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (100, 100, 100), category=dpg.mvThemeCat_Core)
        dpg.bind_theme(disabled_theme)

        with dpg.window(label="Data Visualization", tag="main_window"):
            with dpg.group(horizontal=True):
                # Initial message when application starts
                dpg.add_text("System Idle. Press Start to begin.", tag="info_text")
                dpg.add_button(label="Start", width=75, callback=self.start_stop_handler, tag="start_stop_button")
                dpg.add_button(label="Save", width=75, callback=self.save_handler, tag="save_button", enabled=False) 
            # Batch info text will be updated by update_batch_display
            dpg.add_text("", tag="batch_info_text", pos=(dpg.get_item_pos("save_button")[0] + 85, dpg.get_item_pos("save_button")[1]))
            
            with dpg.window(label="SYSTEM STATUS", modal=False, show=False, tag="safety_alert_window", pos=(0, 700), width=1000, height=100, no_close=True, no_move=True, no_resize=True):
                dpg.add_text("System OK", tag="safety_alert_text", color=(0, 255, 0), wrap=980) # Green for OK

            with dpg.group(horizontal=False):
                self.setup_live_plot()

            with dpg.group(horizontal=False):
                self.setup_progress_plot()

        dpg.set_exit_callback(self.on_attempt_to_close)
        dpg.create_viewport(title='Monitoring Dashboard', width=1024, height=850, disable_close=True)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)
        # Initialize batch display if in batch mode
        if app_state.batch_mode_active :
            self.update_batch_display() # Show "Batch: 1/N" or similar initial state

        if not app_state.batch_mode_active or app_state.batch_total_runs == 0 : # No batches defined or single run mode initially
            dpg.enable_item("save_button") # Enable save if not in a multi-batch sequence waiting to start        

    def update_batch_display(self):
        print(f"DEBUG: update_batch_display called")
        if dpg.does_item_exist("batch_info_text"):
            if app_state.batch_mode_active:
                dpg.set_value("batch_info_text", f"Batch: {app_state.batch_current_run}/{app_state.batch_total_runs}")
            else:
                dpg.set_value("batch_info_text", "Single Run Mode")

    def prepare_for_new_run(self):
        self.clear_live_plot_series()
        self.reset_progress_marker_display()
        
        if dpg.does_item_exist("start_stop_button"):
             dpg.configure_item("start_stop_button", label="Start", enabled=True)
        if dpg.does_item_exist("save_button"):
            # Disable Save button when ready for a new run; it's enabled after a run STOPS or ALL batches complete.
            dpg.disable_item("save_button") 
        if dpg.does_item_exist("info_text") and app_state.batch_mode_active:
             dpg.set_value("info_text", f"Batch {app_state.batch_current_run} ready. Press Start.")
        elif dpg.does_item_exist("info_text"):
             dpg.set_value("info_text", "Ready. Press Start.")

    def clear_live_plot_series(self):
        if dpg.does_item_exist("y_axis"):
            # Slot 1 for series in y_axis
            children_dict = dpg.get_item_info("y_axis")["children"]
            if 1 in children_dict:
                for series_tag in list(children_dict[1]): # Iterate over a copy
                    if dpg.does_item_exist(series_tag):
                        dpg.delete_item(series_tag)
        # The plot_deque in data_manager is cleared by data_manager.reset_data()

    def reset_progress_marker_display(self):
        if dpg.does_item_exist("progress_marker"):
            dpg.configure_item("progress_marker", x=[0.0])

    def reset_progress_marker_start_time(self):
        self.progress_marker_start_time = time.time()

    def prepare_for_new_run(self):
        self.clear_live_plot_series()
        self.reset_progress_marker_display()
        # self.reset_progress_marker_start_time() # now called by task_monitor before starting update_progress_marker task
        
        # Re-enable start button if it was disabled, and set label to "Start"
        if dpg.does_item_exist("start_stop_button"):
             dpg.configure_item("start_stop_button", label="Start", enabled=True)
        if dpg.does_item_exist("save_button"):
            dpg.enable_item("save_button")


    ## GUI---realtime plot
    def update_live_plot(self):
        if not self.data_manager.plot_deque: # If deque is empty, nothing to plot
            # Consider if old series should be explicitly removed if data source becomes empty
            # self.clear_live_plot_series() # This might be too aggressive here
            return

        channels = {channel for _, _, channel, _ in self.data_manager.plot_deque}
        
        # Remove series for channels no longer in the deque (optional, good for dynamic channels)
        if dpg.does_item_exist("y_axis"):
            children_dict = dpg.get_item_info("y_axis")["children"]
            if 1 in children_dict:
                existing_series_tags = list(children_dict[1])
                for series_tag in existing_series_tags:
                    label = dpg.get_item_configuration(series_tag)["label"]
                    if label not in channels and dpg.does_item_exist(series_tag): # Check if series still exists
                        dpg.delete_item(series_tag)

        for channel in channels:
            # Filter data for the current channel
            channel_data = [(dt.timestamp(), data) for dt, _, sid, data in self.data_manager.plot_deque if sid == channel]
            if not channel_data: continue # Skip if no data for this channel (e.g., after filtering)
            
            data_x, data_y = zip(*channel_data)
            series_tag = f"line_{channel}"

            if not dpg.does_item_exist(series_tag):
                if dpg.does_item_exist("y_axis"): # Ensure axis exists
                    dpg.add_line_series(list(data_x), list(data_y), parent="y_axis", label=channel, tag=series_tag)
            else:
                dpg.configure_item(series_tag, x=list(data_x), y=list(data_y))
        
        if dpg.does_item_exist("y_axis"): dpg.fit_axis_data("y_axis")
        if dpg.does_item_exist("x_axis"): dpg.fit_axis_data("x_axis")


    async def live_plot_updater(self):
        try:
            while app_state.is_running(): # Controlled by app_state for the current batch
                if not dpg.is_dearpygui_running(): break
                self.update_live_plot()
                # dpg.render_dearpygui_frame() # Render call is in ApplicationRunner.run
                await asyncio.sleep(1/30)  # Update at roughly 30 FPS
        except asyncio.CancelledError:
            print("Live plot updater cancelled.")
            raise
        finally:
            print("Live plot updater finished.")


    async def update_progress_marker(self):
        # self.progress_marker_start_time is set by reset_progress_marker_start_time()
        try:
            while app_state.is_running(): # Controlled by app_state for the current batch
                if not dpg.is_dearpygui_running(): break
                current_time_elapsed = time.time() - self.progress_marker_start_time
                if dpg.does_item_exist("progress_marker"):
                    dpg.configure_item("progress_marker", x=[current_time_elapsed])
                else:
                    # This might happen if plot is not fully set up yet
                    # print("Progress marker does not exist yet.")
                    pass
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("Progress marker updater cancelled.")
            raise
        finally:
            print("Progress marker updater finished.")


    ### GUI---run live plot
    def setup_live_plot(self):
        with dpg.plot(label="Sensor Data", width=1024, height=600, tag="sensor_plot"):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Time", time=True, tag="x_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="Data", tag="y_axis")
    
    ### GUI---Save button
    def save_handler(self, sender, app_data, user_data):
        loop = self.app_runner.get_loop() # Get the loop from ApplicationRunner
        if loop and not loop.is_closed() and loop.is_running():
            print("GUI: Save button pressed. Creating save task on the explicitly managed loop.")
            loop.create_task(self.data_manager.save_data()) # save_data takes no args here
        else:
            print("GUI ERROR: Event loop not available, closed, or not running when trying to save.")
            if loop:
                print(f"GUI INFO: Loop state - is_closed: {loop.is_closed()}, is_running: {loop.is_running()}")
            else:
                print("GUI INFO: Loop reference is None.")
            if dpg.does_item_exist("info_text"): # Give user feedback
                dpg.set_value("info_text", "Error: Cannot save. Event loop issue.")

    ## GUI---Exit button
    def exit_handler(self):
        print("GUI Exit handler: Attempting to stop application.")
        print(f"DEBUG: exit_handler called from:")
        import traceback
        traceback.print_stack()
        app_state.stop() # Signal ongoing batch (if any) to stop

        # The DPG window closing is handled by ApplicationRunner.run's finally block
        # or its main while loop exiting.
        # We just need to stop DPG itself here.
        if dpg.is_dearpygui_running():
            dpg.stop_dearpygui()

    def show_exit_confirmation_modal(self):
        # Check if app_state is running (meaning a batch is active)
        if app_state.is_running():
            if not dpg.does_item_exist("exit_confirmation_modal"):
                with dpg.window(label="Confirm Exit", modal=True, no_close=True, tag="exit_confirmation_modal", pos=(400,300)):
                    dpg.add_text("A test batch is currently running!")
                    dpg.add_text("Are you sure you want to exit the application?")
                    dpg.add_text("This will stop the current batch and any pending batches.")
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Yes, Exit", width=100, callback=self.exit_handler)
                        dpg.add_button(label="No", width=75, callback=lambda: dpg.delete_item("exit_confirmation_modal"))
        else: # Not running, so safe to exit directly
            self.exit_handler()


    def on_attempt_to_close(self):
        self.show_exit_confirmation_modal()
        # Return True to prevent default close if we want modal to decide.
        # However, our modal calls exit_handler which calls dpg.stop_dearpygui().
        # So, we don't strictly need to prevent default close here if modal is shown.
        # For simplicity, let modal handle it. If modal isn't shown (because not running), exit_handler is called directly.
        return True # Always handle close through our logic


    ### GUI---run progress plot---only for step plot
    def transform_for_step_plot(self, schedule_data):
        step_data = []
        if not schedule_data: return [] # Handle empty schedule data
        for i, (time_val, value) in enumerate(schedule_data):
            if i < len(schedule_data) - 1:
                next_time = schedule_data[i + 1][0]
                step_data.append((time_val, value))
                step_data.append((next_time, value))
            else:
                step_data.append((time_val, value))
                 # Optionally extend the last step for a short duration for visibility
                if len(schedule_data) > 1: # if there's more than one point
                    last_duration_extension = schedule_data[-1][0] - schedule_data[-2][0] if len(schedule_data) > 1 else 1.0 # extend by last step duration or 1s
                    step_data.append((time_val + last_duration_extension * 0.1 , value)) # extend by 10% of last step
                else: # single point schedule
                    step_data.append((time_val + 1.0, value)) # extend by 1s

        return step_data

    ### GUI---run progress plot
    def setup_progress_plot(self):
        try:
            with dpg.plot(label="Progress", width=1024, height=200, tag="pro_plot"):
                dpg.add_plot_legend()
                x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Overall Time (s)")
                y_axis_p = dpg.add_plot_axis(dpg.mvYAxis, label="Value")
                dpg.add_vline_series([0.0], parent=x_axis, label="Current Progress", tag="progress_marker") # Ensure x is float
                
                # This setup is static based on config. If schedules change per batch, this needs to be dynamic.
                # For now, assuming schedules are fixed.
                for equipment in self.eqpt_manager.equipment_list:
                    if hasattr(equipment, 'schedule') and equipment.schedule and \
                       isinstance(equipment.schedule, CsvSchedule) and equipment.schedule.schedule_data:
                        step_data = self.transform_for_step_plot(equipment.schedule.schedule_data)
                        if step_data: # Ensure step_data is not empty
                            times, values = zip(*step_data)
                            dpg.add_line_series(list(times), list(values), parent=y_axis_p, label=equipment.name)
        except Exception as e:
            print(f"Error while creating progress plot: {e}")

    def start_stop_action(self, current_label_or_action):
        print(f"DEBUG: start_stop_action called with: {current_label_or_action}")
        # current_label_or_action can be "Start", "Stop", or the label from the button
        action_is_start = False
        if isinstance(current_label_or_action, str) and current_label_or_action == "Start":
            action_is_start = True
        elif dpg.does_item_exist("start_stop_button") and dpg.get_item_label("start_stop_button") == "Start":
            action_is_start = True

        if action_is_start:
            if dpg.does_item_exist("start_stop_button"): dpg.set_item_label("start_stop_button", "Stop")
            if dpg.does_item_exist("save_button"): dpg.disable_item("save_button") # Disable Save when run starts
            app_state.start()
        else: # Action is Stop
            if dpg.does_item_exist("start_stop_button"): dpg.set_item_label("start_stop_button", "Start")
            if dpg.does_item_exist("save_button"): dpg.enable_item("save_button") # Enable Save when run stops
            if dpg.does_item_exist("info_text"):
                dpg.set_value("info_text", "Run stopped. Data auto-saved. Press Save for additional copy, or Start for next batch.")
            app_state.stop()

    ### GUI---Start button
    def start_stop_handler(self, sender, app_data, user_data):
        current_label = dpg.get_item_label(sender)
        self.start_stop_action(current_label)