from abc import ABC, abstractmethod
import pyvisa

def expand_ranges(input_string):
    items = input_string.split(',')
    full_list = []
    for item in items:
        if ':' in item:
            start, end = item.split(':')
            full_list.extend(range(int(start), int(end) + 1))
        else:
            full_list.append(int(item))
    return full_list

class Equipment(ABC):
    """Base class for all equipment, enforcing a contract for subclasses."""
    def __init__(self, name, mode, address):
        self.name = name
        self.mode = mode # whether it is daq(acquire data) or psu(receive control)
        self.address = address
    
    @abstractmethod
    def connect(self):
        pass  # Subclasses must implement this method

    @abstractmethod
    def disconnect(self):
        pass  # Subclasses must implement this method

    @abstractmethod
    def stop(self):
        pass  # Subclasses must implement this method

    @abstractmethod
    def initialize(self):
        pass

    def identify(self):
        return f"{self.mode} Equipment connected at {self.address}"

class VisaEquipment(Equipment):
    # Class variable for ResourceManager
    rm = pyvisa.ResourceManager()
    def __init__(self, name, mode, address):
        super().__init__(name, mode, address)  # Call to superclass constructor to set address
        self.client = self.connect()

    def connect(self):
        self.client = VisaEquipment.rm.open_resource(self.address)
        print(f"Connecting to VISA equipment at {self.address}")
        return self.client

    def disconnect(self):
        self.client.close()
        print("Disconnecting VISA equipment")

class ModbusEquipment(Equipment):
    def connect(self):
        print(f"Connecting to Modbus equipment at {self.address}")

    def disconnect(self):
        print("Disconnecting Modbus equipment")


# Example subclass for a specific type of equipment
class Daq(VisaEquipment):
    def start_acquisition(self):
        print("Starting data acquisition")

# # Usage
# daq_device = Daq("GPIB0::23::INSTR")
# daq_device.connect()
# daq_device.start_acquisition()
# daq_device.disconnect()
