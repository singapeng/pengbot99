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


class TestMiniprixManagerPrivateMiniFilter(unittest.TestCase):
    """ Adding this with the intention to deal with the following use-case:
        In this query, the last returned MP selection is for 1:09.
        If the user intends to filter for Death Wind White Land (DWWL),
        the next occurence is at 1:10.

        Because of the way the Miniprix query is built, it only ever returns at
        most 10 selections. Applying a filter only looks up for the requested
        track in these 10. Therefore, filtering for DWWL in this case would yield
        no result.

        While this isn't a bug, it would be desirable that when a track filter
        is supplied, the manager returns a longer selection to filter on. There
        are some obstacles to this:
        1) need a way to override the mp_cycles attribute temporarily for such
           query; to the length of the MP schedule would be suitable.
        2) need a way to correctly override private MP in the case of multiple
           public MP in the mp_cycles interval. This is especially likely to
           happen in Machine Shuffle events.
        3) need a way to validate the filtering logic in tests. Currently,
           filtering is a hack in the bot.py module applied to the miniprix
           manager query result. This should be improved.
    """
    def create_manager(self):
        """ Utility returning a built-up Private Miniprix Manager object.
        """
        wdsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_meteor')
        wesched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_weekend_meteor')
        mpsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'miniprix_schedule_v1_7')
        mirrorsc = schedule.load_schedule(self.env['CONFIG_PATH'], 'miniprix_mirroring_schedule')
        plmpsched = schedule.load_schedule(self.env["CONFIG_PATH"], "private_miniprix_schedule")
        slot2mgr = schedule.Slot2ScheduleManager(self.origin, wdsched, wesched)

        mp_offset = 28
        mirror_offset=3
        mgr = miniprix.MiniPrixManager("miniprix", slot2mgr, mpsched, mirrorsc, mp_offset, mirror_offset)
        # force lineup offset to default 5 minutes
        mgr.mp_cycles = 5

        pmp_offset = 17
        pmp_mirror_offset = 0
        pmp_origin = schedule.origin + timedelta(minutes=pmp_offset)
        pmp_mirror_origin = schedule.origin + timedelta(minutes=pmp_mirror_offset)

        pl_slot1 = schedule.Slot1ScheduleManager(pmp_origin, plmpsched)
        mirror_slot1 = schedule.Slot1ScheduleManager(pmp_mirror_origin, mirrorsc)
        pmp_mgr = miniprix.PrivateMPManager("miniprix", pl_slot1, mgr, mirror_slot1)

        return pmp_mgr

    def setUp(self):
        # This .env file only needs CONFIG_PATH declared.
        # .env is covered by .gitignore to avoid secrets accidentally pushed to server
        env_path = "fixtures/.env"
        self.env = utils.load_env("fixtures/.env")
        self.origin = datetime(2025, 4, 23, 0, 0, 0, 0, tzinfo=timezone.utc)
        self.mgr = self.create_manager()

    def test_private_miniprix_selection1(self):
        "This is a placeholder test intended to verify the schedule setup is correct"
        mmstart = datetime(2026, 9, 1, 0, 59, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.get_miniprix(mmstart)
        self.assertEqual(evts[0].name, "Sand_Storm_I > White_Land_I > mPort_Town_II (MiniPrix010.5)")
        self.assertEqual(evts[0].start_time, datetime(2026, 9, 1, 0, 59, 0, 0, tzinfo=timezone.utc))

    def test_private_miniprix_selection2(self):
        "This is a placeholder test intended to verify DWWL (Mystery_3) appears where expected"
        mmstart = datetime(2026, 9, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.get_miniprix(mmstart)
        self.assertEqual(evts[-1].race2, "mMystery_3")
        self.assertEqual(evts[-1].start_time, datetime(2026, 9, 1, 1, 10, 0, 0, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()