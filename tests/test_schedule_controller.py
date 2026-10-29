# Python imports
import os
import shutil
import tempfile
import unittest
from datetime import date, datetime, timezone

# Local imports
from pengbot99 import explain_cmd, gameevents, schedule_controller, utils

CONFIG = os.path.join(os.path.dirname(__file__), '..', 'py', 'pengbot99', 'data')
UTC = timezone.utc


class ScheduleControllerTestCase(unittest.TestCase):
    """ Verify that the schedule controller loads, switches and unloads
        schedule profiles built from the game's schedule files, and that
        reads delegate to the active profile.
    """

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = self._tmpdir.name
        shutil.copy(os.path.join(CONFIG, 'StageList.json'), self.root)
        shutil.copytree(os.path.join(CONFIG, 'event_default'),
                        os.path.join(self.root, "event_default"))
        # a profile with its own drop of the schedule files and no constants
        shutil.copytree(os.path.join(CONFIG, 'event_meteor'),
                        os.path.join(self.root, "event_meteor"))
        # profiles pinning a weekend event of the default files
        pinned = (("queen", "WEEKEND_SCHEDULE_ID=QueenLeagueWeekend\n"),
                  ("plain", "WEEKEND_SCHEDULE_ID=none\n"),
                  ("bogus", "WEEKEND_SCHEDULE_ID=NoSuchWeekend\n"))
        for profile, constants in pinned:
            profile_dir = os.path.join(self.root, "event_{0}".format(profile))
            os.makedirs(profile_dir)
            with open(os.path.join(profile_dir, "constants.dat"), "w") as fd:
                fd.write(constants)
        self._env_path = os.path.join(self.root, ".env")
        with open(self._env_path, "w") as fd:
            fd.write("CONFIG_PATH={0}\n".format(self.root))
            fd.write("CONSTANTS_FILE=constants.dat\n")

    def tearDown(self):
        self._tmpdir.cleanup()

    def create_controller(self, profile='default', csts=None):
        env = utils.load_env(self._env_path)
        return schedule_controller.ScheduleController(env, profile=profile, csts=csts)

    def test_startup_profile_is_active(self):
        c = self.create_controller()
        self.assertEqual(c.name, 'default')
        self.assertEqual(c.active.name, 'default')
        self.assertIn('default', c.list())

    def test_reads_delegate_to_active_schedule(self):
        c = self.create_controller()
        for mgr in ("slot1mgr", "slot2mgr", "r99_mgr", "cmp_mgr", "mp_mgr", "pmp_mgr",
                    "pcmp_mgr", "lineup_mgrs"):
            self.assertIs(getattr(c, mgr), getattr(c.active, mgr))

    def test_profile_builds_every_manager(self):
        c = self.create_controller()
        self.assertIsInstance(c.slot2mgr, gameevents.SlotScheduleManager)
        self.assertIsInstance(c.slot1mgr, gameevents.MysteryTrackManager)
        self.assertIsInstance(c.r99_mgr, gameevents.NinetyNineManager)
        self.assertFalse(c.mp_mgr.private)
        self.assertTrue(c.pmp_mgr.private)
        self.assertFalse(c.cmp_mgr.private)
        self.assertTrue(c.pcmp_mgr.private)
        self.assertEqual(sorted(c.lineup_mgrs),
                         [(mode, private)
                          for mode in ('classic', 'protracks', 'teambattle')
                          for private in (False, True)])

    def test_default_profile_follows_the_calendar(self):
        c = self.create_controller()
        self.assertEqual(c.weekend_event(datetime(2026, 9, 19, tzinfo=UTC)),
                         'QueenLeagueWeekend')
        self.assertIsNone(c.weekend_event(datetime(2026, 10, 15, tzinfo=UTC)))
        self.assertEqual(len(c.calendar()), 26)

    def test_pinned_profile_runs_its_event_at_any_time(self):
        c = self.create_controller()
        c.switch('queen')
        for when in (datetime(2026, 9, 19, tzinfo=UTC),
                     datetime(2026, 10, 15, tzinfo=UTC)):
            self.assertEqual(c.weekend_event(when), 'QueenLeagueWeekend')
        self.assertEqual(c.calendar(), [])

    def test_none_profile_ignores_the_calendar(self):
        c = self.create_controller()
        c.switch('plain')
        self.assertIsNone(c.weekend_event(datetime(2026, 9, 19, tzinfo=UTC)))

    def test_unknown_pinned_event_fails_to_load(self):
        c = self.create_controller()
        with self.assertRaises(KeyError):
            c.load('bogus')

    def test_profile_with_own_files_and_no_constants(self):
        c = self.create_controller()
        c.switch('meteor')
        self.assertEqual(c.name, 'meteor')
        start, end = c.data.active_window
        self.assertEqual(gameevents.from_unix(start),
                         datetime(2026, 10, 19, tzinfo=UTC))
        self.assertEqual(gameevents.from_unix(end), datetime(2026, 11, 9, tzinfo=UTC))
        self.assertIsNone(c.weekend_event(datetime(2026, 10, 24, tzinfo=UTC)))

    def test_load_registers_without_activating(self):
        c = self.create_controller()
        c.load('queen')
        self.assertEqual(c.name, 'default')
        self.assertIn('queen', c.list())

    def test_load_is_idempotent(self):
        c = self.create_controller()
        sched = c.load('meteor')
        self.assertIs(c.load('meteor'), sched)

    def test_switch_activates_loaded_schedule(self):
        c = self.create_controller()
        default = c.active
        c.load('queen')
        c.switch('queen')
        self.assertEqual(c.name, 'queen')
        self.assertIsNot(c.slot2mgr, default.slot2mgr)
        self.assertIs(c.slot2mgr, c.active.slot2mgr)

    def test_switch_lazy_loads(self):
        c = self.create_controller()
        c.switch('meteor')
        self.assertEqual(c.name, 'meteor')
        self.assertIn('meteor', c.list())

    def test_switch_uses_profile_data(self):
        c = self.create_controller()
        when = datetime(2026, 10, 24, 12, tzinfo=UTC)
        self.assertTrue(c.slot2mgr.is_secret_league_on(when))
        c.switch('meteor')
        # the meteor drop lists no Secret League windows
        self.assertFalse(c.slot2mgr.is_secret_league_on(when))

    def test_switching_back_preserves_managers(self):
        c = self.create_controller()
        default = c.active
        c.switch('meteor')
        c.switch('default')
        self.assertIs(c.slot2mgr, default.slot2mgr)
        self.assertIs(c.r99_mgr, default.r99_mgr)

    def test_unload_active_forbidden(self):
        c = self.create_controller()
        c.switch('queen')
        with self.assertRaises(ValueError):
            c.unload('queen')
        self.assertIn('queen', c.list())

    def test_unload_loaded_schedule(self):
        c = self.create_controller()
        c.load('meteor')
        c.unload('meteor')
        self.assertNotIn('meteor', c.list())
        self.assertEqual(c.list(), ['default'])

    def test_switch_reloads_after_unload(self):
        c = self.create_controller()
        c.switch('meteor')
        c.switch('default')
        c.unload('meteor')
        self.assertNotIn('meteor', c.list())
        # unload only frees the schedule; a later switch lazy-loads it
        c.switch('meteor')
        self.assertEqual(c.name, 'meteor')
        self.assertIn('meteor', c.list())

    def test_unload_missing_schedule_is_noop(self):
        c = self.create_controller()
        c.unload('not_a_profile')
        self.assertEqual(c.list(), ['default'])

    def test_profile_schedule_loads_own_constants(self):
        env = utils.load_env(self._env_path)
        sched = schedule_controller.ScheduleProfile(env, 'queen')
        self.assertEqual(sched.weekend_event(datetime(2026, 10, 15, tzinfo=UTC)),
                         'QueenLeagueWeekend')

    def test_controller_loads_own_constants(self):
        env = utils.load_env(self._env_path)
        c = schedule_controller.ScheduleController(env, profile='default')
        self.assertEqual(c.name, 'default')

    def test_explainer_reads_active_slot2mgr(self):
        c = self.create_controller()
        default_mgr = c.slot2mgr
        explainer = explain_cmd.Explainer(c)
        self.assertIs(explainer._mgr, default_mgr)
        # the explainer holds the controller, so it follows a switch
        c.switch('meteor')
        self.assertIs(explainer._mgr, c.slot2mgr)
        self.assertIsNot(explainer._mgr, default_mgr)

    def test_explainer_gp_rotation_via_controller(self):
        c = self.create_controller()
        explainer = explain_cmd.Explainer(c)
        result = explainer.explain('Grand Prix Rotation')
        self.assertIsInstance(result, str)
        self.assertIn('16 Grand Prix-long', result)

    def test_explainer_describes_the_weekend_event(self):
        c = self.create_controller()
        explainer = explain_cmd.Explainer(c)
        now = datetime(2026, 9, 19, 12, tzinfo=UTC)
        current = explainer.explain_current_schedule(now)
        self.assertIn('Queen Leagues Weekend Event** weekend event', current)
        self.assertIn('This event ends <t:1790035200:F>', current)  # Sep 22 00:00 UTC
        upcoming = explainer.explain_upcoming_events(now)
        self.assertIn('Queen Leagues Weekend Event (Default Schedule', upcoming)
        self.assertIn('<t:1790553600:F>   <:WTMini:1462608159913934881> '
                      'Mini World Tour Week', upcoming)  # Sep 28 00:00 UTC
        self.assertIn('Current And Upcoming Events', explainer.topics)


class ProfileSwitchConfigTestCase(unittest.TestCase):
    """ Verify EVENT_SCHEDULE_FILE parsing and the profile switch helper.
    """

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = self._tmpdir.name
        self.env = {'CONFIG_PATH': self.root,
                    'EVENT_SCHEDULE_FILE': 'server_events.csv'}

    def tearDown(self):
        self._tmpdir.cleanup()

    def write_switch_config(self, text):
        path = os.path.join(self.root, 'server_events.csv')
        with open(path, "w") as fd:
            fd.write(text)
        return path

    def test_active_before_first_switch_is_default(self):
        cfg = schedule_controller.ProfileSwitchConfig(rows=[
            ['2025-06-01', 'meteor'],
        ])
        self.assertEqual(cfg.active_on(date(2025, 5, 31)), 'default')

    def test_active_on_switch_date(self):
        cfg = schedule_controller.ProfileSwitchConfig(rows=[
            ['2025-06-01', 'meteor'],
        ])
        self.assertEqual(cfg.active_on(date(2025, 6, 1)), 'meteor')
        self.assertEqual(cfg.active_on(date(2025, 7, 1)), 'meteor')

    def test_latest_switch_up_to_date_wins(self):
        cfg = schedule_controller.ProfileSwitchConfig(rows=[
            ['2025-05-01', 'meteor'],
            ['2025-06-01', 'default'],
            ['2025-07-01', 'machine_shuffle'],
        ])
        self.assertEqual(cfg.active_on(date(2025, 6, 15)), 'default')
        self.assertEqual(cfg.active_on(date(2025, 7, 1)), 'machine_shuffle')

    def test_unsorted_rows_are_sorted(self):
        cfg = schedule_controller.ProfileSwitchConfig(rows=[
            ['2025-07-01', 'machine_shuffle'],
            ['2025-05-01', 'meteor'],
        ])
        self.assertEqual(cfg.active_on(date(2025, 6, 1)), 'meteor')

    def test_profiles_unique_in_order(self):
        cfg = schedule_controller.ProfileSwitchConfig(rows=[
            ['2025-05-01', 'meteor'],
            ['2025-06-01', 'default'],
            ['2025-07-01', 'meteor'],
        ])
        self.assertEqual(cfg.profiles, ['meteor', 'default'])

    def test_comments_and_blank_rows_ignored(self):
        cfg = schedule_controller.ProfileSwitchConfig(rows=[
            ['# a comment'],
            ['2025-06-01', 'meteor'],
            [],
        ])
        self.assertEqual(cfg.profiles, ['meteor'])
        self.assertEqual(cfg.active_on(date(2025, 6, 1)), 'meteor')

    def test_malformed_date_rows_ignored(self):
        cfg = schedule_controller.ProfileSwitchConfig(rows=[
            ['not-a-date', 'meteor'],
            ['2025-06-01', 'meteor'],
        ])
        self.assertEqual(cfg.profiles, ['meteor'])
        self.assertEqual(cfg.active_on(date(2025, 6, 1)), 'meteor')

    def test_row_with_missing_profile_ignored(self):
        cfg = schedule_controller.ProfileSwitchConfig(rows=[
            ['2025-06-01'],
            ['2025-06-02', 'meteor'],
        ])
        self.assertEqual(cfg.active_on(date(2025, 6, 1)), 'default')
        self.assertEqual(cfg.active_on(date(2025, 6, 2)), 'meteor')

    def test_load_profile_switches_absent_returns_none(self):
        self.assertIsNone(schedule_controller.load_profile_switches(self.env))

    def test_load_profile_switches_parses_file(self):
        self.write_switch_config("2025-06-01,meteor\n")
        cfg = schedule_controller.load_profile_switches(self.env)
        self.assertIsInstance(cfg, schedule_controller.ProfileSwitchConfig)
        self.assertEqual(cfg.active_on(date(2025, 6, 1)), 'meteor')

    def test_load_profile_switches_ignores_comments(self):
        self.write_switch_config("# next event\n2025-06-01,meteor\n")
        cfg = schedule_controller.load_profile_switches(self.env)
        self.assertEqual(cfg.profiles, ['meteor'])


if __name__ == "__main__":
    unittest.main()
