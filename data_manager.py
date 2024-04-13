import asyncio
from collections import deque
import pandas as pd
from datetime import datetime
from state import app_state
import os

class AsyncDataManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.plot_deque = deque(maxlen=100)
        # If initial df with columns will create future warning in the concatenate
        self.data_df = pd.DataFrame() # pd.DataFrame(columns=['Timestamp', 'Name', 'Channel', 'Data']).set_index(['Timestamp', 'Name'])
        self.data_accumulator = []

    def reset_data(self):
        self.data_accumulator.clear()
        # self.data_df.iloc[0:0]
        self.data_df = pd.DataFrame() # pd.DataFrame(columns=['Timestamp', 'Name', 'Channel', 'Data']).set_index(['Timestamp', 'Name'])

    async def add_data(self, timestamp, name, channel, new_data):
        """Adds new data to the accumulator."""
        async with self.lock:
            self.plot_deque.append((timestamp, name, channel, new_data))
            self.data_accumulator.append({'Timestamp': timestamp, 'Name':name, 'Channel': channel, 'Data': new_data})

    async def add_data_batch(self, data_tuples):
        """Adds new data in batches to the accumulator. Each tuple in data_tuples contains (timestamp, sensor_id, new_data)."""
        async with self.lock:
            for timestamp, name, channel, new_data in data_tuples:
                self.plot_deque.append((timestamp, name, channel, new_data))
                self.data_accumulator.append({'Timestamp': timestamp, 'Name':name, 'Channel': channel, 'Data': new_data})

    async def update_dataframe(self):
        """Updates the pandas DataFrame with accumulated data."""
        async with self.lock:
            if self.data_accumulator:
                # Convert accumulated data to DataFrame
                new_df = pd.DataFrame(self.data_accumulator)
                new_df.set_index(['Timestamp', 'Name'], inplace=True)
                # Filter out all-NA rows
                new_df = new_df.dropna(how='all')
                if not new_df.empty:
                    # Concatenate while ensuring we don't introduce or propagate NA unnecessarily
                    # self.data_df = pd.concat([self.data_df, new_df], axis=0).sort_index().fillna(method='ffill')
                    self.data_df = pd.concat([self.data_df, new_df], axis=0).sort_index().ffill()
                # Reset the accumulator
                self.data_accumulator.clear()

    async def periodically_update_dataframe(self, interval=5):
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

    async def save_data(self):
        await self.update_dataframe()  # Ensure the DataFrame is up to date
        current_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Ensure the "data" directory exists
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, f"data_{current_time_str}.csv")
        try:
            self.data_df.to_csv(file_path)
            print(f"Data successfully saved to {file_path}.")
        except Exception as e:
            print(f"Error saving data: {e}")