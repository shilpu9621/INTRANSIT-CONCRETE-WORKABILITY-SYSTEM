import json
import os


class HELPER:
    def __init__(self, flow_meter_device=None):
        """
        Initialize Helper
        """
        self.flow_meter_device = flow_meter_device
        self.flow_meter_total = None
        self.PULSE_LIMIT = 65000
        self.FLOW_METER_REGISTER = 2529

    def pulse_to_litre(self, flow_count, flow_pulse_ref, flow_factor_ref):
        """
        Convert flowcount to litres with reference to 100 pulses as half litres
        """
        return (flow_count / flow_pulse_ref) * flow_factor_ref

    def reset_flowcount(self):
        """
        Reset flowcount when it exceeds the pulse limit of 65000
        """
        if self.flow_meter_total is not None:
            current_flow_count = self.flow_meter_total[2]
            if current_flow_count > self.PULSE_LIMIT:
                if self.flow_meter_device:
                    self.flow_meter_device.write_holding_registers(self.FLOW_METER_REGISTER, 0, 1)
                else:
                    raise ValueError("Flow meter device not initialized")

    def get_total_flow(self):
        """
        Fetch total flowcount pulses during every trip
        """
        try:
            with open('flow_meter_total.json', 'r') as file:
                data = json.load(file)
            return float(data['Total_Flow'])
        except (FileNotFoundError, KeyError) as e:
            raise Exception(f"Error reading total flow: {str(e)}")
        
    def write_total_distance(self,total_distance):
        """
        Total Distance travelled since code updated
        """
        json_file = "total_distance.json"
        try:
            with open(json_file, 'w') as file:
                json.dump({
                    'Total_distance': total_distance
                }, file)
        except Exception as e:
            raise Exception(f"Error writing total trip: {str(e)}")        

    def read_distance(self):
        try:
            with open('total_distance.json', 'r') as file:
                data = json.load(file)
                return float(data['Total_distance'])
        except (FileNotFoundError, KeyError) as e:
            raise Exception(f"Error reading total trip: {str(e)}")  
        

    def write_total_flow(self, pulse,flow_pulse,flow_factor):
        """
        Write total pulse and convert litres into json files
        """
        json_file = 'flow_meter_total.json'
        total_pulse = pulse
        total_flow = self.pulse_to_litre(pulse,flow_pulse,flow_factor)

        try:
            if os.path.exists(json_file):
                with open(json_file, 'r') as file:
                    data = json.load(file)
                    total_pulse += data.get('total_pulse', 0)
                    total_flow += data.get('Total_Flow', 0)

            with open(json_file, 'w') as file:
                json.dump({
                    'total_pulse': total_pulse,
                    'Total_Flow': total_flow
                }, file)
        except Exception as e:
            raise Exception(f"Error writing total flow: {str(e)}")

    def get_total_trip(self):
        """
        Fetch total trip from json file
        """
        try:
            with open('total_trip.json', 'r') as file:
                data = json.load(file)
            return float(data['Total_trip'])
        except (FileNotFoundError, KeyError) as e:
            raise Exception(f"Error reading total trip: {str(e)}")
        
    def write_event(self,event):
        json_file = 'event_update.json'
        try:
            if os.path.exists(json_file):
                with open(json_file,'w') as file:
                    json.dump({'Event':event},file)
            
        except Exception as e:
            raise Exception(f"Error writing event:{str(e)}")
        
    def read_event(self):
        """
        Fetch total flowcount pulses during every trip
        """
        json_file = 'event_update.json'
        
        try:
            with open(json_file, 'r') as file:
                data = json.load(file)
            return str(data['Event'])
        except (FileNotFoundError, KeyError) as e:
            raise Exception(f"Error reading total flow: {str(e)}")

    def sw_version(self,version):
        json_file = 'sw_version.json'
        try:
            if os.path.exists(json_file):
                with open(json_file,'w') as file:
                    json.dump({'version':version},file)
            
        except Exception as e:
            raise Exception(f"Error writing event:{str(e)}")
        
    def read_sw_version(self):
        json_file = 'sw_version.json'
        
        try:
            with open(json_file, 'r') as file:
                data = json.load(file)
            return str(data['version'])
        except (FileNotFoundError, KeyError) as e:
            raise Exception(f"Error reading total flow: {str(e)}")
        
    def write_total_trip(self, trip):
        """
        Write total trip to json file
        """
        json_file = 'total_trip.json'
        total_trip = trip

        try:
            if os.path.exists(json_file):
                with open(json_file, 'r') as file:
                    data = json.load(file)
                    total_trip += data.get('Total_trip', 0)

            with open(json_file, 'w') as file:
                json.dump({
                    'Total_trip': total_trip
                }, file)
        except Exception as e:
            raise Exception(f"Error writing total trip: {str(e)}")