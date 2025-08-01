# Python imports
from datetime import datetime, timedelta, timezone


## UI lookup data
# Nice names for event selection dropdown/auto-complete
event_display_names = {
    "ace": "Ace League",
    "classic": "Classic",
    "classicprix": "Classic Mini-Prix",
    "glitch99": "Mystery Track ???",
    "king": "King League",
    "knight": "Knight League",
    "mace": "Mirror Ace League",
    "miniprix": "Mini-Prix",
    "mking": "Mirror King League",
    "mknight": "Mirror Knight League",
    "mqueen": "Mirror Queen League",
    "mysteryprix": "Glitch Mini-Prix",
    "protracks": "Pro-Tracks",
    "queen": "Queen League",
    "shuffleprix": "Machine Shuffle Mini-Prix",
    "teambattle": "Team Battle",
    "worldtour": "World Tour",
    "Mystery_3": "Mystery Track ??? ||:skull:DWWL||",
    "Mystery_4": "Mystery Track ??? ||:fire:FC:fire:||",
}

# These are FZD Custom emoji codes to beautify the schedule printout
event_custom_emoji = {
    "ace": "<:GPAce:1291196458233630760>",
    "classicprix": "<:MPClassicMini:1222897226880123022>",
    "king": "<:GPKing:1195076258002899024>",
    "knight": "<:GPKnight:1195076261232525332>",
    "mace": "<:GPMirrorAce:1400238135232958554>",
    "miniprix": "<:MPMini:1195076264294363187>",
    "mking": "<:GPMirrorKing:1232859986405756968>",
    "mknight": "<:GPMirrorKnight:1222897223054921832>",
    "mqueen": "<:GPMirrorQueen:1227803769950048296>",
    "mysteryprix": "<:WhatQuestionmarksthree:1217243922418368734>",
    "queen": "<:GPQueen:1195076266311811233>",
    "worldtour": "<:WTMini:1368768773301207070>",
}

track_display_names = {
    "Big_Blue": "Big Blue",
    "Big_Blue_II": "Big Blue II",
    "Death_Wind_I": "Death Wind I",
    "Death_Wind_II": "Death Wind II",
    "Fire_Field": "Fire Field",
    "Mute_City_I": "Mute City I",
    "Mute_City_II": "Mute City II",
    "Mute_City_III": "Mute City III",
    "Mute_City_IV": "Mute City IV",
    "Mystery_1": "1CM",
    "Mystery_2": "BBB",
    "Mystery_3": "Death Wind White Land",
    "Mystery_4": "Fire City",
    "Port_Town_I": "Port Town I",
    "Port_Town_II": "Port Town II",
    "Red_Canyon_I": "Red Canyon I",
    "Red_Canyon_II": "Red Canyon II",
    "Sand_Ocean": "Sand Ocean",
    "Sand_Storm_I": "Sand Storm I",
    "Sand_Storm_II": "Sand Storm II",
    "Silence": "Silence",
    "Silence_II": "Silence II",
    "White_Land_I": "White Land I",
    "White_Land_II": "White Land II",
}


track_lookup_names = {
    'Big Blue': 'Big_Blue',
    'Big Blue II': 'Big_Blue_II',
    'Death Wind I': 'Death_Wind_I',
    'Death Wind II': 'Death_Wind_II',
    'Death Wind White Land': 'Mystery_3',
    'Fire City': 'Mystery_4',
    'Fire Field': 'Fire_Field',
    'Mirror Big Blue': 'mBig_Blue',
    'Mirror Big Blue II': 'mBig_Blue_II',
    'Mirror Death Wind I': 'mDeath_Wind_I',
    'Mirror Death Wind II': 'mDeath_Wind_II',
    'Mirror Fire Field': 'mFire_Field',
    'Mirror Mute City I': 'mMute_City_I',
    'Mirror Mute City II': 'mMute_City_II',
    'Mirror Mute City III': 'mMute_City_III',
    'Mirror Mute City IV': 'mMute_City_IV',
    'Mirror Port Town I': 'mPort_Town_I',
    'Mirror Port Town II': 'mPort_Town_II',
    'Mirror Red Canyon I': 'mRed_Canyon_I',
    'Mirror Red Canyon II': 'mRed_Canyon_II',
    'Mirror Sand Ocean': 'mSand_Ocean',
    'Mirror Sand Storm I': 'mSand_Storm_I',
    'Mirror Sand Storm II': 'mSand_Storm_II',
    'Mirror Silence': 'mSilence',
    'Mirror Silence II': 'mSilence_II',
    'Mirror White Land I': 'mWhite_Land_I',
    'Mirror White Land II': 'mWhite_Land_II',
    'Mute City I': 'Mute_City_I',
    'Mute City II': 'Mute_City_II',
    'Mute City III': 'Mute_City_III',
    'Mute City IV': 'Mute_City_IV',
    'Port Town I': 'Port_Town_I',
    'Port Town II': 'Port_Town_II',
    'Red Canyon I': 'Red_Canyon_I',
    'Red Canyon II': 'Red_Canyon_II',
    'Sand Ocean': 'Sand_Ocean',
    'Sand Storm I': 'Sand_Storm_I',
    'Sand Storm II': 'Sand_Storm_II',
    'Silence': 'Silence',
    'Silence II': 'Silence_II',
    'White Land I': 'White_Land_I',
    'White Land II': 'White_Land_II'
}


track_mirroring_enabled = {
    "Big_Blue": True,
    "Big_Blue_II": True,
    "Death_Wind_I": True,
    "Death_Wind_II": True,
    "Fire_Field": True,
    "Mute_City_I": True,
    "Mute_City_II": True,
    "Mute_City_III": True,
    "Mute_City_IV": True,
    "Mystery_1": False,
    "Mystery_2": False,
    "Mystery_3": False,
    "Mystery_4": False,
    "Port_Town_I": True,
    "Port_Town_II": True,
    "Red_Canyon_I": True,
    "Red_Canyon_II": True,
    "Sand_Ocean": True,
    "Sand_Storm_I": True,
    "Sand_Storm_II": True,
    "Silence": True,
    "Silence_II": True,
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
    name = event_display_names.get(internal_name)
    emoji = event_custom_emoji.get(internal_name)
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