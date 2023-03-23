#!/usr/bin/python3
from time import sleep
from RPi import GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)
GPIO.output(26, True)
sleep(0.1)
GPIO.output(26, False)
GPIO.cleanup()

import os, sys
sys.path.append('/home/pi/PiClock/Clock')
from Config import noaastream
os.popen("sudo mpg123 -q " + noaastream)
os.popen("killall -9 -q mpg123")
sys.exit()

# sudo systemctl stop bt_speaker && \

# sudo mpg123 -q http://www.meteonova.ru/speech/forecast_22113_0.mp3")
# && \
#    sudo systemctl start bt_speaker
# ")