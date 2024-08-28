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
        return miniprix.MiniPrixManager("miniprix", slot2mgr, mpsched, mirrorsc)

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



if __name__ == "__main__":
    unittest.main()