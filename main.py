"""
# main.py - wires the NamePlate system together and runs it.
# Pins: LCD I2C on GP0 (SDA) / GP1 (SCL), LED ring on GP2, buzzer on GP16,
# buttons on GP13 (green), GP14 (blue), GP15 (yellow).
"""

import sys
import time
from Log import *
from Displays import LCDDisplay
from Button import Button
from Buzzer import PassiveBuzzer
from LightStrip import LightStrip
from Employee import Administrator, Faculty, Staff, StudentWorker, AWAY, BUSY
from NamePlate import NamePlate
from NamePlateController import NamePlateController

Log.level = WARN          # the device classes log every action - keep the console quiet

PAGE_INTERVAL_MS = 3000   # how often the display moves to the next page

# The Pico's clock starts at midnight each boot. To make the administrator's
# calendar match real time, set it, e.g.:
#   from machine import RTC
#   RTC().datetime((2026, 11, 6, 4, 9, 0, 0, 0))   # (year, month, day, weekday, h, m, s, subsec)


def main():
    employees = [
        Faculty("Dr. Ada Lovelace", "Professor", "Computer Sci", "alovelace@uni.edu", "555-0101",
                ["CS 101", "CS 340"], "Tue/Thu 2-4pm"),
        Staff("Sam Rivera", "Office Manager", "Dean's Office", "srivera@uni.edu", "555-0102"),
        StudentWorker("Jo Chen", "Lab Assistant", "Computer Sci", "jchen@uni.edu", "555-0103"),
        Administrator("Dr. Pat Morgan", "Dean", "Dean's Office", "pmorgan@uni.edu", "555-0100",
                      [("09:00", "10:30", BUSY),
                       ("12:00", "13:00", AWAY),
                       ("14:00", "15:30", BUSY)]),
    ]

    print("NamePlate: starting devices")
    display = LCDDisplay(sda=0, scl=1)
    buzzer = PassiveBuzzer(16, "NavBuzzer")
    strip = LightStrip(pin=2, name="Status", numleds=8, brightness=0.3)
    buttons = [
        Button(13, NamePlateController.NEXT),          # green button, GP13
        Button(14, NamePlateController.PREVIOUS),      # blue button, GP14
        Button(15, NamePlateController.AVAILABILITY),  # yellow button, GP15
    ]

    plate = NamePlate(display)
    controller = NamePlateController(employees, plate, buzzer, strip, buttons)
    print("NamePlate: running")

    lastTick = time.ticks_ms()
    try:
        while True:
            if controller.update():
                lastTick = time.ticks_ms()      # new person: give page 1 a full interval
            if time.ticks_diff(time.ticks_ms(), lastTick) >= PAGE_INTERVAL_MS:
                lastTick = time.ticks_ms()
                plate.onTimerTick()
            time.sleep_ms(20)
    except KeyboardInterrupt:
        pass
    finally:
        for b in buttons:
            b.setHandler(None)
        strip.off()
        display.clear()


try:
    main()
except Exception as e:
    print("NamePlate: ERROR")
    sys.print_exception(e)
