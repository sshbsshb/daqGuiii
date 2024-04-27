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
            for row in reader:
                time = float(row['time'])
                value = float(row['value'])
                schedule_data.append((time, value))
        return schedule_data

    async def setup_schedule(self, task, *args, **kwargs):
        start_time = asyncio.get_event_loop().time()
        last_time = 0
        for time, value in self.schedule_data:
            if app_state.is_running():
                elapsed_time = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, time - last_time - elapsed_time)
                await asyncio.sleep(sleep_time)
                start_time = asyncio.get_event_loop().time()
                await task(value=value)
                last_time = time
                # end_task_time = asyncio.get_event_loop().time()
                # start_time += time + (end_task_time - start_task_time)