# INTRANSIT CONCRETE WORKABILITY SYSTEM

This project is an IoT-based In-Transit Concrete Workability Monitoring System developed using Python and embedded hardware.

## Features
- Sensor data monitoring
- Flow meter calculation
- 4G communication
- Data logging
- OTA update support
- SIM communication
- UPS monitoring

## Modules
- main.py – Main control
- sensor.py – Sensor module
- handle_4G.py – 4G communication
- logging_data.py – Logging
- helper.py – Helper functions
- ota_manager.py – OTA update
- system_control.py – System control
- ups.py – Power monitoring
- sim76xx.py – SIM module

## Description
This system monitors concrete workability in transit mixer using IoT sensors and 4G communication.  
It reads sensor data, calculates flow, logs trip data, and sends information using 4G module.
