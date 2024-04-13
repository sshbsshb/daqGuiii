# In simulated_power_supply.py
from ..equipment import VisaEquipment
import asyncio

class simu_psu(VisaEquipment):
    def __init__(self, name, connection, settings=None, schedule=None, *args, **kwargs):
        self.connection = connection
        super().__init__(name, self.connection['mode'], self.connection['address'])  # Initialize the VisaEquipment part of this object
        self.schedule = schedule

    async def initialize(self):
        await asyncio.sleep(0.5)

    async def set_voltage(self, value=1):
        print(f"Setting power supply voltage to {value}V")
        return True

    async def start(self):
        if self.schedule:
            await self.schedule.setup_schedule(self.set_voltage)

    async def stop(self):
        print("psu stopped")
        return True