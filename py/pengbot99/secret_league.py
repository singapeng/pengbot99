from pengbot99 import utils


class SecretLeagueDataError(Exception):
    pass


class SecretLeagueConfig(object):
    def __init__(self, intervals, offset=None):
        """
        intervals: a comma-separated list of ints
        offset: an integer, or will default to zero if None-like.
        """
        super().__init__()
        try:
            intervals = [int(interval) for interval in intervals.split(',')]
        except:
            raise SecretLeagueDataError("Invalid interval data: {0}".format(intervals))
        try:
            if offset:
                offset = int(offset)
            else:
                offset = 0
        except:
            raise SecretLeagueDataError("Invalid offset data: {0}".format(offset))
        self._intervals = intervals
        self._indices = sorted([(sum(intervals[:i]) + offset) % sum(intervals) for i in range(len(intervals))])
        self.offset = offset

    @property
    def length(self):
        return sum(self._intervals)

    @property
    def intervals(self):
        return self._intervals

    @property
    def interval_count(self):
        return len(self._intervals)

    @property
    def indices(self):
        return self._indices

    def can_glitch(self, event, ongoing=False):
        if event.name not in ('knight', 'mknight', 'queen', 'mqueen', 'king', 'mking', 'ace', 'mace'):
            return False
        if not ongoing and event.cycle % self.length in self.indices:
            # event came from a get_remaining_events query
            return True
        if ongoing:
            # event came from a TimeTable.get_event query.
            # If it is past its first minute, the cycle is already counted.
            if event.get_seconds_left() // 60 < event.duration - 1:
                if (event.cycle - 1) % self.length in self.indices:
                    utils.log("Correcting event cycle for {0}.".format(event.name))
                    return True
            elif event.cycle % self.length in self.indices:
                return True
        return False
