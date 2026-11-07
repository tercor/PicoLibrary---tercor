"""
# Employee.py
# The model: Employee and its subclasses Administrator, Faculty, StudentWorker and Staff.
# Subclasses override getDisplayPages() (and Administrator also overrides
# getAvailability()) - this is the polymorphism.
#
# A "display page" is a tuple (line1, line2). The NamePlate cuts each line to
# the 16 characters the LCD can show.
"""

from Log import *

# Availability states (shared by Employee, Calendar and the controller)
AVAILABLE = "Available"
AWAY = "Away"
BUSY = "Busy"
AVAILABILITY_STATES = (AVAILABLE, AWAY, BUSY)   # the order used when cycling


class Employee:
    def __init__(self, name, position, department, email, phoneNumber):
        self.name = name
        self.position = position
        self.department = department
        self.email = email
        self.phoneNumber = phoneNumber
        self._availability = AVAILABLE

    def getAvailability(self):
        return self._availability

    def setAvailability(self, availability):
        if availability not in AVAILABILITY_STATES:
            raise ValueError("Invalid availability: " + str(availability))
        self._availability = availability

    def cycleAvailability(self):
        i = AVAILABILITY_STATES.index(self._availability)
        self._availability = AVAILABILITY_STATES[(i + 1) % len(AVAILABILITY_STATES)]
        Log.i(f"{self.name} availability is now {self._availability}")

    def getDisplayPages(self):
        """ Default pages. Subclasses override to show different information. """
        return [
            (self.name, self.position),
            (self.department, self.phoneNumber),
            (self.email, ""),
        ]


class Administrator(Employee):
    """
    Availability comes automatically from a Calendar (composition: the
    Administrator creates and owns its Calendar).
    """

    def __init__(self, name, position, department, email, phoneNumber, schedule=None):
        super().__init__(name, position, department, email, phoneNumber)
        from Calendar import Calendar   # imported here because Calendar itself imports from Employee
        self._calendar = Calendar(schedule)

    def getAvailability(self):
        # Automatic - ignores whatever a button press may have stored
        return self._calendar.getAvailability()

    def getDisplayPages(self):
        pages = super().getDisplayPages()
        pages.append(("Calendar status:", self.getAvailability()))
        return pages


class Faculty(Employee):
    """ Adds the courses being taught and office hours. """

    def __init__(self, name, position, department, email, phoneNumber, courses, officeHours):
        super().__init__(name, position, department, email, phoneNumber)
        self._courses = courses
        self._officeHours = officeHours

    def getDisplayPages(self):
        pages = super().getDisplayPages()
        for course in self._courses:
            pages.append(("Teaching:", course))
        pages.append(("Office hours:", self._officeHours))
        return pages


class StudentWorker(Employee):
    """ Compact pages, and no email address shown. """

    def getDisplayPages(self):
        return [
            (self.name, "Student Worker"),
            (self.position, self.department),
            ("Phone:", self.phoneNumber),
        ]


class Staff(Employee):
    """ Staff pages show the role, department, phone and email. """

    def getDisplayPages(self):
        return [
            (self.name, "Staff"),
            (self.position, self.department),
            ("Phone:", self.phoneNumber),
            (self.email, ""),
        ]
