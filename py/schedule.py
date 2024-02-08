from datetime import datetime

import csv


# This should mark a cycle origin in UTC time
# PT 2024-02-07, 13:00:00
# First Knight league after a King.
origin = datetime(2024, 2, 7, 21, 0, 0, 0)


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
                schedule.append((int(row[0]), str(row[1])))
            except Exception as e:
                #TODO: better validation
                raise
    assert schedule[-1][1] == "repeat", "Must end with repeat"
    return schedule


def get_minutes_since_origin():
    now = datetime.utcnow()
    return int((now - origin).seconds / 60)


def get_cycle_minute(schedule):
    """ Returns which minute it is in the current cycle.
    """
    # get the 'repeat' entry
    schedule_length = schedule[-1][0]
    # position in current cycle in minute
    return get_minutes_since_origin() % schedule_length



def get_cycles(origin, schedule):
    """ How many complete cycles of this schedule occured
        since origin.
    """
    now = datetime.utcnow()
    minutes_since_origin = int((now - origin).seconds / 60)
    # get the 'repeat' entry
    schedule_length = schedule[-1][0]
    return int(minutes_since_origin / schedule_length)


def get_event_count(event_name, schedule):
    """ How many times an event appears in a schedule
    """
    count = 0
    for row in schedule:
        if row[1] == event_name:
            count += 1
    return count


def get_past_events_count(event_name, schedule):
    """ How many of an event type have occured since origin.
        This is based on complete cycles, plus any from current cycle.
    """
    event_count = get_event_count(event_name, schedule)
    if not event_count:
        # this event does not appear in this schedule
        return 0
    minutes_since_origin = get_minutes_since_origin()
    # get the 'repeat' entry
    schedule_length = schedule[-1][0]
    past_cycles = int(minutes_since_origin / schedule_length)
    # position in current cycle in minute
    cycle_minute = get_cycle_minute(schedule)
    cycle_events = 0
    for row in schedule:
        if row[0] < cycle_minute and row[1] == event_name:
            cycle_events += 1
    return past_cycles * event_count + cycle_events


def get_current_event(schedule):
    """ What event is on now
    """
    # position in current cycle in minute
    cycle_minute = get_cycle_minute(schedule)
    started_event = ""
    for row in schedule:
        if row[0] <= cycle_minute:
            started_event = row[1]
        # we could break here if row[0] > cycle_minute
        # but assuming the schedule is ordered.
    return started_event


def when_event(event_name, schedule, skip=0):
    """ Returns how many minutes to the next occurence of
        an event.
        If skip is given, skip this many events and return
        the time for next one (skip must be >=0)
    """
    cycle_minute = get_cycle_minute(schedule)
    schedule_length = schedule[-1][0]
    times = []
    for row in schedule:
        if row[1] == event_name:
            times.append(row[0])
    if not times:
        # no such event scheduled
        return -1
    # find where we are in the cycle
    start_index = 0
    for time in times:
        if time < cycle_minute:
            start_index += 1
    # find the correct schedule entry accounting for skip
    res_index = (start_index + skip) % len(times)
    # cycles to pass accounting for skip
    add_cycles = int((start_index + skip) / len(times))
    # example - missed King in a Knight/Queen/Knight/Queen/King rotation
    #  K -- J -- Q -- J -- Q -- K
    # |   ^     |         |         |
    res = times[res_index] - cycle_minute + add_cycles * schedule_length
    return res