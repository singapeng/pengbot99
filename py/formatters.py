# Python imports
from datetime import datetime, timedelta, timezone


## UI lookup data
# Nice names for event selection dropdown/auto-complete
event_display_names = {
    "classic": "Classic",
    "classicprix": "Classic Mini-Prix",
    "glitch99": "Mystery Track ???",
    "king": "King League",
    "knight": "Knight League",
    "miniprix": "Mini-Prix",
    "mking": "Mirror King League",
    "mknight": "Mirror Knight League",
    "mqueen": "Mirror Queen League",
    "mysteryprix": "Glitch Mini-Prix",
    "protracks": "Pro-Tracks",
    "queen": "Festival Queen League",
    "teambattle": "Team Battle",
    "Mystery_3": "Mystery Track ??? ||:skull:DWWL||",
    "Mystery_4": "Mystery Track ??? ||:fire:FC:fire:||",
}

# We're building a serious bot and never use this
event_jokey_names = {
    "classic": "Bunny Classic",
    "classicprix": "MV99 Bishop League",
    "glitch99": "Mystery Egg ???",
    "king": "GX99 Ruby Cup",
    "knight": "GX99 Emerald Cup",
    "miniprix": "MV99 Pawn Mini-Prix",
    "mknight": "Mirror Knight League",
    "mqueen": "Mirror Queen League",
    "mysteryprix": "Glitch Mini-Egg",
    "protracks": "Chocolate Rabbit-Tracks",
    "queen": "GX99 Diamond Cup",
    "teambattle": "Egghunt Battle",
    "Mystery_3": "Mystery Egg ??? ||DWWL||",
    "Mystery_4": "Mystery Egg ??? || FC ||",
}

# These are FZD Custom emoji codes to beautify the schedule printout
event_custom_emoji = {
    "classicprix": "<:MPClassicMini:1222897226880123022>",
    "king": "<:GPKing:1195076258002899024>",
    "knight": "<:GPKnight:1195076261232525332>",
    "miniprix": "<:MPMini:1195076264294363187>",
    "mking": "<:GPMirrorKing:1232859986405756968>",
    "mknight": "<:GPMirrorKnight:1222897223054921832>",
    "mqueen": "<:GPMirrorQueen:1227803769950048296>",
    "mysteryprix": "<:WhatQuestionmarksthree:1217243922418368734>",
    "queen": "<:GPQueen:1195076266311811233>",
}

event_jokey_emoji = {
    "classicprix": "<a:MVBishop:1222655476874084454>",
    "glitch99": "<a:penguinspin:1222378931093635094>",
    "king": "<:gx_ruby_cup:1222655252025839738>",
    "knight": "<:GPKnight:1195076261232525332>",
    "miniprix": "<a:MVPawn:1222655377418621008>",
    "mknight": "<:gx_emerald_cup:1222655313493364809>",
    "mysteryprix": "<:WhatQuestionmarksthree:1217243922418368734>",
    "queen": "<:gx_diamond_cup:1223297468049920170>",
}

track_display_names = {
    "Big_Blue": "Big Blue",
    "Death_Wind_I": "Death Wind I",
    "Death_Wind_II": "Death Wind II",
    "Fire_Field": "Fire Field",
    "Mute_City_I": "Mute City I",
    "Mute_City_II": "Mute City II",
    "Mute_City_III": "Mute City III",
    "Mystery_1": "1CM",
    "Mystery_2": "BBB",
    "Mystery_3": "Death Wind White Land",
    "Mystery_4": "Fire City",
    "Port_Town_I": "Port Town I",
    "Port_Town_II": "Port Town II",
    "Red_Canyon_I": "Red Canyon I",
    "Red_Canyon_II": "Red Canyon II",
    "Sand_Ocean": "Sand Ocean",
    "Silence": "Silence",
    "White_Land_I": "White Land I",
    "White_Land_II": "White Land II",
}


track_mirroring_enabled = {
    "Big_Blue": True,
    "Death_Wind_I": True,
    "Death_Wind_II": True,
    "Fire_Field": True,
    "Mute_City_I": True,
    "Mute_City_II": True,
    "Mute_City_III": True,
    "Mystery_1": False,
    "Mystery_2": False,
    "Mystery_3": False,
    "Mystery_4": False,
    "Port_Town_I": True,
    "Port_Town_II": True,
    "Red_Canyon_I": True,
    "Red_Canyon_II": True,
    "Sand_Ocean": True,
    "Silence": True,
    "White_Land_I": True,
    "White_Land_II": True,
}


track_separators = {
    'choice': ' <> ',
    'classicprix' : ' > ',
    'miniprix' : ' > ',
}


track_custom_emoji = {
    #"Mute_City_II": "<:Festival:1260649041952378930>",
    }


def format_event_name(internal_name):
    """ Adds custom emojis to event name
    """
    now = datetime.now(timezone.utc)
    if not (now.month == 4 and now.day == 1):
        name = event_display_names.get(internal_name)
        emoji = event_custom_emoji.get(internal_name)
    else:
        name = event_jokey_names.get(internal_name)
        emoji = event_jokey_emoji.get(internal_name)
    if not name:
        name = internal_name
    if emoji:
        name = '{0} {1}'.format(emoji, name)
    return name


def format_current_event(event_name, event_end):
    """ Nice display for current event
        Note 2024/3/7: this does not properly deal with the
        Mystery Prix/Regular Prix slot at the moment,
        i.e. it doesn't know that Mystery Prix only
        run first 3 minutes of the 10 minutes slot.
    """
    discord_text = 'Ongoing: {0} (ends <t:{1}:R>)'
    end = int(event_end.timestamp())
    evt_name = format_event_name(event_name)
    return discord_text.format(evt_name, end)


def format_discord_timestamp(dt, inline=False):
    """ Flexible timestamp builder.
        If the event is not in the next few hours, it will use
        a different format automatically.
        Set inline to True if the timestamp appears in a
        started sentence.
    """
    delta = dt - datetime.now(timezone.utc)
    if abs(delta.total_seconds()) > timedelta(hours=20).total_seconds():
        # Discord long date with short time
        t_format = 'f'
        if inline:
            particle = 'on '
        else:
            particle = ''
    else:
        t_format = 't'
        if inline:
            particle = "at "
        else:
            particle = "At "
    text = "{0}<t:{1}:{2}>"
    return text.format(particle, int(dt.timestamp()), t_format)


def format_future_event(evt):
    """ Nice display for events in the future
    """
    ts = format_discord_timestamp(evt.start_time)
    discord_text = "{0}: {1} (<t:{2}:R>)"
    evt_time = int(evt.start_time.timestamp())
    evt_name = format_event_name(evt.name)
    return discord_text.format(ts, evt_name, evt_time)


def format_track_names(tracks, mode):
    """ Nice display for track names
    """
    names = []
    separator = track_separators.get(mode)
    for race in (tracks):
        if race[0] != 'm':
            name = track_display_names.get(race) or race
        else:
            name = track_display_names.get(race[1:]) or race[1:]
            if track_mirroring_enabled.get(race[1:]):
                # Mirror mode on
                name = "_Mirror {0}_".format(name)
        emoji = track_custom_emoji.get(race)
        if mode != "classicprix" and emoji:
            name = '{} {}'.format(emoji, name)
        names.append(name)
    return separator.join(names)


def format_track_selection(evt, verbose=False):
    """ Nice display for Mini-Prix track selection
    """
    ts = format_discord_timestamp(evt.start_time)
    name = format_track_names([evt.race1, evt.race2, evt.race3], evt.mode)
    if verbose:
        name = "{0} ({1})".format(name, evt.mpid)
    return "{0}: {1}".format(ts, name)


def format_track_choice(evt, verbose=False):
    """ Nice display for Choice races
    """
    ts = format_discord_timestamp(evt.start_time)
    tracks = evt.name.split(track_separators['choice'])
    name = format_track_names(tracks, mode='choice')
    # Internally, choice race selection IDs will correspond to
    # the event's start minute in the current cycle plus one,
    # because the ID list starts at 1 and not zero.
    evt_id = '%03d' % (int(evt.start_minute) + 1)
    if verbose:
        name = "{0} ({1})".format(name, evt_id)
    return "{0}: {1}".format(ts, name)