import asyncio
from collections import deque
import pandas as pd
# from datetime import datetime
from state import app_state

class AsyncDataManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.plot_deque = deque(maxlen=100)
        # Initialize DataFrame with 'Timestamp' as the index this time
        self.data_df = pd.DataFrame(columns=['Timestamp']).set_index('Timestamp')
        self.data_accumulator = []

    async def add_data(self, timestamp, sensor_id, new_data):
        """Adds new data to the accumulator."""
        async with self.lock:
            self.plot_deque.append((timestamp, sensor_id, new_data))
            self.data_accumulator.append({'Timestamp': timestamp, 'SensorID': sensor_id, 'Data': new_data})

    async def update_dataframe(self):
        """Updates the pandas DataFrame with accumulated data."""
        async with self.lock:
            if self.data_accumulator:
                # Convert accumulated data to DataFrame
                new_df = pd.DataFrame(self.data_accumulator)
                # Pivot new data to have 'Timestamp' as index and sensor IDs as columns
                new_df = new_df.pivot(index='Timestamp', columns='SensorID', values='Data')
                # Concatenate the new DataFrame with the existing one
                self.data_df = pd.concat([self.data_df, new_df], axis=0).sort_index().ffill()
                # Reset the accumulator
                self.data_accumulator.clear()

    async def periodically_update_dataframe(self, interval=60):
        """Periodically calls update_dataframe at the specified interval (in seconds)."""
        while app_state.is_running():
            try:
                await asyncio.sleep(interval)
                await self.update_dataframe()
            except asyncio.CancelledError:
                # Handle task cancellation
                print("Periodic update was cancelled.")
                break
            except Exception as e:
                # Log or handle the error here
                print(f"Error updating DataFrame: {e}")
