# In simulated_power_supply.py
from ..equipment import VisaEquipment

class simu_psu(VisaEquipment):
    def __init__(self, address='"asrt::23::INSTR"', schedule=None, type = 'psu', name='simu_psu', *args, **kwargs):
        super().__init__(address, type, schedule)
        self.name = name
        self.schedule = schedule

    async def set_voltage(self, value=1):
        print(f"Setting power supply voltage to {value}V")
        return True

    async def start(self):
        if self.schedule:
            await self.schedule.setup_schedule(self.set_voltage)

    
    async def perform_task(self):
        print(f"{self.name} performing its task.")