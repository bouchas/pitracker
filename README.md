# pitracker

## To start the tracker docker image
docker run -d --privileged --device=/dev/ttyS0:/dev/ttyS0 -e MOBILE_NUMBER='+1xxxyyyzzzz' -e MODEM_PORT='/dev/ttyS0' --restart unless-stopped bouchas/pitracker:latest

## To debug
minicom -b 115200 -D /dev/ttyS0
