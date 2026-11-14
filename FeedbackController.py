"""
A basic template file for using the Model class in PicoLibrary
This will allow you to implement simple Statemodels with some basic
event-based transitions.

Satisfaction kiosk - hardware:
  Buzzer (passive) GP16     Green button GP13     Red button GP14
  Ultrasonic       TRIG GP12, ECHO GP11
  LED ring (8)     GP2      LCD 16x2 (I2C)        SDA GP0, SCL GP1

States (see state chart):
  0 Welcome   1 Selection   2 Happy   3 Unhappy   4 Alarm   5 Summary
"""

# Import whatever Library classes you need - StateModel is obviously needed
# Counters imported for Timer functionality, Button imported for button events
import time
from Log import *
from StateModel import *
from Counters import *

## You may want to remove any module you do not need from the imports below
from Button import *
from Lights import *
from LightStrip import LightStrip
from Sensors_advanced import UltrasonicSensor
from Displays import LCDDisplay
from Buzzer import PassiveBuzzer, tones, DO, MI, SO, DO2
from FeedbackStats import FeedbackStats

# ---------------------------------------------------------------- settings
NUM_LEDS = 8                # LEDs on the light ring
DETECT_CM = 10.0            # visitor detected closer than this
TIMEOUT_SEC = 5             # idle timeout for states 1, 2 and 3
START_PERCENT = 70.0        # rating at start-up / after a reset (top of the yellow range)
START_WEIGHT = 1.0          # how many responses' worth of influence the starting rating has.
                            # 1 = two red presses in a row trigger the alarm; 0 = a single
                            # red press does; higher = more red presses are needed
ALARM_TONE_MS = 300         # length of each of the two alarm tones
ALARM_TONES = (tones['A5'], tones['E5'])

# Melodies are lists of (frequency, duration in ms)
HAPPY_MELODY = [(DO, 120), (MI, 120), (SO, 120), (DO2, 250)]
SAD_MELODY = [(tones['E4'], 200), (tones['C4'], 200), (tones['G3'], 400)]


class KioskUltrasonicSensor(UltrasonicSensor):
    """
    UltrasonicSensor.distance() returns -1 when the echo times out, and the
    library's tripped() treats -1 as 'closer than the threshold', which would
    create phantom visitors. This subclass ignores failed readings.
    """

    def tripped(self) -> bool:
        v = self.rawValue()
        if v <= 0:
            return False
        if self._lowActive:
            return v < self._threshold
        return v > self._threshold


"""
This is the template for a Controller - you should rename this class to something
that is supported by your class diagram. This should associate with your other
classes, and any PicoLibrary classes. If you are using Buttons, you will implement
buttonPressed and buttonReleased.

To implement the state model, you will need to implement __init__ and 4 other methods
to support model start, stop, entry actions, exit actions, and state actions.

The following methods must be implemented:
__init__: create instances of your View and Business model classes, create an instance
of the StateModel with the necessary number of states and add the transitions, buttons
and timers that the StateModel needs

stateEntered(self, state, event) - Entry actions
stateLeft(self, state, event) - Exit actions
stateDo(self, state) - do Activities

# A couple other methods are available - but they can be left alone for most purposes

run(self) - runs the State Model - this will start at State 0 and drive the state model
stop(self) - stops the State Model - will stop processing events and stop the timers

This controller implements the satisfaction kiosk: a visitor approaching the
ultrasonic sensor is asked to rate their visit with the green (happy) or red
(unhappy) button. The feedback is tracked by FeedbackStats and shown on the LCD
and the light strip. If the feedback falls too low, an alarm is raised for the
manager.
"""

class FeedbackController:

    def __init__(self):
        
        # STEP 1.
        # Instantiate whatever classes from your own model that you need to control
        # Handlers can now be set to None - we will add them to the model and it will
        # do the handling
        
        # ...
        self._stats = FeedbackStats(red_threshold=30.0, green_threshold=70.0,
                                    start_percent=START_PERCENT, start_weight=START_WEIGHT)
        self._lightstrip = LightStrip(pin=2, name='Lightring', numleds=NUM_LEDS, brightness=0.5)
        self._display = LCDDisplay(sda=0, scl=1)
        self._buzzer = PassiveBuzzer(16, "Buzzer")
        self.update_light_strip()       # show the starting rating (yellow)

        # Instantiate a Model. Needs to have the number of states, self as the handler
        # You can also say debug=True to see some of the transitions on the screen
        # Here is a sample for a model with 4 states
        self._model = StateModel(6, self, debug=True)
        
        # Instantiate any Buttons that you want to process events from and add
        # them to the model
        self._button = Button(13, "green", handler=None)        
        self._model.addButton(self._button)
        
        # add other buttons if needed. Note that button names must be distinct
        # for all buttons. Events will come back with [buttonname]_press and
        # [buttonname]_release

        # ...
        self._redbutton = Button(14, "red", handler=None)
        self._model.addButton(self._redbutton)
        
        # Instantiate any sensor you need to process their trip/untrip events from
        # Events from sensors come back as sensorname_trip and sensorname_untrip

        self._uss = KioskUltrasonicSensor(trigger=12, echo=11, name='uss',
                                          lowActive=True, threshold=DETECT_CM)
        self._model.addSensor(self._uss)

        # Add any timer you have. Multiple timers may be added but they must all
        # have distinct names. Events come back as [timername}_timeout
        self._timer = SoftwareTimer(name="timer", handler=None)
        self._model.addTimer(self._timer)

        # Add any custom events as appropriate for your state model. e.g.
        # self._model.addCustomEvent("collision_detected")
        self._model.addCustomEvent("feedback_below_threshold")
        
        # Now add all the transitions from your state model. Any custom events
        # must be defined above first. You can have a state transition to another
        # state based on multiple events - which is why the eventlist is an array
        # Syntax: self._model.addTransition( SOURCESTATE, [eventlist], DESTSTATE)
        
        # transitions from the state chart:
        self._model.addTransition(0, ["uss_trip"], 1)
        self._model.addTransition(1, ["timer_timeout"], 0)
        self._model.addTransition(1, ["green_press"], 2)
        self._model.addTransition(1, ["red_press"], 3)
        self._model.addTransition(2, ["timer_timeout"], 0)
        self._model.addTransition(3, ["timer_timeout"], 0)
        self._model.addTransition(3, ["feedback_below_threshold"], 4)
        self._model.addTransition(4, ["green_press"], 5)
        self._model.addTransition(5, ["red_press"], 0)

        # etc.

        # Internal bookkeeping for the non-blocking sounds and the state timing
        self._melody = None
        self._note_index = 0
        self._note_end = 0
        self._alarm_next = None
        self._alarm_high = False
    
    def stateEntered(self, state, event):
        """
        stateEntered - is the handler for performing entry actions
        You get the state number of the state that just entered
        Make sure actions here are quick
        """
        
        # If statements to do whatever entry/actions you need for
        # for states that have entry actions
        Log.d(f'State {state} entered on event {event}')

        if state == 0:
            # entry actions for state 0
            self.display_feedback_status("Welcome to IKEA", "")
        
        elif state == 1:
            # entry actions for state 1
            self.handle_motion_detected()

        elif state == 2:
            # entry actions for state 2
            self.handle_green_button_pressed()

        elif state == 3:
            # entry actions for state 3
            self.handle_red_button_pressed()

        elif state == 4:
            # entry actions for state 4 (the alarm sound is a do/action)
            self.display_feedback_status("Calling manager", "")

        elif state == 5:
            # entry actions for state 5
            self.show_summary()
            
    def stateLeft(self, state, event):
        """
        stateLeft - is the handler for performing exit/actions
        You get the state number of the state that just entered
        Make sure actions here are quick
        
        This is just like stateEntered, perform only exit/actions here
        """

        Log.d(f'State {state} exited on event {event}')
        if state in (1, 2, 3):
            # exit actions for states 1, 2 and 3 - make sure no stale timeout comes later
            self._timer.cancel()
        if state in (2, 3):
            self._stop_melody()
        if state == 4:
            # exit actions for state 4
            self.stop_alarm()
        if state == 5:
            # exit actions for state 5 - reset statistics and lights
            self.handle_manager_button_pressed()
        # etc.
    
    def stateEvent(self, state, event)->bool:
        """
        stateEvent - handler for performing actions for a specific event
        without leaving the current state. 
        Note that transitions take precedence over state events, so if you
        have a transition as well as an in-state action for the same event,
        the in-state action will never be called.

        This handler must return True if the event was processed, otherwise
        must return False.
        """
        
        # Recommend using the debug statement below ONLY if necessary - may
        # generate a lot of useless debug information.
        # Log.d(f'State {state} received event {event}')
        
        # The kiosk has no in-state events: anything that does not cause a
        # transition (for example a button press while in state 2) is ignored.
        # Note the return False if none of the conditions are met
        return False

    def stateDo(self, state):
        """
        stateDo - the method that handles the do/actions for each state
        """

        # Keep any melody that is playing moving along (never blocks)
        self._update_sound()
        
        # Now if you want to do different things for each state that has do actions
        if state == 0:
            # State 0 do/actions
            pass
        elif state == 1:
            pass
        elif state == 2:
            pass
        elif state == 3:
            # Has the feedback just dropped below the threshold? If so this
            # fires feedback_below_threshold and we go straight to the alarm.
            self.evaluate_feedback_status()
        elif state == 4:

            # Remember you do not need to create a loop - the model takes care of that
            # For example, if you want a state to flash an LED, just turn it on and off
            # once, and the model will repeat it as long as you are in that state.
            self.activate_alarm()

    # ------------------------------------------------------------------
    # Methods from the class diagram
    # ------------------------------------------------------------------

    def handle_motion_detected(self):
        """ Entry of state 1: prompt the visitor and start the 5 second timer """

        self.display_feedback_status("How was your", "visit?")
        self._timer.start(TIMEOUT_SEC)

    def handle_green_button_pressed(self):
        """ Entry of state 2: record positive feedback """

        self._stats.add_happy()
        self.update_light_strip()
        self.display_feedback_status("Thank you!")
        self._start_melody(HAPPY_MELODY)
        self._timer.start(TIMEOUT_SEC)

    def handle_red_button_pressed(self):
        """ Entry of state 3: record negative feedback """

        self._stats.add_unhappy()
        self.update_light_strip()
        self._timer.start(TIMEOUT_SEC)
        if self._stats.get_light_level() == "red":
            # This press took the rating below the threshold: don't spend time on the
            # 'sorry' message and tone. stateDo(3) will fire feedback_below_threshold
            # on its next pass and we go straight to the alarm state.
            return
        pct = int(self._stats.calculate_percentage() + 0.5)
        self.display_feedback_status("Sorry to hear", f"that. Rating:{pct}%")
        self._start_melody(SAD_MELODY)

    def handle_manager_button_pressed(self):
        """
        Exit of state 5: the manager pressed the red button after reading
        the summary, so reset the statistics and the lights (the rating goes
        back to its starting value, so the strip shows that again).
        """

        self._stats.reset()
        self.update_light_strip()

    def evaluate_feedback_status(self):
        """
        Check the feedback; if the percentage is below the red threshold,
        fire the custom event (state 3 -> state 4).
        """

        if self._stats.get_light_level() == "red":
            self._model.processEvent("feedback_below_threshold")

    def display_feedback_status(self, line0, line1=None):
        """
        Show two lines of text on the 16x2 LCD. If line1 is not given, the
        current satisfaction rating is shown on the second line.
        """

        if line1 is None:
            line1 = f"Rating: {int(self._stats.calculate_percentage() + 0.5)}%"
        self._display.reset()
        self._display.showText(line0[:16], 0, 0)
        if line1:
            self._display.showText(line1[:16], 1, 0)

    def activate_alarm(self):
        """
        One step of the 2-tone alarm - called from stateDo(4) so it repeats
        for as long as we are in the alarm state. Never blocks.
        """

        now = time.ticks_ms()
        if self._alarm_next is None or time.ticks_diff(now, self._alarm_next) >= 0:
            self._alarm_high = not self._alarm_high
            self._buzzer.play(ALARM_TONES[0] if self._alarm_high else ALARM_TONES[1])
            self._alarm_next = time.ticks_add(now, ALARM_TONE_MS)

    def stop_alarm(self):
        """ Silence the alarm """

        self._alarm_next = None
        self._alarm_high = False
        self._buzzer.stop()

    def update_light_strip(self):
        """
        Color = level (red / yellow / green), number of lit LEDs is
        proportional to the percentage (100% = all lit, at least 1 lit).
        """

        level = self._stats.get_light_level()
        if level == "red":
            color = RED
        elif level == "yellow":
            color = YELLOW
        else:
            color = GREEN

        pct = self._stats.calculate_percentage()
        lit = int(pct / 100 * NUM_LEDS + 0.5)
        lit = max(1, min(NUM_LEDS, lit))
        self._lightstrip.setColor(color, lit)

    def show_summary(self):
        """ Entry of state 5: show happy and unhappy counts """

        self.display_feedback_status(f"Happy: {self._stats.get_happy_count()}",
                                     f"Unhappy: {self._stats.get_unhappy_count()}")

    # ------------------------------------------------------------------
    # Non-blocking sound helpers (Buzzer.beep() would block the model loop)
    # ------------------------------------------------------------------

    def _start_melody(self, notes):
        self._melody = notes
        self._note_index = 0
        self._play_current_note()

    def _play_current_note(self):
        freq, ms = self._melody[self._note_index]
        self._buzzer.play(freq)
        self._note_end = time.ticks_add(time.ticks_ms(), ms)

    def _update_sound(self):
        """ Advance the current melody (if any); called every stateDo """

        if self._melody is None:
            return
        if time.ticks_diff(time.ticks_ms(), self._note_end) >= 0:
            self._note_index += 1
            if self._note_index >= len(self._melody):
                self._melody = None
                self._buzzer.stop()
            else:
                self._play_current_note()

    def _stop_melody(self):
        if self._melody is not None:
            self._melody = None
            self._buzzer.stop()

    def run(self):
        """
        Create a run() method - you can call it anything you want really, but
        this is what you will need to call from main.py or someplace to start
        the state model.
        """
        
        # The run method should simply do any initializations (if needed)
        # and then call the model's run method.
        # You can send a delay as a parameter if you want something other
        # than the default 0.1s. e.g.,  self._model.run(0.25)
        # (0.05s here so the tones switch on time)
        self._model.run(0.05)

    def stop(self):
        # The stop method should simply do any cleanup as needed
        # and then call the model's stop method.
        # This removes the button's handlers but will need to see
        # if the IRQ handlers should also be removed
        self._model.stop()
        self._stop_melody()
        self.stop_alarm()
        self._lightstrip.setColor(BLACK)
        self._display.reset()
        

# Test your model. Note that this only runs the template class above
# If you are using a separate main.py or other control script,
# you will run your model from there.
if __name__ == '__main__':
    p = FeedbackController()
    try:
        p.run()
    except KeyboardInterrupt:
        p.stop()    
