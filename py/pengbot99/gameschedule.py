""" F-Zero 99's schedule, computed the way the game computes it.

    The game reads two data files, GameScheduleV1 and WeekendSchedule, and
    evaluates everything from the Unix clock: there is no stored state, no
    origin to fit and no history. A mode's rotation position is the number of
    minutes that mode has been active since the epoch, assuming the current
    tables had always been in force, with weeks counted from Sunday.

    Every method here mirrors a game function; the inputs are the JSON dumps
    of the game's BYML files. Time is always Unix seconds (UTC).
    This module reads no clock and no environment.
"""

import calendar
import time
from itertools import accumulate

MINUTES_PER_WEEK = 10080
# 1970-01-01 is a Thursday; four days of minutes align the week count on Sunday
EPOCH_TO_SUNDAY = 5760
FOREVER = 2 ** 62

DAYS = {'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6}

# game mode types, by the game's numbering
GRAND_PRIX = 0
COLOR_TEAMS = 1
HARD_TRACKS = 2
MINI_PRIX = 3
CLASSIC = 4
CLASSIC_MINI_PRIX = 5
WILDCARD_MINI_PRIX = 6
CLOSED = 7

TYPE_ID = {
    'GrandPrix': GRAND_PRIX, 'Normal': GRAND_PRIX, 'ColorTeams': COLOR_TEAMS,
    'HardTracks': HARD_TRACKS, 'MiniPrix': MINI_PRIX, 'Classic': CLASSIC,
    'ClassicMiniPrix': CLASSIC_MINI_PRIX, 'WildCardMiniPrix': WILDCARD_MINI_PRIX,
    'Closed': CLOSED,
}
PRIX_TYPES = {'GrandPrix', 'MiniPrix', 'WildCardMiniPrix', 'ClassicMiniPrix'}
MINI_PRIX_TYPES = (MINI_PRIX, CLASSIC_MINI_PRIX, WILDCARD_MINI_PRIX)
WORLD_TOUR_LEAGUES = {'WorldTour', 'WorldTour7Races'}
# which track-set table a track mode draws its pairs from
TRACK_SET_BLOCKS = {COLOR_TEAMS: 'TrackSchedule', HARD_TRACKS: 'HardTrackSchedule',
                    CLASSIC: 'ClassicTrackSchedule'}
PLACEHOLDER_TRACK = 'INVALID_STAGE_ID'


def parse_time(text):
    """ '2026-10-19T00:00' to Unix seconds; a missing value is 0, as in the game.
    """
    if not text:
        return 0
    return calendar.timegm(time.strptime(text, '%Y-%m-%dT%H:%M'))


def c_div(a, b):
    """ C integer division: truncates toward zero.
    """
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def c_mod(a, b):
    return a - c_div(a, b) * b


def split_time(t):
    """ (C tm_wday with Sunday as 0, minute of the day) of a Unix time.
    """
    tm = time.gmtime(t)
    return (tm.tm_wday + 1) % 7, tm.tm_hour * 60 + tm.tm_min


class TrackSets(object):
    """ A TrackSchedule, HardTrackSchedule or ClassicTrackSchedule block:
        numbered sets of two tracks, each track an (id, type) pair.
    """
    def __init__(self, block):
        self.interval = block.get('AvailabilityInterval') or 1
        self.sets = [tuple((track['TrackId'], track.get('TrackType', 'Normal'))
                           for track in item['Tracks'])
                     for item in block['Sets']]

    def __len__(self):
        return len(self.sets)

    def wallclock_index(self, t):
        return c_mod(c_div(c_div(t, 60), self.interval), len(self.sets))


class Windows(object):
    """ A MysteryTrackSchedule or MysteryPrixSchedule block.
        InactivePeriods are consecutive gaps on the caller's minute counter;
        a window of AvailabilityInterval minutes opens at the end of each.
        Nothing opens before Start, and nothing opens at all when the block
        lists no periods (the game stores null as an empty list).
    """
    def __init__(self, block):
        self.cumulative = list(accumulate(block.get('InactivePeriods') or []))
        self.interval = block.get('AvailabilityInterval') or 1
        self.items = [item.get('TrackId') or item.get('Name')
                      for item in (block.get('Tracks') or block.get('Leagues') or [])]
        self.start = parse_time(block.get('Start'))

    @property
    def cycle(self):
        return self.cumulative[-1] if self.cumulative else 0

    @property
    def window_starts(self):
        """ Positions in the cycle at which a window opens; the one at 0
            only opens from the second cycle on.
        """
        if len(self.cumulative) < 2:
            return []
        return [0] + self.cumulative[:-1]

    def evaluate(self, minutes, now):
        """ The item index open at a counter value, or -1 when no window is.
        """
        if self.start and now < self.start:
            return -1
        count = len(self.cumulative)
        if not count:
            return -1
        q, r = divmod(minutes, self.cycle)
        if q == 0 or r >= self.interval:
            if count < 2:
                return -1
            i = 0
            while True:
                gap = r - self.cumulative[i]
                if gap < 0:
                    return -1
                if gap < self.interval:
                    break
                i += 1
                if i == count - 1:
                    return -1
        else:
            i = -1
        if not self.items:
            return -1
        return c_mod(q * count + i, len(self.items))

    def item(self, index):
        return self.items[index]

    def windows_between(self, start_minute, end_minute, now):
        """ (first minute, end minute, item) of each window open in a range of
            counter values.
        """
        found = []
        if not self.window_starts:
            return found
        for q in range(start_minute // self.cycle, end_minute // self.cycle + 1):
            for position in self.window_starts:
                opens = q * self.cycle + position
                if opens >= end_minute or opens + self.interval <= start_minute:
                    continue
                index = self.evaluate(opens, now)
                if index != -1:
                    found.append((opens, opens + self.interval, self.item(index)))
        return found


class Entry(object):
    """ One row of an interval table: a set, for a duration.
        per_cycle: minutes of this set in a whole cycle.
        other_before: minutes of other sets that precede this row in the cycle.
        occurrence: how many rows of the same set precede this one.
    """
    __slots__ = ('set', 'duration', 'start', 'occurrence', 'other_before', 'per_cycle')

    def __init__(self, set_index, duration, start, occurrence, other_before):
        self.set = set_index
        self.duration = duration
        self.start = start
        self.occurrence = occurrence
        self.other_before = other_before
        self.per_cycle = 0


class IntervalTable(object):
    """ An 'Interval' or 'IntervalWeekend' list resolved against the sets.
    """
    def __init__(self, rows, set_by_name):
        self.entries = []
        self.occurrences = {}
        self.per_cycle = {}
        elapsed = 0
        for row in rows:
            set_index = set_by_name(row['SetName'])
            duration = row['Duration']
            self.entries.append(Entry(set_index, duration, elapsed,
                                      self.occurrences.get(set_index, 0),
                                      elapsed - self.per_cycle.get(set_index, 0)))
            self.occurrences[set_index] = self.occurrences.get(set_index, 0) + 1
            self.per_cycle[set_index] = self.per_cycle.get(set_index, 0) + duration
            elapsed += duration
        for entry in self.entries:
            entry.per_cycle = self.per_cycle[entry.set]
        self.total = elapsed

    def entry_at(self, position):
        """ (index, entry) of the row covering a minute of the cycle.
        """
        for index, entry in enumerate(self.entries):
            if position < entry.start + entry.duration:
                return index, entry
        return index, entry


class Resolved(object):
    __slots__ = ('interval', 'set', 'mode', 'start', 'end', 'weekend')

    def __init__(self, interval, set_index, mode, start, end, weekend):
        self.interval = interval
        self.set = set_index
        self.mode = mode
        self.start = start
        self.end = end
        self.weekend = weekend


class Lineup(object):
    """ What a join at one minute gets: the mode, and either a league (prix
        modes) or a numbered pair of tracks (track modes).
    """
    __slots__ = ('t', 'mode', 'type', 'league', 'secret', 'mirror', 'set_index',
                 'tracks', 'public')

    def __init__(self, t, mode, type_id):
        self.t = t
        self.mode = mode
        self.type = type_id
        self.league = None
        # the league replacing 'league' while a MysteryPrixSchedule window is open
        self.secret = None
        self.mirror = None
        self.set_index = None
        self.tracks = None
        # True when a private lobby would be handed the public lineup
        self.public = True

    @property
    def set_id(self):
        return None if self.set_index is None else self.set_index + 1


class Schedule(object):
    """ One GameScheduleV1 with one weekend table in force.

        weekend_block is the plain 'WeekendSchedule' block, or one entry of
        'WeekendSchedules' (a weekend event). An entry brings its own sets and
        game modes, applies only inside 'window' and may carry its own
        MysteryPrixSchedule. The per-week totals that drive every rotation
        assume the weekend table on every weekend day of every week, as the
        game assumes.
    """
    def __init__(self, game_schedule, weekend_block, extra_modes=(), window=None):
        self.modes = list(game_schedule['GameModeList']) + list(extra_modes)
        self.mode_index = {mode['Name']: i for i, mode in enumerate(self.modes)}
        sets = (list(game_schedule['GameModeSchedule']['Sets'])
                + list(weekend_block.get('Sets') or []))
        self.sets = [[self.mode_index[mode['Name']] for mode in item['Game Modes']]
                     for item in sets]
        self.weekday = IntervalTable(game_schedule['GameModeSchedule']['Interval'],
                                     self.set_by_name)
        self.weekend = IntervalTable(weekend_block['IntervalWeekend'], self.set_by_name)
        self.weekend_days = {DAYS[day.strip()]
                             for day in weekend_block.get('Weekend', '').split(',')
                             if day.strip()}
        self.window = window or (0, FOREVER)
        self.bonus = weekend_block.get('ActiveBonus') or {}
        self.track_sets = {type_id: TrackSets(game_schedule[block])
                           for type_id, block in TRACK_SET_BLOCKS.items()}
        self.mystery_track = self._windows(game_schedule.get('MysteryTrackSchedule'))
        self.mystery_prix = self._windows(game_schedule.get('MysteryPrixSchedule'))
        self.weekend_mystery_prix = self._windows(
                weekend_block.get('MysteryPrixSchedule'))
        self._build_day_tables()

    @staticmethod
    def _windows(block):
        return Windows(block) if block else None

    def _build_day_tables(self):
        """ Cumulative minutes of each mode, and occurrences of each set, through
            each day of the week (Sunday first); index 6 is the weekly total.
        """
        cycles_wd = 1440 // self.weekday.total
        cycles_we = 1440 // self.weekend.total
        self.set_occurrences = [[0] * 7 for _ in self.sets]
        self.mode_minutes = [[0] * 7 for _ in self.modes]
        for set_index, modes in enumerate(self.sets):
            share = len(modes) or 1
            per_day_wd = (self.weekday.per_cycle.get(set_index, 0) * cycles_wd) // share
            per_day_we = (self.weekend.per_cycle.get(set_index, 0) * cycles_we) // share
            minutes = occurrences = 0
            for day in range(7):
                if day in self.weekend_days:
                    minutes += per_day_we
                    occurrences += (self.weekend.occurrences.get(set_index, 0)
                                    * cycles_we)
                else:
                    minutes += per_day_wd
                    occurrences += (self.weekday.occurrences.get(set_index, 0)
                                    * cycles_wd)
                self.set_occurrences[set_index][day] = occurrences
                for mode in modes:
                    self.mode_minutes[mode][day] += minutes

    def set_by_name(self, name):
        """ The set holding a single mode of that name; the game falls back
            to set 0 when there is none.
        """
        for index, modes in enumerate(self.sets):
            if len(modes) == 1 and self.modes[modes[0]]['Name'] == name:
                return index
        return 0

    def mode_by_type(self, type_id):
        """ The first scheduled mode of a type that carries leagues or tracks.
        """
        for modes in self.sets:
            for mode in modes:
                data = self.modes[mode]
                if not (data.get('Leagues') or data.get('Tracks')):
                    continue
                if TYPE_ID[data['Type']] == type_id:
                    return mode
        return -1

    def is_weekend_time(self, t):
        wday, _ = split_time(t)
        return self.window[0] <= t < self.window[1] and wday in self.weekend_days

    def table_at(self, t):
        return self.weekend if self.is_weekend_time(t) else self.weekday

    @staticmethod
    def weeks(t):
        return (c_div(t, 60) + EPOCH_TO_SUNDAY) // MINUTES_PER_WEEK

    def resolve(self, t):
        """ The interval in force at t: its row, set, mode and bounds.
        """
        table = self.table_at(t)
        wday, day_minute = split_time(t)
        minute = c_div(t, 60)
        position = c_mod(minute, table.total)
        index, entry = table.entry_at(position)
        counter = (self.weeks(t) * self.set_occurrences[entry.set][6]
                   + (self.set_occurrences[entry.set][wday - 1] if wday else 0)
                   + entry.occurrence
                   + (day_minute // table.total) * table.occurrences.get(entry.set, 0))
        modes = self.sets[entry.set]
        mode = modes[counter % len(modes)]
        start = (minute - (position - entry.start)) * 60
        return Resolved(index, entry.set, mode, start, start + entry.duration * 60,
                        table is self.weekend)

    def slot_counter(self, t, interval, mode):
        """ Minutes the mode has been active since the epoch, with the current
            tables always in force.
        """
        table = self.table_at(t)
        wday, day_minute = split_time(t)
        cycles, position = divmod(day_minute, table.total)
        entry = table.entries[interval if interval < len(table.entries) else 0]
        record = self.mode_minutes[mode]
        return ((record[wday - 1] if wday else 0) + self.weeks(t) * record[6]
                + position + entry.per_cycle * cycles - entry.other_before)

    @staticmethod
    def rotation_interval(mode):
        interval = mode.get('RotationInterval', 0)
        return interval if interval >= 2 else 1

    def rotation_index(self, t, interval, mode, extra=0):
        counter = self.slot_counter(t, interval, mode)
        return counter // self.rotation_interval(self.modes[mode]) + extra

    def league(self, t, interval, mode, extra=0):
        """ (index, entry) of the league or track entry the mode runs at t.
        """
        data = self.modes[mode]
        leagues = data.get('Leagues') or data.get('Tracks') or []
        if not leagues:
            return None, None
        index = self.rotation_index(t, interval, mode, extra)
        order = self.rotation_order(data)
        if order:
            league = order[c_mod(index, len(order))] - 1
        else:
            league = c_mod(index, len(leagues))
        if not 0 <= league < len(leagues):
            league = 0
        return league, leagues[league]

    @staticmethod
    def rotation_order(data):
        """ The mode's 1-based RotationOrder list; a scalar value (the game
            writes -1 for a single league) means plain order.
        """
        order = data.get('RotationOrder')
        return order if isinstance(order, list) and order else None

    def rotation(self, mode):
        """ League names in the order the mode rotates through them.
        """
        data = self.modes[mode]
        leagues = data.get('Leagues') or []
        order = self.rotation_order(data) or range(1, len(leagues) + 1)
        return [leagues[i - 1]['Name'] for i in order]

    def mirror_pattern(self, t, interval, mode):
        patterns = self.modes[mode].get('MirrorTrackSubstitutionPatterns')
        if not patterns:
            return None
        return patterns[c_mod(self.rotation_index(t, interval, mode), len(patterns))]

    def secret_prix(self, t, resolved, now):
        """ The league from the MysteryPrixSchedule when its window is open on
            the GP counter at t, or None. World Tour slots are never replaced.
        """
        data = self.modes[resolved.mode]
        if data['Type'] != 'GrandPrix':
            return None
        _, league = self.league(t, resolved.interval, resolved.mode)
        if league is None or league['Name'] in WORLD_TOUR_LEAGUES:
            return None
        if resolved.weekend and self.weekend_mystery_prix:
            windows = self.weekend_mystery_prix
        else:
            windows = self.mystery_prix
        if windows is None:
            return None
        counter = self.slot_counter(t, resolved.interval, resolved.mode)
        index = windows.evaluate(counter, now)
        return None if index == -1 else windows.item(index)

    def lineup(self, t, now=None):
        """ What a public join at t gets.
        """
        now = t if now is None else now
        resolved = self.resolve(t)
        data = self.modes[resolved.mode]
        type_id = TYPE_ID[data['Type']]
        result = Lineup(t, data['Name'], type_id)
        entries = data.get('Leagues') or data.get('Tracks') or []
        placeholder = (len(entries) == 1
                       and entries[0].get('TrackId') == PLACEHOLDER_TRACK)
        if placeholder:
            offset = entries[0].get('Offset', 0)
            if type_id == WILDCARD_MINI_PRIX:
                mode = self.mode_by_type(MINI_PRIX)
                if mode != -1:
                    _, league = self.league(t, resolved.interval, mode, offset)
                    result.league = league['Name']
            else:
                sets = self.track_sets.get(type_id, self.track_sets[COLOR_TEAMS])
                turn = self.rotation_index(t, resolved.interval, resolved.mode)
                index = c_mod(turn + offset, len(sets))
                result.set_index = index
                result.tracks = sets.sets[index]
        elif entries:
            _, league = self.league(t, resolved.interval, resolved.mode)
            result.league = league['Name']
            if type_id == MINI_PRIX:
                result.mirror = self.mirror_pattern(t, resolved.interval, resolved.mode)
            if type_id == GRAND_PRIX:
                result.secret = self.secret_prix(t, resolved, now)
        return result

    def ninety_nine(self, t, now=None):
        """ The 99-race track pair at t, public and private alike: plain wall
            clock, with the mystery track replacing the first track while a
            MysteryTrackSchedule window is open.
        """
        now = t if now is None else now
        sets = self.track_sets[COLOR_TEAMS]
        index = sets.wallclock_index(t)
        tracks = list(sets.sets[index])
        mystery = None
        if self.mystery_track is not None:
            found = self.mystery_track.evaluate(c_div(t, 60), now)
            if found != -1:
                mystery = self.mystery_track.item(found)
                tracks[0] = (mystery, 'Normal')
        return index, tuple(tracks), mystery

    def mystery_track_windows(self, start, end, now=None):
        """ (start, end, track) in Unix seconds of each mystery-track window
            overlapping a time range.
        """
        if self.mystery_track is None:
            return []
        now = start if now is None else now
        return [(opens * 60, closes * 60, track)
                for opens, closes, track in self.mystery_track.windows_between(
                    c_div(start, 60), c_div(end - 1, 60) + 1, now)]

    def private(self, t, type_id, now=None):
        """ What a private lobby opened at t gets for a prix type (MiniPrix,
            ClassicMiniPrix, WildCardMiniPrix) or a track type (ColorTeams,
            HardTracks, Classic). While the public schedule runs the same
            mode, the public lineup is handed out instead.
        """
        now = t if now is None else now
        public = self.lineup(t, now)
        if public.type == type_id:
            return public
        mode = self.mode_by_type(type_id)
        if mode == -1:
            return None
        data = self.modes[mode]
        result = Lineup(t, data['Name'], type_id)
        result.public = False
        minute = c_div(t, 60)
        if type_id in MINI_PRIX_TYPES:
            leagues = data.get('Leagues') or []
            offset = 0
            wildcard = leagues and leagues[0].get('TrackId') == PLACEHOLDER_TRACK
            if type_id == WILDCARD_MINI_PRIX and wildcard:
                offset = leagues[0].get('Offset', 0)
                mode = self.mode_by_type(MINI_PRIX)
                data = self.modes[mode]
                leagues = data.get('Leagues') or []
            turn = c_div(minute, self.rotation_interval(data))
            result.league = leagues[c_mod(turn + offset, len(leagues))]['Name']
            patterns = data.get('MirrorTrackSubstitutionPatterns')
            if patterns:
                result.mirror = patterns[c_mod(turn, len(patterns))]
            return result
        resolved = self.resolve(t)
        _, entry = self.league(t, resolved.interval, mode)
        offset = 0
        if entry and entry.get('TrackId') == PLACEHOLDER_TRACK:
            offset = entry.get('Offset', 0)
        sets = self.track_sets.get(type_id, self.track_sets[COLOR_TEAMS])
        index = c_mod(sets.wallclock_index(t) + offset, len(sets))
        result.set_index = index
        result.tracks = sets.sets[index]
        return result


class ScheduleData(object):
    """ A GameScheduleV1 file with its WeekendSchedule file.

        The WeekendSchedule file may list weekend events ('WeekendSchedules')
        with a calendar ('Schedule') of when each is in force. The schedule in
        force at a time is the base schedule, or the event's schedule inside
        its calendar window. weekend_event pins one event for all time, or
        'none' disables the calendar; the default follows it.
    """
    AUTO = 'auto'
    NONE = 'none'

    def __init__(self, game_schedule, weekend_schedule, weekend_event=AUTO):
        self.game_schedule = game_schedule
        self.weekend_schedule = weekend_schedule
        self.events = {entry['ID']: entry
                       for entry in weekend_schedule.get('WeekendSchedules') or []}
        self.extra_modes = weekend_schedule.get('WeekendGameModeList') or []
        self.calendar = []
        if weekend_event == self.AUTO:
            for row in weekend_schedule.get('Schedule') or []:
                if row['WeekendScheduleID'] in self.events:
                    self.calendar.append((parse_time(row['StartTime']),
                                          parse_time(row['EndTime']),
                                          row['WeekendScheduleID']))
            self.calendar.sort()
        elif weekend_event != self.NONE:
            if weekend_event not in self.events:
                raise KeyError("Unknown weekend schedule '{0}'.".format(weekend_event))
            self.calendar.append((0, FOREVER, weekend_event))
        self._base = Schedule(game_schedule, weekend_schedule['WeekendSchedule'],
                              self.extra_modes)
        self._schedules = {}

    @property
    def active_window(self):
        """ (start, end) of the files' ActiveStartTime/ActiveEndTime, or None
            for files without one.
        """
        start = self.game_schedule.get('ActiveStartTime')
        end = self.game_schedule.get('ActiveEndTime')
        if not (start and end):
            return None
        return parse_time(start), parse_time(end)

    def calendar_entry(self, t):
        for entry in self.calendar:
            if entry[0] <= t < entry[1]:
                return entry
        return None

    def weekend_event(self, t):
        """ The ID of the weekend event in force at t, or None.
        """
        entry = self.calendar_entry(t)
        return entry[2] if entry else None

    def next_change(self, t):
        """ When the schedule in force at t stops being so, or FOREVER.
        """
        entry = self.calendar_entry(t)
        if entry:
            return entry[1]
        later = [start for start, _, _ in self.calendar if start > t]
        return min(later) if later else FOREVER

    def schedule_at(self, t):
        entry = self.calendar_entry(t)
        if entry is None:
            return self._base
        if entry not in self._schedules:
            event = self.events[entry[2]]
            self._schedules[entry] = Schedule(self.game_schedule, event,
                                              self.extra_modes,
                                              window=(entry[0], entry[1]))
        return self._schedules[entry]

    def intervals(self, t, until):
        """ (start, end, schedule) of the intervals in force from the one
            covering t until 'until', clipped at calendar changes.
        """
        while t < until:
            schedule = self.schedule_at(t)
            resolved = schedule.resolve(t)
            end = min(resolved.end, self.next_change(t))
            yield resolved.start, end, schedule
            t = end


def league_tracks(stage_list):
    """ Name to track ids of every league in a StageList file.
    """
    return {league['Name']: [track['TrackId'] for track in league.get('Tracks') or []]
            for league in stage_list['GPList']}
