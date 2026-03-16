import time
import math
import serial

ser=serial.Serial('/dev/ttyS0',115200)


def send_at(command,back,timeout):
        rec_buff = ''
        ser.write((command+'\r\n').encode())
        time.sleep(timeout)
        if ser.inWaiting():
                time.sleep(0.01 )
                rec_buff = ser.read(ser.inWaiting())
        if rec_buff != '':
                if back not in rec_buff.decode():

                        return 0
                else:
                        #print(rec_buff.decode())
                        return 1
        else:
                print('AT commands not responding')
                return 0

def get_gps_position():
        rec_buff = ''
        print()
        send_at('AT+CGPS=1,1','OK',1)
        time.sleep(1)
        answer = send_at('AT+CGPSINFO','+CGPSINFO: ',1)
        if 1 == answer:
                answer = 0
                ser.write(('"AT+CGPSINFO\r\n"').encode())
                time.sleep(1)
                if ser.inWaiting():
                        time.sleep(0.01)
                        rec_buff = ser.read(ser.inWaiting())
                if rec_buff != '' and len(rec_buff) > 50:
                        response_frame = str(rec_buff).split(',')
                        test_frame = ''.join(response_frame)
                        #print("response frame==",response_frame)
                        if "AT+CGPS=1" not in test_frame:
                            gps_lat = response_frame[0].split(":")
                            lat = list(math.modf(float(gps_lat[1])/100))
                            long = list(math.modf(float(response_frame[2])/100))
                            lat = lat[1] + (lat[0] * 100) / 60
                            long = long[1] + (long[0] * 100) / 60
                            speed_knots = float(response_frame[7])
                            speed_kms = speed_knots * 1.852  # Convert knots to km/h
                            #print(f"lat={lat},long={long},speed={speed_kms}")
                            return lat, long, speed_kms, 1
                        else:
                            return 0,0,0,0
                else:
                    return 0,0,0,0
        else:
            return 0,0,0,0


time.sleep(2)
lat,long,speed,val=get_gps_position()

lat1=lat
lat2=lat
lon1=long
lon2=long

class GPS:
    def __init__(self):
        self.gps_failed_count = 0
        self.last_valid_lat = None
        self.last_valid_long = None
        self.min_speed_threshold = 0.5  # km/second, about 1.8 km/h
        self.min_distance_threshold = 1  # meters - minimum distance to consider actual movement
        self.max_distance_thresold = 500
        self.max_reasonable_speed = 100  # km/second, about 144 km/h
        self.position_samples = []  # Store recent positions for averaging
        self.max_samples = 2  # Number of samples to average
        send_at('AT+CVAUX=3050','',1)
        send_at('AT+CVAUXs=1','',1)

    def Reset_GPS(self):
        self.gps_failed_count = 0
        send_at('AT+CVAUX=3050','',1)
        send_at('AT+CVAUXs=1','',1)
        self.last_valid_lat = None
        self.last_valid_long = None
        self.position_samples = []

    def average_position(self, lat, lon):
        """
        Average multiple position readings to reduce noise
        """
        self.position_samples.append((lat, lon))
        if len(self.position_samples) > self.max_samples:
            self.position_samples.pop(0)

        if len(self.position_samples) < 2:  # Need at least 2 samples
            return lat, lon

        avg_lat = sum(p[0] for p in self.position_samples) / len(self.position_samples)
        avg_lon = sum(p[1] for p in self.position_samples) / len(self.position_samples)
        return avg_lat, avg_lon

    def is_within_india(self, lat, lon):
        # Approximate boundaries of India
        lat_min, lat_max = 6.5546, 35.6745
        lon_min, lon_max = 68.1862, 97.3956
        return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max

    def get_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance with improved filtering
        """
        if not (self.is_within_india(lat1, lon1) and self.is_within_india(lat2, lon2)):
            return 0  # Changed to return 0 instead of 10 when outside India

        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        # Calculate distance in meters
        distance = 6371000 * c
        #print("distance======>",distance)

        # Filter out small movements that are likely GPS noise
        if  distance < self.min_distance_threshold :
            return 0
        if distance > self.max_distance_thresold:
            return 0

        return distance

    def update_total_distance(self,lat,lon,speed,val):
        """
        Update total distance with improved filtering
        """
        if val:
            #print("val======>",val)
            # Apply speed threshold filter
            if speed < self.min_speed_threshold or speed > self.max_reasonable_speed:
                return 0

            # Average the position readings
            avg_lat, avg_lon = self.average_position(lat, lon)

            # Initialize last valid position if needed
            if self.last_valid_lat is None:
                self.last_valid_lat = avg_lat
                self.last_valid_long = avg_lon
                return 0

            # Calculate distance
            distance = self.get_distance(self.last_valid_lat, self.last_valid_long, avg_lat, avg_lon)

            # Update last valid position only if we detected actual movement
            if distance > self.min_distance_threshold and distance < self.max_distance_thresold:
                self.last_valid_lat = avg_lat
                self.last_valid_long = avg_lon

            return distance
        return 0
