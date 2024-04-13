from ..equipment import VisaEquipment, expand_ranges
from random import random
import asyncio
from pandas import Timestamp
# import time


class KeysightDAQ(VisaEquipment):
    def __init__(self, name, connection, settings=None, schedule=None, data_manager=None):
        self.connection = connection
        super().__init__(name, self.connection['mode'], self.connection['address'])  # Initialize the VisaEquipment part of this object
        self.schedule = schedule
        self.channels = settings['channels']
        self.data_manager = data_manager  # Store the AsyncDataManager instance
        self.scan_list = []
        if asyncio.run(self.reset_Daq()):
            self.scan_list = asyncio.run(self.setup_channels(self.channels))
        print(self.scan_list)

    async def reset_Daq(self):
        # self.client.write("*RST")
        await asyncio.sleep(0.5)
        print("daq reset!")
        return True

    async def setup_channels(self, channels):
        scan_list = []

        for _, item in enumerate(channels):
             # for old 3497xA, it should be
            # self.client.write(':CONF:%s,%s,(@%s)' % (item['measurement'], item['sensor_type'], item['channel'])) # please check command expert!
            print(':CONF:%s %s,(@%s)' % (item['measurement'], item['sensor_type'], item['channel']))
            # self.client.write(':CONF:%s %s,(@%s)' % (item['measurement'], item['sensor_type'], item['channel']))
            scan_list.append(item['channel'])
            await asyncio.sleep(0.1)

        await asyncio.sleep(0.1)
        scan_list_str = ",".join(str(i) for i in scan_list)
        print((':ROUTe:SCAN (@%s)' % (scan_list_str)))
        # self.client.write(':ROUTe:SCAN (@%s)' % (scan_list_str))
        scan_list =  expand_ranges(scan_list_str)
        return scan_list
    
    async def read_channels(self, value=1):
        for _ in range(round(value)): ## if csv schedule, can record "value" points of data
            reading = ",".join([str(random()) for _ in self.scan_list])
            # reading = self.client.query(':READ?')
            format_values = [float(val) for val in reading.split(",")]
            timestamp = Timestamp.now()
            data_tuples = [(timestamp, self.name, f"Channel_{channel}", voltage) for channel, voltage in zip(self.scan_list, format_values)]
            if self.data_manager:
                await self.data_manager.add_data_batch(data_tuples)
            if  value > 1:
                await asyncio.sleep(0.5) # wait for 0.5 sec for next round of data
    async def start(self):
        if self.schedule:
            await self.schedule.setup_schedule(self.read_channels)
    
    async def perform_task(self):
        print(f"{self.name} performing its task.")
