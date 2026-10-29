# Python imports
import json
import os
import unittest
from datetime import datetime, timezone

# Local import
from pengbot99 import gameschedule

CONFIG = os.path.join(os.path.dirname(__file__), '..', 'py', 'pengbot99', 'data')


def load(profile, name):
    with open(os.path.join(CONFIG, 'event_{0}'.format(profile), name + '.json')) as fd:
        return json.load(fd)


def at(*args):
    return int(datetime(*args, tzinfo=timezone.utc).timestamp())


def names(tracks):
    return ' <> '.join(('m' if kind == 'Mirror' else '') + track
                       for track, kind in tracks)


class WindowsTestCase(unittest.TestCase):
    """ The InactivePeriods window test, on the romfs MysteryPrixSchedule:
        with ten-minute Grand Prix, Grand Prix number g is replaced when
        g mod 39 is one of 0, 11, 17, 24, 27, 35 (never the very first).
    """
    BLOCK = {"AvailabilityInterval": 10, "InactivePeriods": [110, 60, 70, 30, 80, 40],
             "Leagues": [{"Name": "MysteryLeague"}], "Start": "2026-01-19T00:00"}

    def test_window_positions(self):
        windows = gameschedule.Windows(self.BLOCK)
        self.assertEqual(windows.cycle, 390)
        self.assertEqual(windows.window_starts, [0, 110, 170, 240, 270, 350])

    def test_evaluate_matches_the_known_gp_numbers(self):
        windows = gameschedule.Windows(self.BLOCK)
        now = gameschedule.parse_time("2026-02-01T00:00")
        hits = [g for g in range(80) if windows.evaluate(g * 10, now) != -1]
        self.assertEqual(hits, [11, 17, 24, 27, 35, 39, 50, 56, 63, 66, 74, 78])

    def test_minute_inside_window_hits(self):
        windows = gameschedule.Windows(self.BLOCK)
        now = gameschedule.parse_time("2026-02-01T00:00")
        for minute in range(110, 120):
            self.assertEqual(windows.evaluate(minute, now), 0)
        self.assertEqual(windows.evaluate(120, now), -1)

    def test_nothing_before_start(self):
        windows = gameschedule.Windows(self.BLOCK)
        before = gameschedule.parse_time("2026-01-18T23:59")
        self.assertEqual(windows.evaluate(110, before), -1)

    def test_no_periods_means_no_windows(self):
        windows = gameschedule.Windows({"AvailabilityInterval": 10,
                                        "InactivePeriods": None,
                                        "Leagues": [{"Name": "MysteryLeague"}]})
        self.assertEqual(windows.evaluate(110, 0), -1)
        self.assertEqual(windows.windows_between(0, 10000, 0), [])

    def test_windows_between(self):
        windows = gameschedule.Windows(self.BLOCK)
        now = gameschedule.parse_time("2026-02-01T00:00")
        found = windows.windows_between(380, 800, now)
        self.assertEqual([(opens, closes) for opens, closes, _ in found],
                         [(390, 400), (500, 510), (560, 570), (630, 640), (660, 670),
                          (740, 750), (780, 790)])


class DefaultScheduleTestCase(unittest.TestCase):
    """ The romfs schedule, as the game runs it outside any drop.
    """
    @classmethod
    def setUpClass(cls):
        cls.data = gameschedule.ScheduleData(load('default', 'GameScheduleV1'),
                                             load('default', 'WeekendSchedule'))

    def lineups(self, start, minutes):
        found = []
        for begin, end, schedule in self.data.intervals(start, start + minutes * 60):
            lineup = schedule.lineup(begin)
            when = datetime.fromtimestamp(begin, timezone.utc).strftime('%a %H:%M')
            found.append((when, (end - begin) // 60, lineup.mode, lineup.league,
                          lineup.secret))
        return found

    def test_weekday_cycle(self):
        self.assertEqual(self.lineups(at(2026, 10, 15, 0, 0), 180), [
            ('Thu 00:00', 10, 'GrandPrixRotation', 'MirrorAceLeague', None),
            ('Thu 00:10', 20, 'Teams', None, None),
            ('Thu 00:30', 10, 'ClassicMiniPrixRotation', 'ClassicMiniPrix008', None),
            ('Thu 00:40', 20, 'HardTracks', None, None),
            ('Thu 01:00', 10, 'GrandPrixRotation', 'KnightLeague', None),
            ('Thu 01:10', 20, 'Classic', None, None),
            ('Thu 01:30', 10, 'MiniPrixRotation', 'MiniPrix033', None),
            ('Thu 01:40', 20, 'Teams', None, None),
            ('Thu 02:00', 10, 'GrandPrixRotation', 'MirrorQueenLeague', None),
            ('Thu 02:10', 20, 'HardTracks', None, None),
            ('Thu 02:30', 10, 'MiniPrixRotation', 'MiniPrix043', None),
            ('Thu 02:40', 20, 'Classic', None, None),
        ])

    def test_weekend_cycle_and_secret_league(self):
        found = self.lineups(at(2026, 10, 17, 0, 0), 180)
        self.assertEqual([item[1:] for item in found[:4]], [
            (10, 'GrandPrixRotation', 'MirrorAceLeague', None),
            (20, 'Teams', None, None),
            (10, 'GrandPrixRotation', 'KnightLeague', None),
            (20, 'HardTracks', None, None),
        ])
        self.assertEqual([item[0] for item in found if item[4] == 'MysteryLeague'],
                         ['Sat 02:30'])

    def test_grand_prix_rotation_order(self):
        schedule = self.data.schedule_at(at(2026, 10, 15))
        self.assertEqual(schedule.rotation(schedule.mode_index['GrandPrixRotation']), [
            'MirrorAceLeague', 'KnightLeague', 'MirrorQueenLeague', 'KingLeague',
            'MirrorKnightLeague', 'QueenLeague', 'MirrorKingLeague', 'AceLeague',
            'MirrorQueenLeague', 'KingLeague', 'MirrorAceLeague', 'KnightLeague',
            'MirrorKingLeague', 'AceLeague', 'MirrorKnightLeague', 'QueenLeague'])

    def test_mini_prix_mirror_pattern(self):
        schedule = self.data.schedule_at(at(2026, 10, 15))
        lineup = schedule.lineup(at(2026, 10, 15, 1, 30))
        self.assertEqual((lineup.league, lineup.mirror), ('MiniPrix033', '000'))
        lineup = schedule.lineup(at(2026, 10, 15, 1, 31))
        self.assertEqual((lineup.league, lineup.mirror), ('MiniPrix034', '101'))
        lineup = schedule.lineup(at(2026, 10, 15, 0, 31))
        self.assertEqual((lineup.league, lineup.mirror), ('ClassicMiniPrix009', None))

    def test_ninety_nine_pair_and_mystery_track(self):
        """ Gammaween's report: the Fire City mystery race opened at 02:22
            on 2026-09-08 and replaced the first track of the pair.
        """
        schedule = self.data.schedule_at(at(2026, 9, 8))
        pairs = [names(schedule.ninety_nine(at(2026, 9, 8, 2, minute))[1])
                 for minute in range(20, 25)]
        self.assertEqual(pairs, ['Big_Blue_II <> mMute_City_III',
                                 'mSand_Ocean <> mDeath_Wind_I',
                                 'Mystery_4 <> Port_Town_I',
                                 'Mystery_4 <> Red_Canyon_I',
                                 'Big_Blue <> Sand_Storm_I'])
        self.assertEqual(schedule.ninety_nine(at(2026, 9, 8, 2, 22))[2], 'Mystery_4')
        self.assertEqual(schedule.ninety_nine(at(2026, 9, 8, 2, 24))[2], None)

    def test_mystery_track_windows_follow_the_205_minute_cycle(self):
        schedule = self.data.schedule_at(at(2026, 9, 8))
        start = at(2026, 9, 8, 0, 0)
        found = schedule.mystery_track_windows(start, start + 205 * 60)
        self.assertEqual([(opens - start) // 60 for opens, _, _ in found],
                         [5, 51, 82, 119, 142, 182])
        self.assertEqual([track for _, _, track in found],
                         ['Mystery_5', 'Mystery_6', 'Mystery_7', 'Mystery_3',
                          'Mystery_4', 'Mystery_5'])
        self.assertTrue(all(closes - opens == 120 for opens, closes, _ in found))

    def test_private_mini_prix_is_wall_clock(self):
        """ Reported in a private lobby: 2026-09-01 00:59 ran MiniPrix010 with
            its third track mirrored, 01:10 a mirrored Death Wind White Land.
        """
        schedule = self.data.schedule_at(at(2026, 9, 1))
        lineup = schedule.private(at(2026, 9, 1, 0, 59), gameschedule.MINI_PRIX)
        self.assertEqual((lineup.league, lineup.mirror, lineup.public),
                         ('MiniPrix010', '001', False))
        lineup = schedule.private(at(2026, 9, 1, 1, 10), gameschedule.MINI_PRIX)
        self.assertEqual(lineup.league, 'MiniPrix021')
        self.assertEqual(lineup.mirror[1], '1')

    def test_private_lobby_gets_the_public_lineup_while_it_runs(self):
        schedule = self.data.schedule_at(at(2026, 10, 15))
        when = at(2026, 10, 15, 1, 31)
        lineup = schedule.private(when, gameschedule.MINI_PRIX)
        self.assertTrue(lineup.public)
        self.assertEqual(lineup.league, schedule.lineup(when).league)
        lineup = schedule.private(when, gameschedule.CLASSIC_MINI_PRIX)
        self.assertFalse(lineup.public)

    def test_private_track_pairs(self):
        schedule = self.data.schedule_at(at(2026, 10, 15))
        when = at(2026, 10, 15, 1, 31)
        minute = when // 60
        teams = schedule.private(when, gameschedule.COLOR_TEAMS)
        self.assertEqual(teams.set_index, (minute + 6) % 34)
        pairs = schedule.track_sets[gameschedule.COLOR_TEAMS].sets
        self.assertEqual(teams.tracks, pairs[teams.set_index])
        hard = schedule.private(when, gameschedule.HARD_TRACKS)
        self.assertEqual(hard.set_index, minute % 32)
        classic = schedule.private(when, gameschedule.CLASSIC)
        self.assertEqual(classic.set_index, minute % 28)

    def test_public_track_pairs_change_every_minute(self):
        schedule = self.data.schedule_at(at(2026, 10, 15))
        first = schedule.lineup(at(2026, 10, 15, 0, 10))
        second = schedule.lineup(at(2026, 10, 15, 0, 11))
        self.assertEqual((first.mode, first.type), ('Teams', gameschedule.COLOR_TEAMS))
        self.assertEqual(second.set_index, (first.set_index + 1) % 34)
        self.assertEqual(len(first.tracks), 2)
        classic = schedule.lineup(at(2026, 10, 15, 1, 10))
        self.assertEqual({kind for _, kind in classic.tracks}, {'Classic'})


class CalendarTestCase(unittest.TestCase):
    """ The weekend events the romfs WeekendSchedule file lists, picked by
        its calendar.
    """
    @classmethod
    def setUpClass(cls):
        cls.data = gameschedule.ScheduleData(load('default', 'GameScheduleV1'),
                                             load('default', 'WeekendSchedule'))

    def test_calendar_selection(self):
        self.assertEqual(self.data.weekend_event(at(2026, 9, 19)), 'QueenLeagueWeekend')
        self.assertEqual(self.data.weekend_event(at(2026, 11, 28)), 'KingLeagueWeekend')
        self.assertIsNone(self.data.weekend_event(at(2026, 10, 15)))
        self.assertEqual(self.data.next_change(at(2026, 9, 19)), at(2026, 9, 22))
        self.assertEqual(self.data.next_change(at(2026, 10, 15)), at(2026, 10, 21))

    def test_pinned_event(self):
        data = gameschedule.ScheduleData(self.data.game_schedule,
                                         self.data.weekend_schedule,
                                         'KnightLeagueWeekend')
        self.assertEqual(data.weekend_event(at(2026, 10, 15)), 'KnightLeagueWeekend')
        self.assertEqual(data.next_change(at(2026, 10, 15)), gameschedule.FOREVER)

    def test_no_event(self):
        data = gameschedule.ScheduleData(self.data.game_schedule,
                                         self.data.weekend_schedule,
                                         gameschedule.ScheduleData.NONE)
        self.assertIsNone(data.weekend_event(at(2026, 9, 19)))

    def test_unknown_event(self):
        with self.assertRaises(KeyError):
            gameschedule.ScheduleData(self.data.game_schedule,
                                      self.data.weekend_schedule, 'NoSuchWeekend')

    def test_league_weekend_rotation(self):
        """ Queen weekend: Queen and Mirror Queen at :00 and :30, the other
            leagues at :15 and :45, ten-minute specials between.
        """
        found = []
        start = at(2026, 9, 19, 0, 0)
        for begin, end, schedule in self.data.intervals(start, start + 90 * 60):
            lineup = schedule.lineup(begin)
            found.append(((begin - start) // 60, (end - begin) // 60, lineup.league))
        self.assertEqual(found, [
            (0, 5, 'QueenLeague'), (5, 10, None),
            (15, 5, 'KnightLeague'), (20, 10, None),
            (30, 5, 'MirrorQueenLeague'), (35, 10, None),
            (45, 5, 'MirrorKnightLeague'), (50, 10, None),
            (60, 5, 'QueenLeague'), (65, 10, None),
            (75, 5, 'KingLeague'), (80, 10, None),
        ])

    def test_mystery_league_weekend_replaces_every_other_grand_prix(self):
        start = at(2026, 1, 24, 0, 0)
        found = [(schedule.lineup(begin).league, schedule.lineup(begin).secret)
                 for begin, _, schedule in self.data.intervals(start, start + 60 * 60)
                 if schedule.lineup(begin).type == gameschedule.GRAND_PRIX]
        self.assertEqual(found, [('MirrorAceLeague', 'MysteryLeague'),
                                 ('MirrorAceLeague', None),
                                 ('KnightLeague', 'MysteryLeague'),
                                 ('KnightLeague', None)])

    def test_world_tour_week_runs_every_day(self):
        start = at(2026, 9, 30, 0, 0)
        found = [((begin - start) // 60, schedule.lineup(begin).mode)
                 for begin, _, schedule in self.data.intervals(start, start + 80 * 60)]
        self.assertEqual(found, [
            (0, 'MiniWorldTourFeatured'), (5, 'Teams'), (20, 'GrandPrixRotationFast'),
            (25, 'HardTracks'), (40, 'MiniWorldTourFeatured'), (45, 'Classic'),
            (60, 'MiniPrixRotation'), (65, 'Teams'),
        ])
        schedule = self.data.schedule_at(start)
        self.assertEqual(schedule.lineup(start).league, 'WorldTour7Races')
        self.assertTrue(schedule.is_weekend_time(start))

    def test_schedule_changes_at_a_calendar_boundary(self):
        start = at(2026, 9, 15, 23, 30)
        found = list(self.data.intervals(start, start + 60 * 60))
        self.assertEqual([(begin - start) // 60 for begin, _, _ in found],
                         [0, 10, 30, 40])
        self.assertEqual([end for _, end, _ in found][1], at(2026, 9, 16))
        self.assertIs(found[0][2], found[1][2])
        self.assertIsNot(found[1][2], found[2][2])
        self.assertEqual(self.data.schedule_at(found[2][0]).window[0], at(2026, 9, 16))

    def test_shuffle_bonus(self):
        schedule = self.data.schedule_at(at(2026, 10, 10))
        self.assertEqual(schedule.bonus.get('Type'), 1)
        self.assertTrue(schedule.is_weekend_time(at(2026, 10, 10, 12)))
        self.assertFalse(schedule.is_weekend_time(at(2026, 10, 9, 12)))


class DropTestCase(unittest.TestCase):
    """ A BCAT drop: the Lightning Festival files, with a 5/15-minute cycle
        and no Secret League.
    """
    @classmethod
    def setUpClass(cls):
        cls.data = gameschedule.ScheduleData(load('meteor', 'GameScheduleV1'),
                                             load('meteor', 'WeekendSchedule'))

    def test_active_window(self):
        self.assertEqual(self.data.active_window, (at(2026, 10, 19), at(2026, 11, 9)))
        self.assertEqual(self.data.calendar, [])

    def test_compressed_cycle(self):
        start = at(2026, 10, 22, 0, 0)
        found = [((begin - start) // 60, (end - begin) // 60,
                  schedule.lineup(begin).mode)
                 for begin, end, schedule
                 in self.data.intervals(start, start + 40 * 60)]
        self.assertEqual(found, [(0, 5, 'GrandPrixRotation'), (5, 15, 'Teams'),
                                 (20, 5, 'ClassicMiniPrixRotation'),
                                 (25, 15, 'HardTracks')])

    def test_no_secret_league(self):
        start = at(2026, 10, 22, 0, 0)
        secrets = [schedule.lineup(begin).secret
                   for begin, _, schedule
                   in self.data.intervals(start, start + 1440 * 60)]
        self.assertEqual(set(secrets), {None})


class LeagueTracksTestCase(unittest.TestCase):
    def test_mini_prix_leagues(self):
        with open(os.path.join(CONFIG, 'StageList.json')) as fd:
            leagues = gameschedule.league_tracks(json.load(fd))
        self.assertEqual(leagues['MiniPrix001'],
                         ['Mute_City_I', 'Sand_Ocean', 'Sand_Storm_II'])
        self.assertEqual(leagues['ClassicMiniPrix029'],
                         ['Death_Wind_I', 'Sand_Storm_II', 'Red_Canyon_II'])
        mini_prix = [name for name in leagues if name.startswith('MiniPrix0')]
        self.assertEqual(len(mini_prix), 43)


if __name__ == "__main__":
    unittest.main()
