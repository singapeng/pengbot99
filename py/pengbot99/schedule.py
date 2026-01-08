from datetime import datetime, timedelta, timezone

import abc
import csv

# local imports
from pengbot99 import events


# This should mark a cycle origin in UTC time
# At present it drives all GP and MP cycles (public/private)
# but not 99s.
origin = datetime(2025, 4, 23, 0, 0, 0, 0, tzinfo=timezone.utc)
# A point observed to be a glitch sequence origin.
glitch_origin = datetime(2025, 12, 8, 22, 57, tzinfo=timezone.utc)


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


class CycleInfo(object):
    def __init__(self, sched, count, data, minute):
        super().__init__()
        # A counter for the total number of any cycle
        cycle_id = 0
        self._rotations = {}
        self._events = {}
        # Iterate over time tables
        for tt_key in data:
            # Look up how many times this timetable cycled
            tt_cycles = count.get(tt_key, 0)
            cycle_id += tt_cycles
            # Every unique rotation in this timetable
            for rot_key in data[tt_key]:
                # How many times the rotation occurs
                key_count = data[tt_key][rot_key]
                if self._rotations.get(rot_key):
                    # This rotation appears in other timetables
                    self._rotations[rot_key] += tt_cycles * key_count
                else:
                    self._rotations[rot_key] = tt_cycles * key_count
        self.id = cycle_id
        self.minute = minute
        self.schedule = sched
        self._build_event_count()
        if self.minute > 0:
            self._offset_event_count()

    def _build_event_count(self):
        """ How many of each known event already occured.
        """
        for rotation in self._rotations:
            # how many complete rotations happened
            full_rots = self._rotations[rotation] // len(rotation)
            # if we are part-way through a rotation, at which index are we?
            cur_rot = self._rotations[rotation] % len(rotation)
            # the list of unique events in this rotation
            unique_evts = list(set(rotation))
            for evt_name in unique_evts:
                # how many of this event in a full rotation
                full_count = rotation.count(evt_name)
                if cur_rot:
                    # how many events have happened as part of the current rotation
                    cur_count = rotation[:cur_rot].count(evt_name)
                else:
                    cur_count = 0
                # tally this event's occurences from this rotation
                evt_count = full_rots * full_count + cur_count
                if evt_name in self._events:
                    # we have seen this event in another rotation
                    self._events[evt_name] += evt_count
                else:
                    # we have not seen this event yet
                    self._events[evt_name] = evt_count

    def _offset_event_count(self):
        """ If this cycle is in progress, what does it mean for the event count?
        """
        cycle_rots = self.schedule.get_rotations_until(self.minute)
        for rot in set(cycle_rots):
            # how many times did this rotation show up in this cycle?
            count = cycle_rots.count(rot)
            # current index for this rotation at cycle start
            idx = self._rotations[rot] % len(rot)
            for n in range(count):
                evt_name = rot[(idx + n) % len(rot)]
                self._events[evt_name] += 1
            # then we need to update the rotation count
            self._rotations[rot] += count

    def get_rotation(self, evts):
        """ Returns the number of occurences of this rotation of events
        """
        return self._rotations.get(tuple(evts)) or self.id

    def get_event(self, evt):
        """ Returns the number of occurences of this event across all rotations
        """
        return self._events.get(str(evt)) or 0

    def find_rotation(self, evts):
        """ Given a list of event name, returns the first rotation that
            contains any event with such name. Only one name in 'evt' needs to
            match.
        """
        for rot in self._rotations:
            for name in evts:
                if name in rot:
                    return rot
        return None


def build_rotation_data(timetables):
    res = {}
    tt_idx = 0
    for tt in timetables:
        if tt.name:
            res[tt.name] = tt.get_rotations()
        else:
            res[tt_idx] = tt.get_rotations()
            tt_idx += 1
    return res


class TimeTable(object):
    """ This object doesn't know about actual time.
        It is used to query relative time within its schedule, based
        on cycle count.
    """
    def __init__(self, data, name=None):
        super().__init__()
        self.name = name
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
                break
        return next_row

    def get_event(self, cycle_info):
        """ What event is on at specified cycle and minute

            Because this is within the schedule, we need info supplied
            by CycleInfo objects to calculate the state of rotations.
            Most calls rely on get_remaining_events(), so CycleInfo offsets
            for future events, and this call her needs to un-offset
            rotations as a result. This is illustrates a flaw in the
            relation between CycleInfo and TimeTable, which should
            instead both be accessed by a manager class.
        """
        active_row = self._get_active_row(cycle_info.minute)
        if active_row:
            # trim time entry
            start_minute = active_row[0]
            active_row = active_row[1:]
            cycle = cycle_info.get_rotation(active_row)
            if cycle_info.minute > start_minute:
                # the rotation for the current event was already counted
                rot_count = -1
            else:
                # the current event isn't started, rotation uncounted
                rot_count = 0
            rotation_index = (cycle + rot_count) % len(active_row)
            name = active_row[rotation_index]
            next_row = self._get_next_row(cycle_info.minute)
            if next_row:
                end_minute = next_row[0]
            else:
                # likely not needed
                end_minute = start_minute
            return events.Event(
                    name=name, cycle=cycle, cycle_minute=cycle_info.minute,
                    start_minute=start_minute, end_minute=end_minute,
                    rotation=active_row, rotation_offset=rotation_index)
        else:
            return ''

    def get_time_left(self, minute):
        """ How many full minutes remain in the event that is
            active at the given cycle and minute.
        """
        next_row = self._get_next_row(minute)
        if next_row:
            return next_row[0] - minute
        else:
            return -1

    def get_remaining_events(self, cycle_info, all=False, filter=None):
        """ Returns a list of events in the cycle that have yet
            to start.
        """
        minute = cycle_info.minute
        if all:
            # ignore the cycle minute to return every event
            minute = -1
        idx = 0
        evts = []
        # rot_counts is used to keep track of rotations we visited, so that we
        # calculate the correct rotation offset if a rotation appears more than
        # once in remaining events
        rots_count = {}
        while idx < len(self._data):
            row = self._data[idx]
            rotation = row[1:]
            if row[0] > minute:
                start_minute = row[0]
                cycle = cycle_info.get_rotation(rotation) + rots_count.get(rotation, 0)
                rotation_index = cycle % len(rotation)
                current = row[1:][rotation_index]
                if not filter or current in filter or current == 'next':
                    if current != "next":
                        end_minute = self._data[idx + 1][0]
                    else:
                        end_minute = start_minute
                    evts.append(events.Event(
                            name = current, cycle=cycle, cycle_minute=cycle_info.minute,
                            start_minute=start_minute, end_minute=end_minute,
                            rotation=rotation, rotation_offset=rotation_index
                            ))
            if row[0] >= minute:
                # using greater-equal comparison here lets us catch the current event's
                # rotation in case it's relevant to our offset.
                if rotation not in rots_count:
                    rots_count[rotation] = 1
                else:
                    rots_count[rotation] += 1
            idx += 1
        return evts

    def get_rotations(self, name=None):
        """ Returns a dict of rotations with their count.
            Optionally, rotations can be filtered on a specific event name.
            In this case, only rotations including the event will be returned.
        """
        rotations = {}
        for row in self._data[:-1]:
            t_row = tuple(row[1:])
            if name and name not in t_row:
                continue
            if t_row in rotations:
                rotations[t_row] += 1
            else:
                rotations[t_row] = 1
        return rotations

    def get_rotations_until(self, minute):
        """ Returns a list of rotations that occur before the given minute in
            the current cycle.
        """
        rotations = []
        start_minute = 0
        for row in self._data:
            start_minute = row[0]
            # capture past events and in-progress events
            # but not one that's immediately starting.
            if start_minute < minute and row[1] != 'next':
                rotations.append(row[1:])
            else:
                break
        return rotations


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
    def get_cycle_count(self, timestamp):
        """ Which cycle this timestamp falls in.
            Cycle 0 starts at origin.
        """

    @abc.abstractmethod
    def get_cycle_info(self, timestamp=None):
        """ Get a CycleInfo object
        """

    def get_event(self, timestamp):
        """ Returns the name of the event occuring at given timestamp.
        """
        cycle_info = self.get_cycle_info(timestamp)
        event = cycle_info.schedule.get_event(cycle_info)
        minutes_in = event.cycle_minute - event.start_minute
        new_ts = cptime(timestamp) - timedelta(minutes=minutes_in)
        event.set_start_time(new_ts)
        return event

    def get_remaining_events(self, timestamp, all=False, filter=None):
        """ Events left in the current cycle.
        """
        cycle_info = self.get_cycle_info(timestamp)
        remaining_events = cycle_info.schedule.get_remaining_events(cycle_info, all, filter)
        # convert events relative times to datetimes
        ts_events = []
        for event in remaining_events:
            minutes_in = event.start_minute - cycle_info.minute
            event_start = cptime(timestamp) + timedelta(minutes=minutes_in)
            event.set_start_time(event_start)
            ts_events.append(event)
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
        evts = []
        ts_limit = timestamp + timedelta(minutes=limit)
        all = False
        # events left in current cycle
        cycle_start = timestamp
        while cycle_start is not None:
            next_events = self.get_remaining_events(cycle_start, all=all, filter=names)
            for event in next_events:
                if event.start_time <= ts_limit:
                    if event.name == 'next':
                        # we need to query the next cycle
                        cycle_start = event.start_time
                        all = True
                    else:
                        evts.append(event)
                        if count and len(evts) >= count:
                            # we reached the specified count of events
                            return evts
                else:
                    # the next event is outside the timeframe
                    cycle_start = None
        return evts

    def list_events(self, timestamp=None, next=60):
        """ Get a list of all events and their start time
            current and future for the next 'next' minutes.
            This is a short-hand to get_events that also
            fetches current, and sets a short minutes lookahead.
        """
        timestamp = timestamp or datetime.now(timezone.utc)
        evts = self.get_events(timestamp=timestamp, limit=next)
        # the event happening now
        start_event = self.get_event(timestamp)
        return [start_event] + evts

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
        self.sched = TimeTable(sched, "slot1")
        self.rotation_data = build_rotation_data([self.sched])

    def get_cycle_count(self, timestamp):
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
        cycle = {"slot1": self.get_cycle_count(timestamp)}
        minutes = int((timestamp - self.origin).total_seconds()) // 60
        cycle_minute = minutes % self.sched.duration
        return CycleInfo(self.sched, cycle, self.rotation_data, cycle_minute)


class Slot2ScheduleManager(BaseScheduleManager):
    """ Used to manage the cycle of schedules based on current time
        and a time of origin.
        This manager is intended to deal with F-Zero 99's 'slot 2'
        schedule, i.e. the Grand Prix and special events slot.
        It provides support for a dual-schedule rotation with distinct
        weekdays and weekend days timetables.
    """
    def __init__(self, origin, weekday_sched, weekend_sched, glitch_sched=None):
        super().__init__(origin)
        # Monday to Friday schedule
        self.weekday = TimeTable(weekday_sched, "weekday")
        # Saturday and Sunday schedule
        self.weekend = TimeTable(weekend_sched, "weekend")
        # Rotation Data
        self.rotation_data = build_rotation_data([self.weekday, self.weekend])
        # Since 1.5.0, slot2mgr has been updated to support GP rotations
        # that do not start at 0:00 on the first day
        # This caches some data in relation to this.
        self._set_alt_origin()
        # if a Mystery GP weekend is happening (v1.7.0)
        self._mystery_mgr = None
        if glitch_sched:
            self._mystery_mgr = Slot1ScheduleManager(origin, glitch_sched)

    def _set_alt_origin(self):
        """ We may cache the next day from origin and the number of
            minutes between origin and this next day.
            This is to facilitate rotation offset calculations when
            the origin is not at 0:00 on day 1.
        """
        if self.origin.hour or self.origin.minute:
            tmr = self.origin + timedelta(days=1)
            self._alt_origin = datetime(tmr.year, tmr.month, tmr.day, 0, 0,
                    tzinfo=timezone.utc)
            day1mins = (24 - self.origin.hour) * 60 + self.origin.minute
            if self.origin.weekday() < 5:
                self._day1mins = (day1mins, 0)
            else:
                self._day1mins = (0, day1mins)
        else:
            self._alt_origin = None
            self._day1mins = (0, 0)

    def time_types_since_origin(self, until=None):
        """ Utility for breaking down the current time (or the optional
            timestamp) into weekday minutes, and weekend minutes since
            origin.
            The result is returned as a tuple of 2 ints.
        """
        now = until or datetime.now(timezone.utc)
        if now.date() != self.origin.date() and self._alt_origin:
            origin = self._alt_origin
            wd_minutes = self._day1mins[0]
            we_minutes = self._day1mins[1]
        else:
            origin = self.origin
            wd_minutes = 0
            we_minutes = 0
        delta = now - origin
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
        # convert to minutes
        wd_minutes += week_days * 24 * 60
        we_minutes += weekend_days * 24 * 60
        if now.weekday() < 5:
            wd_minutes += minutes_today
        else:
            we_minutes += minutes_today
        return (wd_minutes, we_minutes)

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

    def get_cycle_count(self, timestamp):
        """ This works when cycles are less than a day
            and there's a weekday/weekend change.
            It will not work for Mystery Tracks.
        """
        wd_mins, we_mins = self.time_types_since_origin(timestamp)
        weekday_cycles = wd_mins // self.weekday.duration
        weekend_cycles = we_mins // self.weekend.duration
        return weekday_cycles, weekend_cycles

    def get_cycle_info(self, timestamp=None):
        """ Get cycle id and cycle minute
        """
        timestamp = timestamp or datetime.now(timezone.utc)
        if self.is_weekday(timestamp):
            sched = self.weekday
        else:
            sched = self.weekend
        wdays, wends = self.get_cycle_count(timestamp)
        tt_count = {"weekday": wdays, "weekend": wends}
        day_minutes = timestamp.hour * 60 + timestamp.minute
        cycle_minute = day_minutes % sched.duration
        return CycleInfo(sched, tt_count, self.rotation_data, cycle_minute)

    def _get_daily_event_count(self, day_type, name):
        """ How many times an event occurs in a given day.
            Will raise if cannot be accurately estimated.
        """
        if day_type == "weekday":
            tt = self.weekday
            daily_cycles = self.daily_weekday_cycles
        else:
            tt = self.weekend
            daily_cycles = self.daily_weekend_cycles

        rotations = tt.get_rotations(name)
        if not rotations:
            return 0

        occurences = 0
        for rot in rotations:
            if daily_cycles % len(rot) != 0:
                raise ValueError("Cannot estimate daily occurences of %s." % name)
            occurences += daily_cycles // len(rot) * rot.count(name) * rotations[rot]
        return occurences

    def get_daily_weekday_event_count(self, name):
        return self._get_daily_event_count("weekday", name)

    def get_daily_weekend_event_count(self, name):
        return self._get_daily_event_count("weekend", name)

    def get_remaining_events(self, timestamp, all=False, filter=None):
        """ Events left in the current cycle.
            Overrides base class to manage Mystery GP (v1.7)
        """
        evts = super().get_remaining_events(timestamp, all, filter)
        if self._mystery_mgr:
            evts = self._apply_glitch(evts, timestamp)
        return evts

    def _can_glitch(self, evt):
        if evt.name in ('knight', 'mknight'):
            return True
        return False

    def _apply_glitch(self, evts, timestamp):
        # look up glitch events occuring during the events period
        glitch = None
        if evts:
            limit = (evts[-1].end_time - evts[0].start_time).seconds // 60
            glitches = self._mystery_mgr.get_events(names=["glitchgp"], timestamp=timestamp, limit=limit)
        if glitches:
            glitch = glitches.pop()

        new_evts = []
        for evt in evts:
            if glitch and self._can_glitch(evt) and evt.start_time < glitch.end_time:
                # There's a glitch now and until this event's end
                if glitch.end_time == evt.end_time:
                    # replace this event with Glitch GP
                    new_evts.append(evt.copy_as_glitch())
                elif glitch.end_time < evt.end_time:
                    # there's a Glitch GP now but this event is available later
                    #import pdb; pdb.set_trace()
                    glitched_evt = evt.split_by_glitch(True, glitch.end_time - evt.start_time)
                    new_evts.extend([glitched_evt, evt])
                elif glitch.start_time < evt.end_time:
                    # this event will be cut short by a glitch GP
                    #import pdb; pdb.set_trace()
                    glitched_evt = evt.split_by_glitch(False, evt.end_time - glitch.start_time)
                    new_evts.extend([evt, glitched_evt])
                else:
                    new_evts.append(evt)
            else:
                new_evts.append(evt)
            if glitch and evt.end_time > glitch.end_time:
                glitch = glitches.pop() if glitches else None
        return new_evts