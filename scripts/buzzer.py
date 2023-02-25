#!/usr/bin/env python3
#on GPIO26 for sound
from RPi import GPIO
from time import sleep
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)
GPIO.output(26, True)
sleep(0.2)
GPIO.output(26, False)
GPIO.cleanup()
