from serial import Serial
import socket
import time

try:
    ser = Serial('/dev/ttyS0', 115200, timeout=1)
except Exception as e:
    print("exception", e)

def send_at_command(command):
    try:
        ser.write((command + '\r\n').encode())
        time.sleep(1)
        response = ser.read(ser.in_waiting).decode()
        return response
    except Exception as e:
        print("exception", e)
        return ""

def get_mac(interface='eth0'):
    try:
        with open(f'/sys/class/net/{interface}/address') as f:
            return f.read().strip()
    except Exception as e:
        return f"Error: {e}"

def get_imei():
    time.sleep(0.5)
    response = send_at_command('AT+GSN')  # Standard AT command for IMEI
    lines = response.strip().split('\r\n')
    for line in lines:
        if line and not line.startswith('AT') and not line.startswith('OK'):
            return line.strip()
    return "Unknown"

def get_sim():
    time.sleep(0.5)
    response = send_at_command('AT+CCID')  # Standard AT command for SIM ID
    lines = response.strip().split('\r\n')
    for line in lines:
        if '+CCID:' in line:
            return line.split('+CCID:')[1].strip()
        elif line and not line.startswith('AT') and not line.startswith('OK'):
            return line.strip()
    return "Unknown"

def main():
    hostname = socket.gethostname()
    send_at_command('AT+CREG=1')
    print("Janyu Technologies Pvt Ltd")
    print(f"Device ID:{hostname}")
    print(f"SIM:{get_sim()}")
    print(f"IMEI:{get_imei()}")
    print(f"MAC:{get_mac('eth0')}")

if __name__ == "__main__":
    main()