# In simulated_daq.py
from ..equipment import VisaEquipment, expand_ranges
from random import random
import asyncio
from pandas import Timestamp
# import time

class simu_daq(VisaEquipment):
    def __init__(self, name, connection, settings=None, schedule=None, data_manager=None):
        self.connection = connection
        super().__init__(name, self.connection['mode'], self.connection['address'])  # Initialize the VisaEquipment part of this object
        self.schedule = schedule
        self.channels = settings['channels']
        self.data_manager = data_manager
        self.scan_list = []
        self.scan_list = asyncio.run(self.setup_channels(self.channels))

    async def setup_channels(self, channels):
        scan_list = []

        for _, item in enumerate(channels):
            scan_list.append(item['channel'])
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.1)
        scan_list_str = ",".join(str(i) for i in scan_list)
        scan_list =  expand_ranges(scan_list_str)
        return scan_list

    async def read_channels(self):
        # # Simulate reading voltage (dummy values)
        # print({channel: random() for channel in channels})

        random_floats = [str(random()) for _ in self.scan_list]
        # print(random_floats)
        # Join the float numbers into a string separated by commas
        random_floats_string = ",".join(random_floats)
        format_values = [float(val) for val in random_floats_string.split(",")]
        timestamp = Timestamp.now()
        data_tuples = [(timestamp, f"Channel1_{channel}", voltage) for channel, voltage in zip(self.scan_list, format_values)]
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


    async def start(self):
        if self.schedule:
            await self.schedule.setup_schedule(self.read_channels)
    
    async def perform_task(self):
        print(f"{self.name} performing its task.")