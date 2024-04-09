import asyncio
import csv
from abc import ABC, abstractmethod
from state import app_state

class Schedule(ABC):
    @abstractmethod
    async def setup_schedule(self, task, *args, **kwargs):
        pass

class ConstantIntervalSchedule(Schedule):
    def __init__(self, interval):
        self.interval = interval

    async def setup_schedule(self, task, *args, **kwargs):
        while app_state.is_running():
            await asyncio.sleep(self.interval)
            await task(*args, **kwargs)

class CsvSchedule(Schedule):
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.schedule_data = self._load_csv()

    def _load_csv(self):
        schedule_data = []
        with open(self.csv_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            time = 0.0  # Accumulator for the total elapsed time
            for row in reader:
                time = float(row['time'])
                value = float(row['value'])
                schedule_data.append((time, value))
        return schedule_data

    async def setup_schedule(self, task, *args, **kwargs):
        for time, value in self.schedule_data:
            if app_state.is_running():
                await asyncio.sleep(time)
                await task(value=value)
