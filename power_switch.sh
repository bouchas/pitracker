#!/bin/bash
gpio mode 7 output
gpio write 7 0
sleep 1
gpio write 7 1
gpio mode 7 input
sleep 5
