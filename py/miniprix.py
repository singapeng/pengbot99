from datetime import datetime, timedelta, timezone

# local imports
import events


# 10 miniprix selection cycles per individual mp cycle
# (one each minute)
MP_CYCLES = 10

# Magic number to cause the cycle to line up with known data
# points. In this case, we know mp rotation 959, was a classic
# prix 003.
CLASSIC_LINE_UP_OFFSET = 14
MINIPRIX_LINE_UP_OFFSET = 0
MIRROR_LINE_UP_OFFSET = 6


def print_miniprix_rows(rows):
    minute = 0
    format = "x:3%d %s (ClassicMiniPrix%03d)"
    for row in rows:
        print(format % (minute, row[1], row[0]))
        minute += 1


def _trim_schedule(sched):
    if sched[-1][1] == 'next':
        return sched[:-1]
    else:
        return sched


class MiniPrixManager(object):
    """
    """
    def __init__(self, event_name, cycle_manager, mp_schedule, mirror=None):
        super().__init__()
        self.name = event_name
        self.mgr = cycle_manager
        self._mp_schedule = mp_schedule
        self._mirror_schedule = mirror
        self.mirror_lineup_offset = MIRROR_LINE_UP_OFFSET
        self.mp_cycles = MP_CYCLES
        if self.name == "classicprix":
            self.lineup_offset = CLASSIC_LINE_UP_OFFSET
        else:
            self.lineup_offset = MINIPRIX_LINE_UP_OFFSET

    @property
    def schedule(self):
        return _trim_schedule(self._mp_schedule)

    @property
    def mirror_schedule(self):
        if not self._mirror_schedule:
            return None
        return _trim_schedule(self._mirror_schedule)

    def _get_start_mp_row(self, cycle):
        """ 
        """
        return (cycle * self.mp_cycles - self.lineup_offset) % len(self.schedule)

    def _get_start_mirror_row(self, cycle):
        """ 
        """
        return (cycle * self.mp_cycles - self.mirror_lineup_offset) % len(self.mirror_schedule)

    def _build_rows_from_rotation(self, get_start_fn, sched, cycle):
        first_row = get_start_fn(cycle)
        last_row = first_row + self.mp_cycles
        if last_row > len(sched):
            # Because the mirror schedule length is 9 and there are 10 prix
            # rows, it seems possible that doubling the table size may not
            # be enough in edge cases so let's triple it.
            rows = (sched * 3)[first_row:last_row]
        else:
            rows = sched[first_row:last_row]
        return rows

    def _get_track_selection_rows(self, cycle):
        return self._build_rows_from_rotation(self._get_start_mp_row, self.schedule, cycle)

    def _get_mirroring_rows(self, cycle):
        if self._mirror_schedule:
            return self._build_rows_from_rotation(self._get_start_mirror_row, self.mirror_schedule, cycle)
        return [(0, "000")] * self.mp_cycles

    def get_miniprix(self, timestamp=None):
        next_mp = self.mgr.when_event(names=[self.name], timestamp=timestamp)
        if not next_mp:
            return None
        cycle = next_mp[0].cycle // (len(next_mp[0].rotation) or 1)
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
            start_time = next_mp[0].start_time

        rows = self._get_track_selection_rows(cycle)
        mirror_rows = self._get_mirroring_rows(cycle)
        return self.eventify_rows(start_time, rows, mirror_rows)

    def eventify_rows(self, start_time, rows, mirror_rows):
        res = []
        for idx, row in enumerate(rows):
            name = self.name
            mpid = "{:03d}.{:s}".format(int(row[0]), str(mirror_rows[idx][0]))
            mirror = mirror_rows[idx][1]
            r1, r2, r3 = row[1].split(' > ')
            evt = events.MiniPrixEvent(name, mpid, r1, r2, r3, start_minute=idx, end_minute=idx + 1, mirrored=mirror)
            evt.set_start_time(start_time + timedelta(minutes=idx))
            res.append(evt)
        return res