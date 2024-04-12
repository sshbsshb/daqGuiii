from ..equipment import VisaEquipment
import asyncio

class Ka3005PSU(VisaEquipment):
    def __init__(self, name, connection, settings=None, schedule=None, *args, **kwargs):
        self.connection = connection
        super().__init__(name, self.connection['mode'], self.connection['address'])  # Initialize the VisaEquipment part of this object
        self.schedule = schedule
        asyncio.run(self.set_current(current=0.1)) # precaution
        asyncio.run(self.set_output())

    async def set_output(self):
        self.client.write('OVP1')
        # time.sleep(0.1)
        self.client.write('OCP1')
        # time.sleep(0.1)
        self.client.write('OUT1')
        return True

    async def set_voltage(self, value=0.5):
        print(f"Setting power supply voltage to {value}V")
        self.client.write('VSET1:%4.3f' % (value))
        # return True

    async def set_current(self, current=0.1):
        self.client.write('ISET1:%4.3f' % (current))
        return True

    async def start(self):
        if self.schedule:
            await self.schedule.setup_schedule(self.set_voltage)

    async def get_voltage(self):
        voltage = self.client.query('VOUT1?')
        return voltage

    async def get_current(self):
        current = self.client.query('IOUT1?')
        return current

    async def set_stop(self):
        # self.write('OUT1')
        self.client.write('VSET1:0') ## have to use 0v to stop? bug?
        return True
