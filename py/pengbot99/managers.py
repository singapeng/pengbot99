"""Assembly of the schedule managers from the constants and the content dumps.

This is the one place that knows which CSV feeds which manager and which
constant lines each of them up. It is deliberately free of Discord, and of
anything else a caller cannot supply: no ``.env`` is read, no clock is read,
nothing is logged. ``bot.py`` is one caller; it logs what it gets back.
"""

# Python imports
from dataclasses import dataclass
from datetime import timedelta

# local imports
from pengbot99 import choicerace, schedule, secret_league
from pengbot99.miniprix import MiniPrixManager, PrivateMPManager


@dataclass(frozen=True)
class ScheduleConstants:
    """The constants the assembly needs, read and typed in one place.

    Everything in the constants file is a string, and every offset in it is a
    number of minutes. ``from_mapping`` is the only place that names a
    constant; it also decides whether Shuffle Weekend is on.
    """

    miniprix_lineup_offset: int
    classic_lineup_offset: int
    mirror_lineup_offset: int
    private_mp_offset: int
    private_mp_mirror_offset: int
    private_cmp_offset: int
    ninetynine_offset: int
    secret_league_intervals: str | None = None
    secret_league_offset: str | None = None
    shuffle_lineup_offset: int | None = None
    shuffle_mirror_lineup_offset: int | None = None
    private_shuffle_mp_offset: int | None = None

    @property
    def is_shuffle_on(self):
        """Shuffle Weekend runs when the config lines up its Mini-Prix.

        No SHUFFLE_MINIPRIX_LINE_UP_OFFSET means Shuffle is off, and the rest
        of the SHUFFLE_ constants are not looked at -- they are commented out
        for most of the year.
        """
        return self.shuffle_lineup_offset is not None

    @classmethod
    def from_mapping(cls, csts):
        """Reads the constants out of a mapping of strings, e.g. constants.dat.

        Raises KeyError when a constant the schedule cannot do without is
        missing, including the Shuffle ones once Shuffle is switched on.
        """
        mirror_offset = int(csts["MIRROR_LINE_UP_OFFSET"])
        shuffle_offset = csts.get("SHUFFLE_MINIPRIX_LINE_UP_OFFSET")
        shuffle_on = shuffle_offset is not None
        return cls(
            miniprix_lineup_offset=int(csts["MINIPRIX_LINE_UP_OFFSET"]),
            classic_lineup_offset=int(csts["CLASSIC_LINE_UP_OFFSET"]),
            mirror_lineup_offset=mirror_offset,
            private_mp_offset=int(csts["PRIVATE_MP_MINUTE_OFFSET"]),
            private_mp_mirror_offset=int(csts["PRIVATE_MP_MIRROR_MINUTE_OFFSET"]),
            private_cmp_offset=int(csts["PRIVATE_CMP_MINUTE_OFFSET"]),
            ninetynine_offset=int(csts["NINETYNINE_MINUTE_OFFSET"]),
            # SecretLeagueConfig parses these itself, and tolerates both being
            # absent; it is the one consumer that wants them unconverted.
            secret_league_intervals=csts.get("SECRET_LEAGUE_INTERVALS"),
            secret_league_offset=csts.get("SECRET_LEAGUE_OFFSET"),
            shuffle_lineup_offset=int(shuffle_offset) if shuffle_on else None,
            # Shuffle mirrors on the same offset as the regular Mini-Prix
            # unless the config gives it one of its own.
            shuffle_mirror_lineup_offset=(
                int(csts.get("SHUFFLE_MIRROR_LINE_UP_OFFSET", mirror_offset))
                if shuffle_on
                else None
            ),
            private_shuffle_mp_offset=(
                int(csts["PRIVATE_SHUFFLE_MP_MINUTE_OFFSET"]) if shuffle_on else None
            ),
        )


@dataclass(frozen=True)
class ScheduleManagers:
    """Every manager the schedule answers come out of.

    ``smp_mgr`` and ``psmp_mgr`` are None while Shuffle Weekend is off, which
    is its usual state. ``secret_cfg`` is None when Secret League is not
    running; it is already inside ``slot2mgr``, and is here so a caller can
    report on what was built.
    """

    slot1mgr: schedule.Slot1ScheduleManager
    slot2mgr: schedule.Slot2ScheduleManager
    cmp_mgr: MiniPrixManager
    mp_mgr: MiniPrixManager
    r99_mgr: choicerace.ChoiceRaceManager
    pmp_mgr: PrivateMPManager
    pcmp_mgr: PrivateMPManager
    smp_mgr: MiniPrixManager | None = None
    psmp_mgr: PrivateMPManager | None = None
    secret_cfg: secret_league.SecretLeagueConfig | None = None

    @property
    def is_shuffle_on(self):
        return self.smp_mgr is not None


def build_managers(csts, cfg_path=None):
    """Builds every schedule manager from the constants and the content dumps.

    csts: the constants as a mapping of strings, or a ScheduleConstants.
    cfg_path: the CONFIG_PATH override -- a directory the game content is read
              from instead of the copy that ships inside the package. None
              means the packaged copy.
    """
    if not isinstance(csts, ScheduleConstants):
        csts = ScheduleConstants.from_mapping(csts)

    secret_cfg = None
    if csts.secret_league_intervals:
        secret_cfg = secret_league.SecretLeagueConfig(
            csts.secret_league_intervals, csts.secret_league_offset
        )

    # the schedule for slot 1 (99 races)
    r99sched = schedule.load_schedule(cfg_path, "slot1_schedule")
    # the weekday schedule for slot 2 (Prix and special events)
    wdsched = schedule.load_schedule(cfg_path, "slot2_schedule")
    # the weekend schedule for slot 2 (Prix and special events)
    wesched = schedule.load_schedule(cfg_path, "slot2_schedule_weekend")
    # the Classic Mini Prix track schedule
    cmpsched = schedule.load_schedule(cfg_path, "classic_mp_schedule")
    # the Mini Prix track schedule
    mpsched = schedule.load_schedule(cfg_path, "miniprix_schedule")
    mirrorsc = schedule.load_schedule(cfg_path, "miniprix_mirroring_schedule")
    # the schedules for Private Lobbies Mini-Prix
    plmpsched = schedule.load_schedule(cfg_path, "private_miniprix_schedule")
    plcmpsched = schedule.load_schedule(cfg_path, "private_classic_mp_schedule")

    # The Public schedule managers
    slot1mgr = schedule.Slot1ScheduleManager(schedule.glitch_origin, r99sched)
    slot2mgr = schedule.Slot2ScheduleManager(
        schedule.origin, wdsched, wesched, secret_cfg
    )
    cmp_mgr = MiniPrixManager(
        "classicprix", slot2mgr, cmpsched, offset=csts.classic_lineup_offset
    )
    mp_mgr = MiniPrixManager(
        "miniprix",
        slot2mgr,
        mpsched,
        mirrorsc,
        csts.miniprix_lineup_offset,
        csts.mirror_lineup_offset,
    )
    # init_99_manager reads a .env of its own when handed no env, so it is
    # always handed one -- the config path is all it takes from it.
    r99_mgr = choicerace.init_99_manager(
        name=None,
        glitch_mgr=slot1mgr,
        env={"CONFIG_PATH": cfg_path},
        minutes_offset=csts.ninetynine_offset,
    )

    # The Private Lobby schedule managers
    pmp_origin = schedule.origin + timedelta(minutes=csts.private_mp_offset)
    pmp_mirror_origin = schedule.origin + timedelta(
        minutes=csts.private_mp_mirror_offset
    )
    pcmp_origin = schedule.origin + timedelta(minutes=csts.private_cmp_offset)

    pl_slot1 = schedule.Slot1ScheduleManager(pmp_origin, plmpsched)
    mirror_slot1 = schedule.Slot1ScheduleManager(pmp_mirror_origin, mirrorsc)
    pmp_mgr = PrivateMPManager("miniprix", pl_slot1, mp_mgr, mirror_slot1)
    plcmp_slot1 = schedule.Slot1ScheduleManager(pcmp_origin, plcmpsched)
    pcmp_mgr = PrivateMPManager("classicprix", plcmp_slot1, cmp_mgr)

    built = {
        "slot1mgr": slot1mgr,
        "slot2mgr": slot2mgr,
        "cmp_mgr": cmp_mgr,
        "mp_mgr": mp_mgr,
        "r99_mgr": r99_mgr,
        "pmp_mgr": pmp_mgr,
        "pcmp_mgr": pcmp_mgr,
        "secret_cfg": secret_cfg,
    }
    if not csts.is_shuffle_on:
        return ScheduleManagers(**built)

    # The Shuffle Mini-Prix schedule managers, when Shuffle Weekend is on
    smp_mgr = MiniPrixManager(
        "miniprix",
        slot2mgr,
        mpsched,
        mirrorsc,
        csts.shuffle_lineup_offset,
        csts.shuffle_mirror_lineup_offset,
    )
    psmp_origin = schedule.origin + timedelta(minutes=csts.private_shuffle_mp_offset)
    psl_slot1 = schedule.Slot1ScheduleManager(psmp_origin, plmpsched)
    psmp_mgr = PrivateMPManager("miniprix", psl_slot1, smp_mgr, None)
    return ScheduleManagers(smp_mgr=smp_mgr, psmp_mgr=psmp_mgr, **built)
