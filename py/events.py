from datetime import datetime, timedelta


class Event(object):
    def __init__(self, name, cycle=0, cycle_minute=0, start_minute=0, end_minute=0, rotation=None, rotation_offset=0):
        super().__init__()
        # the event's internal name
        self.name = name
        # what is the event's cycle number
        self.cycle = cycle
        # what minute of the cycle the event was created in
        self.cycle_minute = cycle_minute
        # what minute of the cycle the event starts at
        self.start_minute = start_minute
        # what minute of the cycle the event ends at
        self.end_minute = end_minute
        # what rotation this event comes from, if any
        self.rotation = rotation
        # what position in the rotation the event occupies
        self.rotation_offset = rotation_offset
        # start time
        self.start_time = None

    @property
    def duration(self):
        """ How many minutes this event lasts.
        """
        return self.end_minute - self.start_minute

    def set_start_time(self, timestamp):
        """
        """
        self.start_time = timestamp

    @property
    def end_time(self):
        """
        """
        if not self.start_time:
            return None
        return self.start_time + timedelta(minutes=self.duration)

    def __str__(self):
        """
        """
        start_str = self.start_time.strftime("%Y-%m-%d %H:%M")
        return "{0} - {1} ({2} minutes)".format(start_str, self.name, self.duration)
