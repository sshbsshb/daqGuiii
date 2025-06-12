# In data_manager.py
import asyncio
from collections import deque
import pandas as pd
from datetime import datetime
from state import app_state
import os

class AsyncDataManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.plot_deque = deque(maxlen=100) # Max length of data points for live plotting
        self.data_df = pd.DataFrame()
        self.data_accumulator = []

    def reset_data(self):
        # Called before each batch run
        self.plot_deque.clear()
        self.data_accumulator.clear()
        self.data_df = pd.DataFrame() 
        print("Data manager reset for new batch/run.")

    async def add_data(self, timestamp, name, channel, new_data):
        async with self.lock:
            self.plot_deque.append((timestamp, name, channel, new_data))
            self.data_accumulator.append({'Timestamp': timestamp, 'Name':name, 'Channel': channel, 'Data': new_data})

    async def add_data_batch(self, data_tuples):
        async with self.lock:
            for timestamp, name, channel, new_data in data_tuples:
                self.plot_deque.append((timestamp, name, channel, new_data))
                self.data_accumulator.append({'Timestamp': timestamp, 'Name':name, 'Channel': channel, 'Data': new_data})

    async def add_realtime_plot_data(self, data_tuples):
        async with self.lock:
            for timestamp, name, channel, new_data in data_tuples:
                self.plot_deque.append((timestamp, name, channel, new_data))

    async def update_dataframe(self):
        async with self.lock:
            if self.data_accumulator:
                new_df = pd.DataFrame(self.data_accumulator)
                # It's generally better to set index after concatenation if structure is consistent
                # new_df.set_index(['Timestamp', 'Name'], inplace=True) # This might cause issues if accumulator is empty or types change
                
                # Ensure Timestamp is datetime if not already
                if 'Timestamp' in new_df.columns:
                    new_df['Timestamp'] = pd.to_datetime(new_df['Timestamp'])

                # Concatenate with existing DataFrame
                if not new_df.empty:
                    # If self.data_df is empty and has no columns, concat might behave unexpectedly.
                    # Initialize self.data_df with columns if it's truly always the same structure.
                    # For now, direct concat and then set index.
                    self.data_df = pd.concat([self.data_df, new_df], ignore_index=True)
                    
                self.data_accumulator.clear()

            # Process the combined DataFrame (setting index, sorting, ffill) once after accumulation
            if not self.data_df.empty and 'Timestamp' in self.data_df.columns and 'Name' in self.data_df.columns:
                # Drop rows where essential identifiers like Timestamp or Name might be missing before setting index
                self.data_df.dropna(subset=['Timestamp', 'Name'], inplace=True)
                if not self.data_df.empty: # Check again after dropna
                    self.data_df.set_index(['Timestamp', 'Name'], inplace=True, drop=False) # keep Timestamp, Name as columns
                    self.data_df.sort_index(inplace=True)
                    # Forward fill, but be careful with groupby if channels should not cross-fill
                    # For simplicity, global ffill. If per-Name/Channel ffill is needed, it's more complex.
                    self.data_df = self.data_df.ffill() # Was: .fillna(method='ffill')
                else: # If after dropna it's empty
                    self.data_df = pd.DataFrame() # Reset to empty DF with no index
            elif self.data_df.empty : # if it started empty and nothing was added
                 self.data_df = pd.DataFrame() # Ensure it's a clean empty DF

    async def periodically_update_dataframe(self, interval=5):
        try:
            while app_state.is_running(): # Controlled by app_state for current batch
                await asyncio.sleep(interval)
                if not app_state.is_running(): break # Check again after sleep
                await self.update_dataframe()
        except asyncio.CancelledError:
            print("Periodic dataframe update cancelled.")
            # Final update before exiting if cancelled
            await self.update_dataframe()
            raise
        finally:
            print("Periodic dataframe update finished.")

    async def save_data(self, batch_num=None):
        await self.update_dataframe()  # Ensure the DataFrame is up to date
        
        if self.data_df.empty:
            print("No data to save.")
            return

        current_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
        
        filename_parts = ["data", current_time_str]
        if batch_num is not None:
            filename_parts.append(f"batch_{batch_num}")
        
        file_path = os.path.join(data_dir, f"{'_'.join(filename_parts)}.csv")
        
        try:
            # If index was set with drop=False, it might be duplicated in CSV.
            # Decide if index should be written. If 'Timestamp' and 'Name' are columns, don't write index.
            if 'Timestamp' in self.data_df.columns and 'Name' in self.data_df.columns:
                 self.data_df.to_csv(file_path, index=False)
            else: # If Timestamp and Name are only in index
                 self.data_df.to_csv(file_path, index=True)
            print(f"Data successfully saved to {file_path}.")
        except Exception as e:
            print(f"Error saving data: {e}")