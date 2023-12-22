#!/usr/bin/python3
# coding: utf8 #

import subprocess  # for command execution

def turn_off_monitor(display=":0.0", output="HDMI-1"):
    try:
        command = f"DISPLAY={display} xrandr --output {output} --off"
        subprocess.call(command, shell=True)
        print(f"Monitor {output} turned off successfully on display {display}.")
    except Exception as e:
        print(f"An error occurred: {e}")

turn_off_monitor()