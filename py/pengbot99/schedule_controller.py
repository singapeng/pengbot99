""" Runtime event-schedule management.

    Owns the shared slot 1 (99 races) schedule, and a registry of event
    schedules (slot 2, one per profile), with exactly one active
    at any time. Reads on the controller delegate to the active schedule,
    so existing consumers resolve the currently loaded managers at call
    time.

    See docs/schedule-controller.md for the design.
"""

from datetime import timedelta

# local imports
from pengbot99 import choicerace, miniprix, schedule, secret_league, utils


def build_slot1(env, profile='default'):
    """ Builds the slot-1 (99 races) schedule manager for a profile.
        Slot 1 data does not vary between profiles, so this is built once
        and never swapped by the controller.
    """
    sched_dir = utils.get_schedule_dir(env, profile)
    default_dir = utils.get_schedule_dir(env, 'default')
    r99sched = schedule.load_schedule(sched_dir, 'slot1_schedule', default_dir)
    return schedule.Slot1ScheduleManager(schedule.glitch_origin, r99sched)


def build_r99(env, glitch_mgr, csts, profile='default'):
    """ Builds the 99 races choice manager for a profile.
        Needs the slots constants to compute its minute offset.
    """
    r99_offset = int(csts["NINETYNINE_MINUTE_OFFSET"])
    return choicerace.init_99_manager(name=None, glitch_mgr=glitch_mgr, env=env,
            minutes_offset=r99_offset, profile=profile)


class EventSchedule(object):
    """ One loaded event schedule: Slot 2 for one event profile
        along with Private MP and CMP rotations.

        For Slot 2, this covers:
        - Base Slot 2 rotation (Prix and Special Events),
        - Secret League overlay, if enabled,
        - Mini-Prix and Classic Mini-Prix schedule,
        for weekday plus weekend, including weekend variations
        (such as Shuffle Mini-Prix, if the event is active).

    """
    def __init__(self, env, name, csts=None):
        super().__init__()
        self.name = name
        if csts is None:
            csts = utils.load_csts(env, name)
        sched_dir = utils.get_schedule_dir(env, name)
        default_dir = utils.get_schedule_dir(env, 'default')
        utils.log_profile_csv_warnings(env, name)

        # all env values are str, convert schedule offsets to int now
        mp_offset = int(csts["MINIPRIX_LINE_UP_OFFSET"])
        cmp_offset = int(csts["CLASSIC_LINE_UP_OFFSET"])
        mirror_offset = int(csts["MIRROR_LINE_UP_OFFSET"])

        # Glitch GP
        secret_cfg = None
        we_secret_cfg = None
        if csts.get("SECRET_LEAGUE_ENABLED") == "1":
            secret_cfg = secret_league.SecretLeagueConfig(
                    csts["SECRET_LEAGUE_INTERVALS"],
                    csts.get("SECRET_LEAGUE_OFFSET"),
                )
            utils.log("Secret League initialized with {0}".format(secret_cfg.indices))
        if csts.get("WEEKEND_SECRET_LEAGUE_ENABLED") == "1" and secret_cfg:
            we_secret_cfg = secret_league.SecretLeagueConfig(
                    csts["WEEKEND_SECRET_LEAGUE_INTERVALS"],
                    csts.get("WEEKEND_SECRET_LEAGUE_OFFSET"),
                )
            utils.log("Weekend Secret League is ON: {0}".format(we_secret_cfg.indices))

        # load the weekday schedule for slot 2 (Prix and special events)
        wdsched = schedule.load_schedule(sched_dir, 'slot2_schedule', default_dir)
        # load the weekend schedule for slot 2 (Prix and special events)
        wesched = schedule.load_schedule(sched_dir, 'slot2_schedule_weekend',
                default_dir)
        # load the Classic Mini Prix track schedule
        cmpsched = schedule.load_schedule(sched_dir, 'classic_mp_schedule', default_dir)
        # load the Mini Prix track schedule
        mpsched = schedule.load_schedule(sched_dir, 'miniprix_schedule', default_dir)
        mirrorsc = schedule.load_schedule(sched_dir, 'miniprix_mirroring_schedule',
                default_dir)
        # load the schedules for Private Lobbies Mini-Prix
        plmpsched = schedule.load_schedule(sched_dir, "private_miniprix_schedule",
                default_dir)
        plcmpsched = schedule.load_schedule(sched_dir, "private_classic_mp_schedule",
                default_dir)

        # Create the Public schedule managers
        self.slot2mgr = schedule.Slot2ScheduleManager(
                origin=schedule.origin, weekday_sched=wdsched, weekend_sched=wesched,
                secret_cfg=secret_cfg, we_secret_cfg=we_secret_cfg)
        self.cmp_mgr = miniprix.MiniPrixManager("classicprix", self.slot2mgr,
                cmpsched, offset=cmp_offset)
        self.mp_mgr = miniprix.MiniPrixManager("miniprix", self.slot2mgr, mpsched,
                mirrorsc, mp_offset, mirror_offset)
        utils.log("Setting cycles to {0} for {1}.".format(
                self.mp_mgr.mp_cycles, self.mp_mgr.name))

        # Create Private Lobby schedule managers
        pmp_origin = schedule.origin + timedelta(
                minutes=int(csts["PRIVATE_MP_MINUTE_OFFSET"]))
        pmp_mirror_origin = schedule.origin + timedelta(
                minutes=int(csts["PRIVATE_MP_MIRROR_MINUTE_OFFSET"]))
        pcmp_origin = schedule.origin + timedelta(
                minutes=int(csts["PRIVATE_CMP_MINUTE_OFFSET"]))

        pl_slot1 = schedule.Slot1ScheduleManager(pmp_origin, plmpsched)
        mirror_slot1 = schedule.Slot1ScheduleManager(pmp_mirror_origin, mirrorsc)
        self.pmp_mgr = miniprix.PrivateMPManager("miniprix", pl_slot1,
                self.mp_mgr, mirror_slot1)
        plcmp_slot1 = schedule.Slot1ScheduleManager(pcmp_origin, plcmpsched)
        self.pcmp_mgr = miniprix.PrivateMPManager("classicprix", plcmp_slot1,
                self.cmp_mgr)

        # Shuffle Mini-Prix schedule managers
        self.smp_mgr = None
        self.psmp_mgr = None
        if csts.get("SHUFFLE_ENABLED") == "1":
            smp_offset = int(csts["SHUFFLE_MINIPRIX_LINE_UP_OFFSET"])
            smp_mirror_offset = int(csts.get(
                    "SHUFFLE_MIRROR_LINE_UP_OFFSET", mirror_offset))
            self.smp_mgr = miniprix.MiniPrixManager("miniprix", self.slot2mgr,
                    mpsched, mirrorsc, smp_offset, smp_mirror_offset)
            psmp_origin = schedule.origin + timedelta(
                    minutes=int(csts["PRIVATE_SHUFFLE_MP_MINUTE_OFFSET"]))
            psl_slot1 = schedule.Slot1ScheduleManager(psmp_origin, plmpsched)
            self.psmp_mgr = miniprix.PrivateMPManager("miniprix", psl_slot1,
                    self.smp_mgr, None)
            utils.log("!! Configured Shuffle Weekend !!")

    def is_shuffle_on(self):
        """ Whether the shuffle miniprix managers are configured.
        """
        return self.smp_mgr is not None


class ScheduleController(object):
    """ The registry of loaded event schedules plus the shared slot-1 world.

        Exactly one schedule is active at any time. Unknown attribute
        reads delegate to the active EventSchedule so that pb.<mgr>
        style consumers keep working and always resolve the currently
        active managers.
    """
    def __init__(self, env, profile='default', csts=None):
        super().__init__()
        self.env = env
        self._schedules = {}
        if csts is None:
            csts = utils.load_csts(env, profile)
        # the slot-1 world is built once from the startup profile and
        # never swapped, so 99 races query state is preserved.
        self.slot1mgr = build_slot1(env, profile)
        self.r99_mgr = build_r99(env, self.slot1mgr, csts, profile)
        # load the startup profile schedule (unchanged behaviour)
        self._active = self.load(profile, csts=csts)

    @property
    def name(self):
        """ The name of the currently active schedule.
        """
        return self._active.name

    @property
    def active(self):
        """ The currently active EventSchedule.
        """
        return self._active

    def load(self, name, csts=None):
        """ Builds and registers an event schedule without activating it.
            Returns the (possibly already-registered) schedule.
        """
        if name not in self._schedules:
            sched = EventSchedule(self.env, name, csts=csts)
            self._schedules[name] = sched
            utils.log("Loaded event schedule '{0}'.".format(name))
        return self._schedules[name]

    def switch(self, name):
        """ Activates a loaded schedule by name, lazy-loading it on demand.
        """
        self._active = self.load(name)
        utils.log("Switched to event schedule '{0}'.".format(name))
        return self._active

    def unload(self, name):
        """ Unregisters a loaded schedule. The active schedule cannot be
            unloaded; it must be switched away first.
        """
        if name == self.name:
            raise ValueError(
                "Cannot unload the active schedule '{0}'.".format(name))
        if name in self._schedules:
            del self._schedules[name]
            utils.log("Unloaded event schedule '{0}'.".format(name))

    def list(self):
        """ The names of all loaded schedules.
        """
        return list(self._schedules)

    def __getattr__(self, name):
        """ Delegate unknown attribute reads to the active EventSchedule.
            Called only when normal attribute lookup fails.
        """
        active = self.__dict__.get('_active')
        if active is None:
            raise AttributeError(name)
        return getattr(active, name)