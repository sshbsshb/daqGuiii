import dearpygui.dearpygui as dpg
import asyncio
import threading
import time

def dpg_thread_function():
    dpg.create_context()
    with dpg.window(label="Example Window"):
        dpg.add_text("This is a test")
        dpg.add_button(label="Click Me")
    dpg.create_viewport(title='Custom Title', width=600, height=200)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()  # This will now block until the GUI is closed
    dpg.destroy_context()

async def async_function():
    while True:
        print("Async function is running...")
        await asyncio.sleep(1)

def main():
    # Start DPG in its own thread
    dpg_thread = threading.Thread(target=dpg_thread_function)
    dpg_thread.start()

    # Run asyncio loop in the main thread
    # loop = asyncio.get_event_loop()
    # try:
    #     asyncio.ensure_future(async_function())
    #     loop.run_forever()
    # except KeyboardInterrupt:
    #     pass
    # finally:
    #     loop.close()

    # Wait for the DPG thread to finish
    dpg_thread.join()

if __name__ == "__main__":
    main()
