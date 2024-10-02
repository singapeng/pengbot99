from datetime import datetime, timedelta, timezone

# local imports
from pengbot99 import events
from pengbot99 import formatters
from pengbot99 import schedule
from pengbot99 import utils


def init_99_manager(name=None, glitch_mgr=None, env=None, minutes_offset=0):
    if not name:
        name = FZ99Manager.NAME
    if not env:
        env = utils.load_env()
    # Common origin plus constant offset
    r99_origin = schedule.origin + timedelta(minutes=minutes_offset)
    nnsched = schedule.load_schedule(env['CONFIG_PATH'], 'ninetynine_schedule')
    r99mgr = schedule.Slot1ScheduleManager(r99_origin, nnsched)
    if glitch_mgr:
        return FZ99Manager(r99mgr, glitch_mgr)
    return ChoiceRaceManager(name, r99mgr)


class ChoiceRaceManager(object):
    """ For 99 races and other events on rotation offering a choice to players.
        Predicts the track selection line up for individual races.
    """
    def __init__(self, event_name, cycle_manager):
        super().__init__()
        self.name = event_name
        self.mgr = cycle_manager

    def list_events(self, timestamp=None, next=12):
        return self.mgr.list_events(timestamp=timestamp, next=next)

    def get_formatted_events(self, from_time=None, next=12):
        response = []
        evts = self.list_events(timestamp=from_time, next=next)
        if evts and from_time:
            time_str = formatters.format_discord_timestamp(from_time, inline=True)
            header = "{} events {} local time:"
            response = [header.format(self.name, time_str)]
        elif evts:
            response = ["{} upcoming track selection:\n".format(self.name)]
        for evt in evts:
            response.append(formatters.format_track_choice(evt))
        return response


class FZ99Manager(ChoiceRaceManager):
    """ A ChoiceRaceManager that supports overrides from Glitch events.
    """
    NAME = "F-Zero 99 Races"
    # Glitch events will be named as one of these
    GLITCH_EVT_NAMES = ("Mystery_1", "Mystery_2", "Mystery_3", "Mystery_4")

    def __init__(self, cycle_manager, glitch_manager):
        super().__init__("F-Zero 99 Races", cycle_manager)
        self.glitch_manager = glitch_manager

    def is_glitch(self, evt):
        if evt.name in self.GLITCH_EVT_NAMES:
            return True
        return False

    @staticmethod
    def _apply_glitch_override(evts, glitch):
        for evt in evts:
            if evt.start_time >= glitch.start_time and evt.start_time < glitch.end_time:
                # this event occurs during a Glitch
                track1 = evt.name.split(' ')[0]
                # Glitch always replaces the event's track 1 as per the schedule
                evt._name = evt._name.replace(track1, glitch.name)
        return evts

    def list_events(self, timestamp=None, next=12):
        slot1 = self.glitch_manager.list_events(timestamp, next)
        evts = super().list_events(timestamp, next)
        for item in slot1:
            if self.is_glitch(item):
                evts = self._apply_glitch_override(evts, item)
        return evts
