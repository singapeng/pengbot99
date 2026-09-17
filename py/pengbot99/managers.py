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
from pengbot99 import choicerace, schedule, secret_league, utils
from pengbot99.miniprix import MiniPrixManager, PrivateMPManager


@dataclass(frozen=True)
class ScheduleConstants:
    """The constants the assembly needs, read and typed in one place.

    Everything in the constants file is a string, and every offset in it is a
    number of minutes. ``from_mapping`` is the only place that names a
    constant, and the only place that reads a feature flag: the constants of a
    feature whose flag is off are None here, whatever the file says.
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
    weekend_secret_league_intervals: str | None = None
    weekend_secret_league_offset: str | None = None
    shuffle_lineup_offset: int | None = None
    shuffle_mirror_lineup_offset: int | None = None
    private_shuffle_mp_offset: int | None = None

    @property
    def is_shuffle_on(self):
        """Whether SHUFFLE_ENABLED was set when the constants were read."""
        return self.shuffle_lineup_offset is not None

    @classmethod
    def from_mapping(cls, csts):
        """Reads the constants out of a mapping of strings, e.g. constants.dat.

        A feature is on when its ``_ENABLED`` flag is "1", and only then: the
        constants that tune it stay defined while it is off, so that a profile
        can switch it on or off by overriding the flag alone.

        Raises KeyError when a constant the schedule cannot do without is
        missing, including those of a feature once its flag switches it on.
        """
        mirror_offset = int(csts["MIRROR_LINE_UP_OFFSET"])
        shuffle_on = csts.get("SHUFFLE_ENABLED") == "1"
        secret_on = csts.get("SECRET_LEAGUE_ENABLED") == "1"
        # The weekend rotation only replaces Grand Prix that the weekday one
        # already replaces, so it is never on without it.
        we_secret_on = secret_on and csts.get("WEEKEND_SECRET_LEAGUE_ENABLED") == "1"
        return cls(
            miniprix_lineup_offset=int(csts["MINIPRIX_LINE_UP_OFFSET"]),
            classic_lineup_offset=int(csts["CLASSIC_LINE_UP_OFFSET"]),
            mirror_lineup_offset=mirror_offset,
            private_mp_offset=int(csts["PRIVATE_MP_MINUTE_OFFSET"]),
            private_mp_mirror_offset=int(csts["PRIVATE_MP_MIRROR_MINUTE_OFFSET"]),
            private_cmp_offset=int(csts["PRIVATE_CMP_MINUTE_OFFSET"]),
            ninetynine_offset=int(csts["NINETYNINE_MINUTE_OFFSET"]),
            # SecretLeagueConfig parses these itself, and tolerates a missing
            # offset; it is the one consumer that wants them unconverted.
            secret_league_intervals=(
                csts["SECRET_LEAGUE_INTERVALS"] if secret_on else None
            ),
            secret_league_offset=(
                csts.get("SECRET_LEAGUE_OFFSET") if secret_on else None
            ),
            # A League Weekend runs Secret League on a rotation of its own.
            weekend_secret_league_intervals=(
                csts["WEEKEND_SECRET_LEAGUE_INTERVALS"] if we_secret_on else None
            ),
            weekend_secret_league_offset=(
                csts.get("WEEKEND_SECRET_LEAGUE_OFFSET") if we_secret_on else None
            ),
            shuffle_lineup_offset=(
                int(csts["SHUFFLE_MINIPRIX_LINE_UP_OFFSET"]) if shuffle_on else None
            ),
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
    report on what was built. ``we_secret_cfg`` is the same for the weekend
    rotation, and is None outside a League Weekend.
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
    we_secret_cfg: secret_league.SecretLeagueConfig | None = None

    @property
    def is_shuffle_on(self):
        return self.smp_mgr is not None


def build_managers(csts, cfg_path=None, profile=None):
    """Builds every schedule manager from the constants and the content dumps.

    csts: the constants as a mapping of strings, or a ScheduleConstants. They
          are not read from 'profile' here: ``utils.load_constants`` does
          that, given the same 'cfg_path' and 'profile'.
    cfg_path: the CONFIG_PATH override -- a directory of profile folders the
              game content is read from instead of the copy that ships inside
              the package. None means the packaged copy.
    profile: the event profile whose schedules replace the default ones, file
             by file. None means the default profile alone.
    """
    if not isinstance(csts, ScheduleConstants):
        csts = ScheduleConstants.from_mapping(csts)

    env = {"CONFIG_PATH": cfg_path}
    utils.require_profile(env, profile)
    sched_dir = utils.get_schedule_dir(env, profile)
    default_dir = utils.get_schedule_dir(env)

    def load(name):
        return schedule.load_schedule(sched_dir, name, default_dir)

    secret_cfg = None
    we_secret_cfg = None
    if csts.secret_league_intervals:
        secret_cfg = secret_league.SecretLeagueConfig(
            csts.secret_league_intervals, csts.secret_league_offset
        )
        if csts.weekend_secret_league_intervals:
            we_secret_cfg = secret_league.SecretLeagueConfig(
                csts.weekend_secret_league_intervals, csts.weekend_secret_league_offset
            )

    # the schedule for slot 1 (99 races)
    r99sched = load("slot1_schedule")
    # the weekday schedule for slot 2 (Prix and special events)
    wdsched = load("slot2_schedule")
    # the weekend schedule for slot 2 (Prix and special events)
    wesched = load("slot2_schedule_weekend")
    # the Classic Mini Prix track schedule
    cmpsched = load("classic_mp_schedule")
    # the Mini Prix track schedule
    mpsched = load("miniprix_schedule")
    mirrorsc = load("miniprix_mirroring_schedule")
    # the schedules for Private Lobbies Mini-Prix
    plmpsched = load("private_miniprix_schedule")
    plcmpsched = load("private_classic_mp_schedule")

    # The Public schedule managers
    slot1mgr = schedule.Slot1ScheduleManager(schedule.glitch_origin, r99sched)
    slot2mgr = schedule.Slot2ScheduleManager(
        schedule.origin, wdsched, wesched, secret_cfg, we_secret_cfg
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
        env=env,
        minutes_offset=csts.ninetynine_offset,
        profile=profile,
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
        "we_secret_cfg": we_secret_cfg,
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
