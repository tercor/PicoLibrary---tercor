"""
# Calendar.py
# Gives an Administrator automatic availability based on the current time.
"""

import time
from Employee import AVAILABLE
from Log import *


class Calendar:
    def __init__(self, schedule=None):
        """
        schedule is a list of (start, end, availability) tuples using 24h "HH:MM"
        strings, e.g. [("09:00", "10:30", BUSY)].
        Outside every entry, the administrator is Available.
        """
        self._availability = AVAILABLE
        self._schedule = schedule if schedule else []

    def getAvailability(self):
        t = time.localtime()
        now = "%02d:%02d" % (t[3], t[4])
        status = AVAILABLE
        for (start, end, entryStatus) in self._schedule:
            if start <= now < end:
                status = entryStatus
                break
        self._availability = status
        return status
