# In application_runner.py
import asyncio
from gui_manager import GUIManager 
from equipment_manager import EquipmentManager 
from data_manager import AsyncDataManager 
from state import app_state 
import dearpygui.dearpygui as dpg
from collections import deque
from pandas import Timestamp # Ensure this is imported if used, e.g. by DataManager or DAQ classes

class ApplicationRunner:
    def __init__(self, config, loop_instance):
        self.config = config
        self.loop = loop_instance
        self.data_manager = AsyncDataManager()
        self.eqpt_manager = EquipmentManager(self.config, self.data_manager)
        self.gui_manager = GUIManager(self.eqpt_manager, self.data_manager, self)
        self.safety_halt_active = False
        self.safety_persistence_history = {} # For safety rule persistence
        
        self.orchestrator_task = None
        self.idle_monitoring_task = None # Global task, started once
        self.safety_monitoring_task = None # Global task, started once
        
        # Flags to ensure global monitoring tasks are started only once
        self._idle_monitor_started_globally = False 
        self._safety_monitor_started_globally = False

    def get_loop(self):
        return self.loop

    async def run(self):
        self.gui_manager.setup()

        try:
            print("ApplicationRunner: Initializing all equipment at startup...")
            await self.eqpt_manager.initialize_equipment()
            print("ApplicationRunner: All equipment initialized.")
        except Exception as e_init_all:
            print(f"ApplicationRunner: CRITICAL ERROR initializing equipment at startup: {e_init_all}")
            if dpg.is_dearpygui_running():
                if dpg.does_item_exist("info_text"): dpg.set_value("info_text", "CRITICAL: Equipment Init Failed!")
                if dpg.does_item_exist("safety_alert_text"): dpg.set_value("safety_alert_text", "Equipment Init Failed! System may be unstable.")
            # Depending on severity, you might want to halt further execution:
            # if dpg.is_dearpygui_running(): dpg.stop_dearpygui()
            # return

        # Start only the batch orchestrator initially.
        # Idle and Safety monitoring will be started by batch_orchestrator after the first "Start" press.
        self.orchestrator_task = self.loop.create_task(self.batch_orchestrator())

        try:
            while dpg.is_dearpygui_running():
                dpg.render_dearpygui_frame()
                await asyncio.sleep(0.016) # Yield to the event loop
            print("ApplicationRunner: DPG render loop exited because is_dearpygui_running() returned False")
        except Exception as e:
            print(f"ApplicationRunner: Exception in DPG render loop: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            print("ApplicationRunner: DPG render loop exited or error occurred. Initiating cleanup...")

            if app_state.is_running(): # If a batch was active
                 print("ApplicationRunner: App was running. Signaling app_state.stop().")
                 app_state.stop()
                 await asyncio.sleep(0.2) # Give task_monitor a moment to react

            tasks_to_cancel_explicitly = []
            if self.orchestrator_task and not self.orchestrator_task.done():
                tasks_to_cancel_explicitly.append(self.orchestrator_task)
            
            # Add global monitoring tasks to cancellation list ONLY if they were started
            if self._idle_monitor_started_globally and self.idle_monitoring_task and not self.idle_monitoring_task.done():
                tasks_to_cancel_explicitly.append(self.idle_monitoring_task)
            if self._safety_monitor_started_globally and self.safety_monitoring_task and not self.safety_monitoring_task.done():
                tasks_to_cancel_explicitly.append(self.safety_monitoring_task)
            
            if tasks_to_cancel_explicitly:
                print(f"ApplicationRunner: Cancelling {len(tasks_to_cancel_explicitly)} main background tasks...")
                for task in tasks_to_cancel_explicitly:
                    task.cancel()
                try:
                    await asyncio.gather(*tasks_to_cancel_explicitly, return_exceptions=True)
                    print("ApplicationRunner: Main background tasks cancellation processed.")
                except Exception as e_gather: # Should not happen with return_exceptions=True
                    print(f"ApplicationRunner: Error during gather of main tasks: {e_gather}")

            if not self.safety_halt_active:
                print("ApplicationRunner: Attempting to stop all equipment as part of final cleanup...")
                try:
                    await self.eqpt_manager.stop_equipment()
                    print("ApplicationRunner: All equipment stop commands sent via main cleanup.")
                except Exception as e_stop_eq:
                    print(f"ApplicationRunner: Error during final equipment stop: {e_stop_eq}")
            else:
                print("ApplicationRunner: Equipment stop was presumably handled by the safety system.")

            if dpg.get_dearpygui_version(): 
                try:
                    if dpg.is_dearpygui_running(): 
                        dpg.stop_dearpygui()
                    dpg.destroy_context()
                    print("ApplicationRunner: DearPyGui context destroyed.")
                except Exception as e_dpg:
                    print(f"ApplicationRunner: Error destroying DPG context: {e_dpg} (Context might already be destroyed or invalid)")
            
            print("ApplicationRunner: Run method finished and cleanup sequence completed.")

    async def idle_monitoring_loop(self):
        try:
            idle_config = self.config.get('idle_monitoring', {})
            if not idle_config.get('enabled', False):
                print("Idle monitoring is disabled in config.")
                return

            interval = idle_config.get('interval_seconds', 30) # How often idle monitor tries to read
            # How often to check if main DAQ is busy when idle monitor is "paused"
            pause_check_interval = idle_config.get('pause_check_interval_seconds', 2.0) 
            
            eq_name_idle = idle_config.get('equipment_name')
            # Assuming channels_cfg is for a method like 'read_specific_channels_on_demand'
            # If idle monitor should use read_full_scan_once, this might not be needed or used differently.
            channels_cfg_idle = idle_config.get('channels_config') 

            if not eq_name_idle: # channels_cfg_idle might be optional if using read_full_scan_once
                print("Idle monitoring: 'equipment_name' missing in config.")
                return

            # Find the DAQ equipment designated for idle monitoring
            idle_daq_equipment = next((eq for eq in self.eqpt_manager.equipment_list if eq.name == eq_name_idle), None)

            if not idle_daq_equipment:
                print(f"Idle monitoring: Equipment '{eq_name_idle}' not found.")
                return
            
            # Decide which method the idle monitor uses on its DAQ.
            # Option 1: A specific method for on-demand reads of certain channels.
            # Option 2: Reuse read_full_scan_once if simpler and acceptable.
            read_method_to_use = None
            if hasattr(idle_daq_equipment, 'read_full_scan_once'):
                 read_method_to_use = idle_daq_equipment.read_full_scan_once
                 print(f"Idle monitoring using 'read_full_scan_once' for {eq_name_idle}.")
            elif hasattr(idle_daq_equipment, 'read_specific_channels_on_demand') and channels_cfg_idle:
                 read_method_to_use = lambda: idle_daq_equipment.read_specific_channels_on_demand(channels_cfg_idle)
                 print(f"Idle monitoring using 'read_specific_channels_on_demand' for {eq_name_idle}.")
            else:
                print(f"Idle monitoring: Equipment '{eq_name_idle}' has no suitable read method ('read_specific_channels_on_demand' or 'read_full_scan_once').")
                return
            
            print(f"Idle monitoring started for {eq_name_idle}. Main interval: {interval}s, Pause check: {pause_check_interval}s.")
            
            while True: # Main loop for idle monitoring
                if self.safety_halt_active or not dpg.is_dearpygui_running():
                    # If safety halt or GUI closed, stop idle monitoring.
                    print("Idle_monitor: Safety halt or DPG not running. Stopping.")
                    break
                if not app_state.is_system_stable():
                    # print("Idle_monitor: System not stable, pausing.") # Debug
                    await asyncio.sleep(pause_check_interval)
                    continue 
                # **** NEW: Check if any main DAQ is busy ****
                # self.eqpt_manager needs a method is_main_daq_busy()
                if self.eqpt_manager.is_main_daq_busy(): # This checks 'is_actively_collecting' on equipment
                    # print(f"Idle_monitor: Main DAQ is busy, pausing for {pause_check_interval}s.") # Debug
                    await asyncio.sleep(pause_check_interval)
                    continue # Go back to the start of the loop to re-evaluate all conditions
                # **** END NEW CHECK ****
                
                # If not paused, proceed with idle monitoring read.
                # This part runs regardless of app_state.is_running(), providing data
                # during batch idle times AND between batches, as long as not paused by active DAQ.
                try:
                    # print(f"Idle_monitor: Performing read from {eq_name_idle}.") # Debug
                    data_tuples = await read_method_to_use()

                    if data_tuples:
                        # Use the discussed 'add_realtime_plot_data' if you implement it in DataManager
                        # to separate this data from saved data.
                        # For now, using add_data_batch as per your current DataManager.
                        # This means idle data will also go into the main dataframe and be saved.
                        await self.data_manager.add_data_batch(data_tuples)
                        
                except asyncio.CancelledError:
                    print("Idle monitoring loop's read operation was cancelled.")
                    raise # Propagate cancellation
                except Exception as e:
                    print(f"Error during idle monitoring read from {eq_name_idle}: {e}")
                    # Sleep a bit after an error to avoid spamming logs if error is persistent
                    await asyncio.sleep(min(interval, 5.0)) 
                
                await asyncio.sleep(interval) # Wait for the main idle monitoring interval

        except asyncio.CancelledError:
            print("Idle monitoring loop was cancelled externally.")
        finally:
            print("Idle monitoring loop stopped.")

    async def safety_monitoring_loop(self):
        try:
            safety_config = self.config.get('safety_rules', {})
            if not safety_config.get('enabled', False):
                print("Safety monitoring is disabled in config.")
                return

            rules = safety_config.get('rules', [])
            interval = safety_config.get('check_interval_seconds', 1)
            # Get initial delay from config, default to e.g., 10 seconds
            initial_delay_seconds = safety_config.get('initial_ramp_up_delay_seconds', 10) 
            
            print(f"Safety monitoring starting. Initial ramp-up delay: {initial_delay_seconds}s before active checks.")
            await asyncio.sleep(initial_delay_seconds)
            print(f"Safety monitoring active. Checking {len(rules)} rules every {interval}s.")

            # Initialize persistence history if it hasn't been (for continuous monitoring)
            if not self.safety_persistence_history and rules:
                for rule_cfg in rules: # Renamed to avoid conflict with 'rules' variable name
                    if rule_cfg.get('enabled', False) and rule_cfg.get('persistence_readings', 0) > 0:
                        self.safety_persistence_history[rule_cfg['name']] = deque(maxlen=rule_cfg['persistence_readings'])
            
            while True:
                if not dpg.is_dearpygui_running() or self.safety_halt_active:
                    if self.safety_halt_active: print("Safety monitoring loop: System HALTED. Stopping safety checks.")
                    break # Exit loop if DPG closes or safety halt is active

                if not app_state.is_system_stable():
                    # print("Safety_monitor: System not stable, pausing checks.") # Debug
                    await asyncio.sleep(interval)
                    continue
                # Safety checks run continuously once started and past initial delay
                current_plot_deque_snapshot = list(self.data_manager.plot_deque)
                latest_values = {}
                for _ts, _name, ch_id, val in reversed(current_plot_deque_snapshot):
                    if ch_id not in latest_values:
                        try: latest_values[ch_id] = float(val)
                        except (ValueError, TypeError): latest_values[ch_id] = None

                for rule in rules: # Iterate through configured safety rules
                    if not rule.get('enabled', False) or self.safety_halt_active: continue

                    ch_id_to_check = rule['channel_id']
                    if ch_id_to_check in latest_values and latest_values[ch_id_to_check] is not None:
                        current_value = latest_values[ch_id_to_check]
                        condition_met_this_cycle = False
                        cond = rule['condition']
                        thresh = rule['threshold']
                        
                        if cond == "greater_than" and current_value > thresh: condition_met_this_cycle = True
                        elif cond == "less_than" and current_value < thresh: condition_met_this_cycle = True
                        elif cond == "outside_range" and isinstance(thresh, list) and len(thresh) == 2:
                            if current_value < thresh[0] or current_value > thresh[1]: condition_met_this_cycle = True
                        
                        final_condition_met = False
                        persistence_count = rule.get('persistence_readings', 1)
                        if persistence_count > 1:
                            history_deque = self.safety_persistence_history.get(rule['name'])
                            if history_deque is not None: # Should exist if initialized
                                history_deque.append(condition_met_this_cycle)
                                if len(history_deque) == persistence_count and all(history_deque):
                                    final_condition_met = True
                        else: # No persistence or persistence_readings is 1
                            if condition_met_this_cycle: final_condition_met = True
                            
                        if final_condition_met:
                            alert_message = f"SAFETY RULE '{rule['name']}' VIOLATED for {ch_id_to_check}: Value {current_value} {cond.replace('_',' ')} {thresh}. {rule.get('message', '')}"
                            print(alert_message)
                            if dpg.is_dearpygui_running():
                                if dpg.does_item_exist("safety_alert_text"): dpg.set_value("safety_alert_text", alert_message)
                                if dpg.does_item_exist("safety_alert_window"): dpg.show_item("safety_alert_window")

                            if rule.get('action') == "shutdown":
                                print("SAFETY ACTION: Initiating system shutdown due to rule violation.")
                                self.safety_halt_active = True # Critical: set flag first
                                
                                if app_state.is_running(): # If a batch is running, signal it to stop
                                    app_state.stop() 
                                    await asyncio.sleep(0.2) # Allow task_monitor to react
                                
                                await self.eqpt_manager.stop_equipment() # Stop all equipment
                                print("SAFETY ACTION: Equipment stop commands sent.")
                                
                                if dpg.is_dearpygui_running(): # Update GUI to reflect HALT
                                    if dpg.does_item_exist("start_stop_button"): dpg.configure_item("start_stop_button", label="HALTED", enabled=False)
                                    if dpg.does_item_exist("info_text"): dpg.set_value("info_text", f"SYSTEM HALTED BY SAFETY: {rule['name']}")
                                    if dpg.does_item_exist("batch_info_text"): dpg.set_value("batch_info_text", "SAFETY SHUTDOWN")
                                # Safety halt active, so break from inner rule loop and outer while loop
                    if self.safety_halt_active: break 
                await asyncio.sleep(interval) # Interval for checking safety rules
        except asyncio.CancelledError:
            print("Safety monitoring loop was cancelled.")
        finally:
            print("Safety monitoring loop stopped.")

    async def batch_orchestrator(self):
        try:
            print(f"BatchOrchestrator: Starting. auto_start_next_batch={app_state.auto_start_next_batch}, delay={app_state.auto_start_delay_s}s, total_runs={app_state.batch_total_runs}")
            for i in range(app_state.batch_total_runs):
                print(f"BatchOrchestrator: Loop iteration {i}, batch_current_run will be {i+1}")
                app_state.set_system_stable(False)
                app_state.batch_current_run = i + 1
                
                if self.safety_halt_active:
                    print("Batch orchestrator: System is HALTED due to safety. Cannot start new batch.")
                    if dpg.is_dearpygui_running():
                        if dpg.does_item_exist("info_text"): dpg.set_value("info_text", "SYSTEM HALTED. Restart required.")
                        if dpg.does_item_exist("start_stop_button"): dpg.configure_item("start_stop_button", label="HALTED", enabled=False)
                    break

                is_first_batch = (app_state.batch_current_run == 1)

                if app_state.is_running(): # Ensure previous batch state is cleared
                    # app_state.stop()
                    self.gui_manager.start_stop_action("Stop")
                    await asyncio.sleep(0.5) # Give task_monitor time to clean up previous batch

                print(f"Preparing Batch {app_state.batch_current_run} of {app_state.batch_total_runs}")
                if dpg.is_dearpygui_running():
                    self.gui_manager.update_batch_display()
                    self.gui_manager.prepare_for_new_run() 
                    dpg.set_value("info_text", f"Batch {app_state.batch_current_run} ready. Press Start.")
                else:
                    print("BatchOrchestrator: DPG not running while preparing batch. Exiting.") 
                    break # DPG not running, exit orchestrator

                self.data_manager.reset_data()

                should_auto_start_this_batch = app_state.auto_start_next_batch and not is_first_batch
                if not should_auto_start_this_batch:
                    print(f"Batch {app_state.batch_current_run}: Manual start required.")
                    if dpg.is_dearpygui_running():
                        dpg.set_value("info_text", f"Batch {app_state.batch_current_run} ready. Press Start.")
                        if dpg.does_item_exist("start_stop_button"):
                            dpg.configure_item("start_stop_button", label="Start", enabled=True)
                    # Wait for Start button press
                    while not app_state.is_running() and dpg.is_dearpygui_running() and not self.safety_halt_active:
                        await asyncio.sleep(0.1)
                else: # Auto-start this batch
                    print(f"Batch {app_state.batch_current_run}: Auto-starting in {app_state.auto_start_delay_s}s...")
                    if dpg.is_dearpygui_running():
                        dpg.set_value("info_text", f"Auto-starting Batch {app_state.batch_current_run} in {app_state.auto_start_delay_s}s...")
                        if dpg.does_item_exist("start_stop_button"): # Optionally disable during countdown
                            dpg.configure_item("start_stop_button", enabled=False)
                    
                    await asyncio.sleep(app_state.auto_start_delay_s)

                    if self.safety_halt_active or not dpg.is_dearpygui_running():
                        print(f"Batch {app_state.batch_current_run} auto-start aborted (safety/DPG closed during delay).")
                        if app_state.is_running(): self.gui_manager.start_stop_action("Stop")
                        break # Exit orchestrator loop
                    
                    print(f"Batch {app_state.batch_current_run}: Auto-starting now via GUI action.")
                    self.gui_manager.start_stop_action("Start") # Programmatically "press" start
                    # Wait briefly for app_state to reflect the start
                    for _ in range(10): # Max 1 second wait
                        if app_state.is_running(): break
                        await asyncio.sleep(0.1)

                # Check conditions after waiting for start
                if self.safety_halt_active:
                    print(f"Batch {app_state.batch_current_run} start aborted by safety system post-attempt.")
                    if app_state.is_running(): self.gui_manager.start_stop_action("Stop")
                    break
                if not dpg.is_dearpygui_running():
                    print(f"Batch {app_state.batch_current_run} start aborted (DPG closed post-attempt).")
                    if app_state.is_running(): self.gui_manager.start_stop_action("Stop")
                    break
                if not app_state.is_running():
                    print(f"Batch {app_state.batch_current_run} FAILED TO START (app_state not running post-attempt). Aborting.")
                    break

                # ---- START GLOBAL MONITORING TASKS (if not already started) ----
                if is_first_batch: # Only for the very first batch that successfully starts
                    if not self._idle_monitor_started_globally and self.config.get('idle_monitoring', {}).get('enabled', False) and not self.idle_monitoring_task:
                        print("BatchOrchestrator: First batch started, ensuring global idle_monitoring_loop is active.")
                        self.idle_monitoring_task = self.loop.create_task(self.idle_monitoring_loop())
                        self._idle_monitor_started_globally = True
                    if not self._safety_monitor_started_globally and self.config.get('safety_rules', {}).get('enabled', False) and not self.safety_monitoring_task:
                        print("BatchOrchestrator: First batch started, ensuring global safety_monitoring_loop is active.")
                        self.safety_monitoring_task = self.loop.create_task(self.safety_monitoring_loop())
                        self._safety_monitor_started_globally = True

                print(f"Start signal processed for Batch {app_state.batch_current_run}. Starting batch tasks via task_monitor...")
                if dpg.is_dearpygui_running():
                    dpg.set_value("info_text", f"Running Batch {app_state.batch_current_run}...")
                
                monitor_task_for_this_batch = None
                try:
                    monitor_task_for_this_batch = self.loop.create_task(self.task_monitor())
                    await monitor_task_for_this_batch
                except asyncio.CancelledError: # Orchestrator itself cancelled
                    print(f"BatchOrchestrator: Batch {app_state.batch_current_run} run cancelled as orchestrator was.")
                    if app_state.is_running(): self.gui_manager.start_stop_action("Stop")
                    if monitor_task_for_this_batch and not monitor_task_for_this_batch.done():
                        monitor_task_for_this_batch.cancel()
                        await asyncio.gather(monitor_task_for_this_batch, return_exceptions=True)
                    raise # Re-raise for outer handler
                # No 'finally' here for monitor_task_for_this_batch, task_monitor handles its own full cleanup.

                print(f"Batch {app_state.batch_current_run} processing via task_monitor concluded. app_state.is_running(): {app_state.is_running()}")
                app_state.set_system_stable(False) # Unstable during save and transition

                if not self.safety_halt_active:
                    print(f"BATCH_ORCH: Saving data for batch {app_state.batch_current_run}.")
                    await self.data_manager.save_data()
                else:
                    print(f"Data for batch {app_state.batch_current_run} not saved due to safety halt.")

                # print(f"DEBUG: Post-save. DPG running: {dpg.is_dearpygui_running()}, Safety halt: {self.safety_halt_active}")
                if not dpg.is_dearpygui_running():
                    # print("DEBUG: GUI stopped after batch completion! Breaking orchestrator loop.")
                    break
                if self.safety_halt_active:
                    # print("DEBUG: Safety halt active after batch completion! Breaking orchestrator loop.")
                    break
                
                # print(f"DEBUG: Checking inter-batch conditions. Current: {app_state.batch_current_run}, Total: {app_state.batch_total_runs}")
                if app_state.batch_current_run < app_state.batch_total_runs:
                    # This block is for actions/messages *after* a batch finishes and *before* the next one auto/manual starts
                    if app_state.auto_start_next_batch:
                        print(f"Batch {app_state.batch_current_run} finished. Next batch ({app_state.batch_current_run + 1}) will auto-start after delay (handled at top of next loop).")
                    else: # Manual start for next batch
                        print(f"Batch {app_state.batch_current_run} finished. Next batch ({app_state.batch_current_run + 1}) requires 'Start' press.")
                        if dpg.is_dearpygui_running():
                            try:
                                if dpg.does_item_exist("info_text"):
                                    dpg.set_value("info_text", f"Batch {app_state.batch_current_run} done. Press Start for batch {app_state.batch_current_run + 1}.")
                                if dpg.does_item_exist("start_stop_button"):
                                    dpg.configure_item("start_stop_button", label="Start", enabled=True)
                            except Exception as e_dpg_ui:
                                print(f"BATCH_ORCH_DEBUG: Error updating DPG for manual next batch: {e_dpg_ui}")
                                # Potentially break or handle this error
                    await asyncio.sleep(0.1) # Small pause before looping for clarity in logs or UI updates
                else: # This was the last batch
                    print(f"All {app_state.batch_total_runs} batches have been processed.")
                
                # print(f"DEBUG: End of orchestrator FOR loop iteration for i={i} (Batch {app_state.batch_current_run}).")
            # --- End of for loop ---
            # print(f"DEBUG: Exited orchestrator FOR loop. i={i}, Current Batch: {app_state.batch_current_run}, Total: {app_state.batch_total_runs}")

            # ... (Final GUI messages after loop completion) ...

        except asyncio.CancelledError:
            print("Batch orchestrator loop was CANCELLED externally.")
            # ... (cleanup) ...
        finally:
            print("BatchOrchestrator (outer finally): Ensuring system unstable and equipment stopped.")
            app_state.set_system_stable(False)
            # Only stop equipment if not already halted by safety, as safety_monitoring_loop handles its own stop.
            if not self.safety_halt_active:
                await self.eqpt_manager.stop_equipment()
            print("Batch orchestrator loop has fully stopped.")

    async def task_monitor(self):
        tasks_for_current_batch = []
        all_batch_tasks_started = False
        essential_tasks_completed_naturally = False # New flag

        print(f"TaskMonitor: Entered for Batch {app_state.batch_current_run}.")
        try:
            # This loop now primarily manages the state within a single batch execution.
            # It will exit (return) when the batch is no longer considered active.
            while True:
                if self.safety_halt_active:
                    app_state.set_system_stable(False)
                    print(f"TaskMonitor for Batch {app_state.batch_current_run}: Safety halt detected.")
                    if app_state.is_running(): app_state.stop()
                    # The 'else' block below will handle cleanup and return.

                if app_state.is_running():
                    if not all_batch_tasks_started:
                        print(f"TaskMonitor: Starting tasks for Batch {app_state.batch_current_run}")
                        self.gui_manager.reset_progress_marker_start_time()
                        # Create tasks for equipment, GUI updates, data manager, time limit
                        equipment_op_tasks = [self.loop.create_task(eqpt.start()) for eqpt in self.eqpt_manager.equipment_list]
                        # Store all tasks that define the batch's activity
                        tasks_for_current_batch.extend(equipment_op_tasks)
                        tasks_for_current_batch.append(self.loop.create_task(self.gui_manager.live_plot_updater()))
                        tasks_for_current_batch.append(self.loop.create_task(self.gui_manager.update_progress_marker()))
                        tasks_for_current_batch.append(self.loop.create_task(self.data_manager.periodically_update_dataframe()))
                        tasks_for_current_batch.append(self.loop.create_task(self.overall_time_limit_reached()))
                        all_batch_tasks_started = True
                        app_state.set_system_stable(True)
                        essential_tasks_completed_naturally = False # Reset for current batch
                        print(f"TaskMonitor: {len(tasks_for_current_batch)} tasks started for Batch {app_state.batch_current_run}.")

                    # Check for natural completion of essential tasks (e.g., equipment operations)
                    if all_batch_tasks_started and not essential_tasks_completed_naturally:
                        # Define "essential_tasks" - typically the equipment tasks.
                        # For simplicity, let's assume all tasks in equipment_op_tasks are essential.
                        # If equipment_op_tasks is empty (no equipment), this check might need adjustment.
                        if not equipment_op_tasks: # No equipment, perhaps batch ends immediately or by time limit
                             pass # Or consider it done if other conditions met
                        else:
                            all_essential_done = True
                            for task in equipment_op_tasks: # Check only equipment tasks for natural end
                                if not task.done():
                                    all_essential_done = False
                                    break
                            
                            if all_essential_done:
                                print(f"TaskMonitor: All essential equipment tasks for Batch {app_state.batch_current_run} completed naturally.")
                                essential_tasks_completed_naturally = True
                                if app_state.is_running(): # If batch was still considered running
                                    print(f"TaskMonitor: Signaling natural end of Batch {app_state.batch_current_run} by calling app_state.stop().")
                                    app_state.stop() # This is the key change!
                                # Now, in the next iteration, app_state.is_running() will be false,
                                # leading to the 'else' block for cleanup and return.
                else: # app_state is not running (batch ended by natural completion, user stop, time limit, or safety)
                    app_state.set_system_stable(False)
                    print(f"TaskMonitor: app_state is NOT running for Batch {app_state.batch_current_run}. Proceeding to cleanup.")
                    if tasks_for_current_batch: # If tasks were started, clean them up
                        print(f"TaskMonitor: Stopping equipment and cancelling tasks for Batch {app_state.batch_current_run}.")
                        try:
                            if not self.safety_halt_active:
                                await self.eqpt_manager.stop_equipment()
                            else:
                                print(f"TaskMonitor: Equipment stop deferred to safety system or already done.")

                            for task in tasks_for_current_batch:
                                if not task.done():
                                    task.cancel()
                            results = await asyncio.gather(*tasks_for_current_batch, return_exceptions=True)
                            # Process results (check for unexpected errors during cancellation)
                            for i, res in enumerate(results):
                                if isinstance(res, Exception) and not isinstance(res, asyncio.CancelledError):
                                    task_name = tasks_for_current_batch[i].get_name() if hasattr(tasks_for_current_batch[i], 'get_name') else f"Task {i}"
                                    print(f"TaskMonitor: Exception in gathered task '{task_name}' during stop: {res}")
                            tasks_for_current_batch.clear()
                            print(f"TaskMonitor: Tasks for Batch {app_state.batch_current_run} stopped and cleared.")
                        except Exception as e_cleanup:
                            print(f"TaskMonitor: Error during task cleanup for Batch {app_state.batch_current_run}: {e_cleanup}")
                    
                    # CRITICAL: task_monitor must exit now that this batch's lifecycle is complete.
                    print(f"TaskMonitor for Batch {app_state.batch_current_run} is returning (exiting its execution).")
                    return # This allows `await monitor_task_for_this_batch` in orchestrator to complete.

                await asyncio.sleep(0.2) # Polling interval
        except asyncio.CancelledError:
            app_state.set_system_stable(False)
            print(f"Task monitor for Batch {app_state.batch_current_run} was CANCELLED externally.")
            # This is an expected path if batch_orchestrator or ApplicationRunner.run() cancels it.
        finally:
            # This finally block ensures cleanup if task_monitor is cancelled abruptly.
            app_state.set_system_stable(False)
            print(f"TaskMonitor (finally block) for Batch {app_state.batch_current_run}: Cleaning up...")
            if tasks_for_current_batch:
                # Check if already cleaned up by the 'else' block of the main loop
                # This check might be tricky; rely on idempotency of stop/cancel
                print(f"TaskMonitor (finally): Performing final cleanup of tasks and equipment for batch {app_state.batch_current_run}.")
                try:
                    if not self.safety_halt_active:
                        # Check if stop_equipment was already called in the 'else' block
                        # This might require a flag or more sophisticated state. For now, calling again might be okay if idempotent.
                        await self.eqpt_manager.stop_equipment()
                    for task in tasks_for_current_batch:
                        if not task.done(): task.cancel()
                    await asyncio.gather(*tasks_for_current_batch, return_exceptions=True)
                except Exception as e_final_cleanup:
                    print(f"TaskMonitor (finally): Error during final cleanup for batch {app_state.batch_current_run}: {e_final_cleanup}")
            tasks_for_current_batch.clear() # Ensure it's cleared
            all_batch_tasks_started = False # Reset for any potential (though unlikely) re-entry
            essential_tasks_completed_naturally = False
            print(f"Task monitor for batch {app_state.batch_current_run} has finished execution and cleaned up.")

    async def overall_time_limit_reached(self):
        try:
            time_limit_config = self.config.get('overall_time_limit', 86400) # Default to 24 hours
            # Assuming time_limit_config is a direct integer value for simplicity.
            # If it's from a nested dict: time_limit = time_limit_config.get('value', 86400)
            time_limit = int(time_limit_config)
            
            await asyncio.sleep(time_limit) 
            if app_state.is_running() and not self.safety_halt_active: # Check if batch is still relevant
                print(f"Overall time limit for Batch {app_state.batch_current_run} reached. Stopping batch...")
                self.gui_manager.start_stop_action("Stop") # This will set app_state.is_running() to False
        except asyncio.CancelledError:
            print(f"Overall time limit task for Batch {app_state.batch_current_run} cancelled.")
            # Do not re-raise, allow cancellation to be handled by gather in task_monitor
        except ValueError:
            print(f"Error: overall_time_limit '{time_limit_config}' is not a valid integer.")
        finally:
            print(f"Overall time limit task for batch {app_state.batch_current_run} finished.")