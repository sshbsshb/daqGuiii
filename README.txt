A new generation of DAQ/PSU control system with GUI cating for automatic testing
Features:
    - Flexible loading equipment module from config.yaml
    - Support VISA and Modbus(in progress) communication protocols, fairly easy to add your own equipment driver.
    - New GUI using Dear PyGUI
    - Using asynio to manage all the equipment connection and communication
    - Support constant interval schedule and pre-defined schedule in csv file for equipment control
    - Overall runtime limit to provide some safety measures
