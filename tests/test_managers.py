# Python imports
import unittest
from datetime import timedelta

# local imports
from pengbot99 import managers, schedule, utils

# Shuffle Weekend is off in the shipped constants: its four constants are
# commented out for most of the year. These are the values they carry when it
# is on, and the tests below switch it on by adding them.
SHUFFLE_CONSTANTS = {
    "SHUFFLE_MINIPRIX_LINE_UP_OFFSET": "19",
    "SHUFFLE_MIRROR_LINE_UP_OFFSET": "1",
    "PRIVATE_SHUFFLE_MP_MINUTE_OFFSET": "12",
}


def packaged_constants(**overrides):
    """The shipped constants, with anything given here added or replaced."""
    with utils.open_data_file(None, "constants.dat") as fd:
        csts = utils.parse_env(fd.readlines())
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
        overrides = dict(SHUFFLE_CONSTANTS)
        del overrides["SHUFFLE_MIRROR_LINE_UP_OFFSET"]
        csts = managers.ScheduleConstants.from_mapping(
            packaged_constants(MIRROR_LINE_UP_OFFSET="7", **overrides)
        )
        self.assertEqual(csts.mirror_lineup_offset, 7)
        self.assertEqual(csts.shuffle_mirror_lineup_offset, 7)

    def test_a_missing_constant_is_not_defaulted_away(self):
        csts = packaged_constants()
        del csts["PRIVATE_MP_MIRROR_MINUTE_OFFSET"]
        with self.assertRaises(KeyError):
            managers.ScheduleConstants.from_mapping(csts)

    def test_switching_shuffle_on_requires_its_private_offset(self):
        overrides = dict(SHUFFLE_CONSTANTS)
        del overrides["PRIVATE_SHUFFLE_MP_MINUTE_OFFSET"]
        with self.assertRaises(KeyError):
            managers.ScheduleConstants.from_mapping(packaged_constants(**overrides))


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

    def test_secret_league_is_absent_when_it_is_not_configured(self):
        csts = packaged_constants()
        del csts["SECRET_LEAGUE_INTERVALS"]
        mgrs = managers.build_managers(csts)
        self.assertIsNone(mgrs.secret_cfg)
        self.assertFalse(mgrs.slot2mgr.is_secret_league_on())

    def test_already_typed_constants_are_accepted(self):
        csts = managers.ScheduleConstants.from_mapping(packaged_constants())
        mgrs = managers.build_managers(csts)
        self.assertEqual(mgrs.mp_mgr.lineup_offset, 23)


if __name__ == "__main__":
    unittest.main()
