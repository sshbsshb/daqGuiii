class AppState:
    def __init__(self):
        self._is_running = False

    def start(self):
        self._is_running = True

    def stop(self):
        self._is_running = False

    def is_running(self):
        return self._is_running

app_state = AppState()