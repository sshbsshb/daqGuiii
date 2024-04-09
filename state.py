import time
class AppState:
    def __init__(self):
        self._is_running = False
        self._start_time = time.time()

    def start(self):
        self._is_running = True
        self._start_time = time.time()

    def stop(self):
        self._is_running = False

    def is_running(self):
        return self._is_running
    
    def get_start_time(self):
        return self._start_time

app_state = AppState()