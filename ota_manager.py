from paho.mqtt.client import Client
from time import sleep
from json import dumps, loads
from threading import Thread
import requests
import os
from helper import *
from zipfile import ZipFile
import subprocess
import logging
from logging.handlers import TimedRotatingFileHandler
OTA_ENABLED = False

#version v1.0.0

def setup_logger():
    """
    Set up a logger with both console and time-based rotating file output.
    """
    # Ensure log directory exists
    log_dir = "/home/UbiqCM4/software_update"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "debug.log")

    logger = logging.getLogger("OTA")
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s',
                                          datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(console_formatter)

    file_handler = TimedRotatingFileHandler(
        log_path,
        when="midnight",  # Rotate logs at midnight
        interval=1,       # Rotate every 1 day
        backupCount=30     # Keep 7 days of logs
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Initialize logger
logger = setup_logger()


helpin = HELPER(None)

SW_TITLE_ATTR = "sw_title"
SW_VERSION_ATTR = "sw_version"
SW_STATE_ATTR = "sw_state"
SW_SIZE_ATTR = "sw_size"

new_version=None
new_title=None

services = {
        "main.service",
        "logged_data_sync.service",
        "handle_4G.service",
        "system_control.service",
    }

file_path = "/home/UbiqCM4/access_token.json"
access_token = ""

try:
    with open(file_path, 'r') as file:
        data = json.load(file)
        access_token = data['token']
        logger.info(f"Access token read successfully : {access_token}")
except FileNotFoundError:
    logger.error(f"JSON file not found: {file_path}")
except KeyError:
    logger.error("Token key not found in the JSON file.")
except json.JSONDecodeError:
    logger.error("Invalid JSON format in the file.")

REQUIRED_SHARED_KEYS = f"{SW_TITLE_ATTR},{SW_VERSION_ATTR},{SW_SIZE_ATTR}"

def collect_required_data():
    logger.info(f"Connecting to the Host")
    config = {}
    host = "thingsboard.cloud"
    config["host"] = host if host else "localhost"
    host = ''
    config["port"] = port if port else 1883
    token = ""
    while not token:
        token = access_token
    config["token"] = token
    print("\n", "="*80, "\n", sep="")
    return config


def fetch_bearer_token(base_url, username, password):
    url = f"{base_url}/api/auth/login"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "username": username,
        "password": password
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("token")
    else:
        raise Exception(f"Failed to fetch token: {response.status_code}, {response.text}")

def fetch_ota_packages(base_url, token, page_size=10, page=0):
    url = f"{base_url}/api/otaPackages?pageSize={page_size}&page={page}"
    headers = {
        "X-Authorization": f"Bearer {token}",
        'accept':'application/json'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def fetch_specific_package(new_title, new_version):
    try:
        # Fetch OTA Packages
        logger.info(f"Fetching OTA package for software title: {new_title}")
        logger.info(f"Searching for software version: {new_version}")
        
        # Fetch OTA packages
        ota_packages = fetch_ota_packages(BASE_URL, TOKEN)
        
        if ota_packages.get('data'):
            # Find package with matching title and version
            for pkg in ota_packages['data']:
                # Check if package title matches
                if (pkg.get('title') == new_title and pkg.get('version', '') == new_version):
                    required_id = pkg['id']['id']
                    return required_id
                    
            logger.error(f"No software found with title: {new_title} and version: {new_version}")
            return None
        
        else:
            logger.error("No software found.")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error:,{str(e)}")
        return None
    
def download_ota_package(package_id):
    """
    Download an OTA package using the specific download endpoint
    """
    try:
        # Prepare headers with token
        headers = {
            'X-Authorization': f'Bearer {TOKEN}',
            'accept': 'application/json'
        }

        download_url = f"{BASE_URL}/api/otaPackage/{package_id}/download"
        response = requests.get(download_url, headers=headers, stream=True)
        response.raise_for_status()
        filename = response.headers.get('x-filename', f'{package_id}.zip')
        os.makedirs(PATH, exist_ok=True)
        full_path = os.path.join(PATH, filename)

        with open(full_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        logger.info(f"Software downloaded successfully to {full_path}")
        return filename

    except requests.RequestException as e:
        logger.error(f"Error downloading software: {str(e)}")
        logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
        return None
    
def control_services(control_command,service):
    """
    The function in which based on control command restart or stop the service
    """
    cmd = f"sudo systemctl {control_command} {service}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    sleep(1)
    
def copy_to_dest(file, updated_filename):
    source = f"{PATH}/{updated_filename}/{file}"
    dest = f"{PATH}/{file}"
    cmd = f"sudo cp {source} {dest}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
      
def extract_files(filename):
    """
    Extract files to a specific directory without version number
    """
    # Get base name without extension
    base_name = filename.split('.')[0]
    
    # Create target directory if it doesn't exist
    if not os.path.exists(base_name):
        os.makedirs(base_name)
    
    with ZipFile(filename, 'r') as zip_file:
        for zip_info in zip_file.infolist():
            if zip_info.is_dir():
                continue
            zip_info.filename = os.path.basename(zip_info.filename)
            zip_file.extract(zip_info, base_name)
    
    for service in services:
        control_services('stop', service)
    sleep(1)
    
    for file in os.listdir(base_name):
        if os.path.isfile(os.path.join(base_name, file)):
            copy_to_dest(file, base_name)
       
    logger.info("Updating...................")  
                
    for service in services:
        control_services('restart', service)
    sleep(1)          

def dummy_upgrade(version_from, version_to):
    logger.info(f"Updating from {version_from} to {version_to}:")
    sleep(5)
    logger.info(f"Software is updated!")
    logger.info(f"Current software version is: {version_to}")
    helpin.sw_version(version_to)

class softwareClient(Client):
    def __init__(self):
        super().__init__()
        self.on_connect = self.__on_connect
        self.on_message = self.__on_message

        self.__request_id = 0
        self.__software_request_id = 0

        self.current_software_info = {
            "current_" + SW_TITLE_ATTR: "UB_JTEDS",
            "current_" + SW_VERSION_ATTR: "0"
        }
        self.software_data = b''
        self.software_received = False
        self.__updating_thread = Thread(target=self.__update_thread, name="Updating thread")
        self.__updating_thread.daemon = True
        self.__updating_thread.start()

    def __on_connect(self, client, userdata, flags, result_code, *extra_params):
        logger.info(f"Requesting software info from {config['host']}:{config['port']}..")
        self.subscribe("v1/devices/me/attributes/response/+")
        self.subscribe("v1/devices/me/attributes")
        self.subscribe("v2/sw/response/+")
        self.send_telemetry(self.current_software_info)
        self.request_software_info()

    def __on_message(self, client, userdata, msg):
        global new_title,new_version

        if msg.topic.startswith("v1/devices/me/attributes"):
            self.software_info = loads(msg.payload)

            if "/response/" in msg.topic:
                self.software_info = self.software_info.get("shared", {}) if isinstance(self.software_info, dict) else {}
            if (self.software_info.get(SW_VERSION_ATTR) is not None and self.software_info.get(SW_VERSION_ATTR) != self.current_software_info.get("current_" + SW_VERSION_ATTR)) or \
                    (self.software_info.get(SW_TITLE_ATTR) is not None and self.software_info.get(SW_TITLE_ATTR) != self.current_software_info.get("current_" + SW_TITLE_ATTR)):
                logger.info(f"Software is not the same, new version found")

                # Pass the current software title when fetching the latest package
                new_title = self.software_info.get('sw_title')
                new_version = self.software_info.get('sw_version')
                
                self.current_software_info[SW_STATE_ATTR] = "INITIATED"
                self.send_telemetry(self.current_software_info)
                self.process_software()

    def process_software(self):
        self.current_software_info[SW_STATE_ATTR] = "DOWNLOADING"
        self.send_telemetry(self.current_software_info)
        sleep(1)
        self.software_received = True

    def send_telemetry(self, telemetry):
        return self.publish("v1/devices/me/telemetry", dumps(telemetry), qos=1)

    def request_software_info(self):
        self.__request_id = self.__request_id + 1
        self.publish(f"v1/devices/me/attributes/request/{self.__request_id}", dumps({"sharedKeys": REQUIRED_SHARED_KEYS}))

    def __update_thread(self):
        while True:
            if self.software_received:
                Event = helpin.read_event()
                if Event == "IDLE":
                    
                    logger.info(f"Event is {Event}, Downloading the Software")
                    required_id=fetch_specific_package(new_title,new_version)
                    Update_file=download_ota_package(required_id)
                    
                    self.current_software_info[SW_STATE_ATTR] = "DOWNLOADED"
                    self.send_telemetry(self.current_software_info)
                    sleep(1)
                    
                    extract_files(Update_file)
                    
                    self.current_software_info[SW_STATE_ATTR] = "UPDATING"
                    self.send_telemetry(self.current_software_info)
                    sleep(1)

                    dummy_upgrade(self.current_software_info["current_" + SW_VERSION_ATTR], self.software_info.get(SW_VERSION_ATTR))

                    self.current_software_info = {
                        "current_" + SW_TITLE_ATTR: self.software_info.get(SW_TITLE_ATTR),
                        "current_" + SW_VERSION_ATTR: self.software_info.get(SW_VERSION_ATTR),
                        SW_STATE_ATTR: "UPDATED"
                    }
                    self.send_telemetry(self.current_software_info)
                    self.software_received = False
                    sleep(1)

if __name__ == '__main__':
    config = collect_required_data()
    #BASE_URL = "https://samasth.io:443"
    BASE_URL = "http://10.104.173.233"

    PATH = "/home/UbiqCM4"
    TOKEN = fetch_bearer_token(BASE_URL,"","")
    client = softwareClient()
    client.username_pw_set(config["token"])
    client.connect(config["host"], config["port"])
    client.loop_forever()
