# Python imports
import os
import tempfile
import unittest

# local imports
from conftest import FIXTURES_DIR
from pengbot99 import schedule, utils


class TestPackagedSchedules(unittest.TestCase):
    """ The game content ships with the package.

        A caller with no checkout, no .env and no CONFIG_PATH must still be
        able to compute the schedule: that is the whole point of installing
        this as a library.
    """

    # Every schedule the bot loads at startup, plus the quotes file.
    SHIPPED_SCHEDULES = (
        "classic_mp_schedule",
        "miniprix_mirroring_schedule",
        "miniprix_schedule",
        "ninetynine_schedule",
        "private_classic_mp_schedule",
        "private_miniprix_schedule",
        "slot1_schedule",
        "slot2_schedule",
        "slot2_schedule_weekend",
    )

    def test_every_shipped_schedule_loads_without_a_path(self):
        for name in self.SHIPPED_SCHEDULES:
            with self.subTest(schedule=name):
                sched = schedule.load_schedule(None, name)
                self.assertEqual(sched[-1][1], "next")

    def test_quotes_load_without_a_path(self):
        from pengbot99 import misa

        self.assertTrue(misa.load_quotes(None))


class TestConfigPathPrecedence(unittest.TestCase):
    """ CONFIG_PATH overrides the packaged files and wins.

        This is what keeps an instance run from a directory of hand-edited
        CSVs loading those files rather than the ones that shipped. The
        assertions compare against a fixture that differs from the shipped
        file, so an inverted precedence fails rather than passing quietly.
    """

    def test_the_fixture_differs_from_the_shipped_file(self):
        # Guards the two tests below: they prove nothing if the fixture and
        # the shipped schedule happen to have the same content.
        packaged = schedule.load_schedule(None, "slot2_schedule")
        override = schedule.load_schedule(FIXTURES_DIR, "slot2_schedule")
        self.assertNotEqual(packaged, override)

    def test_a_path_wins_over_the_packaged_schedule(self):
        override = schedule.load_schedule(FIXTURES_DIR, "slot2_schedule")
        # The fixture's opening rotation is six tracks; the shipped one is 16.
        self.assertEqual(len(override[0]) - 1, 6)

    def test_constants_default_to_the_packaged_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w") as fd:
                fd.write("DISCORD_BOT_TOKEN=bogus\n")
            env, csts, xpln = utils.load_config(env_path)
        self.assertNotIn("CONFIG_PATH", env)
        self.assertEqual(csts["MINIPRIX_LINE_UP_OFFSET"], "23")
        # EXPLAIN_FILE has no packaged default: nothing in the package reads it.
        self.assertIsNone(xpln)

    def test_config_path_wins_over_the_packaged_constants(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "constants.dat"), "w") as fd:
                fd.write("# overridden\nMINIPRIX_LINE_UP_OFFSET=999\n")
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w") as fd:
                fd.write("CONFIG_PATH={0}\n".format(tmp))
            _env, csts, _xpln = utils.load_config(env_path)
        self.assertEqual(csts["MINIPRIX_LINE_UP_OFFSET"], "999")


if __name__ == "__main__":
    unittest.main()
