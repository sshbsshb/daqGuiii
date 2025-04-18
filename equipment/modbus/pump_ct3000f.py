from ..equipment import ModbusEquipment
import asyncio
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian

def f32_decode(result):
    decoder = BinaryPayloadDecoder.fromRegisters(result.registers, Endian.Big, wordorder=Endian.Little)
    return decoder.decode_32bit_float()

def f32_encode(value):
    # Create builder with CDAB byte order
    builder = BinaryPayloadBuilder(
                byteorder=Endian.BIG,  # For byte order within each word
                wordorder=Endian.LITTLE      # For word order
            )
    builder.add_32bit_float(value)
    return builder.to_registers()

class pump_ct3000f(ModbusEquipment):
    def __init__(self, name, connection, settings=None, schedule=None, *args, **kwargs):
        self.connection = connection
        super().__init__(name, self.connection)  # Initialize the Equipment part of this object
        self.schedule = schedule

    async def initialize(self):
        await self.set_flow_mode()
        print("ct3000f start!")
        await self.set_start()
        
        print("ct3000f ok!")

    async def set_flow_mode(self, mode=0):
        # write flow rate mode, 0=flow rate mode
        response = self.client.write_registers(4017, mode, self.unit)
        # print(response)
        return True
    
    async def set_start(self):
        # write pump start  
        response = self.client.write_registers(4126, 1, self.unit)
        # print(response)
        return True

    async def set_flowrate(self, value=50):
        print(f"Setting ct3000f pump to {value} ml/min")

        # Get registers to write
        registers = f32_encode(value)

        # Write to registers
        response = self.client.write_registers(4015, registers, self.unit)
        # print(response)
        # return True

    async def start(self):
        if self.schedule:
            await self.schedule.setup_schedule(self.set_flowrate)

    async def get_flowrate(self):
        # q_args = {'address': 4015,
        #   'count': 2,
        #   'slave': 1}
        response = self.client.read_holding_registers(4015, 2, self.unit)#**q_args
        if response.isError():
            print(f"Error reading registers: {response}")
        else:
            flowrate = f32_decode(response)
        return flowrate

    async def stop(self):
        # write flow rate mode
        response = self.client.write_registers(4126, 0, self.unit)
        print(response)
        return True
