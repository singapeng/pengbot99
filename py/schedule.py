from datetime import datetime, timedelta, timezone

import abc
import csv


# This should mark a cycle origin in UTC time
# UTC 2024-02-06, 00:00:00
# First Knight league after a King.
origin = datetime(2024, 2, 6, 0, 0, 0, 0, tzinfo=timezone.utc)
# A point observed to be a glitch sequence origin.
glitch_origin = datetime(2024, 2, 13, 0, 59, tzinfo=timezone.utc)
# A point observed to be a private lobby miniprix sequence origin.
plmp_origin = datetime(2024, 3, 9, 19, 50, tzinfo=timezone.utc)


def load_schedule(path, name):
    """ Loads a CSV schedule from the folder 'path' and the file
        named 'name.csv'.
        Each line in the csv should be formatted as such:
        minutes,name[,name,name...]
        'minutes' represents the event duration as an integer.
        'name' is the event type.
        There must be at least one event type name. If several
        are provided, they represent a rotation for this event.
        The last line event type should be 'next' and represents
        the point at which the schedule moves on to the next cycle.
    """
    schedule_path = '{0}/{1}.csv'.format(path, name)
    with open(schedule_path, newline='') as fd:
        reader = csv.reader(fd, delimiter=',')
        schedule = []
        for row in reader:
            try:
                minutes = int(row[0])
                rotation = [minutes] + [str(item) for item in row[1:]]
                schedule.append(tuple(rotation))
            except Exception as e:
                #TODO: better validation
                raise
    assert schedule[-1][1] == "next", "Must end with next"
    return schedule


def cptime(dt):
    """ Utility to copy a date time into a new object.
    """
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    minute = dt.minute
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class TimeTable(object):
    """ This object doesn't know about actual time.
        It is used to query relative time within its schedule, based
        on cycle count.
    """
    def __init__(self, data):
        super().__init__()
        self._data = data
        self.duration = data[-1][0]

    def _get_active_row(self, minute):
        active_row = []
        for row in self._data:
            if row[0] <= minute:
                active_row = row[:]
            # we could break here if row[0] > cycle_minute
            # but assuming the schedule is ordered.
        return active_row

    def _get_next_row(self, minute):
        next_row = []
        for row in self._data:
            if row[0] > minute:
                next_row = row[:]
        return next_row

    def get_event(self, cycle, minute):
        """ What event is on at specified cycle and minute
        """
        active_row = self._get_active_row(minute)
        if active_row:
            # trim time entry
            active_row = active_row[1:]
            rotation_index = cycle % len(active_row)
            return active_row[rotation_index]
        else:
            return ''

    def get_time_left(self, cycle, minute):
        """ How many full minutes remain in the event that is
            active at the given cycle and minute.
        """
        next_row = self._get_next_row(minute)
        if next_row:
            return next_row[0] - minute
        else:
            return -1

    def get_remaining_events(self, cycle, minute, all=False, filter=None):
        """ Returns a list of events in the cycle that have yet
            to start.
        """
        if all:
            # ignore the cycle minute to return every event
            minute = -1
        events = []
        for row in self._data:
            if row[0] > minute:
                rotation_index = cycle % (len(row) - 1)
                current = row[1:][rotation_index]
                if not filter or current in filter or current == 'next':
                    events.append((row[0], current))
        return events


class BaseScheduleManager(metaclass=abc.ABCMeta):
    """ Used to manage the cycle of schedules based on current time
        and a time of origin.
    """
    def __init__(self, origin):
        super().__init__()
        # Should be UTC time of any day starting at 00:00:00
        # The origin must be a time where 00:00:00 matches
        # the beginning of the schedule file, so that all future
        # cycles have the correct offset in the rotation.
        self.origin = origin

    @abc.abstractmethod
    def get_cycle(self, timestamp):
        """ Which cycle this timestamp falls in.
            Cycle 0 starts at origin.
        """

    @abc.abstractmethod
    def get_cycle_info(self, timestamp=None):
        """ Get cycle id and cycle minute
        """

    def get_event(self, timestamp):
        """ Returns the name of the event occuring at given timestamp.
        """
        cycle, cycle_minute, sched = self.get_cycle_info(timestamp)
        return sched.get_event(cycle, cycle_minute)

    def get_remaining_events(self, timestamp, all=False, filter=None):
        """ Events left in the current cycle.
        """
        cycle, cycle_minute, sched = self.get_cycle_info(timestamp)
        events = sched.get_remaining_events(cycle, cycle_minute, all, filter)
        # convert events relative times to datetimes
        ts_events = []
        for event in events:
            minutes_in = event[0] - cycle_minute
            event_start = cptime(timestamp) + timedelta(minutes=minutes_in)
            ts_events.append((event_start, event[1]))
        return ts_events

    def get_current_event(self):
        """ Returns the name of the event occuring now.
        """
        return self.get_event(datetime.now(timezone.utc))

    def get_events(self, names=None, count=0, timestamp=None, limit=10080):
        """ Get a list of all events and their start time
            for the next 'next' minutes.

            names: a list of event names to filter on, or
                   None to return any event name
            count: the maximum number of events to return
                   or set to zero for no maximum
            timestamp: get events from this time onwards,
                       or None from current time.
            limit: allow events to be looked up to this many
                   minutes in the future. Defaults to 7 days.
        """
        timestamp = timestamp or datetime.now(timezone.utc)
        events = []
        ts_limit = timestamp + timedelta(minutes=limit)
        all = False
        # events left in current cycle
        cycle_start = timestamp
        while cycle_start is not None:
            next_events = self.get_remaining_events(cycle_start, all=all, filter=names)
            for event in next_events:
                if event[0] <= ts_limit:
                    if event[1] == 'next':
                        # we need to query the next cycle
                        cycle_start = event[0]
                        all = True
                    else:
                        events.append((event[0], event[1]))
                        if count and len(events) >= count:
                            # we reached the specified count of events
                            return events
                else:
                    # the next event is outside the timeframe
                    cycle_start = None
        return events

    def list_events(self, timestamp=None, next=60):
        """ Get a list of all events and their start time
            current and future for the next 'next' minutes.
            This is a short-hand to get_events that also
            fetches current, and sets a short minutes lookahead.
        """
        timestamp = timestamp or datetime.now(timezone.utc)
        events = self.get_events(timestamp=timestamp, limit=next)
        # the event happening now
        start_event = self.get_event(timestamp)
        return [(timestamp, start_event)] + events

    def when_event(self, names, count=1, timestamp=None, limit=10080):
        """ When is the next instance of an event.
            This is a shorthand to get_events that sets count to 1
            and requires a names filter.
            names can be given as a list of events to search for
        """
        return self.get_events(names=names, count=count, timestamp=timestamp, limit=limit)


class Slot1ScheduleManager(BaseScheduleManager):
    """ Used to manage the cycle of schedules based on current time
        and a time of origin.
        This manager is intended to deal with F-Zero 99's 'slot 1'
        schedule, i.e. the 99 races slot.
    """
    def __init__(self, origin, sched):
        super().__init__(origin)
        self.sched = TimeTable(sched)

    def get_cycle(self, timestamp):
        """ Which cycle this timestamp falls in.
            Cycle 0 starts at origin.
        """
        now = timestamp or datetime.now(timezone.utc)
        minutes = int((now - self.origin).total_seconds()) // 60
        return minutes // self.sched.duration

    def get_cycle_info(self, timestamp=None):
        """ Get cycle id and cycle minute
        """
        timestamp = timestamp or datetime.now(timezone.utc)
        cycle = self.get_cycle(timestamp)
        minutes = int((timestamp - self.origin).total_seconds()) // 60
        cycle_minute = minutes % self.sched.duration
        return (cycle, cycle_minute, self.sched)


class Slot2ScheduleManager(BaseScheduleManager):
    """ Used to manage the cycle of schedules based on current time
        and a time of origin.
        This manager is intended to deal with F-Zero 99's 'slot 2'
        schedule, i.e. the Grand Prix and special events slot.
        It provides support for a dual-schedule rotation with distinct
        weekdays and weekend days timetables.
    """
    def __init__(self, origin, weekday_sched, weekend_sched):
        super().__init__(origin)
        # Monday to Friday schedule
        self.weekday = TimeTable(weekday_sched)
        # Saturday and Sunday schedule
        self.weekend = TimeTable(weekend_sched)

    def time_types_since_origin(self, until=None):
        """ Utility for breaking down the current time (or the optional
            timestamp) into weekdays, weekend days, and left-over
            minutes since origin.
            The result is returned as a tuple of 3 ints.
        """
        now = until or datetime.now(timezone.utc)
        delta = now - self.origin
        # count full weeks
        weeks = delta.days // 7
        week_days = weeks * 5
        weekend_days = weeks * 2
        minutes_today = delta.seconds // 60
        # add remaining days
        remainder = delta.days % 7
        # this list can contain negative weekdays depending what day is now
        days = [day for day in range(now.weekday() - remainder, now.weekday())]
        # make all days be an int from 0 (monday) to 6 (sunday)
        days = [day if day >= 0 else day + 7 for day in days]
        # update count for week days and week end days
        for day in days:
            if day < 5:
                week_days += 1
            else:
                weekend_days += 1
        return (week_days, weekend_days, minutes_today)

    @property
    def daily_weekday_cycles(self):
        """ How many cycles occur in a week day
            Note: at the moment we assume this is an integer number
        """
        return 60 * 24 // self.weekday.duration

    @property
    def daily_weekend_cycles(self):
        """ How many cycles occur in a week end
            Note: at the moment we assume this is an integer number
        """
        return 60 * 24 // self.weekend.duration

    def is_weekday(self, timestamp=None):
        timestamp = timestamp or datetime.now(timezone.utc)
        theday = timestamp.weekday()
        if theday < 5:
            # Monday to Friday
            return True
        else:
            # Saturday or Sunday
            return False

    def get_cycle(self, timestamp):
        """ This works when cycles are less than a day
            and there's a weekday/weekend change.
            It will not work for Mystery Tracks.
        """
        fwds, fweds, mins = self.time_types_since_origin(timestamp)
        if self.is_weekday(timestamp):
            today_duration = self.weekday.duration
        else:
            today_duration = self.weekend.duration
        today_cycles = mins // today_duration
        weekday_cycles = fwds * self.daily_weekday_cycles
        weekend_cycles = fweds * self.daily_weekend_cycles
        return weekday_cycles + weekend_cycles + today_cycles

    def get_cycle_info(self, timestamp=None):
        """ Get cycle id and cycle minute
        """
        timestamp = timestamp or datetime.now(timezone.utc)
        if self.is_weekday(timestamp):
            sched = self.weekday
        else:
            sched = self.weekend
        cycle = self.get_cycle(timestamp)
        day_minutes = timestamp.hour * 60 + timestamp.minute
        cycle_minute = day_minutes % sched.duration
        return (cycle, cycle_minute, sched)
