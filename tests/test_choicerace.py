# Python imports
from datetime import datetime, timedelta, timezone
import unittest

# Test support
from conftest import FIXTURES_DIR

# Local import
from pengbot99 import schedule
from pengbot99 import choicerace


class TestGlitchManager(unittest.TestCase):
    """ Test that we are correctly fetching glitch races as part of the 99 line-up.
        Check the case where when the glitch event is half-way through when the
        query is run, we don't get the next glitch by accident.
        This will ensure we don't have a regression for a bug reported by
        Gammaween, when Pengbot predicted Mystery_5 (BB+RC) instead of Mystery_4
        (Fire City)
    """
    def create_manager(self):
        """ Utility returning a built-up a 99 lineup manager aware of glitch 99 races.
        """
        # this schedule defines glitch 99 occurences
        r99sched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot1_schedule')
        # this is the 99 track selection, notwithstanding glitches
        nnsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'ninetynine_schedule')
        r99_offset = 25
        r99_origin = self.origin + timedelta(minutes=r99_offset)

        glitch_mgr = schedule.Slot1ScheduleManager(self.glitch_origin, r99sched)
        r99mgr = schedule.Slot1ScheduleManager(r99_origin, nnsched)
        return choicerace.FZ99Manager(r99mgr, glitch_mgr)

    def setUp(self):
        self.env = {"CONFIG_PATH": FIXTURES_DIR}
        self.origin = datetime(2025, 4, 23, 0, 0, 0, 0, tzinfo=timezone.utc)
        self.glitch_origin = datetime(2025, 12, 8, 22, 57, tzinfo=timezone.utc)
        self.mgr = self.create_manager()

    def test_correct_glitch_predicted(self):
        """ Ensure that if we run a query before the glitch start time, we are
            able to get the expected results.
            This test is mostly here as sanity check that we got the correct
            schedule lined up.
        """
        r99time = datetime(2026, 9, 8, 2, 20, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(r99time)
        self.assertEqual(evts[0].name, 'Big_Blue_II <> mMute_City_III')
        self.assertEqual(evts[2].name, 'Mystery_4 <> Port_Town_I')
        self.assertEqual(evts[3].name, 'Mystery_4 <> Red_Canyon_I')

    def test_correct_glitch_predicted_at_glitch_halfway(self):
        """ Ensure that if we run a query before the glitch start time, we are
            able to get the expected results.
            At this time, the glitch already ran for a minute, therefore we
            fetch events starting with the last minute of the glitch.
        """
        r99time = datetime(2026, 9, 8, 2, 23, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(r99time)
        self.assertEqual(evts[0].name, 'Mystery_4 <> Red_Canyon_I')


if __name__ == "__main__":
    unittest.main()