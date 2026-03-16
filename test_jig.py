from sensor import io
import time
import requests
from serial import Serial
from gpiozero import Button, LED
from ups import INA219
from tb_device_http import TBHTTPDevice
from sim76xx import *

import json

ina219 = INA219(i2c_bus=10, addr=0x43)
low = 0
count=0


BUTTON_PIN = 22
LED_PIN = 18
button = Button(BUTTON_PIN, pull_up=True)
led = LED(LED_PIN)


def button_pressed():
    print("Button was pressed!")

try:
    button.when_pressed = button_pressed
except:
    button.close()


#CLASS io Object
PWindow_size = 12
AWindow_size = 5
max_pres = 400
min_pres = 0
max_tank_level = 21
min_tank_level = 5

try:
    me31=io(port='/dev/ttyAMA3', Pressure_window_size = PWindow_size, 
            Avg_Pressure_window_size = AWindow_size,
            min_pressure = min_pres, max_pressure = max_pres, 
            min_tanklevel = min_tank_level, max_tanklevel = max_tank_level)
    me31.connect()
    me31.write_relay(0,False)
    print("IO initialization successful")
except Exception as e:
    print(f"Failed to initialize IO: {str(e)}")

ser = Serial('/dev/ttyS0', 115200, timeout=1)

def send_at_command(command):
    ser.write((command + '\r\n').encode())
    time.sleep(0.5)
    return ser.read(ser.in_waiting).decode()

def get_csq_and_strength():
    response = send_at_command('AT+CSQ')
    if '+CSQ:' in response:
        csq = int(response.split('+CSQ: ')[1].split(',')[0])
        return csq
    return None

# ThingsBoard setup
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

try:
    client = TBHTTPDevice('https://samasth.io:443',access_token)
    client.connect()
except Exception as e:
    print("Connection timeout error: %s", str(e))

def Publish_data(telemetry_with_ts):
    """
    """
    try:
        response = client.send_telemetry(telemetry_with_ts)
        print(f"Server response: {response}")
        # Check the actual response content/status
    except Exception as e:
        log_the_data.save_data_locally(telemetry_with_ts, unpub_file)
        logging.error("Connection timeout error: %s", str(e))

# Global variables
rpm = 0


Mixer_Rotation_Prev = me31.read_pulse_count()

pulse_count = Mixer_Rotation_Prev[1]

Mixer_Rotation_Prev = pulse_count

Mixer_Rotation_Now = pulse_count

#Counting RPM (Revolution per minute)
def read_rpm_every_65s():
    """
    This function reads count of pulses on DI module every 60 seconds to return count of rotations
    """
    pulse_count_all = me31.read_pulse_count()
    if pulse_count_all != None:
        global Mixer_Rotation_Prev
        global rpm
        Mixer_Rotation_Now = pulse_count_all[1]
        if Mixer_Rotation_Now >= Mixer_Rotation_Prev:
            temp = Mixer_Rotation_Now
            #uncomment below linw for debugging
            print("rpm recorded ",Mixer_Rotation_Now - Mixer_Rotation_Prev)
            rpm = Mixer_Rotation_Now - Mixer_Rotation_Prev
            Mixer_Rotation_Prev = temp
            return rpm

    else:
        print("Error reading count of pulses")


def Internet_Connected():
    url = "http://www.google.com"
    timeout = 5
    try:
        requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        return False


def Publish_Data(Data):
    try:
        if Internet_Connected():
            client.send_telemetry(Data)
            return 1
        else:
            print("unable to publish")
    except:
        print("data sending failed")
        return 0


def fetch_ups_battery():
    bus_voltage = ina219.getBusVoltage_V()
    shunt_voltage = ina219.getShuntVoltage_mV() / 1000
    current = ina219.getCurrent_mA() / 1000
    power = ina219.getPower_W()
    p = (bus_voltage - 3)/1.2*100
    if p > 100: p = 100
    if p < 0: p = 0

    if current < 0:
        charge_status=True
    else:
        charge_status=False
    return p, charge_status


PUMP_TIMER_FLAG=False
PUMP_TIMER=time.time()
READ_RPM_TIME=time.time()
READ_RPM_FLAG=False

gps = GPS()


GPS_failed_count=0

GPS_TIMER =time.time()

lat=0
long=0
speed=0
gps_status=False
distance=gps.update_total_distance(lat,long,speed,gps_status)

try:
    while True:
        if (time.time()-GPS_TIMER) > 15:
            GPS_TIMER=time.time()
            lat, long, speed, gps_status = get_gps_position()
            print(f"GPS_sts:- {gps_status}")
            if gps_status:
                telemetry_with_ts = {"ts": int(round(time.time() * 1000)), "values": {"Latitude": lat,"Longitude": long,"Speed": speed}}
                GPS_failed_count = 0
            else:
                telemetry_with_ts = {"ts": int(round(time.time() * 1000)), "values": {"GPS_Error": -1}}
                GPS_failed_count += 1
                if GPS_failed_count > 2:
                    gps.Reset_GPS()
                    GPS_failed_count = 0
            
            print(telemetry_with_ts)
        
        count+=1

        running_pressure = me31.instant_pressure()
        tank_level = me31.tank_level()
        flow_meter_total = me31.read_pulse_count()
        digital_inputs = me31.read_digital_inputs()
        relay_status = me31.relay_status()
        Mixer_direction = me31.check_direction()
        toggle_state = me31.read_digital_inputs()
        csq = get_csq_and_strength()
        battery_percentage, charge_status = fetch_ups_battery()


        if READ_RPM_FLAG!=True:
                READ_RPM_TIME=time.time()
                READ_RPM_FLAG=True

        if (time.time()-READ_RPM_TIME) > 20 :
            read_rpm_every_65s()
            READ_RPM_FLAG=False

        print(f"[{count}]..[tank_level={tank_level[0]:.1f}]..[pressure={running_pressure[0]:.1f}]..[flow_meter_total={flow_meter_total[2]}].."
        f"[rpm={rpm}]..[Mixer_direction={Mixer_direction}].."
        f"[toggle_state={toggle_state[3]}]..[csq={csq}], [battery_percentage={battery_percentage:.2f}]..[charge_status={charge_status}]")


        telemetry_with_ts = {
            "ts": int(round(time.time() * 1000)),
            "values": {
                "Direction": digital_inputs[0],
                "flowmeter": flow_meter_total[2],
                "Running_Pressure": running_pressure[0],
                "Tank_level": tank_level[0],
                "RPM": rpm,
                "battery_percentage": battery_percentage,
                "Charge_status": charge_status,
                "CSQ": csq,
                "lat": lat,
                "long": long
            }
        }

        try:
            client.send_telemetry(telemetry_with_ts)
        except:
            print("data sending failed")

        if Internet_Connected():
            led.on()

            
            #print("LED status: High")
        else:
            led.off()
            
            #print("LED status: Low")

        if PUMP_TIMER_FLAG!=True:
            PUMP_TIMER=time.time()
            PUMP_TIMER_FLAG=True

        if (time.time()-PUMP_TIMER)>90:
            PUMP_TIMER_FLAG=False
            me31.write_relay(1,True)
            me31.write_relay(0,True)
            print("Auto Dosing On")
            time.sleep(30)
            me31.write_relay(1,False)
            me31.write_relay(0,False)


        time.sleep(5)
        #led.close()  # Add a small delay to prevent excessive looping
except KeyboardInterrupt:
    led.close()
    me31.write_relay(0,False)
    me31.write_relay(1,False)
    
    