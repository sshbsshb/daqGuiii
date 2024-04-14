import yaml
import asyncio
from application_runner import ApplicationRunner

def load_config(filename):
    """Load configuration from a YAML file."""
    with open(filename, 'r') as file:
        return yaml.safe_load(file)

async def main():
    # Load configuration
    config = load_config('config.yaml')

    # Create and run the application
    app_runner = ApplicationRunner(config)
    await app_runner.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Caught keyboard interrupt. Exiting...")
    except Exception as e:
        print(f"Unexpected error: {e}")