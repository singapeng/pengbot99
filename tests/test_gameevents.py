# Python imports
import json
import os
import unittest
from datetime import datetime, timedelta, timezone

# Local import
from pengbot99 import gameevents, gameschedule

CONFIG = os.path.join(os.path.dirname(__file__), '..', 'py', 'pengbot99', 'data')
UTC = timezone.utc


def load(profile, name):
    with open(os.path.join(CONFIG, 'event_{0}'.format(profile), name + '.json')) as fd:
        return json.load(fd)


class ManagersTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = gameschedule.ScheduleData(load('default', 'GameScheduleV1'),
                                             load('default', 'WeekendSchedule'))
        with open(os.path.join(CONFIG, 'StageList.json')) as fd:
            cls.leagues = gameschedule.league_tracks(json.load(fd))

    def test_slot_events_around_a_weekend_start(self):
        mgr = gameevents.SlotScheduleManager(self.data)
        evts = mgr.list_events(datetime(2026, 10, 16, 23, 50, tzinfo=UTC), next=60)
        self.assertEqual([(str(e), e.schedule_name) for e in evts], [
            ('2026-10-16 23:40 - classic (20 minutes)', 'weekday'),
            ('2026-10-17 00:00 - mace (10 minutes)', 'weekend'),
            ('2026-10-17 00:10 - teambattle (20 minutes)', 'weekend'),
            ('2026-10-17 00:30 - knight (10 minutes)', 'weekend'),
            ('2026-10-17 00:40 - protracks (20 minutes)', 'weekend'),
        ])
        self.assertEqual(evts[0].end_time, datetime(2026, 10, 17, 0, 0, tzinfo=UTC))
        self.assertEqual(evts[1].mode, 'GrandPrixRotation')
        self.assertEqual(len(evts[1].rotation), 16)
        self.assertEqual(evts[1].rotation[:2], ['mace', 'knight'])

    def test_secret_league_events(self):
        mgr = gameevents.SlotScheduleManager(self.data)
        when = datetime(2026, 10, 16, 23, 50, tzinfo=UTC)
        evts = mgr.when_event(['glitchgp'], count=2, timestamp=when)
        self.assertEqual([str(e) for e in evts],
                         ['2026-10-17 02:30 - glitchgp (10 minutes)',
                          '2026-10-17 04:30 - glitchgp (10 minutes)'])
        self.assertTrue(evts[0].glitch)
        self.assertEqual(evts[0].glitched_name, 'queen')
        # the replaced league still answers a query by its own name
        by_league = mgr.when_event(['queen'], count=1, timestamp=when)
        self.assertEqual(by_league[0].start_time, evts[0].start_time)
        self.assertTrue(mgr.is_secret_league_on(when))

    def test_get_events_count_and_limit(self):
        mgr = gameevents.SlotScheduleManager(self.data)
        when = datetime(2026, 10, 15, 0, 5, tzinfo=UTC)
        self.assertEqual(len(mgr.get_events(timestamp=when, limit=60)), 4)
        evts = mgr.get_events(names=['miniprix'], count=2, timestamp=when)
        self.assertEqual([e.start_time.strftime('%H:%M') for e in evts],
                         ['01:30', '02:30'])
        self.assertEqual(mgr.get_event(when).name, 'mace')
        self.assertEqual(mgr.weekend_event(datetime(2026, 9, 19, tzinfo=UTC)),
                         'QueenLeagueWeekend')

    def test_mystery_track_events(self):
        mgr = gameevents.MysteryTrackManager(self.data)
        when = datetime(2026, 9, 8, 2, 20, tzinfo=UTC)
        evts = mgr.when_event(['glitch99'], count=3, timestamp=when)
        self.assertEqual([str(e) for e in evts],
                         ['2026-09-08 02:22 - Mystery_4 (2 minutes)',
                          '2026-09-08 03:02 - Mystery_5 (2 minutes)',
                          '2026-09-08 03:30 - Mystery_6 (2 minutes)'])
        # a window that already opened is not upcoming
        later = mgr.when_event(['glitch99'], count=1,
                               timestamp=when + timedelta(minutes=2))
        self.assertEqual(str(later[0]), '2026-09-08 03:02 - Mystery_5 (2 minutes)')
        only = mgr.when_event(['Mystery_6'], count=1, timestamp=when)
        self.assertEqual(only[0].name, 'Mystery_6')

    def test_ninety_nine_lineup(self):
        mgr = gameevents.NinetyNineManager(self.data)
        evts = mgr.list_events(datetime(2026, 9, 8, 2, 20, 30, tzinfo=UTC), next=3)
        self.assertEqual([e.name for e in evts], ['Big_Blue_II <> mMute_City_III',
                                                  'mSand_Ocean <> mDeath_Wind_I',
                                                  'Mystery_4 <> Port_Town_I',
                                                  'Mystery_4 <> Red_Canyon_I'])
        self.assertEqual(evts[0].start_time, datetime(2026, 9, 8, 2, 20, tzinfo=UTC))
        # the verbose id of a choice race is the game's SetId
        self.assertEqual([e.start_minute + 1 for e in evts], [15, 16, 17, 18])
        lines = mgr.get_formatted_events(datetime(2026, 9, 8, 2, 20, tzinfo=UTC),
                                         next=1)
        self.assertEqual(len(lines), 3)
        self.assertIn('Big Blue II <> _Mirror Mute City III_', lines[1])

    def test_public_mini_prix_slot(self):
        mgr = gameevents.MiniPrixLineupManager(self.data, self.leagues, 'miniprix')
        evts = mgr.get_miniprix(datetime(2026, 10, 15, 1, 0, tzinfo=UTC))
        self.assertEqual(len(evts), 10)
        self.assertEqual(evts[0].start_time, datetime(2026, 10, 15, 1, 30, tzinfo=UTC))
        self.assertEqual(evts[0].name,
                         'Mute_City_II > Red_Canyon_I > Mystery_6 (MiniPrix033.000)')
        self.assertEqual(evts[0].mpid, 'MiniPrix033.000')
        self.assertEqual(evts[1].mpid, 'MiniPrix034.101')
        self.assertEqual(evts[1].race1, 'mSand_Storm_I')
        self.assertTrue(evts[0].has_track('Red_Canyon_I'))
        self.assertFalse(evts[0].shuffle)
        # a query inside the slot returns that slot from its start
        inside = mgr.get_miniprix(datetime(2026, 10, 15, 1, 35, tzinfo=UTC))
        self.assertEqual(inside[0].start_time, evts[0].start_time)

    def test_classic_mini_prix_has_no_mirror(self):
        mgr = gameevents.MiniPrixLineupManager(self.data, self.leagues, 'classicprix')
        evts = mgr.get_miniprix(datetime(2026, 10, 15, 0, 0, tzinfo=UTC))
        self.assertEqual(evts[0].start_time, datetime(2026, 10, 15, 0, 30, tzinfo=UTC))
        self.assertEqual(evts[0].mpid, 'ClassicMiniPrix008')
        self.assertEqual(
            evts[0].name,
            'Mute_City_III > Sand_Storm_II > Silence_II (ClassicMiniPrix008)')

    def test_private_mini_prix(self):
        mgr = gameevents.MiniPrixLineupManager(self.data, self.leagues, 'miniprix',
                                               private=True)
        evts = mgr.get_miniprix(datetime(2026, 9, 1, 0, 59, tzinfo=UTC))
        self.assertEqual(len(evts), gameevents.PRIVATE_MINUTES + 1)
        self.assertEqual(
            evts[0].name,
            'Sand_Storm_I > White_Land_I > mPort_Town_II (MiniPrix010.001)')
        self.assertEqual(evts[-1].start_time, datetime(2026, 9, 1, 1, 9, tzinfo=UTC))
        later = mgr.get_miniprix(datetime(2026, 9, 1, 1, 0, tzinfo=UTC))
        self.assertEqual(later[-1].race2, 'mMystery_3')
        self.assertEqual(later[-1].start_time, datetime(2026, 9, 1, 1, 10, tzinfo=UTC))
        # while the public Mini-Prix runs, the private lobby gets its lineup
        during = mgr.get_miniprix(datetime(2026, 10, 15, 1, 30, tzinfo=UTC))
        self.assertTrue(during[0].public)
        self.assertEqual(during[0].mpid, 'MiniPrix033.000')
        self.assertFalse(during[-1].public)

    def test_shuffle_flag_on_a_machine_shuffle_weekend(self):
        mgr = gameevents.MiniPrixLineupManager(self.data, self.leagues, 'miniprix')
        evts = mgr.get_miniprix(datetime(2026, 10, 10, 0, 20, tzinfo=UTC))
        self.assertEqual(evts[0].start_time, datetime(2026, 10, 10, 0, 30, tzinfo=UTC))
        self.assertTrue(evts[0].shuffle)
        weekday = mgr.get_miniprix(datetime(2026, 10, 9, 0, 20, tzinfo=UTC))
        self.assertFalse(weekday[0].shuffle)

    def test_public_track_pairs(self):
        mgr = gameevents.TrackPairManager(self.data, 'protracks')
        evts = mgr.list_events(datetime(2026, 10, 15, 0, 0, tzinfo=UTC))
        self.assertEqual(len(evts), 20)
        self.assertEqual(evts[0].start_time, datetime(2026, 10, 15, 0, 40, tzinfo=UTC))
        self.assertEqual([e.start_minute + 1 for e in evts[:3]], [1, 2, 3])
        self.assertEqual(evts[0].name, 'Death_Wind_II <> Port_Town_II')
        teams = gameevents.TrackPairManager(self.data, 'teambattle').list_events(
            datetime(2026, 10, 15, 0, 0, tzinfo=UTC))
        self.assertEqual(teams[0].start_time, datetime(2026, 10, 15, 0, 10, tzinfo=UTC))
        classic = gameevents.TrackPairManager(self.data, 'classic').list_events(
            datetime(2026, 10, 15, 0, 0, tzinfo=UTC))
        self.assertEqual(classic[0].start_time,
                         datetime(2026, 10, 15, 1, 10, tzinfo=UTC))

    def test_private_track_pairs(self):
        mgr = gameevents.TrackPairManager(self.data, 'teambattle', private=True)
        when = datetime(2026, 10, 15, 0, 5, tzinfo=UTC)
        evts = mgr.list_events(when)
        self.assertEqual(len(evts), gameevents.PRIVATE_MINUTES + 1)
        minute = int(when.timestamp()) // 60
        self.assertEqual(evts[0].start_minute, (minute + 6) % 34)
        self.assertFalse(evts[0].public)
        # from 00:10 the public Team Battle slot runs and takes over
        self.assertTrue(evts[5].public)
        public = gameevents.TrackPairManager(self.data, 'teambattle').list_events(when)
        self.assertEqual(evts[5].name, public[0].name)


if __name__ == "__main__":
    unittest.main()
