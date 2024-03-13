# Python imports
from datetime import datetime, timedelta


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
    "glitch99": "Mystery Track ???",
    "king": "King League",
    "knight": "Knight League",
    "miniprix": "Mini-Prix",
    "mysteryprix": "Glitch ??? Mini-Prix",
    "protracks": "Pro-Tracks",
    "queen": "Queen League",
    "teambattle": "Team Battle",
}

# These are FZD Custom emoji codes to beautify the schedule printout
event_custom_emoji = {
    "king": "<:GPKing:1195076258002899024>",
    "knight": "<:GPKnight:1195076261232525332>",
    "miniprix": "<:MPMini:1195076264294363187>",
    "mysteryprix": "<:MPMini:1195076264294363187>",
    "queen": "<:GPQueen:1195076266311811233>",
}

# Internal event names to look up upon user selection
event_choices = {
    "Classic": ["classic"],
    "Glitch 99": ["glitch99"],
    "Glitch Mini-Prix": ["mysteryprix"],
    "Grand Prix": ["knight", "queen", "king"],
    "King League": ["king"],
    "Knight League": ["knight"],
    "Mini-Prix": ["miniprix", "mysteryprix"],
    "Private Glitch Mini-Prix": ["mysteryprix"],
    "Pro-Tracks": ["protracks"],
    "Queen League": ["queen"],
    "Retro": ["classic"],
    "Team Battle": ["teambattle"],
}


def format_event_name(internal_name):
    """ Adds custom emojis to event name
    """
    name = event_display_names.get(internal_name)
    emoji = event_custom_emoji.get(internal_name)
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
    discord_text = 'At <t:{0}:t>: {1} (<t:{2}:R>)'
    evt_time = int(event_row[0].timestamp())
    evt_name = format_event_name(event_row[1])
    return discord_text.format(evt_time, evt_name, evt_time)


async def get_event_types(ctx: discord.AutocompleteContext):
    """ 
    """
    return list(event_choices.keys())


@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")
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


@bot.slash_command(name="when", description="List time for specific events")
async def when(
        ctx: discord.ApplicationContext,
        event_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_event_types)),
        ):
    log(f"{ctx.author.name} used {ctx.command}.")
    names = event_choices.get(event_type)
    count = 5
    if ctx.author.name == "nickg0949":
        count = 10
    if event_type == "Glitch 99":
        mgr = slot1mgr
    elif event_type == "Private Glitch Mini-Prix":
        mgr = plmp_mgr
    else:
        mgr = slot2mgr
    evts = mgr.when_event(names=names, count=count)
    if not evts:
        print("Could not fetch any event :(")
        return None
    response = ["Next {0} events in your local time:".format(event_type)]
    for evt in evts:
        response.append(format_future_event(evt))
    await ctx.respond('\n'.join(response))


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
    has_glitch_mp = False
    ongoing_evt = evts[0][1]
    ongoing_evt_end = evts[1][0]
    response.append(format_current_event(ongoing_evt, ongoing_evt_end))
    for evt in evts[1:]:
        response.append(format_future_event(evt))
        if evt[1] == "mysteryprix":
            has_glitch_mp = True
            # As of March 2024, the Mini Prix slot has 3 minutes of
            # Glitch prix followed by 7 minutes of regular Miniprix.
            # Let's split mystery prix row in two
            # so it's clearer for readers
            mini_time = evt[0] + timedelta(minutes=3)
            response.append(format_future_event((mini_time, "miniprix")))
    if glitches:
        response.append("\nNext Glitch Races:")
        for glitch in glitches:
            response.append(format_future_event(glitch))
    if not has_glitch_mp:
        gmp_evt = slot2mgr.when_event(names=["mysteryprix"], count=1)
        if gmp_evt:
            response.append("\nNext Glitch Mini-Prix:")
            response.append(format_future_event(gmp_evt[0]))
        
    await channel.send('\n'.join(response))


@bot.slash_command(name="ping", description="Sends the bot's latency.")
async def ping(ctx): # a slash command will be created with the name "ping"
    log(f"{ctx.author.name} used {ctx.command}.")
    await ctx.respond(f"Pong! Latency is {bot.latency}")


if __name__ == "__main__":
    bot.run(env['DISCORD_BOT_TOKEN']) # run the bot with the token