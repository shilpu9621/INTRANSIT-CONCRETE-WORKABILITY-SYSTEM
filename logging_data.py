import os
from datetime import datetime
import json
import csv
import logging

##added from bin files
logging.basicConfig(
    level=logging.INFO,
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class log:
    """
    A class for handling logging operations including data storage, backup, and tracking of published/unpublished data.
    """
    
    def __init__(self, unpub=None, back_up=None, failed_unpub_count_file=None, success_pub_count_file=None):
        """
        Initialize the log class with specified directory paths.
        """
        self.missed_data = unpub
        self.all_data = back_up
        self.Fpub_count = failed_unpub_count_file
        self.Spub_count = success_pub_count_file
        
        # Create directories only if they are specified
        if self.missed_data:
            os.makedirs(self.missed_data, exist_ok=True)
        if self.all_data:
            os.makedirs(self.all_data, exist_ok=True)


    def unpub_data(self):
        """
        Create a hierarchical directory structure for unpublished data based on current date.
        """
        current_datetime = datetime.now()
        year_folder = os.path.join(self.missed_data, current_datetime.strftime('%Y'))
        month_folder = os.path.join(year_folder, current_datetime.strftime('%m-%B'))
        day_folder = os.path.join(month_folder, current_datetime.strftime('%d'))
        os.makedirs(day_folder, exist_ok=True)
        return day_folder
    
        
    def backup_data(self):
        """
        Create a hierarchical directory structure for backup data based on current date.
        """
        current_datetime = datetime.now()
        year_folder = os.path.join(self.all_data, current_datetime.strftime('%Y'))
        month_folder = os.path.join(year_folder, current_datetime.strftime('%m-%B'))
        day_folder = os.path.join(month_folder, current_datetime.strftime('%d'))
        os.makedirs(day_folder, exist_ok=True)
        return day_folder    
    
    def save_data_locally(self, data, folder_path):
        """
        Save data to a JSON file in the specified folder with timestamp-based filename.
        """
        os.makedirs(folder_path, exist_ok=True)
        timestamp = datetime.now().strftime('%H-%M-%S')
        filename = os.path.join(folder_path, f"{timestamp}.json")
        with open(filename, 'w') as file:
            json.dump(data, file)
            logging.info("Saved the Unpublished data")
            
        
    def read_unpub_count(self, folderpath):
        """
        Read the unpublished count from a file.
        """
        try:
            if os.path.exists(folderpath):
                with open(folderpath, "r") as file:
                    return int(file.read().strip())
        except PermissionError:
            logging.error(f"Permission denied: '{folderpath}'. Ensure the file is not open elsewhere and you have read permissions.")
        return 0
    

    def write_unpub_count(self, count, folderpath):
        """
        Write the unpublished count to a file.
        """
        try:
            with open(folderpath, "w") as file:
                file.write(str(count))
        except PermissionError:
            logging.error(f"Permission denied: '{folderpath}'. Ensure the file is not open elsewhere and you have write permissions.")
            

    def save_data_locally_csv(self, data, folder_path):
        """
        Save data to a CSV file with date-based filename with dynamic columns, ensuring timestamp is first.
        """
        try:
            os.makedirs(folder_path, exist_ok=True)
            today_date = datetime.now().strftime('%Y-%m-%d')
            csv_filename = os.path.join(folder_path, f"{today_date}.csv")
            file_exists = os.path.isfile(csv_filename)

            # Get the current data fields
            current_data = {"timestamp": data["ts"]}
            if "values" in data:
                current_data.update(data["values"])
            else:
                current_data.update(data)

            # Read existing headers and data if file exists
            existing_headers = ["timestamp"]
            existing_data = []
            if file_exists:
                with open(csv_filename, 'r') as file:
                    reader = csv.reader(file)
                    existing_headers = next(reader)
                    # Store existing data
                    existing_data = [row for row in reader]

            # Create new complete set of headers
            all_headers = set(existing_headers) | set(current_data.keys())
            # Ensure timestamp is first, followed by sorted other headers
            final_headers = ["timestamp"] + sorted([h for h in all_headers if h != "timestamp"])

            # Write all data with updated headers
            with open(csv_filename, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=final_headers)
                writer.writeheader()
                
                # Write existing data
                for row in existing_data:
                    row_dict = dict(zip(existing_headers, row))
                    writer.writerow(row_dict)
                
                # Write new data
                writer.writerow(current_data)

            logging.info(f"Saved data to {csv_filename}")
        except Exception as e:
            logging.error(f"An error occurred while saving data: {e}")
            logging.error(f"Error details: {str(e)}")
            

    def read_unpublished_data(self, directory):
        """
        Read content from all files in the specified directory.
        """
        for dirpath, dirnames, filenames in os.walk(directory):
            for file in filenames:
                file_path = os.path.join(dirpath, file)
                with open(file_path, "r") as fh:
                    content = fh.read()
                    return content
                

    def get_directory_size(self, directory):
        """
        Calculate the total size of all files in a directory and its subdirectories.
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for file in filenames:
                file_path = os.path.join(dirpath, file)
                total_size += os.path.getsize(file_path)
        return total_size
    

    def fetch_size(self, file1, file2):
        """
        Calculate the combined size of two directories.
        """
        filesize1 = self.get_directory_size(file1)
        filesize2 = self.get_directory_size(file2)
        file_size = filesize1 + filesize2
        return file_size

