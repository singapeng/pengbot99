# Python imports
import os
import shutil
import tempfile
import unittest
from datetime import date

# Local imports
from pengbot99 import explain_cmd, schedule_controller, utils


class ScheduleControllerTestCase(unittest.TestCase):
    """ Verify that the schedule controller loads, switches and unloads
        schedule profiles, and that reads delegate to the active schedule
        while the slot 1 schedule stays global.
    """

    DEFAULT_CONSTANTS = (
        "CLASSIC_LINE_UP_OFFSET=0\n"
        "MINIPRIX_LINE_UP_OFFSET=23\n"
        "MIRROR_LINE_UP_OFFSET=1\n"
        "PRIVATE_MP_MINUTE_OFFSET=17\n"
        "PRIVATE_MP_MIRROR_MINUTE_OFFSET=0\n"
        "PRIVATE_CMP_MINUTE_OFFSET=8\n"
        "NINETYNINE_MINUTE_OFFSET=25\n"
        "SECRET_LEAGUE_ENABLED=1\n"
        "SECRET_LEAGUE_INTERVALS=11,6,7,3,8,4\n"
        "SECRET_LEAGUE_OFFSET=21\n"
        "WEEKEND_SECRET_LEAGUE_ENABLED=0\n"
        "WEEKEND_SECRET_LEAGUE_INTERVALS=22,12,14,6,16,8\n"
        "WEEKEND_SECRET_LEAGUE_OFFSET=60\n"
        "SHUFFLE_ENABLED=0\n"
        "SHUFFLE_MINIPRIX_LINE_UP_OFFSET=19\n"
        "SHUFFLE_MIRROR_LINE_UP_OFFSET=1\n"
        "PRIVATE_SHUFFLE_MP_MINUTE_OFFSET=12\n"
        "PRIVATE_SHUFFLE_MP_MIRROR_MINUTE_OFFSET=0\n"
    )
    SHUFFLE_CONSTANTS = (
        "# Machine Shuffle event overrides\n"
        "SHUFFLE_ENABLED=1\n"
        "SHUFFLE_MINIPRIX_LINE_UP_OFFSET=14\n"
        "SECRET_LEAGUE_OFFSET=18\n"
    )
    METEOR_CONSTANTS = (
        "# Meteor Festival event overrides\n"
        "SECRET_LEAGUE_ENABLED=0\n"
        "CLASSIC_LINE_UP_OFFSET=3\n"
    )
    # files copied verbatim from the tests fixtures into the default
    # profile folder, so schedules are valid and need no handcrafting.
    DEFAULT_CSVS = (
        "slot2_schedule.csv",
        "slot2_schedule_weekend.csv",
        "miniprix_schedule.csv",
        "miniprix_mirroring_schedule.csv",
        "private_miniprix_schedule.csv",
        "slot1_schedule.csv",
        "ninetynine_schedule.csv",
    )
    PRIVATE_CLASSIC_MP = (
        "0,Silence,White_Land_II,Fire_Field\n"
        "15,next\n"
    )
    CLASSIC_MP = (
        "0,Silence > White_Land_II > Fire_Field\n"
        "15,next\n"
    )

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = self._tmpdir.name
        self.fixtures = os.path.join(os.path.dirname(__file__), 'fixtures')
        default_dir = os.path.join(self.root, "event_default")
        os.makedirs(default_dir)
        for name in self.DEFAULT_CSVS:
            shutil.copy(os.path.join(self.fixtures, name), default_dir)
        with open(os.path.join(default_dir, "private_classic_mp_schedule.csv"),
                  "w") as fd:
            fd.write(self.PRIVATE_CLASSIC_MP)
        with open(os.path.join(default_dir, "classic_mp_schedule.csv"), "w") as fd:
            fd.write(self.CLASSIC_MP)
        with open(os.path.join(default_dir, "constants.dat"), "w") as fd:
            fd.write(self.DEFAULT_CONSTANTS)
        # profile folders only override constants; all schedules fall
        # back to the default profile folder.
        for profile, constants in (("machine_shuffle", self.SHUFFLE_CONSTANTS),
                                   ("meteor", self.METEOR_CONSTANTS)):
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

    def load_default_csts(self, profile='default'):
        env = utils.load_env(self._env_path)
        return env, utils.load_csts(env, profile)

    def test_startup_profile_is_active(self):
        c = self.create_controller()
        self.assertEqual(c.name, 'default')
        self.assertEqual(c.active.name, 'default')
        self.assertIn('default', c.list())

    def test_reads_delegate_to_active_schedule(self):
        c = self.create_controller()
        self.assertIs(c.slot2mgr, c.active.slot2mgr)
        for mgr in ("cmp_mgr", "mp_mgr", "pmp_mgr", "pcmp_mgr", "smp_mgr", "psmp_mgr"):
            self.assertIs(getattr(c, mgr), getattr(c.active, mgr))

    def test_is_shuffle_on_reflects_active_schedule(self):
        c = self.create_controller()
        self.assertFalse(c.is_shuffle_on())
        c.switch('machine_shuffle')
        self.assertTrue(c.is_shuffle_on())
        self.assertIsNotNone(c.smp_mgr)
        self.assertIsNotNone(c.psmp_mgr)

    def test_global_slot1_schedule(self):
        c = self.create_controller()
        self.assertIsNotNone(c.slot1mgr)
        self.assertIs(c.r99_mgr.glitch_manager, c.slot1mgr)

    def test_load_registers_without_activating(self):
        c = self.create_controller()
        c.load('machine_shuffle')
        self.assertEqual(c.name, 'default')
        self.assertIn('machine_shuffle', c.list())

    def test_load_is_idempotent(self):
        c = self.create_controller()
        sched = c.load('meteor')
        self.assertIs(c.load('meteor'), sched)

    def test_switch_activates_loaded_schedule(self):
        c = self.create_controller()
        default = c.active
        c.load('machine_shuffle')
        c.switch('machine_shuffle')
        self.assertEqual(c.name, 'machine_shuffle')
        self.assertIsNot(c.slot2mgr, default.slot2mgr)
        self.assertIs(c.slot2mgr, c.active.slot2mgr)

    def test_switch_lazy_loads(self):
        c = self.create_controller()
        c.switch('meteor')
        self.assertEqual(c.name, 'meteor')
        self.assertIn('meteor', c.list())

    def test_switch_uses_profile_constants(self):
        c = self.create_controller()
        c.switch('meteor')
        # Meteor disables Secret League, so its slot2 mananger must too
        self.assertFalse(c.slot2mgr.is_secret_league_on())

    def test_switching_back_preserves_managers(self):
        c = self.create_controller()
        default = c.active
        c.switch('meteor')
        c.switch('default')
        self.assertIs(c.slot2mgr, default.slot2mgr)
        self.assertIs(c.r99_mgr, c.r99_mgr)

    def test_unload_active_forbidden(self):
        c = self.create_controller()
        c.switch('machine_shuffle')
        with self.assertRaises(ValueError):
            c.unload('machine_shuffle')
        self.assertIn('machine_shuffle', c.list())

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
        env, _ = self.load_default_csts()
        sched = schedule_controller.ScheduleProfile(env, 'machine_shuffle')
        self.assertTrue(sched.is_shuffle_on())

    def test_controller_loads_own_constants(self):
        env = utils.load_env(self._env_path)
        c = schedule_controller.ScheduleController(env, profile='default')
        self.assertEqual(c.name, 'default')

    def test_explainer_reads_active_slot2mgr(self):
        c = self.create_controller()
        default_mgr = c.slot2mgr
        explainer = explain_cmd.Explainer(None, c)
        self.assertIs(explainer._mgr, default_mgr)
        # the explainer holds the controller, so it follows a switch
        c.switch('meteor')
        self.assertIs(explainer._mgr, c.slot2mgr)
        self.assertIsNot(explainer._mgr, default_mgr)

    def test_explainer_gp_rotation_via_controller(self):
        c = self.create_controller()
        explainer = explain_cmd.Explainer(None, c)
        result = explainer.explain('Grand Prix Rotation')
        self.assertIsInstance(result, str)
        self.assertTrue(result)


class ProfileSwitchConfigTestCase(unittest.TestCase):
    """ Verify server_events.csv parsing and the profile switch helper.
    """

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = self._tmpdir.name
        self.env = {'CONFIG_PATH': self.root}

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