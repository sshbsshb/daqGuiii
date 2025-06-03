# In state.py
import traceback # For stack trace

class AppState:
    def __init__(self):
        self._is_running = False
        self.batch_current_run = 0
        self.batch_total_runs = 1
        self.batch_mode_active = False
        self.auto_start_next_batch = False
        self.auto_start_delay_s = 5
        self.system_is_stable_for_monitoring = False # Default to not stable
        print(f"AppState initialized. _is_running: {self._is_running}")

    def start(self):
        print(f"APP_STATE: start() called. Current batch_current_run: {self.batch_current_run}")
        # For detailed debugging, uncomment the next line:
        # print("Call stack for app_state.start():")
        # traceback.print_stack(limit=5)
        print("AppState.start() called, _is_running set to True.")
        self._is_running = True

    def stop(self):
        print(f"APP_STATE: stop() called. Current batch_current_run: {self.batch_current_run}")
        # For detailed debugging, uncomment the next line:
        # print("Call stack for app_state.stop():")
        # traceback.print_stack(limit=5)
        self._is_running = False
        print("AppState.stop() called, _is_running set to False.")

    def is_running(self):
        return self._is_running
    
    def set_system_stable(self, stable: bool):
        print(f"AppState: Setting system_is_stable_for_monitoring to {stable}")
        self.system_is_stable_for_monitoring = stable

    def is_system_stable(self):
        return self.system_is_stable_for_monitoring

app_state = AppState()