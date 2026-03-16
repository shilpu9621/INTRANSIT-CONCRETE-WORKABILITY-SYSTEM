import logging
from logging.handlers import TimedRotatingFileHandler
import os
from tb_device_mqtt import TBDeviceMqttClient, TBPublishInfo
import subprocess
import json
from logging_data import log
import time
from timeloop import Timeloop
from datetime import timedelta
import requests
from ups import *

log_the_data=log(
            unpub="/home/UbiqCM4/mqtt_data/datalogs",       #file to save unpublished data into json
            back_up="/home/UbiqCM4/mqtt_data/All_datalogs", #file to save all data into CSV format
            )

unpub_file = log_the_data.unpub_data() #this creates the directory for unpublished file
back_up = log_the_data.backup_data()   #this creates the directory for all the data

logger = logging.getLogger('system')
logger.setLevel(logging.DEBUG)
log_file = os.path.join("/home/UbiqCM4/system_logs", 'debug.log')

timed_handler = TimedRotatingFileHandler(
    log_file,    # Separate file for time-based rotation
    when='midnight',        # Rotate at midnight
    interval=1,            # Rotate every day
    backupCount=15         # Keep 15 backup files
)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
timed_handler.setFormatter(formatter)
timed_handler.setLevel(logging.DEBUG)

logger.addHandler(timed_handler)
logger.info(f'Logger initialized. Log files: {log_file}')
link = ""

# File path for access token
file_path = "/home/UbiqCM4/access_token.json"
access_token = ""
try:
    with open(file_path, 'r') as file:
        data = json.load(file)
        access_token = data['token']
except FileNotFoundError:
    logger.info(f"JSON file not found: {file_path}")
except KeyError:
    logger.info("Token key not found in the JSON file.")
except json.JSONDecodeError:
    logger.info("Invalid JSON format in the file.")


try:
#    client = TBDeviceMqttClient("samasth.io",username=access_token) #access token to be added
    client = TBDeviceMqttClient(
    "thingsboard.cloud",
    port=1883,
    username=access_token)

    client.connect()
except Exception as e:
    logger.error(f"connection error,{e}")

def on_attributes_change(result, exception):
    """Handle attribute updates."""
    if exception is not None:
        logger.error("Exception:", str(exception))
    else:
       update_attributes(result)

def on_attributes_request_response(result, exception):
    """Handle initial attribute request."""
    if exception is not None:
        logger.error("Exception:", str(exception))
    else:
        update_attributes(result)

def update_attributes(update):
    global link
    try:
        if "string" in update:
            link = update["string"]
        
        command = f"{link}"
        logger.info(f"Executing Command {link}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if link == "sudo nohup apt -y purge remoteit":
            if result.returncode == 0:
                logger.info("Remote.it agent uninstalled successfully.")
                telemetry_with_ts={"ts": int(round(time.time() * 1000)),"values":{ "Last_remote_cmd":1}}
                Publish(telemetry_with_ts)
            else:
                logger.error(f"Failed to uninstall Remote.it agent. Error: {result.stderr}")
                subprocess.run("sudo dpkg --configure -a", shell=True, capture_output=True, text=True)
                telemetry_with_ts={"ts": int(round(time.time() * 1000)),"values":{ "Last_remote_cmd":-1}}
                Publish(telemetry_with_ts)
        
        elif link == "sudo systemctl stop main":
            if result.returncode == 0:
                logger.info("Main service was stopped")
            else:
                logger.error(f"Failed to stop main: {result.stderr}")
                
        elif link == "sudo systemctl restart main":
            if result.returncode == 0:
                logger.info("Main service was started")
            else:
                logger.error(f"Failed to start main: {result.stderr}")

        elif link.startswith("R3_REGISTRATION_CODE"):
            if result.returncode == 0:
                logger.info("Remote.it agent installed successfully.")
                telemetry_with_ts={"ts": int(round(time.time() * 1000)),"values":{ "Last_remote_cmd":11}}
                Publish(telemetry_with_ts)
            else:
                logger.error(f"Failed to install Remote.it agent. Error: {result.stderr}")
                subprocess.run("sudo dpkg --configure -a", shell=True, capture_output=True, text=True)
                telemetry_with_ts={"ts": int(round(time.time() * 1000)),"values":{ "Last_remote_cmd":-11}}
                Publish(telemetry_with_ts)        
                      
    except Exception as e:
        logging.error("Connection timeout error: %s", str(e))
        subprocess.run("sudo dpkg --configure -a", shell=True, capture_output=True, text=True)
        subprocess.run("sudo nohup apt -y purge remoteit", shell=True, capture_output=True, text=True)
        subprocess.run("")
        telemetry_with_ts={"ts": int(round(time.time() * 1000)),"values":{ "Last_remote_cmd":-111}}
        Publish(telemetry_with_ts)

def connect_and_setup_client():

    try:
        if client.is_connected():
            client.disconnect()

        client.connect()
        logger.info("Connected to MQTT broker")

        client.subscribe_to_all_attributes(on_attributes_change)

        client.request_attributes(shared_keys=["string"], callback=on_attributes_request_response)

    except Exception as e:
        logger.error(f"Connection and setup error: {e}")

connect_and_setup_client()

def Publish(telemetry_with_ts):
    try:
        client.connect()
        client.send_telemetry(telemetry_with_ts)
        
    except Exception as e:
        logging.error("Connection timeout error: %s", str(e))
        log_the_data.save_data_locally(telemetry_with_ts,unpub_file)
        client.disconnect()
        
#INA_FLAG=True
#t1 = Timeloop()

#try:
 #   ina219 = INA219(i2c_bus=10, addr=0x43)
  #  logger.info("INA219 initialization successful")
   # INA_FLAG = True
#except Exception as e:
   # logger.error(f"Failed to initialize INA219: {str(e)}")
    #INA_FLAG = False

def UPS_init():
    """
    This function initializes and check UPS working or not
    """
    #from ups import INA219
 #   global INA_FLAG,ina219
  #  try:
   #     ina219 = INA219(i2c_bus=10, addr=0x43)
    #    logger.info("INA219 initialization successful")
     #   INA_FLAG = True
    #except Exception as e:
     #   logger.error(f"Failed to initialize INA219: {str(e)}")
      #  INA_FLAG = False

@t1.job(interval=timedelta(seconds=90))
def ups():
    try:
        global INA_FLAG
        if INA_FLAG:
            bus_voltage = ina219.getBusVoltage_V()             # voltage on V- (load side)
            shunt_voltage = ina219.getShuntVoltage_mV() / 1000 # voltage between V+ and V- across the shunt
            current = ina219.getCurrent_mA() / 1000            # current in A
            power = ina219.getPower_W()                        # power in W
            p = (bus_voltage - 3)/1.2*100
            if p > 100: p = 100
            if p < 0: p = 0
            
            logger.info(f"Load Voltage: {bus_voltage:.3f} V, Current: {current:.3f} A, Power: {power:.3f} W, Percent: {p:.1f}%")
            
            telemetry_with_ts={"ts": int(round(time.time() * 1000)),"values":{ "Load_Voltage":f"{bus_voltage:.3f}", "Current":f"{current:.3f}","Power":f"{power:.3f}","Percent": f"{p:.1f}"}}

            Publish(telemetry_with_ts)
        else:
            telemetry_with_ts={"ts": int(round(time.time() * 1000)),"values":{ "Power":-999}}
            Publish(telemetry_with_ts)
            UPS_init()

    except Exception as e:
        logger.error(f"An error occurred: {e}")  
        telemetry_with_ts={"ts": int(round(time.time() * 1000)),"values":{ "Power":-999}}
        Publish(telemetry_with_ts)
        UPS_init()
        
t1.start(block=False)      


def get_service_status(service_name="main"):
    """
    Retrieve the current status of a systemd service.
    """
    try:
        result = subprocess.run(["systemctl", "is-active", service_name],
                              capture_output=True,
                              text=True)
        status = result.stdout.strip()
        return status
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        return "unknown"

service_current_state = " "
Prev_current_state = " "
PowerState = False

while True:
    try:
        unpub_file = log_the_data.unpub_data()
        back_up = log_the_data.backup_data()

        time.sleep(2)
        service_current_state = get_service_status()

        if service_current_state != Prev_current_state:
            Prev_current_state = service_current_state
            telemetry_with_ts = {"ts": int(round(time.time() * 1000)), "values": {"Service_Status": service_current_state}}
            time.sleep(2)
            Publish(telemetry_with_ts)

        if PowerState != True:
            PowerState = True
            telemetry_with_ts = {"ts": int(round(time.time() * 1000)), "values": {"Power_Status": PowerState}}
            time.sleep(2)
            logger.info("Device is in ON Mode")
            Publish(telemetry_with_ts)

    except Exception as e:
        logger.info(f"exception : {str(e)}")
        client.disconnect()
        break

    
