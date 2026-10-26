import time
time.sleep(0.1)  # Wait for USB to become ready

from Displays import LCDDisplay
from Buzzer import PassiveBuzzer
from LightStrip import LightStrip
from Sensors import AnalogSensor
from MysteryGadget import MysteryGadget

gadget = MysteryGadget(
    LCDDisplay(sda=0, scl=1),
    PassiveBuzzer(pin=16),
    LightStrip(pin=2, numleds=8, brightness=0.3),
    AnalogSensor(pin=26, name='Throttle'),
)

gadget.start()                 # start the engine
gadget.control(duration=10)    # turn the pot for about 10 seconds!
gadget.stop()                  # stop the engine
