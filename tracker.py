import time
import math
import os
from pygsm import GsmModem

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
SMSLoop = 2             # Check SMS message every x seconds 

PreviousSeconds = 0
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

# If the send notification is active. You can start the notification by sending 'Start'
Started = False
SendStatus = True

print "Waiting for incoming messages..."

while True:
    # check for new messages
	message = modem.next_message()

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
			print "Stop sending Position."
			print
		elif text[0:6] == 'Status':
			SendStatus = True
			print "Sending current status."
			print

	# Get position
	reply = modem.command('AT+CGNSINF')
	# reply example: ['+CGNSINF: 1,1,20211218220507.000,45.398859,-73.482280,21.155,0.00,1.5,1,,0.9,1.3,1.0,,9,10,9,,35,,', 'OK']

	list = reply[0].split(",")
	if len(list[2]) > 14:
		UTC = list[2][0:4]+'-'+list[2][4:6]+'-'+list[2][6:8]+' '+list[2][8:10]+':'+list[2][10:12]+':'+list[2][12:14]
		Latitude = list[3]
		Longitude = list[4]
		Altitude = list[5]
		print 'Position: ' + UTC + ', ' + Latitude + ', ' + Longitude + ', ' + Altitude
		Seconds = int(UTC[11:13]) * 3600 + int(UTC[14:16]) * 60 + int(UTC[17:19])
		
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
					MsgTitle = "Timeout"
					print MsgTitle
					
				Distance = abs(CalculateDistance(Latitude, Longitude, PreviousLatitude, PreviousLongitude))
				if Distance >= HorizontalDelta:
					Send = True
					MsgTitle = "HorizontalDelta: " + str(Distance)
					print MsgTitle
				
				if abs(Altitude - PreviousAltitude) >= VerticalDelta:
					Send = True
					MsgTitle = "VerticalDelta: " + str(abs(Altitude - PreviousAltitude))
					print MsgTitle
				
				if SendStatus:
					Send = True
					MsgTitle = "Status"
						
				if Send:
					PreviousSeconds = Seconds
					PreviousAltitude = Altitude
					PreviousLatitude = Latitude
					PreviousLongitude = Longitude

					if Started or SendStatus:
						# Text to my mobile
						Message = MsgTitle + ',  ' + UTC + ', ' + str(Latitude) + ', ' + str(Longitude) + ', ' + str(int(Altitude)) + ' http://maps.google.com/?q=' + str(Latitude) + ',' + str(Longitude)
						print "Sending to mobile " + MobileNumber + ": " + Message
						modem.send_sms(MobileNumber, Message)
						SendStatus = False
					else:
						print "Sending position not activated."
					
	time.sleep(SMSLoop)
