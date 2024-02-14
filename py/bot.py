# 3rd party imports
import discord

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

wdsched = schedule.load_schedule(env['CONFIG_PATH'], 'slot2_schedule')
wesched = schedule.load_schedule(env['CONFIG_PATH'], 'slot2_schedule_weekend')
mgr = schedule.ScheduleManager(schedule.origin, wdsched, wesched)

bot = discord.Bot()

event_display_names = {
    "classic": "Classic",
    "king": ":crown: King League",
    "knight": ":horse: Knight League",
    "miniprix": "Mini-Prix",
    "protracks": "Pro-Tracks",
    "queen": "Queen League",
    "teambattle": "Team Battle",
}


event_choices = {
    "Classic": ["classic"],
    "Grand Prix": ["knight", "queen", "king"],
    "King League": ["king"],
    "Knight League": ["knight"],
    "Mini-Prix": ["miniprix"],
    "Pro-Tracks": ["protracks"],
    "Queen League": ["queen"],
    "Retro": ["classic"],
    "Team Battle": ["teambattle"],
}


def format_current_event(event_name, event_end):
    """ Nice display for current event
    """
    discord_text = 'Ongoing: {0} (ends <t:{1}:R>)'
    end = int(event_end.timestamp())
    evt_name = event_display_names.get(event_name)
    return discord_text.format(evt_name, end)


def format_future_event(event_row):
    """ Nice display for events in the future
    """
    discord_text = 'At <t:{0}:t>: {1} (<t:{2}:R>)'
    evt_time = int(event_row[0].timestamp())
    evt_name = event_display_names.get(event_row[1])
    return discord_text.format(evt_time, evt_name, evt_time)


async def get_event_types(ctx: discord.AutocompleteContext):
    """ 
    """
    return list(event_choices.keys())


@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")


@bot.slash_command(name = "showevents", description = "Shows upcoming events")
async def showevents(ctx):
    evts = mgr.list_events()
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


@bot.slash_command(name="when", description="List time for specific events", guild_ids=[945747217522753587])
async def when(
        ctx: discord.ApplicationContext,
        event_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_event_types)),
        ):
    names = event_choices.get(event_type)
    count = 5
    evts = mgr.when_event(names=names, count=count)
    if not evts:
        print("Could not fetch any event :(")
        return None
    response = ["Next {0} events in your local time:".format(event_type)]
    for evt in evts:
        response.append(format_future_event(evt))
    await ctx.respond('\n'.join(response))


@bot.slash_command(name="ping", description="Sends the bot's latency.")
async def ping(ctx): # a slash command will be created with the name "ping"
    await ctx.respond(f"Pong! Latency is {bot.latency}")


bot.run(env['DISCORD_BOT_TOKEN']) # run the bot with the token