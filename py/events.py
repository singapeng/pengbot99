from datetime import datetime, timedelta


class Event(object):
    def __init__(self, name, cycle=0, cycle_minute=0, start_minute=0, end_minute=0, rotation=None, rotation_offset=0):
        super().__init__()
        # the event's internal name
        self._name = name
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
    def name(self):
        """ The Event's human-readable name
        """
        return self._name

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


class MiniPrixEvent(Event):
    def __init__(self, mp_type, mp_id, race1, race2, race3, start_minute=0, end_minute=0, mirrored="000"):
        if mp_type == "classicprix":
            code = "ClassicMiniPrix"
        else:
            code = "MiniPrix"
        miniprix_id = "{:s}{:s}".format(code, mp_id)
        name = "{0} > {1} > {2} ({3})".format(race1, race2, race3, miniprix_id)
        super().__init__(name=miniprix_id, start_minute=start_minute, end_minute=end_minute)
        self._race1 = race1
        self._race2 = race2
        self._race3 = race3
        self._mirrored = mirrored
        self._mpid = miniprix_id

    @property
    def name(self):
        name_fmt = "{0} > {1} > {2} ({3})"
        return name_fmt.format(self.race1, self.race2, self.race3, self._name)

    @property
    def race1(self):
        if self._mirrored[0] == '1':
            return 'm' + self._race1
        return self._race1

    @property
    def race2(self):
        if self._mirrored[1] == '1':
            return 'm' + self._race2
        return self._race2

    @property
    def race3(self):
        if self._mirrored[2] == '1':
            return 'm' + self._race3
        return self._race3

    @property
    def mpid(self):
        return self._mpid

    def has_track(self, track_name):
        if track_name in (self._race1, self._race2, self._race3):
            return True
        return False