import io
import logging
import os
import sys
import tempfile
import unittest

from pengbot99 import schedule, utils


class TestScheduleConfigProfile(unittest.TestCase):
    """ Verify that schedule configuration is resolved from profile folders
        of the CONFIG_PATH root, and that an event profile overlays the
        default config. Uses fixtures mirroring the 'queen' weekend event.
    """

    DEFAULT_CONSTANTS = (
        "SECRET_LEAGUE_ENABLED=1\n"
        "SECRET_LEAGUE_OFFSET=21\n"
        "WEEKEND_SECRET_LEAGUE_ENABLED=0\n"
        "NINETYNINE_MINUTE_OFFSET=25\n"
    )
    QUEEN_CONSTANTS = (
        "# Queen Leagues Weekend Event overrides\n"
        "SECRET_LEAGUE_OFFSET=30\n"
        "WEEKEND_SECRET_LEAGUE_ENABLED=1\n"
    )
    DEFAULT_WEEKEND = (
        "0,mace,knight,mqueen,king,mknight,queen,mking,ace,mqueen,king,mace,knight,mking,ace,mknight,queen\n"
        "10,teambattle,protracks,classic\n"
        "30,next\n"
    )
    QUEEN_WEEKEND = (
        "0,queen,knight,mqueen,mknight,queen,king,mqueen,mking,queen,ace,mqueen,mace\n"
        "10,teambattle,protracks,classic\n"
        "30,next\n"
    )
    CLASSIC_SCHEDULE = (
        "0,Silence,White_Land_II,Fire_Field\n"
        "15,next\n"
    )

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = self._tmpdir.name
        default_dir = os.path.join(self.root, "event_default")
        queen_dir = os.path.join(self.root, "event_queen")
        os.makedirs(default_dir)
        os.makedirs(queen_dir)
        with open(os.path.join(default_dir, "constants.dat"), "w") as fd:
            fd.write(self.DEFAULT_CONSTANTS)
        with open(os.path.join(queen_dir, "constants.dat"), "w") as fd:
            fd.write(self.QUEEN_CONSTANTS)
        with open(os.path.join(default_dir, "slot2_schedule_weekend.csv"), "w") as fd:
            fd.write(self.DEFAULT_WEEKEND)
        with open(os.path.join(queen_dir, "slot2_schedule_weekend.csv"), "w") as fd:
            fd.write(self.QUEEN_WEEKEND)
        # a schedule file only present in default, to exercise fallback
        with open(os.path.join(default_dir, "classic_mp_schedule.csv"), "w") as fd:
            fd.write(self.CLASSIC_SCHEDULE)
        # explainer data loads from the config root, not a profile folder
        with open(os.path.join(self.root, "explain.dat"), "w") as fd:
            fd.write("QUEEN_LEAGUE=often on weekends\n")
        self._env_path = os.path.join(self.root, ".env")
        with open(self._env_path, "w") as fd:
            fd.write("CONFIG_PATH={0}\n".format(self.root))
            fd.write("CONSTANTS_FILE=constants.dat\n")
            fd.write("EXPLAIN_FILE=explain.dat\n")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_schedule_dir_resolves_default(self):
        env = {"CONFIG_PATH": self.root}
        self.assertEqual(utils.get_schedule_dir(env),
                         os.path.join(self.root, "event_default"))

    def test_schedule_dir_accepts_profile(self):
        env = {"CONFIG_PATH": self.root}
        self.assertEqual(utils.get_schedule_dir(env, profile="queen"),
                         os.path.join(self.root, "event_queen"))

    def test_constants_loaded_from_default_profile(self):
        env, csts, xpln = utils.load_config(path=self._env_path)
        self.assertEqual(csts["SECRET_LEAGUE_OFFSET"], "21")
        self.assertEqual(csts["WEEKEND_SECRET_LEAGUE_ENABLED"], "0")

    def test_explicit_default_profile_is_unchanged(self):
        env, csts, xpln = utils.load_config(path=self._env_path, profile="default")
        self.assertEqual(csts["SECRET_LEAGUE_OFFSET"], "21")
        self.assertEqual(csts["WEEKEND_SECRET_LEAGUE_ENABLED"], "0")

    def test_profile_constants_override_default(self):
        env, csts, xpln = utils.load_config(path=self._env_path, profile="queen")
        self.assertEqual(csts["SECRET_LEAGUE_OFFSET"], "30")
        self.assertEqual(csts["WEEKEND_SECRET_LEAGUE_ENABLED"], "1")
        # constants not overridden by the profile are inherited
        self.assertEqual(csts["SECRET_LEAGUE_ENABLED"], "1")
        self.assertEqual(csts["NINETYNINE_MINUTE_OFFSET"], "25")

    def test_explain_loaded_from_config_root(self):
        env, csts, xpln = utils.load_config(path=self._env_path, profile="queen")
        self.assertEqual(xpln["QUEEN_LEAGUE"], "often on weekends")

    def test_profile_schedule_overrides_default(self):
        default_dir = os.path.join(self.root, "event_default")
        queen_dir = os.path.join(self.root, "event_queen")
        sched = schedule.load_schedule(queen_dir, "slot2_schedule_weekend", default_dir)
        self.assertEqual(sched[0][1], "queen")

    def test_profile_schedule_falls_back_to_default(self):
        default_dir = os.path.join(self.root, "event_default")
        queen_dir = os.path.join(self.root, "event_queen")
        override = schedule.load_schedule(queen_dir, "classic_mp_schedule", default_dir)
        baseline = schedule.load_schedule(default_dir, "classic_mp_schedule")
        self.assertEqual(override, baseline)

    def test_load_schedule_still_works_without_default_path(self):
        default_dir = os.path.join(self.root, "event_default")
        sched = schedule.load_schedule(default_dir, "slot2_schedule_weekend")
        self.assertEqual(sched[0][1], "mace")

    def test_is_valid_profile_true_for_default(self):
        env = {"CONFIG_PATH": self.root}
        self.assertTrue(utils.is_valid_profile(env))

    def test_is_valid_profile_true_for_existing_event(self):
        env = {"CONFIG_PATH": self.root}
        self.assertTrue(utils.is_valid_profile(env, "queen"))

    def test_is_valid_profile_false_for_unknown_event(self):
        env = {"CONFIG_PATH": self.root}
        self.assertFalse(utils.is_valid_profile(env, "not_a_profile"))


class TestLogging(unittest.TestCase):
    """ Verify that log() routes through the logging module, and that
        silence_logging() toggles the effective log level.
    """

    def setUp(self):
        self._logger = utils.logger
        self._stream = io.StringIO()
        self._handler = logging.StreamHandler(self._stream)
        self._handler.setFormatter(
            logging.Formatter(utils.LOG_FORMAT, datefmt=utils.LOG_DATEFMT))
        self._handler.setLevel(logging.INFO)
        self._previous_handlers = self._logger.handlers[:]
        self._previous_level = self._logger.level
        self._logger.handlers[:] = [self._handler]
        self._logger.setLevel(logging.INFO)

    def tearDown(self):
        self._logger.handlers[:] = self._previous_handlers
        self._logger.setLevel(self._previous_level)

    def captured(self, *texts):
        for text in texts:
            utils.log(text)
        return self._stream.getvalue()

    def test_log_prints_timestamped_line_by_default(self):
        out = self.captured("hello")
        self.assertRegex(out, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} hello\n$")

    def test_silence_logging_hides_info_lines(self):
        with utils.silence_logging():
            self.assertEqual(self.captured("hidden"), "")

    def test_silence_logging_keeps_warnings(self):
        with utils.silence_logging():
            out = self.captured("WARNING: something is off")
        self.assertRegex(
            out,
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} WARNING: something is off\n$")

    def test_logging_restored_after_context(self):
        with utils.silence_logging():
            self.assertEqual(self.captured("hidden"), "")
        self.assertIn("visible", self.captured("visible"))

    def test_log_is_silent_by_default(self):
        # with only the default null handler (as in the test suite),
        # neither info nor warning output reaches the console
        self._logger.handlers[:] = [logging.NullHandler()]
        self._logger.setLevel(logging.NOTSET)
        self.assertEqual(self.captured("hidden", "WARNING: also hidden"), "")

    def test_configure_logging_adds_console_handler(self):
        self._logger.handlers[:] = [logging.NullHandler()]
        utils.configure_logging()
        stream_handlers = [h for h in self._logger.handlers
                           if isinstance(h, logging.StreamHandler)]
        self.assertEqual(len(stream_handlers), 1)
        self.assertIs(stream_handlers[0].stream, sys.stdout)


if __name__ == "__main__":
    unittest.main()