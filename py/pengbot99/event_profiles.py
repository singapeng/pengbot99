"""Titles and explanations of schedule profiles for /explain."""

from pengbot99 import formatters


def _event(name):
    return formatters.format_event_name(name)


SHUFFLE_MP = "{0} Machine Shuffle Mini-Prix".format(
    formatters.event_custom_emoji['miniprix'])


def _league_profile(name):
    league = name.title()
    icons = "{0} {1}".format(formatters.event_custom_emoji[name],
                             formatters.event_custom_emoji['m' + name])
    title = "{0} {1} Leagues Weekend Event".format(icons, league)
    description = (
        "During weekdays, Grand Prix run hourly at :00, with {mp} or {cmp} at :30.\n"
        "During the weekend, {standard} and {mirror} start at :00 and :30. "
        "Other Grand Prix run at :15 and :45. Secret League remains enabled, "
        "but during the weekend it can only replace {standard} or {mirror}."
    ).format(mp=_event('miniprix'), cmp=_event('classicprix'),
             standard=_event(name), mirror=_event('m' + name))
    return title, description


PROFILE_INFO = {
    'default': (
        'Default Schedule: Grand Prix Weekend Event',
        "During weekdays, Grand Prix run hourly at :00, with {mp} or {cmp} at :30.\n"
        "During weekends, Grand Prix run every 30 minutes and Secret League is enabled. "
        "This schedule is also used for Lucky Weekend Events."
        .format(mp=_event('miniprix'), cmp=_event('classicprix')),
    ),
    'secret': (
        "{0} Secret League Weekend Event".format(formatters.event_custom_emoji['glitchgp']),
        "During weekdays, Grand Prix run hourly at :00, with {mp} or {cmp} at :30.\n"
        "During the weekend, {secret} runs at :00 and :30, while other Grand Prix "
        "run at :15 and :45."
        .format(mp=_event('miniprix'), cmp=_event('classicprix'),
                secret=_event('glitchgp')),
    ),
    'machine_shuffle': (
        SHUFFLE_MP + ' Weekend Event',
        "During weekdays, Grand Prix run hourly at :00, with {mp} or {cmp} at :30.\n"
        "During the weekend, Grand Prix run every two hours, with {shuffle} "
        "every 30 minutes between them. Private {mp} are also Shuffle events, but do not "
        "feature Mirror tracks unless the lobby opens during a public {shuffle}. "
        "Secret League is enabled."
        .format(mp=_event('miniprix'), cmp=_event('classicprix'), shuffle=SHUFFLE_MP),
    ),
    'team_battle': (
        'Team Battle Weekend Event',
        "During weekdays, Grand Prix run hourly at :00, with {mp} or {cmp} at :30.\n"
        "During the weekend, Grand Prix still run hourly, while {mp} and {cmp} occur "
        "equally often at :30. The :40 special event is always Team Battle. "
        "Secret League is enabled."
        .format(mp=_event('miniprix'), cmp=_event('classicprix')),
    ),
    'mini_world_tour': (
        "{0} Mini World Tour Week".format(formatters.event_custom_emoji['worldtour']),
        "This schedule is the same on weekdays and weekends. A seven-race {tour} "
        "begins every 40 minutes. In the slots between tours, a Prix alternates "
        "between a Grand Prix and {mp} or {cmp}. Secret League is disabled."
        .format(tour=_event('worldtour'), mp=_event('miniprix'),
                cmp=_event('classicprix')),
    ),
    'festival_world_tour': (
        "{0} Festival World Tour/Frozen World Tour".format(
            formatters.event_custom_emoji['worldtour']),
        "Festival and Frozen World Tour share this schedule. A nine-race {tour} "
        "begins every 40 minutes. Between tours, weekday Prix slots alternate "
        "between Grand Prix and {mp} or {cmp}; weekend Prix slots are all Grand Prix. "
        "Secret League is disabled. These events typically last multiple weeks."
        .format(tour=_event('worldtour'), mp=_event('miniprix'),
                cmp=_event('classicprix')),
    ),
    'meteor': (
        'Meteor Festival/Lightning Festival',
        "Meteor and Lightning Festival share this schedule. It follows the default "
        "event rotation, compressed from 60 to 40 minutes on weekdays and from "
        "30 to 20 minutes on weekends. Secret League is disabled.",
    ),
}

for _name in ('knight', 'queen', 'king', 'ace'):
    PROFILE_INFO[_name] = _league_profile(_name)


def display_name(name):
    """Readable title, including for profiles without a description."""
    return PROFILE_INFO.get(name, (name.replace('_', ' ').title(), None))[0]
