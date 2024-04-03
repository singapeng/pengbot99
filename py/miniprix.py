from datetime import datetime, timedelta, timezone

# local imports
import events


def print_miniprix_rows(rows):
    minute = 0
    format = "x:3%d %s (ClassicMiniPrix%03d)"
    for row in rows:
        print(format % (minute, row[1], row[0]))
        minute += 1


class MiniPrixManager(object):
    """
    """
    def __init__(self, event_name, cycle_manager, mp_schedule):
        super().__init__()
        self.name = event_name
        self.mgr = cycle_manager
        # we don't actually care about the 'next' entry here
        if mp_schedule[-1][1] == 'next':
            self.schedule = mp_schedule[:-1]
        else:
            self.schedule = mp_schedule
        # 10 miniprix selection cycles per individual mp cycle
        # (one each minute)
        self.MP_CYCLES = 10
        # Magic number to cause the cycle to line up with known data
        # points. In this case, we know mp rotation 959, was a classic
        # prix 003.
        self.LINEUP_OFFSET = 14

    def _get_start_mp_row(self, cycle):
        """ 
        """
        return (cycle * self.MP_CYCLES - self.LINEUP_OFFSET) % len(self.schedule)

    def get_miniprix(self, timestamp=None):
        next_cmp = self.mgr.when_event(names=[self.name], timestamp=timestamp)
        if not next_cmp:
            return None
        cycle = next_cmp[0].cycle // (len(next_cmp[0].rotation) or 1)
        start_time = None
        if not timestamp:
            current = self.mgr.get_current_event()
            if current.name == self.name:
                # if there's an ongoing miniprix, this is the one we wanna display
                cycle -= 1
                start_time = current.start_time
        else:
            ts_evt = self.mgr.get_event(timestamp)
            if ts_evt.name == self.name:
                # if the requested time falls in a miniprix, let's make sure we
                # don't return the following time slot.
                cycle -= 1
                start_time = ts_evt.start_time
        if not start_time:
            start_time = next_cmp[0].start_time

        first_row = self._get_start_mp_row(cycle)
        last_row = first_row + 10
        if last_row > len(self.schedule):
            rows = (self.schedule + self.schedule)[first_row:last_row]
        else:
            rows = self.schedule[first_row:last_row]
        return self.eventify_rows(start_time, rows)

    def eventify_rows(self, start_time, rows):
        res = []
        for idx, row in enumerate(rows):
            name = "{:s} (ClassicMiniPrix{:03d})".format(row[1], row[0])
            evt = events.Event(name, start_minute=idx, end_minute=idx + 1)
            evt.set_start_time(start_time + timedelta(minutes=idx))
            res.append(evt)
        return res