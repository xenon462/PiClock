#!/usr/bin/python3
# coding: utf8 #

import subprocess  # for command execution

def turn_on_monitor(display=":0.0", output="HDMI-1", mode="1280x800 --rate 60"):
    try:
        command = f"DISPLAY={display} xrandr --output {output} --mode {mode}"
        subprocess.call(command, shell=True)
        print(f"Monitor {output} turned on successfully on display {display}.")
    except Exception as e:
        print(f"An error occurred: {e}")

turn_on_monitor()