#!/usr/bin/python3

import time
from rpi_ws281x import PixelStrip, Color

import datetime

LED_COUNT = 34        # Number of LED pixels.
LED_PIN = 13          # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 1       # set to '1' for GPIOs 13, 19, 41, 45 or 53

import subprocess
proc = subprocess.Popen(["pkill", "-f", "/home/pi/PiClock/Leds/rainbow.py"], stdout=subprocess.PIPE)
proc.wait()

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()


def WhiteDawn(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()


while True:
#    print(datetime.datetime.now())
#    time1 = datetime.datetime.now()
    for i in range(255):
        WhiteDawn(strip, Color(i, i, i))
        time.sleep(4)                    # 17 min
    WhiteDawn(strip, Color(0, 0, 0))
#    print(datetime.datetime.now())
#    time2 = datetime.datetime.now()
#    print("TIME==", time2 - time1)
    quit()