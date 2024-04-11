# In simulated_daq.py
from ..equipment import VisaEquipment
from random import random
import asyncio
from pandas import Timestamp
# import time

class simu_daq(VisaEquipment):
    def __init__(self, address="GPIB0::23::INSTR", schedule=None, data_manager=None, type = 'daq', channels=list(range(101, 197)), recording_interval=1, name='simu_psu', *args, **kwargs):
        super().__init__(address, type, schedule)  # Initialize the VisaEquipment part of this object

        self.name = name
        self.channels = channels
        self.type = type
        self.recording_interval = recording_interval
        self.data_manager = data_manager  # Store the AsyncDataManager instance

    async def read_voltage(self, channels=list(range(101, 197))):
        # # Simulate reading voltage (dummy values)
        # print({channel: random() for channel in channels})

        random_floats = [str(random()) for _ in range(101, 197)]
        # print(random_floats)
        # Join the float numbers into a string separated by commas
        random_floats_string = ",".join(random_floats)
        format_values = [float(val) for val in random_floats_string.split(",")]
        timestamp = Timestamp.now()
        data_tuples = [(timestamp, f"Channel_{channel}", voltage) for channel, voltage in zip(channels, format_values)]
        if self.data_manager:
            await self.data_manager.add_data_batch(data_tuples)
        # """Simulates reading voltage values from the channels."""
        # for channel in self.channels:
        #     voltage = random()  # Simulate a voltage reading
        #     timestamp = Timestamp.now()
        #     # timestamp = time.time()
        #     # Use the AsyncDataManager instance to save the data
        #     if self.data_manager:
        #         await self.data_manager.add_data(timestamp, f"Channel_{channel}", voltage)
        # # Simulate the delay until the next reading
        # await asyncio.sleep(self.recording_interval)

    async def start(self):
        if self.schedule:
            await self.schedule.setup_schedule(self.read_voltage)
    
    async def perform_task(self):
        print(f"{self.name} performing its task.")