import time
import math
import os
from pygsm import GsmModem
from datetime import datetime
from datetime import timedelta
from dateutil import tz

def degreesToRadians(degrees):
    return degrees * math.pi / 180

# Calculate the Distance between two coordinates
# https://stackoverflow.com/questions/365826/calculate-distance-between-2-gps-coordinates
def distanceInMeterBetweenEarthCoordinates(lat1, lon1, lat2, lon2):
    earthRadiusMeter = 6371000;
    dLat = degreesToRadians(lat2-lat1);
    dLon = degreesToRadians(lon2-lon1);

    lat1 = degreesToRadians(lat1)
    lat2 = degreesToRadians(lat2)
    
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.sin(dLon/2) * math.sin(dLon/2) * math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return earthRadiusMeter * c

# Configuration
SendTimeout = 10    	# Send position every x minutes regardless of movement
HorizontalDelta = 10	# Send position if it moves horizontally by at keast this many metres
VerticalDelta = 50		# Send position if it moves vertically by at least this many metres
MaxGSMAltitude = 2000	# Don't try to send above this altitude
SMSLoop = 5             # Check SMS message every x seconds 

utc_zone = tz.gettz('UTC')
to_zone = tz.gettz('America/New_York')

PreviousDateTime = datetime(1970, 1, 1, 0, 0, 0, 0, utc_zone)
# print 'previous: ' + str(PreviousDateTime)
PreviousAltitude = 0
PreviousLatitude = 0
PreviousLongitude = 0

MobileNumber = os.environ.get('MOBILE_NUMBER')
ModemPort = os.environ.get('MODEM_PORT')

# Check if the modem is ready, if not we assume the modem need to be power on
if (os.system("timeout 10s python gsmready.py") != 0):
	print "Can't find modem, trying to powering up"
	os.system("bash power_switch.sh")

# Set mobile number here
print "Texts will be sent to mobile phone " + MobileNumber

print "Booting modem ..."
modem = GsmModem(port=ModemPort)
modem.boot()

print "Modem details:"
reply = modem.hardware()
print "Manufacturer = " + reply['manufacturer']
print "Model = " + reply['model']
print

# Try and get phone number
reply = modem.command('AT+CNUM')
if len(reply) > 1:
	list = reply[0].split(",")
	phone = list[1].strip('\"')
	print "Phone number = " + phone
	print
	
print "Deleting old messages ..."
modem.query("AT+CMGD=70,4")
print

# Switch GPS on
print "Switching GPS on ..."
reply = modem.command('AT+CGNSPWR=1')
print reply

onTimeout = False
onMove = True
sendStatus = True

Message = 'Tracker App started!'
modem.send_sms(MobileNumber, Message)

print "Waiting for incoming messages..."

while True:
    # check for new messages
	message = modem.next_message()

	if message:
		print message
		text = message.text
		if text[0:7] == 'Timeout':
			if onTimeout:
				onTimeout = False
				sendStatus = True
				print 'Stop sending Position on Timeout'
			else:
				onTimeout = True
				PreviousDateTime = datetime(1970, 1, 1, 0, 0, 0, 0, utc_zone)
				print 'Start sending Position on Timeout'
		elif text[0:4] == 'Move':
			if onMove:
				onMove = False
				sendStatus = True
				print 'Stop sending Position on Movement'
			else:
				onMove = True
				PreviousAltitude = 0
				PreviousLatitude = 0
				PreviousLongitude = 0
				print 'Start sending Position on Movement'
		elif text[0:6] == 'Status':
			sendStatus = True
			print 'Sending current status.'
		elif text[0:5] == 'delta':
			sendStatus = True
			print 'text: ' + text
			newdelta = int(text[5:7])
			print 'newdelta: ' + str(newdelta)
			SendTimeout = newdelta
		# elif text[0:7] == 'SMSLoop':
		# 	newSmsLoop = int(text[7:9])
		# 	print 'newSmsLoop: ' + str(newSmsLoop)
		# 	SMSLoop = newSmsLoop			

	# Get position
	reply = modem.command('AT+CGNSINF')
	# reply example: ['+CGNSINF: 1,1,20211218220507.000,45.398859,-73.482280,21.155,0.00,1.5,1,,0.9,1.3,1.0,,9,10,9,,35,,', 'OK']

	list = reply[0].split(",")
	if len(list[2]) > 14:
		utc = datetime(int(list[2][0:4]), int(list[2][4:6]), int(list[2][6:8]), int(list[2][8:10]), int(list[2][10:12]), int(list[2][12:14]), 0, utc_zone)
		# Convert to local time zone
		local = utc.astimezone(to_zone)

		Latitude = list[3]
		Longitude = list[4]
		Altitude = list[5]
		# print str(utc) + ', ' + Latitude + ', ' + Longitude + ', ' + Altitude
		
		if Altitude <> '':
			Latitude = float(Latitude)
			Longitude = float(Longitude)
			Altitude = float(Altitude)
						
			# Send now ?
			if Altitude <= MaxGSMAltitude:
				# Low enough

				# print 'current:  ' + str(utc)
				# print 'previous: ' + str(PreviousDateTime)
				# print 'delta:    ' + str(timedelta(seconds=SendTimeout*60))
				# print 'next:     ' + str(PreviousDateTime + timedelta(seconds=SendTimeout*60))
				# print

				if sendStatus:
					Title = 'Status'
					Message = str(local) + ', onTimeout(' + str(onTimeout) + ',' + str(SendTimeout) + '), onMove(' + str(onMove) + ',' + str(HorizontalDelta) + ',' + str(VerticalDelta) + ')'
					print 'Sending to mobile ' + MobileNumber + ": " + Message
					modem.send_sms(MobileNumber, Message)
					sendStatus = False

				if onTimeout and utc > (PreviousDateTime + timedelta(seconds=SendTimeout*60)): 
					PreviousDateTime = utc
					PreviousAltitude = Altitude
					PreviousLatitude = Latitude
					PreviousLongitude = Longitude
					Title = 'Timeout reached, onTimeout(' + str(onTimeout) + ',' + str(SendTimeout) + ')'
					Message = str(local) + ', ' + Title + ', ' + str(Latitude) + ', ' + str(Longitude) + ' http://maps.google.com/?q=' + str(Latitude) + ',' + str(Longitude)
					print 'Sending to mobile ' + MobileNumber + ": " + Message
					modem.send_sms(MobileNumber, Message)
				
				Distance = distanceInMeterBetweenEarthCoordinates(Latitude, Longitude, PreviousLatitude, PreviousLongitude)

				if onMove and Distance >= HorizontalDelta:
					if Distance > 5000: Distance = 0 # we assume if the distance is greather the 5000,  that the unit reboot
					PreviousDateTime = utc
					PreviousAltitude = Altitude
					PreviousLatitude = Latitude
					PreviousLongitude = Longitude
					Title = "HorizontalDelta: " + str(Distance) + ', onMove(' + str(onMove) + ',' + str(HorizontalDelta) + ',' + str(VerticalDelta) + ')'
					Message = str(local) + ', ' + Title + ', ' + str(Latitude) + ', ' + str(Longitude) + ' http://maps.google.com/?q=' + str(Latitude) + ',' + str(Longitude)
					print 'Sending to mobile ' + MobileNumber + ": " + Message
					modem.send_sms(MobileNumber, Message)
				
				if onMove and abs(Altitude - PreviousAltitude) >= VerticalDelta:
					PreviousDateTime = utc
					PreviousAltitude = Altitude
					PreviousLatitude = Latitude
					PreviousLongitude = Longitude
					Title = "VerticalDelta: " + str(abs(Altitude - PreviousAltitude)) + ', onMove(' + str(onMove) + ',' + str(HorizontalDelta) + ',' + str(VerticalDelta) + ')'
					Message = str(local) + ', ' + Title + ', ' + str(Latitude) + ', ' + str(Longitude) + ' http://maps.google.com/?q=' + str(Latitude) + ',' + str(Longitude)
					print 'Sending to mobile ' + MobileNumber + ": " + Message
					modem.send_sms(MobileNumber, Message)
				
	time.sleep(SMSLoop)
