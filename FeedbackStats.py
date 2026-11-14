"""
# FeedbackStats.py
# Business-model class for the satisfaction kiosk.
# Keeps track of happy (green button) and unhappy (red button) feedback
# counts and answers questions about them (percentage, light level).
"""

from Log import *


class FeedbackStats:
    """
    Tracks positive and negative feedback.

    The rating does not start at 0%. It starts at start_percent (default 70%,
    the highest value that is still 'yellow') and is pulled up or down by the
    real feedback. start_weight says how many responses' worth of influence that
    starting value has:
        start_weight = 1   -> the starting rating counts as one response (default)
        start_weight = 0   -> no starting influence: the first response decides
                              the rating (one red press = 0%)
        start_weight = 10  -> the starting rating takes many presses to move

    Light levels returned by get_light_level():
        "red"    - percentage is below red_threshold (default 30)
        "yellow" - percentage is between the two thresholds (inclusive)
        "green"  - percentage is above green_threshold (default 70)

    The happy/unhappy counts and the total only ever include real feedback.
    """

    def __init__(self, red_threshold=30.0, green_threshold=70.0,
                 start_percent=70.0, start_weight=1.0):
        Log.i("FeedbackStats: constructor")
        self._happy_count = 0
        self._unhappy_count = 0
        self._red_threshold = red_threshold
        self._green_threshold = green_threshold
        self._start_percent = start_percent
        self._start_weight = start_weight

    def get_total_count(self) -> int:
        """ Total number of real feedback responses """

        return self._happy_count + self._unhappy_count

    def get_light_level(self) -> str:
        """ "red", "yellow" or "green" based on the current percentage """

        pct = self.calculate_percentage()
        if pct < self._red_threshold:
            return "red"
        if pct > self._green_threshold:
            return "green"
        return "yellow"

    def calculate_percentage(self) -> float:
        """
        Current rating (0-100): the share of feedback that is positive, with the
        starting rating counted as start_weight responses.
        """

        weight = self.get_total_count() + self._start_weight
        if weight == 0:
            return self._start_percent
        happy = self._happy_count + self._start_weight * self._start_percent / 100.0
        return happy * 100.0 / weight

    def add_happy(self):
        """ Record one positive feedback """

        self._happy_count += 1
        Log.i(f"FeedbackStats: happy count is now {self._happy_count}")

    def add_unhappy(self):
        """ Record one negative feedback """

        self._unhappy_count += 1
        Log.i(f"FeedbackStats: unhappy count is now {self._unhappy_count}")

    def reset(self):
        """ Reset the statistics - the rating goes back to its starting value """

        Log.i("FeedbackStats: reset")
        self._happy_count = 0
        self._unhappy_count = 0

    def get_happy_count(self) -> int:
        return self._happy_count

    def get_unhappy_count(self) -> int:
        return self._unhappy_count


# Quick self-test - run this module directly
if __name__ == "__main__":
    def close(a, b):
        return abs(a - b) < 0.01

    # Default: starts at 70% (yellow), start_weight 1
    s = FeedbackStats()
    assert close(s.calculate_percentage(), 70.0) and s.get_light_level() == "yellow"
    assert s.get_total_count() == 0
    s.add_unhappy()                      # 0.7/2 = 35% -> still yellow
    assert close(s.calculate_percentage(), 35.0) and s.get_light_level() == "yellow"
    s.add_unhappy()                      # 0.7/3 = 23.3% -> red
    assert close(s.calculate_percentage(), 23.33) and s.get_light_level() == "red"
    assert s.get_total_count() == 2 and s.get_unhappy_count() == 2
    s.reset()
    assert close(s.calculate_percentage(), 70.0) and s.get_total_count() == 0

    s.add_happy()                        # 1.7/2 = 85% -> green
    assert close(s.calculate_percentage(), 85.0) and s.get_light_level() == "green"

    # start_weight 0: the first response decides
    s = FeedbackStats(start_weight=0)
    assert close(s.calculate_percentage(), 70.0)
    s.add_unhappy()
    assert close(s.calculate_percentage(), 0.0) and s.get_light_level() == "red"

    # start_weight 10: needs many presses to fall below 30%
    s = FeedbackStats(start_weight=10)
    presses = 0
    while s.get_light_level() != "red":
        s.add_unhappy()
        presses += 1
    assert presses == 14, presses

    print("FeedbackStats self-test passed")
