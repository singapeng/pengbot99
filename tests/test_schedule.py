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


class TestMiniWorldTourRotation(unittest.TestCase):
    """ Test when the special event rotation is Team Battle/Pro-Tracks/Classic
        and appears 4 times in the cycle.
    """

    def create_manager(self):
        """ Utility returning a built-up Slot 2 schedule manager
        """
        wdsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_miniworldtour')
        wesched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_weekend_miniworldtour')
        slot2mgr = schedule.Slot2ScheduleManager(self.origin, wdsched, wesched)
        return slot2mgr

    def setUp(self):
        # This .env file only needs CONFIG_PATH declared.
        # .env is covered by .gitignore to avoid secrets accidentally pushed to server
        env_path = "fixtures/.env"
        self.env = utils.load_env("fixtures/.env")
        self.origin = datetime(2025, 5, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
        self.mgr = self.create_manager()

    def test_list_events_specials_1(self):
        ts = datetime(2025, 5, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        self.assertEqual(evts[0].name, "worldtour")
        self.assertEqual(evts[1].name, "classic")

    def test_list_events_specials_2(self):
        ts = datetime(2025, 5, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        self.assertEqual(evts[3].name, "teambattle")

    def test_list_events_specials_3(self):
        ts = datetime(2025, 5, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        self.assertEqual(evts[5].name, "protracks")

    def test_list_events_specials_4(self):
        ts = datetime(2025, 5, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        self.assertEqual(evts[7].name, "classic")

    def test_cycle_info_count_at_origin(self):
        ci = self.mgr.get_cycle_info(self.origin)
        self.assertEqual(ci.get_event("teambattle"), 0)

    def test_cycle_info_count_at_cycle_one(self):
        """ We've had Classic, Team Battle, Protracks and Classic"""
        cycle_duration = self.mgr.weekday.duration
        assert cycle_duration == 80
        ci = self.mgr.get_cycle_info(self.origin + timedelta(minutes=cycle_duration))
        self.assertEqual(ci.get_event("classic"), 2)
        self.assertEqual(ci.get_event("teambattle"), 1)
        self.assertEqual(ci.get_event("protracks"), 1)

    def test_cycle_info_count_at_cycle_two(self):
        """ We've had Classic (1), Team Battle (1), Protracks (1), Classic (2) in cycle one
        then Team Battle (2), Protracks (2), Classic (3), Team Battle (3) in cycle 2 """
        cycle_duration = self.mgr.weekday.duration
        ci = self.mgr.get_cycle_info(self.origin + timedelta(minutes=cycle_duration * 2))
        self.assertEqual(ci.get_event("classic"), 3)
        self.assertEqual(ci.get_event("teambattle"), 3)
        self.assertEqual(ci.get_event("protracks"), 2)

    def test_cycle_info_count_at_cycle_three(self):
        """ We've had Classic (1), Team Battle (1), Protracks (1), Classic (2) in cycle one
        then Team Battle (2), Protracks (2), Classic (3), Team Battle (3) in cycle 2
        then Protracks (3), Classic (4), Team Battle (4), Protracks (4) in cycle 3"""
        cycle_duration = self.mgr.weekday.duration
        ci = self.mgr.get_cycle_info(self.origin + timedelta(minutes=cycle_duration * 3))
        self.assertEqual(ci.get_event("classic"), 4)
        self.assertEqual(ci.get_event("teambattle"), 4)
        self.assertEqual(ci.get_event("protracks"), 4)

    def test_cycle_info_count_inside_cycle_zero(self):
        """ We've had Classic only"""
        ci = self.mgr.get_cycle_info(self.origin + timedelta(minutes=20))
        self.assertEqual(ci.get_event("classic"), 1)
        self.assertEqual(ci.get_event("teambattle"), 0)
        self.assertEqual(ci.get_event("protracks"), 0)


class TestMiniWorldTourRotation_EdgeCase(unittest.TestCase):
    """ Test when the special event rotation is Team Battle/Pro-Tracks/Classic
        and appears 4 times in the cycle.
        Another case discovered after the weekend rotation appeared.
    """

    def create_manager(self):
        """ Utility returning a built-up Slot 2 schedule manager
        """
        wdsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_miniworldtour_edge')
        wesched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_weekend_miniworldtour_edge')
        slot2mgr = schedule.Slot2ScheduleManager(self.origin, wdsched, wesched)
        return slot2mgr

    def setUp(self):
        # This .env file only needs CONFIG_PATH declared.
        # .env is covered by .gitignore to avoid secrets accidentally pushed to server
        env_path = "fixtures/.env"
        self.env = utils.load_env("fixtures/.env")
        self.origin = datetime(2025, 5, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
        self.mgr = self.create_manager()


    def test_list_events_specials_edge_case_1(self):
        ts = datetime(2025, 5, 10, 1, 40, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        expected = ("classic", "teambattle", "protracks", "classic")
        result = (evts[1].name, evts[3].name, evts[5].name, evts[7].name)

    def test_list_events_specials_edge_case_2(self):
        ts = datetime(2025, 5, 10, 1, 50, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        expected = ("classic", "teambattle", "protracks", "classic")
        result = (evts[0].name, evts[2].name, evts[4].name, evts[6].name)
        self.assertEqual(result, expected)


class TestPost160_GPRotation_EdgeCase(unittest.TestCase):
    """ Fixing the edge case with multiple multi-events rotations appearances
        caused an issue with Grand Prix Rotation.
    """

    def create_manager(self):
        """ Utility returning a built-up Slot 2 schedule manager
        """
        wdsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_edge160')
        wesched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_weekend_edge160')
        slot2mgr = schedule.Slot2ScheduleManager(self.origin, wdsched, wesched)
        return slot2mgr

    def setUp(self):
        # This .env file only needs CONFIG_PATH declared.
        # .env is covered by .gitignore to avoid secrets accidentally pushed to server
        env_path = "fixtures/.env"
        self.env = utils.load_env("fixtures/.env")
        self.origin = datetime(2025, 5, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
        self.mgr = self.create_manager()

    def test_list_events_specials_edge_case_gp_1(self):
        ts = datetime(2025, 5, 15, 2, 0, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        self.assertEqual(evts[0].name, "mqueen")

    def test_list_events_specials_edge_case_gp_2(self):
        ts = datetime(2025, 5, 15, 2, 1, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        self.assertEqual(evts[0].name, "mqueen")

    def test_list_events_specials_edge_case_3(self):
        ts = datetime(2025, 5, 16, 2, 16, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        expected = ("protracks", "classic", "teambattle")
        result = (evts[0].name, evts[2].name, evts[4].name)
        self.assertEqual(result, expected)


class Test_Yet_Another_Rotation_EdgeCase(unittest.TestCase):
    """ Fixing the edge case with multiple multi-events rotations appearances
    """

    def create_manager(self):
        """ Utility returning a built-up Slot 2 schedule manager
        """
        wdsched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_tbptc_edge')
        wesched = schedule.load_schedule(self.env['CONFIG_PATH'], 'slot2_schedule_weekend_tbptc_edge')
        slot2mgr = schedule.Slot2ScheduleManager(self.origin, wdsched, wesched)
        return slot2mgr

    def setUp(self):
        # This .env file only needs CONFIG_PATH declared.
        # .env is covered by .gitignore to avoid secrets accidentally pushed to server
        env_path = "fixtures/.env"
        self.env = utils.load_env("fixtures/.env")
        self.origin = datetime(2025, 5, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
        self.mgr = self.create_manager()

    def test_list_events_specials_edge_case_4(self):
        ts = datetime(2025, 5, 22, 3, 10, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        expected = ("teambattle", "protracks", "classic", "teambattle")
        result = (evts[0].name, evts[2].name, evts[4].name, evts[6].name)
        self.assertEqual(result, expected)

    def test_list_events_specials_edge_case_5(self):
        ts = datetime(2025, 5, 22, 3, 20, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        expected = ("teambattle", "protracks", "classic", "teambattle")
        result = (evts[0].name, evts[2].name, evts[4].name, evts[6].name)
        self.assertEqual(result, expected)

    def test_list_events_specials_garusan_report(self):
        ts = datetime(2025, 5, 22, 13, 27, 0, 0, tzinfo=timezone.utc)
        evts = self.mgr.list_events(timestamp=ts, next=119)
        expected = ("classic", "teambattle", "protracks", "classic")
        result = (evts[0].name, evts[2].name, evts[4].name, evts[6].name)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()