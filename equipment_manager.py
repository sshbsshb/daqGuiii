from state import app_state
from schedule import ConstantIntervalSchedule, CsvSchedule
import importlib
import asyncio

class EquipmentManager:
    def __init__(self, config, data_manager):
        self.config = config
        self.equipment_list = []
        self.data_manager = data_manager
        self.load_equipment()

    def load_equipment(self):
        for eq_config in self.config['equipment']:
            # Example for determining which schedule to use based on config
            if 'sample_interval' in eq_config['schedule']:
                schedule = ConstantIntervalSchedule(eq_config['schedule']['sample_interval'])
            elif 'schedule_csv' in eq_config['schedule']:
                schedule = CsvSchedule(eq_config['schedule']['schedule_csv'])
            else:
                schedule = None

            # Dynamic class loading based on the equipment type
            module_path = f"equipment.{eq_config['connection']['mode'].lower()}.{eq_config['class'].lower()}"
            module = importlib.import_module(module_path)
            class_ = getattr(module, eq_config['class'])
            equipment_instance = class_(name=eq_config['name'], connection=eq_config['connection'], settings=eq_config['settings'], schedule=schedule, data_manager=self.data_manager)
            self.equipment_list.append(equipment_instance)
    
    async def initialize_equipment(self):
        try:
            for eqpt in self.equipment_list:
                await eqpt.initialize()
        except Exception as e:
            print(f"Error initializing equipment: {e}")
        print("Everything has been initialized.")

    async def stop_equipment(self):
        try:
            for eqpt in self.equipment_list:
                await eqpt.stop()
        except Exception as e:
            print(f"Error stopping equipment: {e}")
        print("Everything has been stopped.")