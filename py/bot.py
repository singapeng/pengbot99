# Python imports
from datetime import datetime, timedelta, timezone


# 3rd party imports
import discord
from discord.ext import tasks


# local imports
import schedule


def load_env():
    """ Reads the .env file and returns a dict
    """
    env = {}
    with open(".env") as fd:
        lines = fd.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith('#'):
            # ignore comments
            continue
        var_name, var_value = line.split('=', 1)
        env[var_name] = var_value
    return env


def log(text):
    """ Log to stdout with timestamp.
    TODO: replace with logging
    """
    stamp = datetime.now()
    ymd = "%04d-%02d-%02d" % (stamp.year, stamp.month, stamp.day)
    hms = "%02d:%02d:%02d" % (stamp.hour, stamp.minute, stamp.second)
    print("{0} {1} {2}".format(ymd, hms, text))


env = load_env()

# load the schedule for slot 1 (99 races)
r99sched = schedule.load_schedule(env['CONFIG_PATH'], 'slot1_schedule')
# load the weekday schedule for slot 2 (Prix and special events)
wdsched = schedule.load_schedule(env['CONFIG_PATH'], 'slot2_schedule')
# load the weekend schedule for slot 2 (Prix and special events)
wesched = schedule.load_schedule(env['CONFIG_PATH'], 'slot2_schedule_weekend')
# load the schedule for Private Lobbies Mini-Prix
pmpsched = schedule.load_schedule(env['CONFIG_PATH'], 'pl_miniprix')

# Create the schedule managers
slot1mgr = schedule.Slot1ScheduleManager(schedule.glitch_origin, r99sched)
slot2mgr = schedule.Slot2ScheduleManager(schedule.origin, wdsched, wesched)
plmp_mgr = schedule.Slot1ScheduleManager(schedule.plmp_origin, pmpsched)

bot = discord.Bot()


## UI lookup data
# Nice names for event selection dropdown/auto-complete
event_display_names = {
    "classic": "Classic",
    "classicprix": "Classic Mini-Prix",
    "glitch99": "Mystery Track ???",
    "king": "King League",
    "knight": "Knight League",
    "miniprix": "Mini-Prix",
    "mknight": "Mirror Knight League",
    "mysteryprix": "Glitch Mini-Prix",
    "protracks": "Pro-Tracks",
    "queen": "Queen League",
    "teambattle": "Team Battle",
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
    "mysteryprix": "Glitch Mini-Egg",
    "protracks": "Chocolate Rabbit-Tracks",
    "queen": "GX99 Diamond Cup",
    "teambattle": "Egghunt Battle",
}

# These are FZD Custom emoji codes to beautify the schedule printout
event_custom_emoji = {
    "classicprix": "<:MPMini:1195076264294363187>",
    "king": "<:GPKing:1195076258002899024>",
    "knight": "<:GPKnight:1195076261232525332>",
    "miniprix": "<:MPMini:1195076264294363187>",
    "mknight": "<:GPMirrorKnight:1222897223054921832>",
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

# Internal event names to look up upon user selection
event_choices = {
    "Classic": ["classic"],
    "Classic Mini-Prix": ["classicprix"],
    "Glitch 99": ["glitch99"],
    "Glitch Mini-Prix": ["mysteryprix"],
    "Grand Prix": ["knight", "mknight", "queen", "mqueen", "king", "mking"],
    "King League": ["king", "mking"],
    "Knight League": ["knight", "mknight"],
    "Knight League (no mirror)": ["knight"],
    "Mirror Knight League": ["mknight"],
    "Mini-Prix": ["classicprix", "miniprix", "mysteryprix"],
    "Pro-Tracks": ["protracks"],
    "Queen League": ["queen", "mqueen"],
    "Retro": ["classic"],
    "Team Battle": ["teambattle"],
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


def format_future_event(event_row):
    """ Nice display for events in the future
    """
    if event_row[0] - datetime.now(timezone.utc) > timedelta(hours=20):
        # Discord long date with short time
        t_format = 'f'
        particle = ''
    else:
        t_format = 't'
        particle = 'At '
    discord_text = '{0}<t:{1}:{2}>: {3} (<t:{4}:R>)'
    evt_time = int(event_row[0].timestamp())
    evt_name = format_event_name(event_row[1])
    return discord_text.format(particle, evt_time, t_format, evt_name, evt_time)


async def get_event_types(ctx: discord.AutocompleteContext):
    """ 
    """
    return list(event_choices.keys())


@bot.event
async def on_ready():
    log(f"{bot.user} is ready and online!")
    # Kick-off the automatic announce
    announce_schedule.start()


@bot.slash_command(name = "showevents", description = "Shows upcoming events")
async def showevents(ctx):
    log(f"{ctx.author.name} used {ctx.command}.")
    evts = slot2mgr.list_events()
    if not evts:
        print("Could not fetch any event :(")
        return None
    response = ["F-Zero 99 Upcoming events in your local time:"]
    ongoing_evt = evts[0][1]
    ongoing_evt_end = evts[1][0]
    response.append(format_current_event(ongoing_evt, ongoing_evt_end))
    for evt in evts[1:]:
        response.append(format_future_event(evt))
    await ctx.respond('\n'.join(response))


def _private_mini_when(names, from_time, count):
    """ When the Private Lobby Mini-Prix time coincides with a Public
        Mini-Prix, the private lobby type is overridden by the public
        type, i.e. if the public lobby is a regular MP, then there
        won't be a glitch in Private MP lobbies.
        This function looks up both MP schedules and will discard or
        add times accordingly.
        Research credits: SpringyRubber (FZD)
    """
    # we look up more events than necessary because we may have to discard some
    evts = plmp_mgr.when_event(names=names, count=count * 2, timestamp=from_time)
    # it seems unlikely we'd have to look up very far along the MP schedule
    # based on current timing - this isn't a very scientific way.
    pubmp = slot2mgr.when_event(names=event_choices.get("Mini-Prix"), count=count, timestamp=from_time)
    # we're using timestamps as dict keys and taking advantage of 'update'
    evts_dict = dict(evts)
    evts_dict.update(dict(pubmp))
    merged_evts = []
    for key in sorted(evts_dict.keys()):
        if evts_dict[key] == "mysteryprix":
            merged_evts.append((key, evts_dict[key]))
        if len(merged_evts) >= count:
            break
    return merged_evts


def _when(event_type, from_time=None, count=5):
    names = event_choices.get(event_type)
    if event_type == "Private Glitch Mini-Prix":
        # This cannot happen as of 1.3.0 update, so the choice is removed.
        evts = _private_mini_when(names, from_time, count)
    elif event_type == "Glitch 99":
        mgr = slot1mgr
        evts = mgr.when_event(names=names, count=count, timestamp=from_time)
    else:
        mgr = slot2mgr
        evts = mgr.when_event(names=names, count=count, timestamp=from_time)
    if not evts:
        print("Could not fetch any event :(")
        return None
    response = ["Next {0} events in your local time:".format(event_type)]
    for evt in evts:
        response.append(format_future_event(evt))
    return '\n'.join(response)


@bot.slash_command(name="when", description="List time for specific events")
async def when(
        ctx: discord.ApplicationContext,
        event_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_event_types)),
        ):
    log(f"{ctx.author.name} used {ctx.command}.")
    response = _when(event_type)
    if response:
        await ctx.respond(response)
    else:
        await ctx.respond("POWER DOWN! No result for '{0}' :(".format(event_type))


# command option help tips
TIP_WHEN_FROM_TIME = "The UTC time from which to display events as YYYY-MM-DD HH:MM"
TIP_WHEN_COUNT = "How many events to display - must be from 1 to 20 (default 5)"


@bot.slash_command(name="utc_when", description="List time for events starting from UTC time")
async def utc_when(
        ctx: discord.ApplicationContext,
        event_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_event_types)),
        from_time: discord.Option(str, description=TIP_WHEN_FROM_TIME),
        count: discord.Option(int, required=False, default=5, description=TIP_WHEN_COUNT),
        ):
    log(f"{ctx.author.name} used {ctx.command}.")
    if not 0 < count < 13:
        await ctx.respond("Disqualified! Invalid 'count' value {0}. Must be between 1 and 12.".format(count))
        return
    if from_time:
        try:
            from_time = datetime.strptime(from_time, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            msg = "Disqualified! Invalid 'from_time' value '{0}'. Need 'YYYY-MM-DD HH:MM'."
            await ctx.respond(msg.format(from_time))
            return
    response = _when(event_type, from_time, count)
    if response:
        await ctx.respond(response)
    else:
        await ctx.respond("POWER DOWN! No result for '{0}' :(".format(event_type))


@tasks.loop(seconds=3600)
async def announce_schedule():
    await bot.wait_until_ready()
    channel = bot.get_channel(int(env["ANNOUNCE_CHANNEL"]))
    evts = slot2mgr.list_events(next=120)
    glitches = slot1mgr.when_event(names=["glitch99"], count=5, limit=120)
    if not evts:
        print("Could not fetch any event :(")
        return None
    response = ["F-Zero 99 Upcoming events in your local time:"]
    has_king_gp = False
    ongoing_evt = evts[0][1]
    ongoing_evt_end = evts[1][0]
    response.append(format_current_event(ongoing_evt, ongoing_evt_end))
    for evt in evts[1:]:
        response.append(format_future_event(evt))
        if evt[1] == "king":
            has_king_gp = True
    if glitches:
        response.append("\nNext Glitch Races:")
        for glitch in glitches:
            response.append(format_future_event(glitch))
    if not has_king_gp:
        king_evt = slot2mgr.when_event(names=["king"], count=1)
        if king_evt:
            response.append("\nNext King League:")
            response.append(format_future_event(king_evt[0]))
    await channel.send('\n'.join(response))


@bot.slash_command(name="ping", description="Sends the bot's latency.")
async def ping(ctx): # a slash command will be created with the name "ping"
    log(f"{ctx.author.name} used {ctx.command}.")
    await ctx.respond(f"Pong! Latency is {bot.latency}")


if __name__ == "__main__":
    bot.run(env['DISCORD_BOT_TOKEN']) # run the bot with the token