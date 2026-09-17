# Python imports
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# local imports
from pengbot99 import managers, schedule, utils

# Shuffle Weekend is off in the shipped constants: SHUFFLE_ENABLED is 0, and
# the constants that tune it are defined regardless. The tests below switch it
# on by the flag, and pin the tuning constants so that they do not move with
# the shipped file.
SHUFFLE_CONSTANTS = {
    "SHUFFLE_ENABLED": "1",
    "SHUFFLE_MINIPRIX_LINE_UP_OFFSET": "19",
    "SHUFFLE_MIRROR_LINE_UP_OFFSET": "1",
    "PRIVATE_SHUFFLE_MP_MINUTE_OFFSET": "12",
}


def packaged_constants(**overrides):
    """The shipped default constants, with anything given here added or replaced."""
    csts = utils.load_constants()
    csts.update(overrides)
    return csts


class TestScheduleConstants(unittest.TestCase):
    """ The constants are read and typed in one place.

        Everything in constants.dat is a string. Six of them were cast to int
        at their point of use, spread across the bot's startup; a consumer of
        the library needs them converted once, before anything is built.
    """

    def test_the_offsets_are_read_as_minutes(self):
        csts = managers.ScheduleConstants.from_mapping(packaged_constants())
        self.assertEqual(csts.miniprix_lineup_offset, 23)
        self.assertEqual(csts.classic_lineup_offset, 0)
        self.assertEqual(csts.mirror_lineup_offset, 1)
        self.assertEqual(csts.private_mp_offset, 17)
        self.assertEqual(csts.private_mp_mirror_offset, 0)
        self.assertEqual(csts.private_cmp_offset, 8)
        self.assertEqual(csts.ninetynine_offset, 25)

    def test_secret_league_is_passed_through_unconverted(self):
        # SecretLeagueConfig parses the interval list itself.
        csts = managers.ScheduleConstants.from_mapping(packaged_constants())
        self.assertEqual(csts.secret_league_intervals, "11,6,7,3,8,4")
        self.assertEqual(csts.secret_league_offset, "21")

    def test_shuffle_is_off_in_the_shipped_constants(self):
        csts = managers.ScheduleConstants.from_mapping(packaged_constants())
        self.assertFalse(csts.is_shuffle_on)
        self.assertIsNone(csts.shuffle_lineup_offset)
        self.assertIsNone(csts.shuffle_mirror_lineup_offset)
        self.assertIsNone(csts.private_shuffle_mp_offset)

    def test_shuffle_constants_are_read_when_shuffle_is_on(self):
        csts = managers.ScheduleConstants.from_mapping(
            packaged_constants(**SHUFFLE_CONSTANTS)
        )
        self.assertTrue(csts.is_shuffle_on)
        self.assertEqual(csts.shuffle_lineup_offset, 19)
        self.assertEqual(csts.shuffle_mirror_lineup_offset, 1)
        self.assertEqual(csts.private_shuffle_mp_offset, 12)

    def test_shuffle_mirrors_on_the_regular_offset_by_default(self):
        # SHUFFLE_MIRROR_LINE_UP_OFFSET is optional; without it, Shuffle
        # mirrors where the regular Mini-Prix does.
        csts = packaged_constants(MIRROR_LINE_UP_OFFSET="7", **SHUFFLE_CONSTANTS)
        del csts["SHUFFLE_MIRROR_LINE_UP_OFFSET"]
        csts = managers.ScheduleConstants.from_mapping(csts)
        self.assertEqual(csts.mirror_lineup_offset, 7)
        self.assertEqual(csts.shuffle_mirror_lineup_offset, 7)

    def test_a_missing_constant_is_not_defaulted_away(self):
        csts = packaged_constants()
        del csts["PRIVATE_MP_MIRROR_MINUTE_OFFSET"]
        with self.assertRaises(KeyError):
            managers.ScheduleConstants.from_mapping(csts)

    def test_switching_shuffle_on_requires_its_private_offset(self):
        csts = packaged_constants(**SHUFFLE_CONSTANTS)
        del csts["PRIVATE_SHUFFLE_MP_MINUTE_OFFSET"]
        with self.assertRaises(KeyError):
            managers.ScheduleConstants.from_mapping(csts)

    def test_a_flag_that_is_off_wins_over_the_constants_it_gates(self):
        # The shipped file defines every tuning constant whether or not its
        # feature is on, so their presence must not switch anything on.
        csts = managers.ScheduleConstants.from_mapping(
            packaged_constants(
                SECRET_LEAGUE_ENABLED="0",
                WEEKEND_SECRET_LEAGUE_ENABLED="1",
                SHUFFLE_ENABLED="0",
            )
        )
        self.assertIsNone(csts.secret_league_intervals)
        self.assertIsNone(csts.secret_league_offset)
        # The weekend rotation is never on without the weekday one.
        self.assertIsNone(csts.weekend_secret_league_intervals)
        self.assertFalse(csts.is_shuffle_on)

    def test_a_mapping_without_flags_switches_nothing_on(self):
        csts = packaged_constants(**SHUFFLE_CONSTANTS)
        for flag in (
            "SECRET_LEAGUE_ENABLED",
            "WEEKEND_SECRET_LEAGUE_ENABLED",
            "SHUFFLE_ENABLED",
        ):
            del csts[flag]
        csts = managers.ScheduleConstants.from_mapping(csts)
        self.assertIsNone(csts.secret_league_intervals)
        self.assertFalse(csts.is_shuffle_on)


class TestBuildManagers(unittest.TestCase):
    """ One assembly path, and it needs nothing but the constants.

        Nothing here passes a config path or an env, so every assertion also
        stands as a check that the factory reads no .env of its own: the test
        suite runs from a directory that has none, and init_99_manager reads
        one when it is handed no env.
    """

    # Every manager, and whether it survives Shuffle being off.
    ALWAYS_BUILT = (
        "slot1mgr",
        "slot2mgr",
        "cmp_mgr",
        "mp_mgr",
        "r99_mgr",
        "pmp_mgr",
        "pcmp_mgr",
    )
    SHUFFLE_ONLY = ("smp_mgr", "psmp_mgr")

    def test_every_manager_is_built_with_shuffle_off(self):
        mgrs = managers.build_managers(packaged_constants())
        for name in self.ALWAYS_BUILT:
            with self.subTest(manager=name):
                self.assertIsNotNone(getattr(mgrs, name))
        for name in self.SHUFFLE_ONLY:
            with self.subTest(manager=name):
                self.assertIsNone(getattr(mgrs, name))
        self.assertFalse(mgrs.is_shuffle_on)

    def test_every_manager_is_built_with_shuffle_on(self):
        mgrs = managers.build_managers(packaged_constants(**SHUFFLE_CONSTANTS))
        for name in self.ALWAYS_BUILT + self.SHUFFLE_ONLY:
            with self.subTest(manager=name):
                self.assertIsNotNone(getattr(mgrs, name))
        self.assertTrue(mgrs.is_shuffle_on)

    def test_the_lineup_offsets_reach_the_managers_that_use_them(self):
        # A dropped offset produces managers that build and answer wrongly,
        # which is the failure this assembly is most exposed to.
        mgrs = managers.build_managers(packaged_constants(**SHUFFLE_CONSTANTS))
        self.assertEqual(mgrs.cmp_mgr.lineup_offset, 0)
        self.assertEqual(mgrs.mp_mgr.lineup_offset, 23)
        self.assertEqual(mgrs.mp_mgr.mirror_lineup_offset, 1)
        self.assertEqual(mgrs.smp_mgr.lineup_offset, 19)
        self.assertEqual(mgrs.smp_mgr.mirror_lineup_offset, 1)

    def test_the_minute_offsets_reach_the_private_lobby_origins(self):
        mgrs = managers.build_managers(packaged_constants(**SHUFFLE_CONSTANTS))
        origin = schedule.origin
        self.assertEqual(mgrs.pmp_mgr.mgr.origin, origin + timedelta(minutes=17))
        self.assertEqual(mgrs.pmp_mgr.mirror_mgr.origin, origin + timedelta(minutes=0))
        self.assertEqual(mgrs.pcmp_mgr.mgr.origin, origin + timedelta(minutes=8))
        self.assertEqual(mgrs.psmp_mgr.mgr.origin, origin + timedelta(minutes=12))
        self.assertEqual(mgrs.r99_mgr.mgr.origin, origin + timedelta(minutes=25))
        self.assertEqual(mgrs.slot1mgr.origin, schedule.glitch_origin)
        self.assertEqual(mgrs.slot2mgr.origin, origin)

    def test_the_public_managers_share_the_slot2_cycle(self):
        mgrs = managers.build_managers(packaged_constants(**SHUFFLE_CONSTANTS))
        self.assertIs(mgrs.cmp_mgr.mgr, mgrs.slot2mgr)
        self.assertIs(mgrs.mp_mgr.mgr, mgrs.slot2mgr)
        self.assertIs(mgrs.smp_mgr.mgr, mgrs.slot2mgr)
        # Private Mini-Prix defers to the public selection when both run.
        self.assertIs(mgrs.pmp_mgr.pmp_mgr, mgrs.mp_mgr)
        self.assertIs(mgrs.pcmp_mgr.pmp_mgr, mgrs.cmp_mgr)
        self.assertIs(mgrs.psmp_mgr.pmp_mgr, mgrs.smp_mgr)
        # Shuffle's private lobbies have no mirror manager of their own.
        self.assertIsNone(mgrs.psmp_mgr.mirror_mgr)
        self.assertIs(mgrs.r99_mgr.glitch_manager, mgrs.slot1mgr)

    def test_secret_league_reaches_the_slot2_manager(self):
        mgrs = managers.build_managers(packaged_constants())
        self.assertIsNotNone(mgrs.secret_cfg)
        self.assertEqual(mgrs.secret_cfg.offset, 21)
        self.assertTrue(mgrs.slot2mgr.is_secret_league_on())

    def test_secret_league_is_absent_when_it_is_switched_off(self):
        mgrs = managers.build_managers(packaged_constants(SECRET_LEAGUE_ENABLED="0"))
        self.assertIsNone(mgrs.secret_cfg)
        self.assertFalse(mgrs.slot2mgr.is_secret_league_on())

    def test_already_typed_constants_are_accepted(self):
        csts = managers.ScheduleConstants.from_mapping(packaged_constants())
        mgrs = managers.build_managers(csts)
        self.assertEqual(mgrs.mp_mgr.lineup_offset, 23)


class TestEventProfiles(unittest.TestCase):
    """ An event profile is a partial config laid over the default one.

        The CONFIG_PATH root here holds a complete default profile, copied
        from the packaged one, and an 'event' profile of one constant and one
        CSV. Everything the event does not name has to come from the default.
    """

    EVENT_CONSTANTS = "MINIPRIX_LINE_UP_OFFSET=5\n"
    EVENT_WEEKEND = "0,queen,king\n10,classic\n30,next\n"
    # 2025-04-26 is a Saturday, 2025-04-23 a Wednesday.
    WEEKEND = datetime(2025, 4, 26, 12, 0, tzinfo=timezone.utc)
    WEEKDAY = datetime(2025, 4, 23, 12, 0, tzinfo=timezone.utc)

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = self._tmpdir.name
        default_dir = os.path.join(self.root, "default")
        event_dir = os.path.join(self.root, "event")
        os.makedirs(default_dir)
        os.makedirs(event_dir)
        for entry in utils.get_schedule_dir({}).iterdir():
            with open(os.path.join(default_dir, entry.name), "w") as fd:
                fd.write(entry.read_text())
        with open(os.path.join(event_dir, "constants.dat"), "w") as fd:
            fd.write(self.EVENT_CONSTANTS)
        with open(os.path.join(event_dir, "slot2_schedule_weekend.csv"), "w") as fd:
            fd.write(self.EVENT_WEEKEND)

    def tearDown(self):
        self._tmpdir.cleanup()

    def build(self, profile=None):
        csts = utils.load_constants(self.root, profile)
        return managers.build_managers(csts, self.root, profile)

    @staticmethod
    def names(mgr, when):
        return [evt.name for evt in mgr.get_events(timestamp=when, limit=240)]

    def test_the_profile_sets_what_it_names(self):
        event = self.build("event")
        self.assertEqual(event.mp_mgr.lineup_offset, 5)
        gps = set(self.names(event.slot2mgr, self.WEEKEND))
        self.assertTrue(gps & {"queen", "king"})
        self.assertFalse(gps & {"knight", "ace", "mknight", "mace"})

    def test_everything_else_falls_through_to_the_default(self):
        default = self.build()
        event = self.build("event")
        self.assertEqual(default.mp_mgr.lineup_offset, 23)
        self.assertEqual(event.cmp_mgr.lineup_offset, default.cmp_mgr.lineup_offset)
        self.assertEqual(event.r99_mgr.mgr.origin, default.r99_mgr.mgr.origin)
        # The weekday schedule and the 99 schedule are not in the profile.
        self.assertEqual(
            self.names(event.slot2mgr, self.WEEKDAY),
            self.names(default.slot2mgr, self.WEEKDAY),
        )
        self.assertEqual(
            self.names(event.slot1mgr, self.WEEKEND),
            self.names(default.slot1mgr, self.WEEKEND),
        )

    def test_a_profile_without_constants_changes_none(self):
        os.remove(os.path.join(self.root, "event", "constants.dat"))
        self.assertEqual(
            utils.load_constants(self.root, "event"), utils.load_constants(self.root)
        )

    def test_an_unknown_profile_is_refused(self):
        # Every file of a profile is optional, so without this a misspelt name
        # would quietly run the default schedule.
        with self.assertRaises(FileNotFoundError):
            utils.load_constants(self.root, "evnet")
        with self.assertRaises(FileNotFoundError):
            managers.build_managers(utils.load_constants(self.root), self.root, "evnet")

    def test_every_packaged_profile_builds(self):
        for entry in utils.get_schedule_dir({}).parent.iterdir():
            if not entry.is_dir():
                continue
            with self.subTest(profile=entry.name):
                mgrs = managers.build_managers(
                    utils.load_constants(None, entry.name), None, entry.name
                )
                self.assertTrue(self.names(mgrs.slot2mgr, self.WEEKEND))


if __name__ == "__main__":
    unittest.main()
