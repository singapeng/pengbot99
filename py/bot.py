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


env = load_env()

r99sched = schedule.load_schedule(env['CONFIG_PATH'], 'slot1_schedule')
wdsched = schedule.load_schedule(env['CONFIG_PATH'], 'slot2_schedule')
wesched = schedule.load_schedule(env['CONFIG_PATH'], 'slot2_schedule_weekend')

slot1mgr = schedule.Slot1ScheduleManager(schedule.glitch_origin, r99sched)
slot2mgr = schedule.Slot2ScheduleManager(schedule.origin, wdsched, wesched)

bot = discord.Bot()

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


event_custom_emoji = {
    "king": "<:GPKing:1195076258002899024>",
    "knight": "<:GPKnight:1195076261232525332>",
    "miniprix": "<:MPMini:1195076264294363187>",
    "mysteryprix": "<:MPMini:1195076264294363187>",
    "queen": "<:GPQueen:1195076266311811233>",
}


event_choices = {
    "Classic": ["classic"],
    "Glitch 99": ["glitch99"],
    "Glitch Mini-Prix": ["mysteryprix"],
    "Grand Prix": ["knight", "queen", "king"],
    "King League": ["king"],
    "Knight League": ["knight"],
    "Mini-Prix": ["miniprix", "mysteryprix"],
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
    # Kick-off the automatically announce
    #announce_schedule.start()


@bot.slash_command(name = "showevents", description = "Shows upcoming events")
async def showevents(ctx):
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
    names = event_choices.get(event_type)
    count = 5
    if event_type == "Glitch":
        mgr = slot1mgr
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
    channel = bot.get_channel(int(env["DISCORD_BOT_CHANNEL"]))
    evts = slot2mgr.list_events(next=120)
    glitches = slot1mgr.when_event(names=["glitch99"], count=5, limit=120)
    if not evts:
        print("Could not fetch any event :(")
        return None
    response = ["F-Zero 99 Upcoming events in your local time:"]
    ongoing_evt = evts[0][1]
    ongoing_evt_end = evts[1][0]
    response.append(format_current_event(ongoing_evt, ongoing_evt_end))
    for evt in evts[1:]:
        response.append(format_future_event(evt))
    if glitches:
        response.append("\nNext Glitch Races:")
        for glitch in glitches:
            response.append(format_future_event(glitch))
    await channel.send('\n'.join(response))


"""
@announce_schedule.after_loop
async def set_next_announce_time():
    evts = slot2mgr.get_events(count=1)
    next_time = evts[0][0].timetz()
    announce_schedule.change_interval(time=next_time)
    print("Set next time to {0}.".format(next_time))
    """


@bot.slash_command(name="ping", description="Sends the bot's latency.")
async def ping(ctx): # a slash command will be created with the name "ping"
    await ctx.respond(f"Pong! Latency is {bot.latency}")


bot.run(env['DISCORD_BOT_TOKEN']) # run the bot with the token