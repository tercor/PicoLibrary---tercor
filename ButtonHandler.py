"""
# ButtonHandler.py
# The interface that Button calls back into (buttonPressed / buttonReleased).
"""


class ButtonHandler:
    """ <<Interface>> - implemented by NamePlateController """

    def buttonPressed(self, name):
        raise NotImplementedError

    def buttonReleased(self, name):
        raise NotImplementedError
