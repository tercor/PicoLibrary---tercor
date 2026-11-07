"""
# NamePlateController.py
# The controller. Receives the three buttons, manages the employee list,
# and drives the NamePlate (LCD), PassiveBuzzer (sound) and LightStrip (status).
#
# Button callbacks arrive in interrupt context, so buttonPressed() only records
# the request. The real work happens when the main loop calls update().
"""

from ButtonHandler import ButtonHandler
from Employee import AVAILABLE, AWAY
from Lights import GREEN, YELLOW, RED
from Log import *

# LightStrip color for each availability (Teams-style); anything else (Busy) is red
_COLORS = {AVAILABLE: GREEN, AWAY: YELLOW}


class NamePlateController(ButtonHandler):
    NEXT = "next"
    PREVIOUS = "previous"
    AVAILABILITY = "availability"

    def __init__(self, employees, view, buzzer, strip, buttons):
        """
        employees: list of Employee
        view: NamePlate
        buzzer: PassiveBuzzer
        strip: LightStrip
        buttons: the three Buttons, named NEXT, PREVIOUS and AVAILABILITY
        """
        if not employees:
            raise ValueError("NamePlateController needs at least one employee")
        self._employees = employees
        self._currentEmployeeIndex = 0
        self._view = view
        self._buzzer = buzzer
        self._strip = strip
        self._buttons = buttons
        self._pending = {self.NEXT: False, self.PREVIOUS: False, self.AVAILABILITY: False}
        self._lastAvailability = None
        for button in self._buttons:
            button.setHandler(self)
        self._updateDisplay()

    # ---- ButtonHandler interface (may run in interrupt context) ----
    def buttonPressed(self, name):
        if name in self._pending:
            self._pending[name] = True

    def buttonReleased(self, name):
        pass

    # ---- Called from the main loop ----
    def update(self):
        """ Process pending button presses. Returns True if the person changed pages/employee. """
        changed = False
        if self._pending[self.NEXT]:
            self._pending[self.NEXT] = False
            self._nextEmployee()
            changed = True
        if self._pending[self.PREVIOUS]:
            self._pending[self.PREVIOUS] = False
            self._previousEmployee()
            changed = True
        if self._pending[self.AVAILABILITY]:
            self._pending[self.AVAILABILITY] = False
            self._cycleAvailability()
        # Administrator availability changes by itself (calendar), so keep the strip current
        self._updateLight()
        return changed

    # ---- Private ----
    def _nextEmployee(self):
        self._currentEmployeeIndex = (self._currentEmployeeIndex + 1) % len(self._employees)
        self._updateDisplay()
        self._view.playNavigationSound(self._buzzer)

    def _previousEmployee(self):
        self._currentEmployeeIndex = (self._currentEmployeeIndex - 1) % len(self._employees)
        self._updateDisplay()
        self._view.playNavigationSound(self._buzzer)

    def _cycleAvailability(self):
        employee = self._employees[self._currentEmployeeIndex]
        employee.cycleAvailability()   # Administrator ignores this: its availability is automatic
        self._updateLight()
        self._view.showAvailability(employee.getAvailability())

    def _updateDisplay(self):
        employee = self._employees[self._currentEmployeeIndex]
        self._view.showEmployee(employee)
        self._lastAvailability = None   # force the strip to refresh for the new person
        self._updateLight()

    def _updateLight(self):
        availability = self._employees[self._currentEmployeeIndex].getAvailability()
        if availability != self._lastAvailability:
            self._lastAvailability = availability
            self._strip.setColor(_COLORS.get(availability, RED))
