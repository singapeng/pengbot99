# Python imports
from datetime import datetime, timedelta, timezone
import unittest

# Local import
from pengbot99 import utils
from pengbot99 import schedule


class TestSchedule(unittest.TestCase):
    """ Test when the Grand Prix rotation doesn't fit nicely within a day/week
    """
    GPS = ['ace', 'knight', 'mknight', 'queen', 'mqueen', 'king', 'mking']

    def create_manager(self):
        """ Utility returning a built-up Slot 2 schedule manager
        """
        wdsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_anniversary')
        wesched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_weekend_anniversary')
        slot2mgr = schedule.Slot2ScheduleManager(self.origin, wdsched, wesched)
        return slot2mgr

    def setUp(self):
        # This .env file only needs CONFIG_PATH declared.
        # .env is covered by .gitignore to avoid secrets accidentally pushed to server
        env_path = "fixtures/.env"
        self.env = utils.load_env("fixtures/.env")
        self.origin = datetime(2024, 10, 2, 2, 0, 0, 0, tzinfo=timezone.utc)
        self.mgr = self.create_manager()

    def test_when_event(self):
        """ Ensure we properly calculate the rotation offset when the
            schedule changes from weekday to weekend and the rotation
            does not nicely fit in a 24-hours period.
        """
        we_start = datetime(2024,10,4,23,0, tzinfo=timezone.utc)
        evts = self.mgr.when_event(self.GPS, timestamp=we_start, count=5)
        self.assertEqual(evts[3].rotation_offset, 7)
        self.assertEqual(evts[4].rotation_offset, 8)

    def test_get_cycle_count_origin(self):
        res = self.mgr.get_cycle_count(self.origin)
        self.assertEqual(res, (0, 0))

    def test_get_cycle_count_before_weekend_start(self):
        bwe_start = datetime(2024,10,4,23,0, tzinfo=timezone.utc)
        res = self.mgr.get_cycle_count(bwe_start)
        self.assertEqual(res, (69, 0))

    def test_get_cycle_count_at_weekend_start(self):
        awe_start = datetime(2024,10,5, 0,0, tzinfo=timezone.utc)
        res = self.mgr.get_cycle_count(awe_start)
        self.assertEqual(res, (70, 0))


if __name__ == "__main__":
    unittest.main()