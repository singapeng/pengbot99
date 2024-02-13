from datetime import datetime, timedelta

import csv


# This should mark a cycle origin in UTC time
# UTC 2024-02-06, 00:00:00
# First Knight league after a King.
origin = datetime(2024, 2, 6, 0, 0, 0, 0)


def load_env():
    """ Reads the .env file and returns a dict
    """
    env = {}
    with open(".env") as fd:
        lines = fd.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith('#'):
            # ignore comments
            continue
        var_name, var_value = line.split('=', 1)
        env[var_name] = var_value
    return env


def load_schedule(path, name):
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


class TimeTable(object):
    """ This object doesn't know about actual time.
        It is used to query relative time within its schedule, based
        on cycle count.
    """
    def __init__(self, data):
        super().__init__()
        self._data = data
        self.duration = data[-1][0]

    def get_event(self, cycle, minute):
        """ What event is on at specified cycle and minute
        """
        active_row = []
        for row in self._data:
            if row[0] <= minute:
                active_row = row[1:]
            # we could break here if row[0] > cycle_minute
            # but assuming the schedule is ordered.
        if active_row:
            rotation_index = cycle % len(active_row)
            return active_row[rotation_index]
        else:
            return ''


class ScheduleManager(object):
    """ Used to manage the cycle of schedules based on current time
        and a time of origin.
    """
    def __init__(self, origin, weekday_sched, weekend_sched):
        super().__init__()
        # Should be UTC time of any day starting at 00:00:00
        # The origin must be a time where 00:00:00 matches
        # the beginning of the schedule file, so that all future
        # cycles have the correct offset in the rotation.
        self.origin = origin
        # Monday to Friday schedule
        self.weekday = TimeTable(weekday_sched)
        # Saturday and Sunday schedule
        self.weekend = TimeTable(weekend_sched)

    def time_types_since_origin(self, until=None):
        """
        """
        now = until or datetime.utcnow()
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
        timestamp = timestamp or datetime.utcnow()
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

    def get_current_cycle(self):
        return self.get_cycle(datetime.utcnow())

    def get_event(self, timestamp):
        now = timestamp
        if self.is_weekday(timestamp):
            sched = self.weekday
        else:
            sched = self.weekend
        cycle = self.get_cycle(timestamp)
        today_minutes = now.hour * 60 + now.minute
        cycle_minute = today_minutes % sched.duration
        return sched.get_event(cycle, cycle_minute)

    def get_current_event(self):
        return self.get_event(datetime.utcnow())