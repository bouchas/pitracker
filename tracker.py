import time
import math
import os
from pygsm import GsmModem

# Switch GPS on
def SwitchGPSon():
    print "Switching GPS on ..."
    reply = gsm.command('AT+CGNSPWR=1')
    print reply
    print

# Calculate the Distance between two coordinates
def CalculateDistance(Latitude1, Longitude1, Latitude2, Longitude2):
	Latitude1 = Latitude1 * math.pi / 180
	Longitude1 = Longitude1 * math.pi / 180
	Latitude2 = Latitude2 * math.pi / 180
	Longitude2 = Longitude2 * math.pi / 180

	return 6371000 * math.acos(math.sin(Latitude2) * math.sin(Latitude1) + math.cos(Latitude2) * math.cos(Latitude1) * math.cos(Longitude2-Longitude1))

# Configuration
SendTimeout = 5	    	# Send position every x minutes regardless of movement
HorizontalDelta = 50	# Send position if it moves horizontally by at keast this many metres
VerticalDelta = 50		# Send position if it moves vertically by at least this many metres
MaxGSMAltitude = 2000	# Don't try to send above this altitude
LoopDelay = 10			# Delay between getting gps position

PreviousSeconds = 0
PreviousAltitude = 0
PreviousLatitude = 0
PreviousLongitude = 0

# Set mobile number here
MobileNumber = os.environ.get('MOBILE_NUMBER')
print "Texts will be sent to mobile phone " + MobileNumber

print "Booting modem ..."
ModemPort = os.environ.get('MODEM_PORT')
gsm = GsmModem(port=ModemPort)
gsm.boot()

print "Modem details:"
reply = gsm.hardware()
print "Manufacturer = " + reply['manufacturer']
print "Model = " + reply['model']
print

# Try and get phone number
reply = gsm.command('AT+CNUM')
if len(reply) > 1:
	list = reply[0].split(",")
	phone = list[1].strip('\"')
	print "Phone number = " + phone
	print
	
print "Deleting old messages ..."
gsm.query("AT+CMGD=70,4")
print

SwitchGPSon()

# If the send notification is active. You can start the notification by sending 'Start'
Started = False

while True:

    # Check messages
	message = gsm.next_message()

	if message:
		print message
		text = message.text
		if text[0:5] == 'Start':
			Started = True
			PreviousSeconds = 0
			print "Start sending Position ..."
			print
		elif text[0:4] == 'Stop':
			Started = False
			print "Text was Stop. Stop sending Position."
			print
		elif text[0:6] == 'Status':
			Message = 'Status: ' + UTC + ', Started: ' + str(Started) + ', LoopDelay: ' + str(LoopDelay) 
			print "Sending to mobile " + MobileNumber + ": " + Message
			gsm.send_sms(MobileNumber, Message)

	# Get position
	reply = gsm.command('AT+CGNSINF')
	list = reply[0].split(",")
	if len(list[2]) > 14:
		UTC = list[2][8:10]+':'+list[2][10:12]+':'+list[2][12:14]
		Latitude = list[3]
		Longitude = list[4]
		Altitude = list[5]
		print 'Position: ' + UTC + ', ' + Latitude + ', ' + Longitude + ', ' + Altitude
		Seconds = int(UTC[0:2]) * 3600 + int(UTC[3:5]) * 60 + int(UTC[6:8])
		
		if Altitude <> '':
			Latitude = float(Latitude)
			Longitude = float(Longitude)
			Altitude = float(Altitude)
			
			if Seconds < PreviousSeconds:
				PreviousSeconds = PreviousSeconds - 86400
			
			# Send now ?
			if Altitude <= MaxGSMAltitude:
				# Low enough
				Send = False
				if Seconds > (PreviousSeconds + SendTimeout * 60):
					Send = True
					print("Timeout")
					
				Distance = abs(CalculateDistance(Latitude, Longitude, PreviousLatitude, PreviousLongitude))
				if Distance >= HorizontalDelta:
					Send = True
					print "HorizontalDelta: " + str(Distance)
				
				if abs(Altitude - PreviousAltitude) >= VerticalDelta:
					Send = True
					print "VerticalDelta: " + str(abs(Altitude - PreviousAltitude))
						
				if Send:
					PreviousSeconds = Seconds
					PreviousAltitude = Altitude
					PreviousLatitude = Latitude
					PreviousLongitude = Longitude
			
					if Started:
						# Text to my mobile
						Message = 'Position: ' + UTC + ', ' + str(Latitude) + ', ' + str(Longitude) + ', ' + str(int(Altitude)) + ' http://maps.google.com/?q=' + str(Latitude) + ',' + str(Longitude)
						print "Sending to mobile " + MobileNumber + ": " + Message
						gsm.send_sms(MobileNumber, Message)
					else:
						print "Sending position not activated."
					
	time.sleep(LoopDelay)
