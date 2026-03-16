import pymodbus
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ConnectionException
import time
import math
import logging


logging.basicConfig(
    level=logging.INFO,
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class io:
    def __init__(self, port='/dev/ttyAMA3', baudrate=19200, bytesize=8, parity='N', stopbits=1, timeout=1, unit=1, 
                 Pressure_window_size=12,Avg_Pressure_window_size=5,min_pressure=0,max_pressure=400,min_tanklevel=5,max_tanklevel=21):
        """
        Initialize the Modbus IO interface with communication parameters.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.Pressure_window_size = Pressure_window_size
        self.Avg_Pressure_window_size = Avg_Pressure_window_size
        self.min_pressure=min_pressure
        self.max_pressure=max_pressure
        self.min_tanklevel=min_tanklevel
        self.max_tanklevel=max_tanklevel
        self.pressure_list = []
        self.pressure_sum = 0
        self.tank_list = []
        self.tank_sum = 0
        self.m_pressure_list = []
        self.m_pressure_sum = 0
        self.c_pressure_list = []
        self.c_pressure_sum = 0
        self.pss = 0
        self.tss = 0
    
   
    def update_sensors_val(self, pressure_window_size=0, avg_pressure_window_size=0,min_pressure=0,max_pressure=400,min_tanklevel=5,max_tanklevel=21):
        
        self.Pressure_window_size = pressure_window_size
        self.Avg_Pressure_window_size = avg_pressure_window_size
        self.min_pressure=min_pressure
        self.max_pressure=max_pressure
        self.min_tanklevel=min_tanklevel
        self.max_tanklevel=max_tanklevel

    def connect(self):
        while True:
            try:
                self.client = ModbusSerialClient(port=self.port,baudrate=self.baudrate,bytesize=self.bytesize,parity=self.parity,stopbits=self.stopbits,timeout=self.timeout)
                self.client.connect()
                logging.info('Connected to Modbus Device')
                break
            except ConnectionException as e:
                logging.error("Error connecting to Modbus Device: %s", str(e))
                logging.info('retrying in 2 seconds')
                time.sleep(2)

    def close(self):
        self.client.close()

    def read_holding_registers(self,address,count,slave=1):
        try:
            response = self.client.read_holding_registers(address,count,slave)
            if response.isError():
                logging.error('Error readig holding registers: %s ',str(response))
                return 0
            else:
                return response.registers
        except ConnectionException as e:
            logging.error('Modbus connection error: %s',str(e))
            return 0,0

    def read_discrete_inputs(self,address,count,slave=1):
        try:
            response = self.client.read_discrete_inputs(address,count,slave)
            if response.isError():
                logging.error('Error readig inputs: %s',str(response))
                return 0
            else:
                return response.bits
        except ConnectionException as e:
            logging.error('Modbus connection error: %s',str(e))
            return 0,0 #returning adition status code


    def read_input_registers(self,address,count,slave=1):
        try:

            response = self.client.read_input_registers(address,count,slave)
            #print("response from",response)
            if response.isError():
                logging.error('Error readig input registers %s',str(response))
                return None
            else:
                return response.registers
        except ConnectionException as e:
            logging.error('Modbus connection error: %s',str(e))
            return 0,0 #returning aditional status code

    def read_analog_inputs(self):
        """
        Reads all the integer and engineering values for Analog Inputs
        """
        try:
            analog_inputs = self.read_input_registers(100, 2, 1)
            return analog_inputs
        except Exception as e:
            logging.error("Error reading analog inputs: %s",str(e))
            return 0 #returning aditional status code


    def read_digital_inputs(self):
        """
        Reads all digital inputs data
        """
        try:
            digital_inputs = self.read_discrete_inputs(0, 4, 1)
            if digital_inputs ==0:
                return 0,0,0,0
            return digital_inputs
        except Exception as e:
            logging.error("Error reading digital inputs: %s",str(e))
            return -1,-1 #returning aditional status code

    def read_pulse_count(self):
        """
        Reads pulse count number from all digital inputs
        """
        try:
            pulse_count = self.read_holding_registers(2527, 4, 1)
            if pulse_count == 0 or None:
                return 0,0,0,0
            return pulse_count
        except Exception as e:
            logging.error("Error reading pulse count: %s",str(e))
            return 0

    def write_holding_registers(self, address, values, slave=1):
        try:
            response = self.client.write_registers(address, values, slave=slave)

            if response.isError():
                logging.error("Error writing to holding registers: %s",str(response))
                return 0
            else:
                return response.registers
        except Exception as e:
            logging.error("Error writing to holding registers: %s",str(e))
            return False

    def instant_pressure(self):
        try:
            current_mA=0
            analog_inputs = self.read_analog_inputs()
            if analog_inputs is None or 0:
                logging.error("Failed to read analog inputs or no data available")
                return 0, 0

            try:
                current_mA = analog_inputs[0]/1000
            except:
                logging.info("Cannot divide 0 to obtain current_mA")
                current_mA=0

            calibrated_value = (((current_mA ) - 4)/16) * (400 - 0) + 0
            if calibrated_value <= 0 and current_mA < 3.5:
                logging.error("sensor disconnected ")
                return 0, 0
            elif calibrated_value < 0:
                #   print(calibrated_value)
                return 0, 1
            else:
                #print(calibrated_value)
                return calibrated_value,1
        except Exception as e:
            logging.error("Error in instant_pressure: %s",str(e))
            return 0, 0

    def running_pressure_average(self):
        try:
            result = self.instant_pressure()
            if result is None:
                logging.error("Error: instant_pressure returned None")
                return 0

            pressure, status_code = result

            if pressure <= 0:
                return 0

            if status_code:
                self.pressure_list.append(pressure*pressure)
                self.pressure_sum += pressure*pressure

                if len(self.pressure_list) >  self.Pressure_window_size:
                    self.pressure_sum -= self.pressure_list.pop(0)

                try:
                    avg = math.sqrt(self.pressure_sum / len(self.pressure_list))
                    return avg
                except (ValueError, ZeroDivisionError) as e:
                    logging.error("Error calculating pressure average: %s", str(e))
                    return 0
            else:
                logging.error("Status code is False, returning 0")
                return 0
        except Exception as e:
            logging.error("Error in running_pressure_average: %s", str(e))
            return 0

    def master_pressure_average(self):
        """
        Calculates the master pressure average
        """
        try:
            pressure = self.running_pressure_average()
            if pressure is None:
                logging.error("Error: Master Pressure returned None")
                return 0

            self.m_pressure_list.append(pressure*pressure)
            self.m_pressure_sum += pressure*pressure

            if len(self.m_pressure_list) > 5:
                self.m_pressure_sum -= self.m_pressure_list.pop(0)

            try:
                avg = math.sqrt(self.m_pressure_sum/len(self.m_pressure_list))
                return avg
            except (ValueError, ZeroDivisionError) as e:
                logging.error("Error calculating master pressure average: %s", str(e))
                return 0
        except Exception as e:
            logging.error("Error in master_pressure_average: %s", str(e))
            return 0

    def current_pressure_average(self):
        """
        Calculates the current pressure average
        """
        try:
            pressure = self.running_pressure_average()
            if pressure is None:
                logging.error("Error: Current Pressure returned None")
                return 0

            self.c_pressure_list.append(pressure*pressure)
            self.c_pressure_sum += pressure*pressure

            if len(self.c_pressure_list) > 5:
                self.c_pressure_sum -= self.c_pressure_list.pop(0)

            try:
                avg = math.sqrt(self.c_pressure_sum/len(self.c_pressure_list))
                return avg
            except (ValueError, ZeroDivisionError) as e:
                logging.error("Error calculating current pressure average: %s", str(e))
                return 0
        except Exception as e:
            logging.error("Error in current_pressure_average: %s", str(e))
            return 0

    def tank_level(self):
        """
        Read Analog input from IO module and calibrate on the scale of 0 to 400 bars
                a simple calibration formula as follows
        PV[units] = ((I-4)/16) * (PVmax -PVmin) + PVmin
                PV = Process Variable
                PVmax - Upper range of Process variable
                PVmin = Lower range of Process variable
                """
        analog_inputs = self.read_analog_inputs()
        if analog_inputs is not None:
            try:
                current_mA = analog_inputs[1]/1000
                calibrated_value = (((current_mA ) - 4)/16) * (21 - 5) + 5
                if calibrated_value < 0:
                    logging.error("tank level sensor disconnected ")
                    return 0,0
                else:
                   # print(calibrated_value)
                    return calibrated_value , 1
            except:
                logging.error("tank level sensor disconnected")
                return 0,0
        else:
            return 0,0


    def tank_level_average(self):
        """
        this function averages the every 5 instant tank level and returns it
        """
        try:
            result = self.tank_level()
            if result is None:
                logging.error("Error: instant_pressure returned None")
                return 0

            tank_volume, status_code = self.tank_level()
            if status_code:
                self.tank_list.append(tank_volume*tank_volume)
                self.tank_sum += tank_volume * tank_volume

                if len(self.tank_list) > self.Pressure_window_size:
                    self.tank_sum -= self.tank_list.pop(0)

                try:
                    avg = math.sqrt(self.tank_sum / len(self.tank_list))
                    return avg
                except (ValueError, ZeroDivisionError) as e:
                    logging.error("Error calculating tank level average: %s", str(e))
                    return 0
            else:
                logging.error("Status code is False, returning 0")
                return 0
        except Exception as e:
            logging.error("Error in tank_level_average: %s", str(e))
            return 0


    def check_direction(self):
        try:
            digital_inputs = self.read_digital_inputs()
            if digital_inputs is None:
                logging.error('error reading digital inputs')
                return None
            if digital_inputs != 0:
                DI1 = digital_inputs[0]
                Direction = DI1
                return Direction
            return None
        except Exception as e:
            logging.error("Error checking direction: %s", str(e))
            return None

    def write_relay(self, addr, value):
        """
        Writes values to relay to toggle relay ON/OFF
        """
        try:
            # Write coils
            response = self.client.write_coil(addr,value,1)
            #print(response)
            if response.isError():
                logging.error("Error writing coils: %s",str(response))
            else:
               # print(f"Coils written successfully: {response}")
                self.relay_status()
                return 1
        except Exception as e:
            logging.error("Error writing coils: %s",str(e))
        return 0

    def relay_status(self):
        """
        Reads Relay status and returns whether relay is ON or OFF
        """
        try:
            relay_status = self.client.read_coils(0, 2, 1)
            if relay_status.isError():
                logging.error("Error reading relay status: %s",str(relay_status))
                return 0
            #print(relay_status.bits[0])
            #print(relay_status.bits[1])
            return relay_status.bits[0]
        except AttributeError as e:
            logging.error(f"AttributeError: {str(e)}. The response doesn't have 'bits' attribute.")
            return 0
        except Exception as e:
            logging.error(f"Error in relay_status: {str(e)}")
            return 0
