from ..equipment import VisaEquipment
import asyncio

class psu_e36155(VisaEquipment):
    def __init__(self, name, connection, settings=None, schedule=None, *args, **kwargs):
        self.connection = connection
        super().__init__(name, self.connection['mode'], self.connection['address'])  # Initialize the VisaEquipment part of this object
        self.schedule = schedule

    async def initialize(self):
        await self.set_sense()
        await self.set_protection()
        print("e36155 ok!")

    async def set_sense(self):
        self.client.write('VOLT:SENS EXT') # set 4-wire sense

    async def set_protection(self):
        self.client.write('VOLT:PROT MAX')
        # time.sleep(0.1)
        self.client.write('CURR:PROT:STAT ON')
        # time.sleep(0.1)
        self.client.write('OUTP ON')
        return True

    async def set_voltage(self, value=0.5):
        print(f"Setting power supply voltage to {value}V")
        resistance = 13
        current = 1.5 * 6 * value / resistance # 150% of the 6 units' max current
        self.client.write('APPL %4.3f, %4.3f' % (value, current)) 
        # self.client.write('OUTP ON')
        # return True

    async def set_current(self, current=0.1):
        pass

    async def start(self):
        if self.schedule:
            await self.schedule.setup_schedule(self.set_voltage)

    async def get_voltage(self):
        voltage = self.client.query('MEAS:VOLT?')
        return voltage

    async def get_current(self):
        current = self.client.query('MEAS:CURR?')
        return current

    async def stop(self):
        # self.write('OUT1')
        self.client.write('OUTP OFF') ## have to use 0v to stop? bug?
        return True
