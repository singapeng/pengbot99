""" Bot-facing views of the game schedule: Event lists built from
    gameschedule.ScheduleData, in the vocabulary the bot and its formatters
    use (knight, mknight, miniprix, teambattle ...).

    No manager here reads configuration; the schedule data is handed in.
"""

from datetime import datetime, timezone

from pengbot99 import events, formatters, gameschedule

LEAGUE_NAMES = {
    'KnightLeague': 'knight', 'MirrorKnightLeague': 'mknight',
    'QueenLeague': 'queen', 'MirrorQueenLeague': 'mqueen',
    'KingLeague': 'king', 'MirrorKingLeague': 'mking',
    'AceLeague': 'ace', 'MirrorAceLeague': 'mace',
    'WorldTour': 'worldtour', 'WorldTour7Races': 'worldtour',
    'MysteryLeague': 'glitchgp',
}
MODE_NAMES = {
    gameschedule.COLOR_TEAMS: 'teambattle', gameschedule.HARD_TRACKS: 'protracks',
    gameschedule.CLASSIC: 'classic', gameschedule.MINI_PRIX: 'miniprix',
    gameschedule.CLASSIC_MINI_PRIX: 'classicprix',
    gameschedule.WILDCARD_MINI_PRIX: 'mysteryprix', gameschedule.CLOSED: 'closed',
}
TRACK_MODE_TYPES = {
    'teambattle': gameschedule.COLOR_TEAMS, 'protracks': gameschedule.HARD_TRACKS,
    'classic': gameschedule.CLASSIC,
}
MINI_PRIX_MODE_TYPES = {
    'miniprix': gameschedule.MINI_PRIX, 'classicprix': gameschedule.CLASSIC_MINI_PRIX,
}
# the ActiveBonus type a Machine Shuffle weekend carries
SHUFFLE_BONUS = 1
# rows of a private lineup query: the opening minute plus this many
PRIVATE_MINUTES = 10
# how far get_events() looks ahead by default, in minutes
WEEK = 10080


def to_unix(timestamp):
    return int(timestamp.timestamp())


def from_unix(t):
    return datetime.fromtimestamp(t, timezone.utc)


def floor_minute(timestamp):
    return timestamp.replace(second=0, microsecond=0)


def now_utc():
    return datetime.now(timezone.utc)


def lineup_name(lineup):
    """ The bot's name for what a lineup runs.
    """
    if lineup.type == gameschedule.GRAND_PRIX:
        return LEAGUE_NAMES.get(lineup.league, lineup.league)
    return MODE_NAMES[lineup.type]


def track_name(track):
    """ 'mBig_Blue' for a mirror track, the id otherwise.
    """
    track_id, track_type = track
    return ('m' if track_type == 'Mirror' else '') + track_id


def track_pair_name(tracks):
    separator = formatters.track_separators['choice']
    return separator.join(track_name(track) for track in tracks)


class GameEvent(events.Event):
    """ An Event that also knows the game mode it came from, the league
        rotation of that mode, and whether it ran under a shuffle bonus.
    """
    def __init__(self, name, start, end, lineup, schedule):
        duration = (end - start) // 60
        weekend = schedule.is_weekend_time(start)
        super().__init__(name=name, end_minute=duration,
                         schedname='weekend' if weekend else 'weekday')
        self.set_start_time(from_unix(start))
        self.mode = lineup.mode
        self.rotation = []
        if lineup.type == gameschedule.GRAND_PRIX:
            rotation = schedule.rotation(schedule.mode_index[lineup.mode])
            self.rotation = [LEAGUE_NAMES.get(league, league) for league in rotation]
        self.glitch = lineup.secret is not None
        self.shuffle = is_shuffle(schedule, start)


class LineupEvent(events.MiniPrixEvent):
    """ A MiniPrixEvent that knows whether it ran under a shuffle bonus and
        whether a private lobby would have been handed it as the public lineup.
    """
    def __init__(self, mp_type, lineup, tracks, start, schedule):
        number = lineup.league[-3:]
        mp_id = number
        if lineup.mirror is not None:
            mp_id = '{0}.{1}'.format(number, lineup.mirror)
        super().__init__(mp_type, mp_id, tracks[0], tracks[1], tracks[2],
                         start_minute=0, end_minute=1, mirrored=lineup.mirror or '000',
                         schedname=lineup.mode)
        self.set_start_time(from_unix(start))
        self.shuffle = is_shuffle(schedule, start)
        self.public = lineup.public


def is_shuffle(schedule, t):
    return schedule.is_weekend_time(t) and schedule.bonus.get('Type') == SHUFFLE_BONUS


def matches(event, names):
    """ Whether an event answers a names filter: by its own name, or by the
        league a Secret League replaces.
    """
    return not names or event.name in names or event.glitched_name in names


class SlotScheduleManager(object):
    """ The sequence of game modes: Grand Prix leagues, Mini-Prix slots and
        special events, with Secret League replacements.
    """
    def __init__(self, data):
        self.data = data

    def _event(self, start, end, schedule):
        lineup = schedule.lineup(start)
        return GameEvent(lineup_name(lineup), start, end, lineup, schedule)

    def get_event(self, timestamp):
        """ The event ongoing at the timestamp.
        """
        t = to_unix(timestamp)
        start, end, schedule = next(self.data.intervals(t, t + 1))
        return self._event(start, end, schedule)

    def get_current_event(self):
        return self.get_event(now_utc())

    def get_events(self, names=None, count=0, timestamp=None, limit=WEEK):
        """ Events starting after the timestamp's minute, within 'limit'
            minutes, optionally filtered by name and capped at 'count'.
        """
        timestamp = floor_minute(timestamp or now_utc())
        t = to_unix(timestamp)
        found = []
        for start, end, schedule in self.data.intervals(t, t + limit * 60):
            if start <= t:
                continue
            event = self._event(start, end, schedule)
            if matches(event, names):
                found.append(event)
                if count and len(found) >= count:
                    break
        return found

    def list_events(self, timestamp=None, next=60):
        """ The ongoing event followed by those starting in the next minutes.
        """
        timestamp = timestamp or now_utc()
        upcoming = self.get_events(timestamp=timestamp, limit=next)
        return [self.get_event(timestamp)] + upcoming

    def when_event(self, names, count=1, timestamp=None, limit=WEEK):
        return self.get_events(names=names, count=count, timestamp=timestamp,
                               limit=limit)

    def is_secret_league_on(self, timestamp=None):
        """ Whether the schedule in force can replace a Grand Prix with the
            Secret League at all.
        """
        schedule = self.data.schedule_at(to_unix(timestamp or now_utc()))
        return any(windows is not None and windows.cycle for windows in
                   (schedule.mystery_prix, schedule.weekend_mystery_prix))

    def weekend_event(self, timestamp=None):
        """ The weekend event in force, by the game's ID, or None.
        """
        return self.data.weekend_event(to_unix(timestamp or now_utc()))


class MysteryTrackManager(object):
    """ The windows in which a Mystery track replaces the first track of the
        99-race pair.
    """
    def __init__(self, data):
        self.data = data

    def get_events(self, names=None, count=0, timestamp=None, limit=WEEK):
        timestamp = floor_minute(timestamp or now_utc())
        t = to_unix(timestamp)
        found = []
        for start, end, schedule in self.data.intervals(t, t + limit * 60):
            windows = schedule.mystery_track_windows(start, end, now=start)
            for opens, closes, track in windows:
                if opens <= t or opens < start:
                    continue
                if names and track not in names and 'glitch99' not in names:
                    continue
                event = events.Event(name=track, end_minute=(closes - opens) // 60)
                event.set_start_time(from_unix(opens))
                found.append(event)
                if count and len(found) >= count:
                    return found
        return found

    def when_event(self, names, count=1, timestamp=None, limit=WEEK):
        return self.get_events(names=names, count=count, timestamp=timestamp,
                               limit=limit)


class NinetyNineManager(object):
    """ The 99-race track pair minute by minute, mystery tracks included.
    """
    NAME = 'F-Zero 99 Races'

    def __init__(self, data):
        self.data = data
        self.name = self.NAME

    def list_events(self, timestamp=None, next=12):
        """ The pair for the timestamp's minute and each of the next minutes.
        """
        timestamp = floor_minute(timestamp or now_utc())
        t = to_unix(timestamp)
        found = []
        for minute in range(next + 1):
            at = t + minute * 60
            set_index, tracks, _ = self.data.schedule_at(at).ninety_nine(at)
            event = events.Event(name=track_pair_name(tracks),
                                 start_minute=set_index, end_minute=set_index + 1)
            event.set_start_time(from_unix(at))
            found.append(event)
        return found

    def get_formatted_events(self, from_time=None, next=12):
        found = self.list_events(timestamp=from_time, next=next)
        if from_time:
            header = '{0} events {1} local time:'.format(
                self.name, formatters.format_discord_timestamp(from_time, inline=True))
        else:
            header = '{0} upcoming track selection:\n'.format(self.name)
        return [header] + [formatters.format_track_choice(event) for event in found]


class TrackPairManager(object):
    """ Team Battle, Pro-Tracks and Classic track pairs, which change every
        minute. Public queries cover the ongoing or next slot of the mode;
        private ones the minutes following the timestamp.
    """
    def __init__(self, data, mode_name, private=False):
        self.data = data
        self.name = mode_name
        self.type = TRACK_MODE_TYPES[mode_name]
        self.private = private

    def _event(self, lineup, at):
        event = events.Event(name=track_pair_name(lineup.tracks),
                             start_minute=lineup.set_index,
                             end_minute=lineup.set_index + 1)
        event.set_start_time(from_unix(at))
        event.public = lineup.public
        return event

    def list_events(self, timestamp=None, next=PRIVATE_MINUTES):
        timestamp = floor_minute(timestamp or now_utc())
        t = to_unix(timestamp)
        if self.private:
            return [self._event(self.data.schedule_at(at).private(at, self.type), at)
                    for at in (t + minute * 60 for minute in range(next + 1))]
        slot = next_slot(self.data, t, self.type)
        if slot is None:
            return []
        start, end, schedule = slot
        return [self._event(schedule.lineup(at), at) for at in range(start, end, 60)]


class MiniPrixLineupManager(object):
    """ Mini-Prix and Classic Mini-Prix track selections, minute by minute.
        Public queries cover the ongoing or next slot of the mode; private
        ones the minutes following the timestamp, handing out the public
        selection whenever the public slot is running.
    """
    def __init__(self, data, league_tracks, mp_type, private=False):
        self.data = data
        self.league_tracks = league_tracks
        self.name = mp_type
        self.type = MINI_PRIX_MODE_TYPES[mp_type]
        self.private = private

    def _event(self, lineup, at, schedule):
        tracks = self.league_tracks[lineup.league]
        return LineupEvent(self.name, lineup, tracks, at, schedule)

    def get_miniprix(self, timestamp=None):
        timestamp = floor_minute(timestamp or now_utc())
        t = to_unix(timestamp)
        if self.private:
            found = []
            for minute in range(PRIVATE_MINUTES + 1):
                at = t + minute * 60
                schedule = self.data.schedule_at(at)
                found.append(self._event(schedule.private(at, self.type), at, schedule))
            return found
        slot = next_slot(self.data, t, self.type)
        if slot is None:
            return None
        start, end, schedule = slot
        return [self._event(schedule.lineup(at), at, schedule)
                for at in range(start, end, 60)]


def next_slot(data, t, type_id, limit=WEEK):
    """ (start, end, schedule) of the slot of a mode type ongoing at t or the
        first one after it, or None when none runs within 'limit' minutes.
    """
    for start, end, schedule in data.intervals(t, t + limit * 60):
        if schedule.lineup(start).type == type_id:
            return start, end, schedule
    return None
