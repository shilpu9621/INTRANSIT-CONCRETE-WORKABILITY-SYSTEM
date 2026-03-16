from gpiozero import LED
import RPi.GPIO as GPIO
import subprocess
import re
import time
import socket

#set GPIO mode to
GPIO.setmode(GPIO.BCM)

GPIO.setup(6, GPIO.OUT) #4G power access Pin
GPIO.output(6, GPIO.LOW)


#GPIO.setup(18, GPIO.OUT) #4G power access Pin
led = LED(18)

# List USB ports

#Timer to reset 4G every 24 hours
RESET_4G_TIMER=time.time()
print("time===",RESET_4G_TIMER)

def reset_4G():
    """
    This function pulls down gpio6 to high once and low again
    """
    reset_GPIO()
    GPIO.output(6, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(6, GPIO.LOW)
    GPIO.cleanup()

def check_4G_USB():
    """
    This functions checks whether Qualcomm network interface is available
    return True if found else false
    """
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        usb_ports = result.stdout.strip()
        #print(usb_ports) uncomment for debugging
        result2 = subprocess.run(['route'], capture_output=True, text=True)
        USB_network_card = result2.stdout.strip()
        if 'usb0' in USB_network_card:
            print('4g route found')
        if 'Qualcomm' in usb_ports:
            print('Qualcomm port found')
            if 'usb0' in USB_network_card:
                print('4G connection Dialed up')
                return True
        else:
            print('4G dial up connection not found, try resetting the power pin of 4G module')
            return False
    except  Exception as e:
        print('Exception occured ',e)
        return False


def check_network_connection():
    """
    This function checks the network connection and turns on blue led if network found
    """
    try:
        socket.create_connection(('thingsboard.cloud', 1883), timeout=2)
        led.on()
        print("connected to Internet")
        return True
    except Exception as e:
        print('Exception occured ',e)
        led.off()
        return False

def reset_GPIO():
    """
    This function re-initialize the gpio pin when called
    """
        #set GPIO mode to
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(6, GPIO.OUT) #4G power access Pin
    GPIO.output(6, GPIO.LOW)


def reset_4G_per_day():
    """
    Reset 4G every 24 hours
    24 Hours = 24 * 60 * 60 = 86400 secs.

    """
    global RESET_4G_TIMER

    #Uncomment below to debug it
    #print("time passed since 4g reset ====> ",time.time()-RESET_4G_TIMER)

    if (time.time()-RESET_4G_TIMER) > 86400 :
        time.sleep(1)
        reset_4G()
        RESET_4G_TIMER=time.time()
        print("Resetting 4G every 24 hours done successfully")


while True:
    
    try:
        reset_4G_per_day()
        if check_network_connection():
            pass
        else:
            reset_4G()
            
        if check_4G_USB():
            print('4G dial found normal')
        else :
            print('Need to reset 4G initiating reset')
            reset_4G()
    except Exception as e:
        print(e)
        led.close()
    #print("Waiting every 30 secs")
    time.sleep(180)
    GPIO.cleanup()

