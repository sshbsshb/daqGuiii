from ..equipment import VisaEquipment, expand_ranges # Make sure this relative import is correct
import asyncio
from pandas import Timestamp

class daq_keysight(VisaEquipment):
    def __init__(self, name, connection, settings=None, schedule=None, data_manager=None):
        # self.connection = connection # Store original if needed, but super().__init__ uses parts of it
        super().__init__(name, connection['mode'], connection['address'])
        
        self.schedule = schedule
        self.channels_config = settings.get('channels', []) if settings else [] # Use .get for safety
        self.data_manager = data_manager
        self.scan_list = [] # Will be populated by setup_channels
        self.is_actively_collecting = False
        # No self.running flag for now, relying on task cancellation

    async def initialize(self):
        if not self.client:
            print(f"{self.name}: VISA client not available for initialize.")
            return False
        try:
            await self.reset_Daq()
            self.scan_list = await self.setup_channels(self.channels_config)
            print(f"{self.name}: DAQ initialized successfully. Scan list: {self.scan_list}")
            return True
        except Exception as e:
            print(f"{self.name}: Error during DAQ initialization: {e}")
            return False

    async def reset_Daq(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.client.write, "*RST")
        await asyncio.sleep(0.5) # Allow time for DAQ to reset
        print(f"{self.name}: *RST command sent.")
        return True

    async def setup_channels(self, channels_config_list):
        loop = asyncio.get_running_loop()
        temp_scan_list_numbers = [] # Store channel numbers as strings

        for item in channels_config_list:
            channel_str = str(item['channel']) # Ensure channel is a string for VISA
            # User's command format:
            conf_cmd = f":CONF:{item['measurement']} {item['sensor_type']},(@{channel_str})"
            print(f"{self.name}: Sending command: {conf_cmd}")
            await loop.run_in_executor(None, self.client.write, conf_cmd)
            
            if item['measurement'] == "FRES":
                # This command needs verification for the specific DAQ model (e.g., DAQ970A)
                # It might be channel-specific or global. Assuming global as in user's code.
                print(f"{self.name}: Note - Sending 'FRES:OCOM ON'. Verify this command.")
                await loop.run_in_executor(None, self.client.write, 'FRES:OCOM ON')
            
            temp_scan_list_numbers.append(channel_str)

        if not temp_scan_list_numbers:
            print(f"{self.name}: No channels were configured.")
            return []

        scan_list_for_route_cmd = ",".join(temp_scan_list_numbers)
        route_scan_cmd = f':ROUTe:SCAN (@{scan_list_for_route_cmd})'
        print(f"{self.name}: Sending command: {route_scan_cmd}")
        await loop.run_in_executor(None, self.client.write, route_scan_cmd)
        
        # expand_ranges should parse the command string (e.g. "101,103:105")
        # into a list of actual channel numbers/strings in scan order.
        actual_scan_order_list = expand_ranges(scan_list_for_route_cmd)
        return actual_scan_order_list # e.g., ['101', '103', '104', '105']

    async def read_full_scan_once(self):
        if not self.scan_list:
            print(f"{self.name}: No scan list configured. Cannot read.")
            return []
        if not self.client:
            print(f"{self.name}: VISA client not available for read.")
            return []

        loop = asyncio.get_running_loop()
        try:
            raw_reading_str = await loop.run_in_executor(None, self.client.query, ':READ?')
            format_values_str_list = raw_reading_str.strip().split(',')
            
            if len(format_values_str_list) != len(self.scan_list):
                print(f"{self.name}: Mismatch in scan data. Expected {len(self.scan_list)} for channels {self.scan_list}, got {len(format_values_str_list)}. Data: '{raw_reading_str}'")
                format_values_float = [float('nan')] * len(self.scan_list)
            else:
                try:
                    format_values_float = [float(val_str) for val_str in format_values_str_list]
                except ValueError as ve:
                    print(f"{self.name}: Could not convert all readings to float: {ve}. Data: '{raw_reading_str}'")
                    format_values_float = [float('nan')] * len(self.scan_list)

            current_timestamp = Timestamp.now()
            data_tuples = []
            # self.scan_list contains the channel identifiers in the order they are scanned
            for i, channel_id_str in enumerate(self.scan_list):
                data_tuples.append((
                    current_timestamp,
                    self.name,
                    f"Channel_{channel_id_str}", # Use the actual channel ID from scan_list
                    format_values_float[i]
                ))
            return data_tuples
        except Exception as e: # Catch VISA communication errors
            print(f"{self.name}: Error during VISA read in read_full_scan_once: {e}")
            current_timestamp = Timestamp.now()
            return [(current_timestamp, self.name, f"Channel_{ch_id}", float('nan')) for ch_id in self.scan_list]

    async def read_channels(self, value=1): # 'value' from CSV is num_scans_to_acquire
        num_scans = int(value)
        if num_scans <= 0:
            return

        # print(f"{self.name}: Starting active DAQ period to acquire {num_scans} scans.")
        self.is_actively_collecting = True
        try:
            for i in range(num_scans):
                # If this task is cancelled (e.g., batch stop), CancelledError will be raised
                # at the next await point (read_full_scan_once or asyncio.sleep).
                data_tuples = await self.read_full_scan_once()
                if data_tuples and self.data_manager:
                    # Assuming add_data_batch is the method in your AsyncDataManager
                    await self.data_manager.add_data_batch(data_tuples)
                
                if num_scans > 1 and i < num_scans - 1: # If multiple readings in this burst
                    await asyncio.sleep(0.4) # Interval between scans within this burst
        
        # Corrected indentation for these except blocks
        except asyncio.CancelledError:
            print(f"{self.name}: read_channels task was cancelled.")
            raise # Important to propagate so the scheduler/monitor knows it was cancelled
        except Exception as e:
            print(f"{self.name}: Error during read_channels active period: {e}")
            # Depending on severity, you might want to re-raise or just log
        finally:
            self.is_actively_collecting = False
            # print(f"{self.name}: is_actively_collecting set to False.")

    async def start(self): # Effective start method
        # Called by task_monitor at the beginning of a batch for this equipment.
        self.is_actively_collecting = False # Ensure initial state

        if self.schedule and hasattr(self.schedule, 'setup_schedule'):
            print(f"{self.name}: Starting scheduled operations via {type(self.schedule).__name__}.")
            try:
                # This await means self.start() will complete when the entire schedule
                # for this equipment is done, or if CsvSchedule is stopped/cancelled.
                await self.schedule.setup_schedule(self.read_channels)
            except asyncio.CancelledError:
                print(f"{self.name}: Scheduled operations for {self.name} were cancelled.")
                # This is an expected path if the batch is stopped.
            except Exception as e:
                print(f"{self.name}: Error during scheduled operations for {self.name}: {e}")
            finally:
                print(f"{self.name}: Scheduled operations for {self.name} concluded or were terminated.")
                self.is_actively_collecting = False # Final safety net
        else:
            print(f"{self.name}: Start called, but no schedule defined. Equipment will be idle unless called by other means.")
            # If no schedule, start() completes quickly. Equipment might still be used by idle_monitor for on-demand reads.

    async def stop(self):
        print(f"{self.name}: Stop command received.")
        self.is_actively_collecting = False # Reset flag immediately

        if self.client:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.client.write, 'ABORt') # ABORt scan
                print(f"{self.name}: ABORt command sent.")
            except Exception as e:
                print(f"{self.name}: Error sending ABORt command: {e}")
        
        print(f"{self.name} (daq_keysight) processing for stop command complete.")
        return True