"""
# MysteryGadget.py
# A simulated engine: LCD shows RPM/speed, buzzer hums, light strip is a tach,
# and a potentiometer acts as the throttle.
#
# Expects:
#   display  - LCDDisplay (Displays.py)      uses showText(), clear()
#   buzzer   - object with play(freq) and stop()   (Buzzer below is a simple one)
#   strip    - LightStrip (LightStrip.py)    uses setColor(), off()
#   pot      - AnalogSensor (Sensors.py)     uses rawValue() -> 0..65535
"""

import time
from machine import Pin, PWM
from Log import *
from Buzzer import *

class MysteryGadget:
    IDLE_RPM = 800
    MAX_RPM = 7000
    MAX_SPEED = 220          # km/h at MAX_RPM
    LOW_FREQ = 60            # Hz buzzer at idle
    HIGH_FREQ = 300          # Hz buzzer at max RPM
    ADC_MAX = 65535

    GREEN = (0, 255, 0)
    YELLOW = (255, 160, 0)
    RED = (255, 0, 0)

    def __init__(self, display, buzzer, strip, potentiometer, numleds=None):
        self._display = display
        self._buzzer = buzzer
        self._strip = strip
        self._pot = potentiometer
        # LightStrip keeps its LED count private; fall back to 8 if not found
        self._numleds = numleds or getattr(strip, '_numleds', 8)
        self._rpm = 0.0
        self._running = False
        self._last_text = ("", "")

    # ------------------------------------------------------------------ public
    def start(self):
        """ Simulate an engine start: crank, catch, settle to idle. """
        if self._running:
            return
        Log.i("MysteryGadget: starting engine")
        self._display.clear()
        self._show("Starting...", "")

        # Cranking: stuttering low growl
        for _ in range(6):
            self._buzzer.play(self.LOW_FREQ - 20)
            time.sleep(0.12)
            self._buzzer.stop()
            time.sleep(0.06)

        # Engine catches and revs up to idle
        self._running = True
        steps = 15
        for i in range(1, steps + 1):
            self._rpm = self.IDLE_RPM * i / steps
            self._update_outputs()
            time.sleep(0.05)
        self._rpm = float(self.IDLE_RPM)
        self._update_outputs()

    def stop(self):
        """ Stop the engine: silence, dark strip, 'Engine stopped' on LCD. """
        Log.i("MysteryGadget: stopping engine")
        self._running = False   # lets a running control() loop exit
        self._rpm = 0.0
        self._buzzer.stop()
        self._strip.off()
        self._display.clear()
        self._last_text = ("", "")
        self._show("Engine stopped", "")

    def control(self, duration=None, interval=0.1):
        """
        Read the potentiometer and drive RPM from it until stop() is called,
        `duration` seconds pass (if given), or Ctrl-C is pressed.
        Pot fully counter-clockwise = idle, fully clockwise = redline.
        """
        if not self._running:
            Log.e("MysteryGadget: control() called but engine is not running")
            return
        began = time.ticks_ms()
        try:
            while self._running:
                if duration is not None and time.ticks_diff(time.ticks_ms(), began) > duration * 1000:
                    break
                self._step()
                time.sleep(interval)
        except KeyboardInterrupt:
            Log.i("MysteryGadget: control interrupted")

    # ----------------------------------------------------------------- private
    def _step(self):
        """ One control iteration: read pot, ease RPM toward target, update outputs. """
        raw = self._pot.rawValue()
        target = self.IDLE_RPM + (raw / self.ADC_MAX) * (self.MAX_RPM - self.IDLE_RPM)
        # Engine inertia: move 25% of the way toward the target each step
        self._rpm += (target - self._rpm) * 0.25
        self._update_outputs()

    def _speed(self):
        frac = (self._rpm - self.IDLE_RPM) / (self.MAX_RPM - self.IDLE_RPM)
        return int(max(0.0, frac) * self.MAX_SPEED)

    def _update_outputs(self):
        frac = min(max(self._rpm / self.MAX_RPM, 0.0), 1.0)

        # Buzzer pitch rises with RPM
        self._buzzer.play(int(self.LOW_FREQ + frac * (self.HIGH_FREQ - self.LOW_FREQ)))

        # Light strip tachometer: more LEDs and hotter color with RPM
        lit = max(1, round(frac * self._numleds))
        color = self.GREEN if frac < 0.6 else (self.YELLOW if frac < 0.85 else self.RED)
        self._strip.setColor(color, lit)

        # LCD
        self._show(f"RPM: {int(self._rpm)}", f"Speed: {self._speed()} km/h")

    def _show(self, line0, line1):
        """ Write two 16-char padded lines; skip the write if nothing changed. """
        text = (f"{line0:<16}"[:16], f"{line1:<16}"[:16])
        if text[0] != self._last_text[0]:
            self._display.showText(text[0], 0, 0)
        if text[1] != self._last_text[1]:
            self._display.showText(text[1], 1, 0)
        self._last_text = text


if __name__ == "__main__":
    from Displays import LCDDisplay
    from LightStrip import LightStrip
    from Sensors import AnalogSensor

    gadget = MysteryGadget(
        LCDDisplay(sda=0, scl=1),
        PassiveBuzzer(16),
        LightStrip(pin=2, numleds=8, brightness=0.3),
        AnalogSensor(pin=26, name='Throttle'),
    )
    gadget.start()
    gadget.control(duration=20)   # turn the pot!
    gadget.stop()
