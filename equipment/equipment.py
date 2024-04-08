from abc import ABC, abstractmethod
import pyvisa

class Equipment(ABC):
    """Base class for all equipment, enforcing a contract for subclasses."""
    def __init__(self, address, type, schedule):
        self.address = address
        self.type = type # whether it is daq(acquire data) or psu(receive control)
        self.schedule = schedule
    
    @abstractmethod
    def connect(self):
        pass  # Subclasses must implement this method

    @abstractmethod
    def disconnect(self):
        pass  # Subclasses must implement this method

    @abstractmethod    
    def identify(self):
        pass

class VisaEquipment(Equipment):
    # Class variable for ResourceManager
    rm = pyvisa.ResourceManager()
    def __init__(self, address, type, schedule):
        super().__init__(address, type, schedule)  # Call to superclass constructor to set address
        self.client = None

    def connect(self):
        print(f"Connecting to VISA equipment at {self.address}")
        # Example connection using ResourceManager
        # self.client = VisaEquipment.rm.open_resource(self.address)

    def disconnect(self):
        print("Disconnecting VISA equipment")
        # Assuming there's a close or similar method to disconnect
        # self.client.close()

    def identify(self):
        return "VISA Equipment"

class ModbusEquipment(Equipment):
    def connect(self):
        print(f"Connecting to Modbus equipment at {self.address}")

    def disconnect(self):
        print("Disconnecting Modbus equipment")

    def identify(self):
        return "Modbus Equipment"

# Example subclass for a specific type of equipment
class Daq(VisaEquipment):
    def start_acquisition(self):
        print("Starting data acquisition")

# # Usage
# daq_device = Daq("GPIB0::23::INSTR")
# daq_device.connect()
# daq_device.start_acquisition()
# daq_device.disconnect()
