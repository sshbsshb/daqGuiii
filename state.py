# In state.py
import traceback # For stack trace

class AppState:
    def __init__(self):
        self._is_running = False
        self.batch_current_run = 0
        self.batch_total_runs = 1
        self.batch_mode_active = False

    def start(self):
        print(f"APP_STATE: start() called. Current batch_current_run: {self.batch_current_run}")
        # For detailed debugging, uncomment the next line:
        # print("Call stack for app_state.start():")
        # traceback.print_stack(limit=5)
        self._is_running = True

    def stop(self):
        print(f"APP_STATE: stop() called. Current batch_current_run: {self.batch_current_run}")
        # For detailed debugging, uncomment the next line:
        # print("Call stack for app_state.stop():")
        # traceback.print_stack(limit=5)
        self._is_running = False

    def is_running(self):
        return self._is_running

app_state = AppState()