"""
# main.py
# Entry point for the satisfaction kiosk on the Raspberry Pi Pico.
# Save this file to the Pico as main.py so it runs automatically on power-up.
"""

from Log import *
from FeedbackController import FeedbackController

# Log verbosity: ALL/INFO prints everything (useful while testing, but slows
# the LCD and button response a bit). Use WARN or ERROR for normal operation.
Log.level = ERROR
Log.name = 'Kiosk'

controller = None

try:
    controller = FeedbackController()
    controller.run()
except KeyboardInterrupt:
    # Ctrl+C in Thonny: stop cleanly (silences buzzer, turns off lights, clears LCD)
    pass
except Exception as e:
    # Always report unexpected errors, even at a quiet log level
    Log.e(f"Fatal error: {e}")
    raise
finally:
    if controller is not None:
        controller.stop()
