# Python imports
from datetime import datetime, timedelta, timezone
import unittest

# Local import
from pengbot99 import utils
from pengbot99 import schedule
from pengbot99 import miniprix


class TestMiniprixManagerMachineShuffle(unittest.TestCase):
    """ These test cases cover a scenario where the Miniprix occurs multiple times
        during the weekend rotation, as part of a single schedule.
        The relevant schedule is contained in 'slot2_schedule_weekend'.
        We test that the first miniprix in each of the first two schedule runs is
        iterating as expected.
        In the real event, mirror was disabled. Enabling it here to further test
        the mirror rotation.
    """
    def create_manager(self):
        """ Utility returning a built-up Miniprix Manager object.
        """
        wdsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule')
        wesched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_weekend')
        mpsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'miniprix_schedule')
        mirrorsc = schedule.load_schedule(self.env['CONFIG_PATH'], 'miniprix_mirroring_schedule')
        slot2mgr = schedule.Slot2ScheduleManager(self.origin, wdsched, wesched)

        mp_offset = 24
        mirror_offset=6
        mgr = miniprix.MiniPrixManager("miniprix", slot2mgr, mpsched, mirrorsc, mp_offset, mirror_offset)
        # force lineup offset to default 10 minutes
        mgr.mp_cycles = 10
        return mgr

    def setUp(self):
        # This .env file only needs CONFIG_PATH declared.
        # .env is covered by .gitignore to avoid secrets accidentally pushed to server
        env_path = "fixtures/.env"
        self.env = utils.load_env("fixtures/.env")
        self.origin = datetime(2024, 2, 6, 0, 0, 0, 0, tzinfo=timezone.utc)
        self.mgr = self.create_manager()

    def test_miniprix_weekend_selection1(self):
        mmstart = datetime(2024, 8, 24, 0, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.get_miniprix(mmstart)
        self.assertEqual(evts[0].name, "Big_Blue > mDeath_Wind_I > White_Land_I (MiniPrix025.3)")
        self.assertEqual(evts[0].start_time, datetime(2024, 8, 24, 0, 30, 0, 0, tzinfo=timezone.utc))

    def test_miniprix_weekend_selection2(self):
        mmstart = datetime(2024, 8, 24, 1, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.get_miniprix(mmstart)
        self.assertEqual(evts[0].name, "mBig_Blue > Red_Canyon_I > mPort_Town_II (MiniPrix035.4)")
        self.assertEqual(evts[0].start_time, datetime(2024, 8, 24, 1, 0, 0, 0, tzinfo=timezone.utc))

    def test_miniprix_weekend_selection3(self):
        mmstart = datetime(2024, 8, 24, 2, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.get_miniprix(mmstart)
        self.assertEqual(evts[0].name, "mMute_City_III > Sand_Ocean > Port_Town_II (MiniPrix007.6)")
        self.assertEqual(evts[0].start_time, datetime(2024, 8, 24, 2, 30, 0, 0, tzinfo=timezone.utc))


class TestMiniprixManagerMiniWorldTourClassic(unittest.TestCase):
    """ These test cases cover a scenario where the Miniprix event duration is set to
        5 minutes instead of 10.
    """
    def create_manager(self):
        """ Utility returning a built-up Miniprix Manager object.
        """
        wdsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_miniworldtour')
        wesched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_weekend_miniworldtour')
        mpsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'classic_mp_schedule_miniworldtour')
        slot2mgr = schedule.Slot2ScheduleManager(self.origin, wdsched, wesched)

        mp_offset = 18
        mgr = miniprix.MiniPrixManager("classicprix", slot2mgr, mpsched, None, mp_offset, 0)
        # force lineup offset to default 5 minutes
        mgr.mp_cycles = 5
        return mgr

    def setUp(self):
        # This .env file only needs CONFIG_PATH declared.
        # .env is covered by .gitignore to avoid secrets accidentally pushed to server
        env_path = "fixtures/.env"
        self.env = utils.load_env("fixtures/.env")
        self.origin = datetime(2025, 4, 23, 0, 0, 0, 0, tzinfo=timezone.utc)
        self.mgr = self.create_manager()

    def test_classicprix_selection1(self):
        mmstart = datetime(2025, 5, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.get_miniprix(mmstart)
        self.assertEqual(evts[0].name, "Silence > White_Land_II > Fire_Field (ClassicMiniPrix024.0)")
        self.assertEqual(evts[0].start_time, datetime(2025, 5, 5, 2, 20, 0, 0, tzinfo=timezone.utc))

    def test_classicprix_selection2(self):
        mmstart = datetime(2025, 5, 5, 3, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.get_miniprix(mmstart)
        self.assertEqual(evts[0].name, "Mute_City_IV > Red_Canyon_I > Silence_II (ClassicMiniPrix029.0)")
        self.assertEqual(evts[0].start_time, datetime(2025, 5, 5, 5, 0, 0, 0, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()