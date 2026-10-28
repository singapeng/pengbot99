from datetime import datetime, time, timezone

from pengbot99 import event_profiles
from pengbot99 import formatters
from pengbot99 import schedule_controller
from pengbot99 import ui


### GRAND PRIX ROTATION METHODS ###

def _gp_rotation_split(evts):
    """ Create a split between events so that some are displayed ahead
        of the current time, some after. This is based on the total
        number of events in the rotation, not the events actual time.
    """
    # We define this for cosmetic purposes
    LONG_ROTATION = 7
    SHORT_PRE = 1
    LONG_PRE = 2

    if len(evts) == 1:
        # Sometimes the rotation is just 1 GP.
        # This usually happens when a new league is introduced and
        # there is a special event.
        # In this case, duplicate the rotation for the split.
        pre = evts
        post = evts
    elif len(evts) < LONG_ROTATION:
        # In this case, we'll show just one event before split.
        pre = evts[-SHORT_PRE:]
        post = evts[:-SHORT_PRE]
    elif len(evts) >= LONG_ROTATION:
        pre = evts[-LONG_PRE:]
        post = evts[:-LONG_PRE]
    return pre, post


def _format_gp_list(gps):
    emojis = []
    for gp in gps:
        # if no emoji is defined for a gp, we just print its name
        emojis.append(formatters.event_custom_emoji.get(gp.name, gp.name))
    return ' > '.join(emojis)


def _display_gp_rotation(evts, current, pre, post):
    # header
    msg_str = "Grand Prix Leagues rotate in a cycle."
    msg_str += "The current cycle is {0} Grand Prix-long.\n\n"
    msg_str += "Here is a representation of the cycle relative to now.\n"
    msg = msg_str.format(len(evts))
    # events before now
    str_pre = _format_gp_list(pre)
    # marker for now
    if current:
        str_now = " (NOW) > "
    else:
        str_now = " > (NOW) > "
    # events after now
    str_post = _format_gp_list([post[0]])
    str_post += " (<t:{0}:R>)".format(int(post[0].start_time.timestamp()))
    if len(post) > 1:
        str_post = str_post + " > " + _format_gp_list(post[1:])
    return msg + str_pre + str_now + str_post

### Explainer Class definition ###

MAX_SCHEDULE_LINES = 12
TOPICS_BASE = {
    'Grand Prix Rotation': 'explain_gp_rotation',
    'Current Schedule': 'explain_current_schedule',
    'Current And Upcoming Events': 'explain_upcoming_events',
}


class Explainer(object):
    def __init__(self, mgr_holder, env=None, auto_switch=False):
        self._topics = TOPICS_BASE
        # a holder exposing the current slot2mgr, resolved lazily so that
        # a schedule profile switch is reflected at explain time.
        self._holder = mgr_holder
        self._env = env
        self._auto_switch = auto_switch

    @property
    def _mgr(self):
        return self._holder.slot2mgr

    def _switch_config(self):
        if self._auto_switch and self._env:
            return schedule_controller.load_profile_switches(self._env)
        return None

    def _upcoming_switches(self, switches, now):
        """Actual future profile changes, including at most one per UTC date."""
        upcoming = []
        active = self._holder.name
        today = now.astimezone(timezone.utc).date()
        for day, name in switches:
            if day <= today:
                continue
            # On the same date the last CSV row wins, as in active_on().
            if upcoming and day == upcoming[-1][0]:
                upcoming.pop()
                active = upcoming[-1][1] if upcoming else self._holder.name
            if name != active:
                upcoming.append((day, name))
                active = name
        return upcoming

    def _weekend_event(self, now):
        """ (ID, end) of the weekend event the active profile runs at now,
            or None.
        """
        lookup = getattr(self._holder, 'weekend_event', None)
        if lookup is None:
            return None
        event_id = lookup(now)
        if event_id is None:
            return None
        for start, end, name in self._holder.calendar():
            if name == event_id and start <= now < end:
                return event_id, end
        return event_id, None

    def explain_current_schedule(self, now=None):
        now = now or datetime.now(timezone.utc)
        title, description = event_profiles.profile_info(self._holder.name)
        response = ["The currently active schedule is **{0}**.".format(title), "", description]
        weekend = self._weekend_event(now)
        if weekend:
            event_id, end = weekend
            title, description = event_profiles.weekend_event_info(event_id)
            response += ["", "The game is running the **{0}** weekend event.".format(
                title), description]
            if end:
                response += ["", "This event ends <t:{0}:F>.".format(
                    int(end.timestamp()))]
        config = self._switch_config()
        if config:
            future = self._upcoming_switches(config.switches, now)
            if future:
                switch = datetime.combine(future[0][0], time.min, tzinfo=timezone.utc)
                response += ["", "This schedule will remain active until <t:{0}:F>.".format(
                    int(switch.timestamp()))]
            else:
                response += ["", "No upcoming schedule change is listed."]
        return '\n'.join(response)

    def _upcoming_calendar(self, now):
        """ (start, title) of the weekend events the active profile's game
            data lists after now.
        """
        calendar = getattr(self._holder, 'calendar', None)
        if calendar is None:
            return []
        return [(start, event_profiles.weekend_event_info(event_id)[0])
                for start, _, event_id in calendar() if start > now]

    def explain_upcoming_events(self, now=None):
        config = self._switch_config()
        now = now or datetime.now(timezone.utc)
        upcoming = self._upcoming_calendar(now)
        if config is None and not upcoming:
            return "Sorry, the event schedule is not available."
        active = event_profiles.display_name(self._holder.name)
        weekend = self._weekend_event(now)
        if weekend:
            title = event_profiles.weekend_event_info(weekend[0])[0]
            active = "{0} ({1})".format(title, active)
        response = ["Current and Expected Game Events:", "",
                    "**Currently Active**: {0}".format(active)]
        if config is not None:
            for day, name in self._upcoming_switches(config.switches, now):
                switch = datetime.combine(day, time.min, tzinfo=timezone.utc)
                upcoming.append((switch, event_profiles.display_name(name)))
        upcoming = sorted(set(upcoming), key=lambda item: item[0])
        for start, title in upcoming[:MAX_SCHEDULE_LINES - len(response)]:
            response.append("<t:{0}:F>   {1}".format(int(start.timestamp()), title))
        return '\n'.join(response)

    @property
    def topics(self):
        """ build a list of topics that can be auto-completed in the slash command
        """
        topics = list(self._topics.keys())
        now = datetime.now(timezone.utc)
        if self._switch_config() is None and not self._upcoming_calendar(now):
            # bot is operating with single --profile forever
            topics.remove('Current And Upcoming Events')
        return topics

    def explain_gp_rotation(self, timestamp=None):
        """
        Loads up a full rotation of Grand Prix to display
        how it is put together.
        """
        gps = ui.event_choices.get("Grand Prix")
        current = self._mgr.get_event(timestamp or datetime.now(timezone.utc))
        if current.glitched_name not in gps:
            current = None
        anchor = current or self._mgr.when_event(names=gps, count=1,
                                                 timestamp=timestamp)[0]
        evts = self._mgr.when_event(names=gps, count=len(anchor.rotation),
                                    timestamp=timestamp)

        pre_evts, post_evts = _gp_rotation_split(evts)
        return _display_gp_rotation(evts, current, pre_evts, post_evts)

    def explain(self, topic):
        if topic not in self._topics:
            return "Sorry, I cannot explain '%s'." % topic
        explanation = self._topics.get(topic)
        if explanation == 'explain_gp_rotation':
            return self.explain_gp_rotation()
        elif explanation == 'explain_current_schedule':
            return self.explain_current_schedule()
        elif explanation == 'explain_upcoming_events':
            return self.explain_upcoming_events()
