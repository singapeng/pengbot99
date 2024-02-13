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


@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")


@bot.slash_command(name = "hello", description = "Say hello to the bot")
async def hello(ctx):
    await ctx.respond("Hey!")

@bot.slash_command(name = "showevents", description = "Shows upcoming events")
async def showevents(ctx):
    evts = mgr.get_events()
    response = ["Upcoming Events:"]
    for evt in evts:
        ts = int(evt[0].timestamp())
        response.append('<t:{0}>: {1} (<t:{2}:R>)'.format(ts, evt[1], ts))
    await ctx.respond('\n'.join(response))

@bot.slash_command(name="ping", description="Sends the bot's latency.")
async def ping(ctx): # a slash command will be created with the name "ping"
    await ctx.respond(f"Pong! Latency is {bot.latency}")


bot.run(env['DISCORD_BOT_TOKEN']) # run the bot with the token