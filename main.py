# In main.py
import yaml
import asyncio
from application_runner import ApplicationRunner
from state import app_state # Assuming app_state is still used for global state

def load_config(filename):
    """Load configuration from a YAML file."""
    with open(filename, 'r') as file:
        return yaml.safe_load(file)

async def main_coroutine(loop_instance): # Renamed and accepts the loop instance
    # Load configuration
    config = load_config('config.yaml')

    # Setup batch parameters in app_state
    batch_config = config.get('batch_settings', {})
    app_state.batch_total_runs = batch_config.get('batch_repetitions', 1)
    if app_state.batch_total_runs > 1:
        app_state.batch_mode_active = True
        app_state.auto_start_next_batch = batch_config.get('auto_start_next_batch', False)
        app_state.auto_start_delay_s = batch_config.get('auto_start_delay_seconds', 5)

    # Create and run the application, passing the loop
    app_runner = ApplicationRunner(config, loop_instance)
    await app_runner.run()

if __name__ == "__main__":
    active_loop = None
    try:
        # Get an event loop
        try:
            active_loop = asyncio.get_running_loop()
        except RuntimeError: # No running loop
            active_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(active_loop)

        active_loop.run_until_complete(main_coroutine(active_loop))
    except KeyboardInterrupt:
        print("Caught keyboard interrupt. Exiting...")
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            print(f"Main loop error: {e}. The event loop was closed unexpectedly.")
        else:
            print(f"Unexpected runtime error in main: {e}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"Unexpected error in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if active_loop and not active_loop.is_closed():
            print("Main: Cleaning up tasks and closing event loop...")
            # Gather all remaining tasks (except the current one, if any)
            tasks = [t for t in asyncio.all_tasks(loop=active_loop) if t is not asyncio.current_task(loop=active_loop)]
            if tasks:
                print(f"Main: Cancelling {len(tasks)} outstanding tasks...")
                for task in tasks:
                    task.cancel()
                # Give tasks a chance to process cancellation
                try:
                    # This gather should run on the loop if it's still running,
                    # but if run_until_complete exited, the loop might be stopping.
                    active_loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                    print("Main: Outstanding tasks processed.")
                except RuntimeError as e_gather: # Handle if loop is already stopping/closed
                     print(f"Main: Error during gather in finally: {e_gather}")
                     # If loop is closed, tasks might not have cleaned up via gather
                     for task in tasks: # Check their state
                         if not task.done() and not task.cancelled():
                             print(f"Main: Task {task.get_name()} did not complete cancellation.")

            active_loop.close()
            print("Main: Event loop closed.")
        elif active_loop and active_loop.is_closed():
            print("Main: Event loop was already closed.")
        else:
            print("Main: No active event loop found in finally block.")