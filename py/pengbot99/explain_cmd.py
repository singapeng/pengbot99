from datetime import datetime

from pengbot99 import formatters
from pengbot99 import ui
from pengbot99 import utils


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

TOPICS_BASE = {
    'Grand Prix Rotation': 'explain_gp_rotation'
}


class Explainer(object):
    def __init__(self, config, mgr):
        self._topics = TOPICS_BASE
        self._initialize_topics(config)
        # a slot2mgr instance used by GP rotation explainer
        self._mgr = mgr

    def _initialize_topics(self, config):
        if config:
            self._topics.update(config)

    @property
    def topics(self):
        """ build a list of topics that can be auto-completed in the slash command
        """
        return list(self._topics.keys())

    def explain_gp_rotation(self, timestamp=None):
        """
        Loads up a full rotation of Grand Prix to display
        how it is put together.
        """
        cinfo = self._mgr.get_cycle_info(timestamp)
        gps = ui.event_choices.get("Grand Prix")
        rotation = cinfo.find_rotation(gps)
        evts = self._mgr.when_event(names=gps, count=len(rotation), timestamp=timestamp)
        current = self._mgr.get_events(timestamp=timestamp, count=1)[0]
        if not current.name in gps:
            current = None

        pre_evts, post_evts = _gp_rotation_split(evts)
        return _display_gp_rotation(evts, current, pre_evts, post_evts)

    def explain(self, topic):
        if topic not in self._topics:
            return "Sorry, I cannot explain '%s'." % topic
        if self._topics.get(topic) == 'explain_gp_rotation':
            return self.explain_gp_rotation()
        else:
            # definition entry
            return self._topics.get(topic)