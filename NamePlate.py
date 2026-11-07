"""
# NamePlate.py
# The view. Shows an employee's pages on the display, one page at a time.
"""

from Buzzer import DO2
from Log import *

LCD_WIDTH = 16


def _fit(text):
    """ Cut text to the LCD width and pad with spaces (MicroPython strings have no ljust) """
    text = str(text)[:LCD_WIDTH]
    return text + " " * (LCD_WIDTH - len(text))


class NamePlate:
    def __init__(self, display):
        """ display is an LCDDisplay (any Display with showText(text, row, col)) """
        self._display = display
        self._currentPages = []
        self._currentPageIndex = 0

    def showEmployee(self, employee):
        """ Start showing an employee, beginning with their first page """
        self._currentPages = employee.getDisplayPages()
        self._currentPageIndex = 0
        self._showPage()

    def showAvailability(self, availability):
        """ Show the availability on the second line (until the next page change) """
        self._display.showText(_fit("Now: " + str(availability)), 1, 0)

    def playNavigationSound(self, buzzer):
        """ Short chirp, played on the buzzer the controller hands us """
        buzzer.beep(DO2, 100)

    def onTimerTick(self):
        """ Called every few seconds - move to the next page of the current employee """
        if not self._currentPages:
            return
        self._currentPageIndex = (self._currentPageIndex + 1) % len(self._currentPages)
        self._showPage()

    def _showPage(self):
        if not self._currentPages:
            return
        page = self._currentPages[self._currentPageIndex]
        line1 = page[0] if len(page) > 0 else ""
        line2 = page[1] if len(page) > 1 else ""
        self._display.showText(_fit(line1), 0, 0)
        self._display.showText(_fit(line2), 1, 0)
