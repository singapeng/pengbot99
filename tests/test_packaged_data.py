# Python imports
import os
import tempfile
import unittest
from datetime import datetime, timezone

# local imports
from pengbot99 import schedule_controller, utils

# 2026-10-17 is a Saturday.
WEEKEND = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


class TestPackagedSchedules(unittest.TestCase):
    """ The game's schedule files ship with the package.

        A caller with no checkout, no .env and no CONFIG_PATH must still be
        able to compute the schedule: that is the whole point of installing
        this as a library.
    """

    def test_the_default_profile_is_packaged(self):
        self.assertIn('default', utils.list_profiles({}))

    def test_every_packaged_profile_builds(self):
        for name in utils.list_profiles({}):
            with self.subTest(profile=name):
                sched = schedule_controller.ScheduleProfile({}, name)
                self.assertTrue(sched.slot2mgr.list_events(timestamp=WEEKEND, next=60))
                self.assertTrue(sched.r99_mgr.list_events(timestamp=WEEKEND, next=1))

    def test_the_league_tracks_are_packaged(self):
        leagues = schedule_controller.load_league_tracks({})
        self.assertIn('KnightLeague', leagues)

    def test_the_switch_calendar_is_packaged(self):
        env = {'EVENT_SCHEDULE_FILE': 'server_events.csv'}
        self.assertIsNotNone(schedule_controller.load_profile_switches(env))


class TestConfigPathPrecedence(unittest.TestCase):
    """ CONFIG_PATH overrides the packaged files and wins.

        This is what keeps an instance run from a directory of hand-edited
        files loading those rather than the ones that shipped. The override
        pins a weekend event the packaged default follows by calendar, so an
        inverted precedence fails rather than passing quietly.
    """

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = self._tmpdir.name
        default_dir = os.path.join(self.root, 'event_default')
        os.makedirs(default_dir)
        packaged_default = utils.get_schedule_dir({})
        for name in (schedule_controller.GAME_SCHEDULE_FILE,
                     schedule_controller.WEEKEND_SCHEDULE_FILE):
            with utils.open_data_file(packaged_default, name) as fd:
                content = fd.read()
            with open(os.path.join(default_dir, name), 'w') as fd:
                fd.write(content)
        with utils.open_data_file(None, schedule_controller.STAGE_LIST_FILE) as fd:
            content = fd.read()
        stage_list = os.path.join(self.root, schedule_controller.STAGE_LIST_FILE)
        with open(stage_list, 'w') as fd:
            fd.write(content)
        with open(os.path.join(default_dir, 'constants.dat'), 'w') as fd:
            fd.write('WEEKEND_SCHEDULE_ID=QueenLeagueWeekend\n')

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_the_packaged_default_follows_the_calendar(self):
        # Guards the test below: it proves nothing if the packaged default
        # pins the same event.
        self.assertEqual(utils.load_constants()['WEEKEND_SCHEDULE_ID'], 'auto')
        self.assertTrue(schedule_controller.ScheduleProfile({}, 'default').calendar())

    def test_a_path_wins_over_the_packaged_files(self):
        env = {'CONFIG_PATH': self.root}
        self.assertEqual(utils.load_csts(env)['WEEKEND_SCHEDULE_ID'],
                         'QueenLeagueWeekend')
        sched = schedule_controller.ScheduleProfile(env, 'default')
        self.assertEqual(sched.calendar(), [])
        self.assertEqual(sched.weekend_event(WEEKEND), 'QueenLeagueWeekend')

    def test_a_path_without_the_profile_is_refused(self):
        # The packaged profiles are not consulted behind a CONFIG_PATH.
        with self.assertRaises(FileNotFoundError):
            utils.load_constants(self.root, 'queen')


if __name__ == "__main__":
    unittest.main()
