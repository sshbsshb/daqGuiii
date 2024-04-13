import dearpygui.dearpygui as dpg
from state import app_state
from schedule import ConstantIntervalSchedule, CsvSchedule
import asyncio

class GUIManager:
    def __init__(self, eqpt_manager, data_manager):
        self.eqpt_manager = eqpt_manager
        self.data_manager = data_manager

    def setup(self):
        dpg.create_context()
        with dpg.theme() as disabled_theme:
            with dpg.theme_component(dpg.mvButton, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (100, 100, 100), category=dpg.mvThemeCat_Core)
        dpg.bind_theme(disabled_theme)

        with dpg.window(label="Data Visualization", tag="main_window"):
            with dpg.group(horizontal=True):
                dpg.add_text("Equipment connected and press start ----->", tag="info_text")
                dpg.add_button(label="Start", width=75, callback=self.start_stop_handler, tag="start_stop_button")
                dpg.add_button(label="Save", width=75, callback=self.save_handler, tag="save_button")
            with dpg.group(horizontal=False):
                self.setup_live_plot()

            with dpg.group(horizontal=False):
                self.setup_progress_plot()

        dpg.set_exit_callback(self.on_attempt_to_close)
        dpg.create_viewport(title='Monitoring Dashboard', width=1024, height=850, disable_close=True)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

    ### GUI---run live plot
    def setup_live_plot(self):
        with dpg.plot(label="Sensor Data", width=1024, height=600, tag="sensor_plot"):
            dpg.add_plot_legend()
            # Note: Removed direct series creation from here, it will be handled dynamically
            dpg.add_plot_axis(dpg.mvXAxis, label="Time", time=True, tag="x_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="Data", tag="y_axis")
    
    def saving_data_action(self):
        asyncio.create_task(self.data_manager.save_data())

    ### GUI---Save button
    def save_handler(self, sender, app_data, user_data):
        # print("saving....")
        self.saving_data_action()

    ### GUI---Exit button
    def exit_handler(self):
        app_state.stop()
        # asyncio.create_task(self.eqpt_manager.stop_equipment())
        asyncio.run(self.eqpt_manager.stop_equipment())
        dpg.stop_dearpygui()

    def show_exit_confirmation_modal(self):
        if not dpg.does_item_exist("exit_confirmation_modal"):
            with dpg.window(label="Confirm Exit", modal=True, no_close=True, tag="exit_confirmation_modal"):
                dpg.add_text("The equipment are still running!!! Are you sure you want to exit?")
                with dpg.group(horizontal=True, ):
                    dpg.add_button(label="Yes", width=75, callback=self.exit_handler)
                    dpg.add_button(label="No", width=75, callback=lambda: dpg.delete_item("exit_confirmation_modal"), before="Yes")

    def on_attempt_to_close(self):
        self.show_exit_confirmation_modal()
        return True  # Prevent the default close operation

    ### GUI---run progress plot---only for step plot
    def transform_for_step_plot(self, schedule_data):
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
    def setup_progress_plot(self):
        try:
            with dpg.plot(label="Progress", width=1024, height=200, tag="pro_plot"):
                dpg.add_plot_legend()
                x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Overall Time (s)")
                y_axis_p = dpg.add_plot_axis(dpg.mvYAxis, label="Value")
                # Assuming x_axis and y_axis are correctly set up
                dpg.add_vline_series([0], parent=x_axis, label="Current Progress", tag="progress_marker")
                for equipment in self.eqpt_manager.equipment_list:
                    if isinstance(equipment.schedule, CsvSchedule):
                        # times, values = zip(*equipment.schedule.schedule_data)
                        # dpg.add_line_series(times, values, parent=y_axis_p, label=equipment.name)
                        # Transform the original schedule data for a step plot
                        step_data = self.transform_for_step_plot(equipment.schedule.schedule_data)
                        times, values = zip(*step_data)
                        dpg.add_line_series(times, values, parent=y_axis_p, label=equipment.name)
        except Exception as e:
            print(f"Error while creating progress plot: {e}")

    def start_stop_action(self, current_label):
        if current_label == "Start":
            dpg.set_item_label("start_stop_button", "Stop")
            dpg.disable_item("save_button")
            # Signal tasks to stop
            app_state.start()
        else:
            dpg.set_item_label("start_stop_button", "Start")
            dpg.enable_item("save_button")
            # Signal tasks to stop
            app_state.stop()
            # asyncio.create_task(self.eqpt_manager.stop_equipment())

    ### GUI---Start button
    def start_stop_handler(self, sender, app_data, user_data):
        current_label = dpg.get_item_label(sender)
        self.start_stop_action(current_label)




