#!/usr/bin/env python3
from RPi import GPIO
from time import sleep
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)
GPIO.output(26, True)
sleep(0.2)
GPIO.output(26, False)
GPIO.cleanup()

import os
os.popen("sudo mpg123 -q http://www.meteonova.ru/speech/forecast_22113_1.mp3")

