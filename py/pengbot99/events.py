from datetime import datetime, timedelta


class EventModificationError(Exception):
    pass


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
        # is a glitch active?
        self.glitch = False

    @property
    def name(self):
        """ The Event's human-readable name
        """
        if self.glitch:
            # used by Secret League only
            return 'glitchgp'
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

    def delay(self, delta):
        """
        Delay an event's start by a timedelta.
        The event must still start before its current end time.
        This makes the event's duration shorter.
        """
        if delta.seconds >= self.duration * 60:
            raise EventModificationError("Event cannot be delayed more than its duration.")
        minutes = delta.seconds // 60
        self.set_start_time(self.start_time + delta)
        self.start_minute += minutes

    def cut_short(self, delta):
        """
        Adjust an event to end earlier than its currently set time.
        The event must end no earlier than its current start time.
        This makes the event's duration shorter.
        """
        if delta.seconds >= self.duration * 60:
            raise EventModificationError("Event cannot be cut short more than its duration.")
        minutes = delta.seconds // 60
        self.end_minute -= minutes

    @property
    def end_time(self):
        """
        """
        if not self.start_time:
            return None
        return self.start_time + timedelta(minutes=self.duration)

    def has(self, trackname):
        """ Checks if this track name is contained in the event name.
            Note this uses track internal names (not display names),
            e.g. 'mMute_City_II'
        """
        if trackname in self.name.split():
            return True
        return False

    def copy_as_glitch(self):
        """ Returns a glitched copy of self.
            This intentionally does not bring over cycle info.
        """
        new_evt = Event(name=self.name, start_minute=self.start_minute, end_minute=self.end_minute)
        new_evt.set_start_time(self.start_time)
        new_evt.glitch = True
        return new_evt

    def split_by_glitch(self, glitch_first, split_delta):
        """ Change this event into two events, one being a glitch,
            the other a shorter version of self.

            split_delta is an int. It is the point in the event when
            the split occurs. This value must be less than the event
            duration, otherwise an error will occur.

            glitch_first is a boolean. Use True to make the first part
            of the event a glitch, false to have it be the second part.
            Self is modified in place with adjusted start/end time.

            Returns the glitched event.
        """
        if split_delta.total_seconds() < 60:
            msg = "Given value ({0}) would create a zero duration event."
            raise EventModificationError(msg.format(split_delta.seconds))
        glitch_event = self.copy_as_glitch()
        if glitch_first is True:
            glitch_event.cut_short(split_delta)
            self.delay(split_delta)
        else:
            self.cut_short(split_delta)
            glitch_event.delay(split_delta)
        return glitch_event

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
        self._mode = mp_type
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

    @property
    def mode(self):
        return self._mode

    def has_track(self, track_name):
        if track_name in (self._race1, self._race2, self._race3):
            return True
        return False