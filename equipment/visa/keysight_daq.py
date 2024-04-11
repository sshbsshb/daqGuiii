# In simulated_daq.py
from ..equipment import VisaEquipment
from random import random
import asyncio
from pandas import Timestamp
# import time

class KeysightDAQ(VisaEquipment):
    def __init__(self, address="GPIB0::23::INSTR", schedule=None, data_manager=None, type = 'daq', channels=list(range(101, 197)), recording_interval=1, name='simu_psu', *args, **kwargs):
        super().__init__(address, type, schedule)  # Initialize the VisaEquipment part of this object
        super().connect()
        self.name = name
        self.channels = channels
        self.type = type
        self.recording_interval = recording_interval
        self.data_manager = data_manager  # Store the AsyncDataManager instance
        self.restDaq()

    async def restDaq(self):
        self.client.write("*RST")
        time.sleep(0.5)

    def setDaqChannels(self, loaded_setting):

        scan_list = []
        if not self.debug:
            self.restDaq()

            for i, item in enumerate(loaded_setting):
                # print(':CONFigure:%s %s,%s,(@%s)' % (item['Measurement'], item['Probe type'], item['Sensor type'], item['Channel id']))
                # for old 3497xA, it should be
                # self.client.write(':CONF:%s,%s,(@%s)' % (item['Measurement'], item['Sensor type'], item['Channel id'])) # please check command expert!
                self.client.write(':CONF:%s %s,(@%s)' % (item['Measurement'], item['Sensor type'], item['Channel id']))
                time.sleep(0.1)
                scan_list.append(item['Channel id'])
                # self.updateDisplayData(i, item['Display'])
            time.sleep(0.1)
            scan_list_str = ",".join(str(i) for i in scan_list)
            # print((':ROUTe:SCAN (@%s)' % (scan_list_str)))
            self.client.write(':ROUTe:SCAN (@%s)' % (scan_list_str))
            # sum(list(map(scan_list_str, count_element)))
        else:
            for i, item in enumerate(loaded_setting):
                scan_list.append(item['Channel id'])
            # scan_list_str = ",".join(str(i) for i in scan_list)

        return scan_list
    
    async def read_voltage(self, channels=list(range(101, 197))):
        # # Simulate reading voltage (dummy values)
        # print({channel: random() for channel in channels})
        reading = self.client.query(':READ?')
        # time.sleep(0.5)
        format_values = [float(val) for val in reading.split(",")]
        """Simulates reading voltage values from the channels."""
        for channel in self.channels:
            voltage = random()  # Simulate a voltage reading
            timestamp = Timestamp.now()
            # timestamp = time.time()
            # Use the AsyncDataManager instance to save the data
            if self.data_manager:
                await self.data_manager.add_data(timestamp, f"Channel_{channel}", voltage)
        # Simulate the delay until the next reading
        # await asyncio.sleep(self.recording_interval)

    async def start(self):
        if self.schedule:
            await self.schedule.setup_schedule(self.read_voltage)
    
    async def perform_task(self):
        print(f"{self.name} performing its task.")

import time
import random

class keysightDaq:

    def __init__(self, client, debug=True):
        self.debug = debug

        self.serialNumber = None
        self.client = client

    def setValue(self, value):
        print(f"Type A setting value: {value}")
    
    def restDaq(self):
        self.client.write("*RST")
        time.sleep(0.5)

    def setDaqChannels(self, loaded_setting):

        scan_list = []
        if not self.debug:
            self.restDaq()

            for i, item in enumerate(loaded_setting):
                # print(':CONFigure:%s %s,%s,(@%s)' % (item['Measurement'], item['Probe type'], item['Sensor type'], item['Channel id']))
                # for old 3497xA, it should be
                # self.client.write(':CONF:%s,%s,(@%s)' % (item['Measurement'], item['Sensor type'], item['Channel id'])) # please check command expert!
                self.client.write(':CONF:%s %s,(@%s)' % (item['Measurement'], item['Sensor type'], item['Channel id']))
                time.sleep(0.1)
                scan_list.append(item['Channel id'])
                # self.updateDisplayData(i, item['Display'])
            time.sleep(0.1)
            scan_list_str = ",".join(str(i) for i in scan_list)
            # print((':ROUTe:SCAN (@%s)' % (scan_list_str)))
            self.client.write(':ROUTe:SCAN (@%s)' % (scan_list_str))
            # sum(list(map(scan_list_str, count_element)))
        else:
            for i, item in enumerate(loaded_setting):
                scan_list.append(item['Channel id'])
            # scan_list_str = ",".join(str(i) for i in scan_list)

        return scan_list

    def getDaqChannels(self, args):
        if not self.debug:
            # temp_data = []
            # for channel in self.channels:
            #     reading = self.daq.query(f"MEASure:VOLTage:DC? (@{channel})")
            #     temp_data.append(float(reading))
            reading = self.client.query(':READ?')
            # time.sleep(0.5)
            format_values = [float(val) for val in reading.split(",")]
            # self.data_ready.emit(format_values)
        else:
            self.nPlots = 7
            format_values = random.sample(range(101), self.nPlots)

            # Convert the list to a string
            # reading = ', '.join(str(x) for x in my_list)
            # self.data_ready.emit(my_list)
        return format_values