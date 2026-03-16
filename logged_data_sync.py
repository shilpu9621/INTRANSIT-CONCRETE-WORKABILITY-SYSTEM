import os
import json
import time
from datetime import datetime
from logging_data import log
from tb_device_mqtt import TBDeviceMqttClient, TBPublishInfo
import socket


file_path = "/home/UbiqCM4/access_token.json"
access_token = ""

logging = log(
    unpub="/home/UbiqCM4/mqtt_data/datalogs",  # file to save unpublished data into json
    back_up="/home/UbiqCM4/mqtt_data/All_datalogs",  # file to save all data into CSV format
)

unpub_file = logging.unpub_data()  # this creates the directory for unpublished file
back_up = logging.backup_data()  # this creates the directory for all the data

file_path="/home/UbiqCM4/access_token.json"
access_token = " "

try:
    with open(file_path, 'r') as file:
        data = json.load(file)
        access_token = data['token']
        print(f"Access token read successfully : {access_token}")
except FileNotFoundError:
    print(f"JSON file not found: {file_path}")
except KeyError:
    print("Token key not found in the JSON file.")
except json.JSONDecodeError:
    print("Invalid JSON format in the file.")

#client = TBDeviceMqttClient("", username=access_token)
client = TBDeviceMqttClient("thingsboard.cloud", port=1883, username=access_token)

def connect_client():
    """
    Attempts to connect to the MQTT broker.
    Prints a success message if connected, or an error message if connection fails.
    """
    try:
        client.connect()
        print("Connected to MQTT broker")
        time.sleep(5)
    except Exception as e:
        print("Connection error:", e)

def Publish_data(telemetry):
    """
    Attempts to publish telemetry data to the MQTT broker.
    If successful, returns True. If failed, saves data locally and returns False.
    """
    try:
        if not client.is_connected():
            connect_client()
        client.send_telemetry(telemetry)
        return True
    except Exception as e:
        print("Publishing error:", e)
        logging.save_data_locally(telemetry, unpub_file)
        client.disconnect()
        return False
 

def get_sorted_json_files(root_directory):
    """
    Recursively searches for JSON files in the given root directory and its subdirectories.
    Returns a sorted list of full file paths.
    """
    json_files = []
    for year in sorted(os.listdir(root_directory)):
        year_path = os.path.join(root_directory, year)
        if not os.path.isdir(year_path):
            continue
        for month in sorted(os.listdir(year_path)):
            month_path = os.path.join(year_path, month)
            if not os.path.isdir(month_path):
                continue
            for day in sorted(os.listdir(month_path)):
                day_path = os.path.join(month_path, day)
                if not os.path.isdir(day_path):
                    continue
                for file in sorted(os.listdir(day_path)):
                    if file.endswith('.json'):
                        full_path = os.path.join(day_path, file)
                        json_files.append(full_path)
    return json_files

def read_json_file(file_path):
    """
    Reads and returns the contents of a JSON file.
    Returns None if the file is empty or invalid.
    """
    try:
        with open(file_path, 'r') as fh:
            content = fh.read().strip()
            if not content:  # Check if file is empty
                print(f"Warning: Empty file encountered: {file_path}")
                return None
            return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in file {file_path}: {str(e)}")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None

def save_last_processed_file(file_path):
    """
    Saves the path of the last processed file to a text file.
    """
    with open("/home/UbiqCM4/last_processed_file.txt", "w") as f:
        f.write(file_path)

def get_last_processed_file():
    """
    Retrieves the path of the last processed file from a text file.
    """
    try:
        with open("/home/UbiqCM4/last_processed_file.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def process_data(root_directory):
    """
    Continuously processes JSON files in the given root directory.
    Reads data from files, publishes it to MQTT, and keeps track of the last processed file.
    Skips empty or invalid JSON files.
    """
    last_processed_file = get_last_processed_file()
    while True:
        json_files = get_sorted_json_files(root_directory)

        if not json_files:
            print("No files to process. Waiting...")
            time.sleep(10)
            continue

        if last_processed_file:
            try:
                start_index = json_files.index(last_processed_file) + 1
            except ValueError:
                start_index = 0
        else:
            start_index = 0

        new_files_processed = False
        for current_file in json_files[start_index:]:
            data = read_json_file(current_file)
            
            if data is None:  # Skip empty or invalid files
                print(f"Skipping file {current_file} and moving to next...")
                last_processed_file = current_file
                save_last_processed_file(last_processed_file)
                continue

            # Handle both single data point and list of data points
            if isinstance(data, list):
                telemetry_list = data
            else:
                telemetry_list = [data]

            for telemetry in telemetry_list:
                if Publish_data(telemetry):
                    print(f"Successfully published data from file {current_file}")
                    last_processed_file = current_file
                    save_last_processed_file(last_processed_file)
                    new_files_processed = True
                else:
                    print(f"Failed to publish data from file {current_file}")
                    time.sleep(5)  # Wait before retrying
                    break  # Exit the loop to retry this file in the next iteration

                time.sleep(2)  # Wait for 0.1 seconds before sending the next data point

        if not new_files_processed:
            print("No new files to process. Waiting for new data...")
            time.sleep(10)  # Wait for 1 minute before checking for new files

def main():
    """
    The main function that initializes the MQTT client connection and starts the data processing loop.
    """
    root_directory = "/home/UbiqCM4/mqtt_data/datalogs"
    connect_client()
    process_data(root_directory)

if __name__ == "__main__":
    main()
