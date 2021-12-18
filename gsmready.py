from pygsm import GsmModem

modem = GsmModem(port="/dev/ttyS0")
modem.boot()
reply = modem.command("AT")
print reply
