""" Runtime profile-schedule management.

    A registry of schedule profiles, each built from the game's own schedule
    files, with exactly one active at any time. Reads on the controller
    delegate to the active profile, so consumers resolve the currently
    loaded managers at call time.

    See docs/schedule-controller.md for the design.
"""

import csv
import json
from datetime import datetime

# local imports
from pengbot99 import gameevents, gameschedule, utils

GAME_SCHEDULE_FILE = 'GameScheduleV1.json'
WEEKEND_SCHEDULE_FILE = 'WeekendSchedule.json'
STAGE_LIST_FILE = 'StageList.json'
# constants.dat key naming the weekend event to run: 'auto' follows the
# calendar in the WeekendSchedule file, 'none' ignores it, any other value
# is a WeekendScheduleID pinned for the whole profile.
WEEKEND_SCHEDULE_KEY = 'WEEKEND_SCHEDULE_ID'


def load_profile_file(env, profile, name):
    """ A file from the profile folder, or from the default folder when the
        profile does not override it.
    """
    folder = utils.get_schedule_dir(env, profile)
    if not utils.has_data_file(folder, name):
        folder = utils.get_schedule_dir(env, 'default')
    with utils.open_data_file(folder, name) as fd:
        return json.load(fd)


def load_schedule_data(env, profile='default', csts=None):
    """ The game's schedule data for a profile.
    """
    if csts is None:
        csts = utils.load_csts(env, profile)
    weekend_event = csts.get(WEEKEND_SCHEDULE_KEY, gameschedule.ScheduleData.AUTO)
    return gameschedule.ScheduleData(
            load_profile_file(env, profile, GAME_SCHEDULE_FILE),
            load_profile_file(env, profile, WEEKEND_SCHEDULE_FILE),
            weekend_event)


def load_league_tracks(env):
    """ Name to tracks of every league, from the StageList file in the
        CONFIG_PATH root, or the packaged one when the env names no root.
    """
    with utils.open_data_file(env.get('CONFIG_PATH'), STAGE_LIST_FILE) as fd:
        return gameschedule.league_tracks(json.load(fd))


class ScheduleProfile(object):
    """ One loaded schedule profile: the game's schedule files for one
        drop, and every manager the bot reads from them.

        slot2mgr: Grand Prix, Mini-Prix and special event slots.
        slot1mgr: Mystery track windows of the 99 races.
        r99_mgr: 99-race track pairs.
        mp_mgr, cmp_mgr, pmp_mgr, pcmp_mgr: public and private Mini-Prix and
        Classic Mini-Prix track selections.
        lineup_mgrs: Team Battle, Pro-Tracks and Classic track pairs, keyed
        by (event name, private).
    """
    def __init__(self, env, name, csts=None):
        super().__init__()
        self.name = name
        if csts is None:
            csts = utils.load_csts(env, name)
        utils.log_profile_file_warnings(env, name)
        self.data = load_schedule_data(env, name, csts)
        leagues = load_league_tracks(env)
        data = self.data
        self.slot2mgr = gameevents.SlotScheduleManager(data)
        self.slot1mgr = gameevents.MysteryTrackManager(data)
        self.r99_mgr = gameevents.NinetyNineManager(data)
        self.mp_mgr = gameevents.MiniPrixLineupManager(data, leagues, 'miniprix')
        self.cmp_mgr = gameevents.MiniPrixLineupManager(data, leagues, 'classicprix')
        self.pmp_mgr = gameevents.MiniPrixLineupManager(data, leagues, 'miniprix',
                                                        private=True)
        self.pcmp_mgr = gameevents.MiniPrixLineupManager(data, leagues, 'classicprix',
                                                         private=True)
        self.lineup_mgrs = {
            (mode, private): gameevents.TrackPairManager(data, mode, private=private)
            for mode in gameevents.TRACK_MODE_TYPES for private in (False, True)
        }
        window = data.active_window
        if window:
            start, end = (gameevents.from_unix(t).strftime('%Y-%m-%d %H:%M')
                          for t in window)
            utils.log("Schedule files of profile '{0}' are active "
                      "from {1} to {2}.".format(name, start, end))
        weekend_event = csts.get(WEEKEND_SCHEDULE_KEY, gameschedule.ScheduleData.AUTO)
        if weekend_event == gameschedule.ScheduleData.AUTO:
            weekend_event = 'calendar of {0}'.format(len(data.calendar))
        utils.log("Profile '{0}' weekend events: {1}.".format(name, weekend_event))

    def weekend_event(self, timestamp=None):
        """ The weekend event in force, by the game's ID, or None.
        """
        return self.slot2mgr.weekend_event(timestamp)

    def calendar(self):
        """ (start, end, ID) of the weekend events the profile knows of, as
            UTC datetimes.
        """
        return [(gameevents.from_unix(start), gameevents.from_unix(end), event_id)
                for start, end, event_id in self.data.calendar
                if end < gameschedule.FOREVER]


class ScheduleController(object):
    """ The registry of loaded schedule profiles.

        Exactly one schedule is active at any time. Unknown attribute
        reads delegate to the active ScheduleProfile so that consumers
        always resolve the currently active managers.
    """
    def __init__(self, env, profile='default', csts=None):
        super().__init__()
        self.env = env
        self._profiles = {}
        self._active = self.load(profile, csts=csts)

    @property
    def name(self):
        """ The name of the currently active schedule.
        """
        return self._active.name

    @property
    def active(self):
        """ The currently active ScheduleProfile.
        """
        return self._active

    def load(self, name, csts=None):
        """ Builds and registers a schedule profile without activating it.
            Returns the (possibly already-registered) schedule.
        """
        if name not in self._profiles:
            sched = ScheduleProfile(self.env, name, csts=csts)
            self._profiles[name] = sched
            utils.log("Loaded schedule profile '{0}'.".format(name))
        return self._profiles[name]

    def switch(self, name):
        """ Activates a loaded schedule by name, lazy-loading it on demand.
        """
        self._active = self.load(name)
        utils.log("Switched to schedule profile '{0}'.".format(name))
        return self._active

    def unload(self, name):
        """ Unregisters a loaded schedule. The active schedule cannot be
            unloaded; it must be switched away first.
        """
        if name == self.name:
            raise ValueError(
                "Cannot unload the active schedule '{0}'.".format(name))
        if name in self._profiles:
            del self._profiles[name]
            utils.log("Unloaded schedule profile '{0}'.".format(name))

    def list(self):
        """ The names of all loaded schedules.
        """
        return list(self._profiles)

    def __getattr__(self, name):
        """ Delegate unknown attribute reads to the active ScheduleProfile.
            Called only when normal attribute lookup fails.
        """
        active = self.__dict__.get('_active')
        if active is None:
            raise AttributeError(name)
        return getattr(active, name)


def load_profile_switches(env):
    """ Loads the profile switch config from 'EVENT_SCHEDULE_FILE' in the
        CONFIG_PATH root, or in the packaged data when the env names no
        root. Returns None if the file is absent.
    """
    name = env.get('EVENT_SCHEDULE_FILE')
    root = env.get('CONFIG_PATH')
    if not name or not utils.has_data_file(root, name):
        return None
    with utils.open_data_file(root, name, newline='') as fd:
        rows = list(csv.reader(fd, delimiter=','))
    return ProfileSwitchConfig(rows=rows)


class ProfileSwitchConfig(object):
    """ Switch times read from a EVENT_SCHEDULE_FILE file.

        Each row is '<YYYY-MM-DD>,<profile>', meaning that the
        profile named by '<profile>' becomes active at 00:00
        UTC on that date. Rows do not need to be sorted; they are
        sorted by date on load. Comments (lines starting with '#')
        and malformed rows are ignored with a warning.
    """
    def __init__(self, path=None, rows=None):
        super().__init__()
        if rows is None:
            rows = self._load(path)
        self._switches = self._parse(rows)

    def _load(self, path):
        rows = []
        with open(path, newline='') as fd:
            reader = csv.reader(fd, delimiter=',')
            for row in reader:
                rows.append(row)
        return rows

    def _parse(self, rows):
        """ Turns raw csv rows into sorted (date, profile) switches.
        """
        switches = []
        for row in rows:
            if not row or row[0].startswith('#'):
                continue
            if len(row) < 2:
                self._warn(row)
                continue
            try:
                day = datetime.strptime(row[0], '%Y-%m-%d').date()
            except ValueError:
                self._warn(row)
                continue
            switches.append((day, row[1]))
        switches.sort(key=lambda item: item[0])
        return switches

    def _warn(self, row):
        utils.log("EVENT_SCHEDULE_FILE: ignoring malformed row '{0}'.".format(
                ','.join(row)))

    def active_on(self, day):
        """ The profile active at 00:00 UTC of the given date.
            Falls back to 'default' for dates before the first switch.
        """
        profile = 'default'
        for switch_day, name in self._switches:
            if switch_day <= day:
                profile = name
            else:
                break
        return profile

    @property
    def switches(self):
        """Chronologically ordered (UTC date, profile) entries."""
        return tuple(self._switches)

    @property
    def profiles(self):
        """ The unique profile names referenced by the config,
            in the order they first appear.
        """
        profiles = []
        for _, name in self._switches:
            if name not in profiles:
                profiles.append(name)
        return profiles
