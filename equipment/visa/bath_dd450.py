from ..equipment import VisaEquipment
import asyncio
from pandas import Timestamp

class bath_dd450(VisaEquipment):
    def __init__(self, name, connection, settings=None, schedule=None, data_manager=None):
        self.connection = connection
        super().__init__(name, self.connection['mode'], self.connection['address'])  # Initialize the VisaEquipment part of this object
        self.schedule = schedule
        self.data_manager = data_manager  # Store the AsyncDataManager instance

    async def initialize(self):
        await self.set_start()
        await self.set_protection()
        print("dd450 ok!")

    async def set_protection(self):
        self.client.write('out_sp_03 95') # set high temperature
        # time.sleep(0.1)
        self.client.write('out_sp_04 5') # set low temperature
        # time.sleep(0.1)
        return True

    async def set_temperature(self, value=25):
        temperature_raw = self.client.query('in_pv_02')
        actual_temperature = float(temperature_raw)
        print(f"PT100 temperature is {actual_temperature}C")

        print(f"Setting bath temperature to {value}C")
        self.client.write('out_sp_00 %4.2f' % (value)) 

        # actual_temperature = float(temperature_raw)
        # print(f"PT100 temperature is {actual_temperature}C")
        # if self.data_manager:
        #         print("PT100 temperature datad")
        #         timestamp = Timestamp.now()
        #         await self.data_manager.add_data(self, timestamp, self.name, f"Actual_temperature", actual_temperature)
        # return True

    async def set_start(self):
        self.client.write('out_mode_05 1')  # Start command of the device in remote control
        self.client.write('out_mode_04 1')  # use external temperature sensor control
        return True

    async def start(self):
        if self.schedule:
            await self.schedule.setup_schedule(self.set_temperature)

    async def stop(self):
        self.client.write('out_mode_04 0') # use internal temperature sensor control
        self.client.write('out_mode_05 0') # Stop command of the device in remote control
        return True
