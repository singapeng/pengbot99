from datetime import datetime, timedelta, timezone


class MiniPrixManager(object):
    """
    """
    def __init__(self, event_name, rotation, cycle_manager, mp_schedule):
        super().__init__()
        self.name = event_name
        self._rotation = rotation
        try:
            self._offset = rotation.index(event_name)
        except ValueError:
            raise ValueError("Event name {0} must exist in rotation.".format(event_name))
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
        self.LINEUP_OFFSET = 15

    def _get_start_mp_row(self, cycle):
        """ Hacky
        """
        return (cycle * self.MP_CYCLES - self.LINEUP_OFFSET) % len(self.schedule)

    def get_miniprix(self, timestamp=None):
        next_cmp = self.mgr.when_event(names=[self.name], timestamp=timestamp)
        if not next_cmp:
            return None
        cycle_info = self.mgr.get_cycle_info(next_cmp[0][0])
        cycle = cycle_info.get(self._rotation) // len(self._rotation)
        first_row = self._get_start_mp_row(cycle)
        last_row = first_row + 10
        if last_row > len(self.schedule):
            rows = (self.schedule + self.schedule)[first_row:last_row]
        else:
            rows = self.schedule[first_row:last_row]
        res = []
        i = 0
        for item in rows:
            res.append((i, item[1]))
            i += 1
        return res