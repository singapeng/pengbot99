# Python imports
from datetime import datetime, timedelta, timezone


# 3rd party imports
import discord
from discord.ext import tasks


# local imports
from pengbot99 import apiadapter
from pengbot99 import choicerace
from pengbot99 import formatters
from pengbot99 import miniprix
from pengbot99 import misa
from pengbot99 import schedule
from pengbot99 import utils


env = utils.load_env()

# load the schedule for slot 1 (99 races)
r99sched = schedule.load_schedule(env['CONFIG_PATH'], 'slot1_schedule')
# load the weekday schedule for slot 2 (Prix and special events)
wdsched = schedule.load_schedule(env['CONFIG_PATH'], 'slot2_schedule')
# load the weekend schedule for slot 2 (Prix and special events)
wesched = schedule.load_schedule(env['CONFIG_PATH'], 'slot2_schedule_weekend')
# load the Classic Mini Prix track schedule
cmpsched = schedule.load_schedule(env['CONFIG_PATH'], 'classic_mp_schedule')
# load the Classic Mini Prix track schedule
mpsched = schedule.load_schedule(env['CONFIG_PATH'], 'miniprix_schedule')
mirrorsc = schedule.load_schedule(env['CONFIG_PATH'], 'miniprix_mirroring_schedule')
# load the schedule for Private Lobbies Mini-Prix
plmpsched = schedule.load_schedule(env["CONFIG_PATH"], "private_miniprix_schedule")
plcmpsched = schedule.load_schedule(env["CONFIG_PATH"], "private_classic_mp_schedule")

# Create the Public schedule managers
slot1mgr = schedule.Slot1ScheduleManager(schedule.glitch_origin, r99sched)
slot2mgr = schedule.Slot2ScheduleManager(schedule.origin, wdsched, wesched)
cmp_mgr = miniprix.MiniPrixManager("classicprix", slot2mgr, cmpsched)
mp_mgr = miniprix.MiniPrixManager("miniprix", slot2mgr, mpsched, mirrorsc)
r99_mgr = choicerace.init_99_manager(name=None, glitch_mgr=slot1mgr)

# Create Private Lobby schedule managers
pl_slot1 = schedule.Slot1ScheduleManager(schedule.origin, plmpsched)
mirror_slot1 = schedule.Slot1ScheduleManager(schedule.origin, mirrorsc)
pmp_mgr = miniprix.PrivateMPManager("miniprix", pl_slot1, mp_mgr, mirror_slot1)
plcmp_slot1 = schedule.Slot1ScheduleManager(schedule.pl_origin, plcmpsched)
pcmp_mgr = miniprix.PrivateMPManager("classicprix", plcmp_slot1, cmp_mgr)

# Create the quotes manager
quotes = misa.Quotes(env['CONFIG_PATH'])


bot = discord.Bot()


# Internal event names to look up upon user selection
event_choices = {
    "Classic": ["classic"],
    "Classic Mini-Prix": ["classicprix"],
    "Glitch 99": ["glitch99", "Mystery_3", "Mystery_4"],
    "Glitch Mini-Prix": ["mysteryprix"],
    "Grand Prix": ["knight", "mknight", "queen", "mqueen", "king", "mking"],
    "King League": ["king", "mking"],
    "King League (no mirror)": ["king"],
    "Knight League": ["knight", "mknight"],
    "Knight League (no mirror)": ["knight"],
    "Queen League (no mirror)": ["queen"],
    "Mirror King League": ["mking"],
    "Mirror Knight League": ["mknight"],
    "Mirror Queen League": ["mqueen"],
    "Mini-Prix": ["classicprix", "miniprix", "mysteryprix"],
    "Pro-Tracks": ["protracks"],
    "Queen League": ["queen", "mqueen"],
    "Retro": ["classic"],
    "Team Battle": ["teambattle"],
}


# Internal mini-prix types to look up upon user selection
mp_event_choices = {
    "Classic Mini-Prix": "classicprix",
    "Mini-Prix": "miniprix",
    "Private Classic Mini-Prix": "classicprix",
    "Private Mini-Prix": "miniprix",
}


mp_track_choices = {
    "Big Blue": "Big_Blue",
    "Death Wind I": "Death_Wind_I",
    "Death Wind II": "Death_Wind_II",
    "Death Wind White Land": "Mystery_3",
    "Fire City": "Mystery_4",
    "Mute City I": "Mute_City_I",
    "Mute City II": "Mute_City_II",
    "Mute City III": "Mute_City_III",
    "Port Town I": "Port_Town_I",
    "Port Town II": "Port_Town_II",
    "Red Canyon I": "Red_Canyon_I",
    "Red Canyon II": "Red_Canyon_II",
    "Sand Ocean": "Sand_Ocean",
    "White Land I": "White_Land_I",
}


cmp_track_choices = {
    "Big Blue": "Big_Blue",
    "Death Wind I": "Death_Wind_I",
    "Death Wind II": "Death_Wind_II",
    "Fire Field": "Fire_Field",
    "Mute City I": "Mute_City_I",
    "Mute City II": "Mute_City_II",
    "Mute City III": "Mute_City_III",
    "Port Town I": "Port_Town_I",
    "Port Town II": "Port_Town_II",
    "Red Canyon I": "Red_Canyon_I",
    "Red Canyon II": "Red_Canyon_II",
    "Sand Ocean": "Sand_Ocean",
    "Silence": "Silence",
    "White Land I": "White_Land_I",
    "White Land II": "White_Land_II",
}


def _validate_utc_time(str_time):
    if not str_time:
        return None, None
    try:
        utc_time = datetime.strptime(str_time, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        msg = "Disqualified! Invalid 'from_time' value '{0}'. Need 'YYYY-MM-DD HH:MM'."
        return msg.format(str_time), None
    return None, utc_time


async def get_event_types(ctx: discord.AutocompleteContext):
    """ 
    """
    return list(event_choices.keys())


async def get_mp_types(ctx: discord.AutocompleteContext):
    """ 
    """
    return list(mp_event_choices.keys())


async def get_tracks(ctx: discord.AutocompleteContext):
    """ 
    """
    if ctx.options.get("event_type") == "Classic Mini-Prix":
        return list(cmp_track_choices.keys())
    else:
        return list(mp_track_choices.keys())


async def create_schedule_messages():
    mp_thread_id, mp_msg_id = await post_miniprix_thread("miniprix")
    cmp_thread_id, cmp_msg_id = await post_miniprix_thread("classicprix")
    msg_env = {
            "MINIPRIX_MSG_ID": mp_msg_id,
            "MINIPRIX_THREAD_ID": mp_thread_id,
            "CLASSICPRIX_MSG_ID": cmp_msg_id,
            "CLASSICPRIX_THREAD_ID": cmp_thread_id,
        }
    env.update(msg_env)
    main_id = await post_schedule_message()
    msg_env["ANNOUNCE_MSG_ID"] = main_id
    env.update(msg_env)

    return msg_env


async def configure_schedule_edit():
    """
    """
    msg_env = utils.read_msg_struct()
    if not msg_env:
        utils.log("Creating message structure...")
        msg_env = await create_schedule_messages()
        utils.write_msg_struct(msg_env)
        utils.log("Configuration updated.")
    else:
        env.update(msg_env)
        for mp_type in ("miniprix", "classicprix"):
            await _edit_miniprix_message(mp_type)

    # local time for the bot
    now = datetime.now(timezone.utc)
    # round minutes to the tens
    minute = now.minute // 10 * 10
    # add 10 minutes delta
    delta = timedelta(minutes=10)
    kickoff_time = datetime(now.year, now.month, now.day, now.hour, minute, tzinfo=timezone.utc) + delta

    @tasks.loop(time=kickoff_time.time(), count=1)
    async def start_schedule_edit():
        utils.log("Starting the schedule editing loop!")
        edit_schedule_message.start()

    utils.log("Schedule edit will start at {0}.".format(kickoff_time.strftime("%H:%M")))
    start_schedule_edit.start()


@bot.event
async def on_ready():
    utils.log(f"{bot.user} is ready and online!")
    # configure schedule edit task
    await configure_schedule_edit()
    # Kick-off the automatic announce
    announce_schedule.start()


# command option help tips
TIP_SHOWEVENTS_FROM_TIME = "The UTC time from which to display events as YYYY-MM-DD HH:MM"
# limit count to avoid tripping Discord message length limit
MAX_COUNT_VALUE = 12
# command option help tips
TIP_WHEN_FROM_TIME = "The UTC time from which to display events as YYYY-MM-DD HH:MM"
TIP_WHEN_COUNT = "How many events to display - must be from 1 to {0} (default 5)".format(MAX_COUNT_VALUE)


@bot.slash_command(name = "showevents", description = "Shows upcoming events")
async def showevents(
        ctx: discord.ApplicationContext,
        utc_time: discord.Option(str, required=False, description=TIP_SHOWEVENTS_FROM_TIME),
        ):
    utils.log(f"{ctx.author.name} used {ctx.command}.")
    err, from_time = _validate_utc_time(utc_time)
    if err:
        await ctx.respond(err)
        return None
    evts = slot2mgr.list_events(timestamp=from_time, next=90)
    if not evts:
        await ctx.respond("Could not fetch any event :(")
        return None
    if from_time:
        header = "F-Zero 99 events {0} local time:"
        response = [header.format(formatters.format_discord_timestamp(from_time, inline=True))]
    else:
        response = ["F-Zero 99 Upcoming events in your local time:"]
        ongoing_evt = evts[0].name
        ongoing_evt_end = evts[0].end_time
        response.append(formatters.format_current_event(ongoing_evt, ongoing_evt_end))
        evts = evts[1:]
    for evt in evts:
        response.append(formatters.format_future_event(evt))
    await ctx.respond('\n'.join(response))


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
    if from_time:
        header = "{0} events {1} local time:"
        time_str = formatters.format_discord_timestamp(from_time, inline=True)
        response = [header.format(event_type, time_str)]
    else:
        response = ["Next {0} events in your local time:".format(event_type)]
    for evt in evts:
        response.append(formatters.format_future_event(evt))
    return '\n'.join(response)


@bot.slash_command(name="when", description="List time for specific events")
async def when(
        ctx: discord.ApplicationContext,
        event_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_event_types)),
        count: discord.Option(int, required=False, default=5, description=TIP_WHEN_COUNT),
        ):
    utils.log(f"{ctx.author.name} used {ctx.command}.")
    if not 0 < count <= MAX_COUNT_VALUE:
        response = "Disqualified! Invalid 'count' value {0}. Must be between 1 and 12.".format(count)
    else:
        response = _when(event_type, count=count)
    if response:
        await ctx.respond(response)
    else:
        await ctx.respond("POWER DOWN! No result for '{0}' :(".format(event_type))


@bot.slash_command(name="utc_when", description="List time for events starting from UTC time")
async def utc_when(
        ctx: discord.ApplicationContext,
        event_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_event_types)),
        from_time: discord.Option(str, description=TIP_WHEN_FROM_TIME),
        count: discord.Option(int, required=False, default=5, description=TIP_WHEN_COUNT),
        ):
    utils.log(f"{ctx.author.name} used {ctx.command}.")
    err, response = None, None
    if not 0 < count <= MAX_COUNT_VALUE:
        err = "Disqualified! Invalid 'count' value {0}. Must be between 1 and 12.".format(count)
    else:
        err, from_time = _validate_utc_time(from_time)
    if not err:
        response = _when(event_type, from_time, count)
        if not response:
            err = "POWER DOWN! No result for '{0}' :(".format(event_type)
    await ctx.respond(err or response)


# command option help tips
TIP_MINIPRIX_VERBOSE = "Set True to display the track selection internal code name."
TIP_MINIPRIX_TRACK_FILTER = "Only show track selections that include this track."


def _create_miniprix_message(event_type, track_filter, utc_time, verbose, private=False):
    """
    """
    err, response = None, None
    err, from_time = _validate_utc_time(utc_time)

    if event_type == "classicprix":
        if private:
            mgr = pcmp_mgr
        else:
            mgr = cmp_mgr
        track = cmp_track_choices.get(track_filter)
    else:
        if private:
            mgr = pmp_mgr
        else:
            mgr = mp_mgr
        track = mp_track_choices.get(track_filter)

    if not err:
        evts = mgr.get_miniprix(timestamp=from_time)
        if evts:
            start = int(evts[0].start_time.timestamp())
            evt_name = formatters.event_display_names.get(event_type)
            if private:
                evt_name = "Private {0}".format(evt_name)
            header = "Track selection for {0} scheduled <t:{1}:R>".format(evt_name, start)
            response = [header]
            for evt in evts:
                if not track_filter or evt.has_track(track):
                    response.append(formatters.format_track_selection(evt, verbose))
            if len(response) == 1:
                response.append("No results :(")
            response = '\n'.join(response)
    return err, response


async def post_miniprix_thread(event_type):
    channel = bot.get_channel(int(env["SCHEDULE_EDIT_CHANNEL"]))
    ctype = discord.ChannelType.public_thread
    thread_name = "See {0} schedule".format(formatters.event_display_names.get(event_type))
    thread = await channel.create_thread(name=thread_name, message=None, auto_archive_duration=10080, type=ctype)

    err, response = _create_miniprix_message(event_type, None, None, False)
    if not response:
        return

    msg = await thread.send(response)
    if event_type == "miniprix":
        env["MINIPRIX_MSG_URL"] = msg.jump_url
    else:
        env["CLASSICPRIX_MSG_URL"] = msg.jump_url

    return thread.id, msg.id


async def _edit_miniprix_message(mp_type):
    if mp_type == "miniprix":
        msg_id_key = "MINIPRIX_MSG_ID"
        thread_id_key = "MINIPRIX_THREAD_ID"
        msg_url_key = "MINIPRIX_MSG_URL"
    else:
        msg_id_key = "CLASSICPRIX_MSG_ID"
        thread_id_key = "CLASSICPRIX_THREAD_ID"
        msg_url_key = "CLASSICPRIX_MSG_URL"

    channel = bot.get_channel(int(env["SCHEDULE_EDIT_CHANNEL"]))

    msg_id = int(env[msg_id_key])
    thread_id = int(env[thread_id_key])
    thread = await apiadapter.get_thread(channel, thread_id)
    msg = await thread.fetch_message(msg_id)

    if not env.get(msg_url_key):
        env[msg_url_key] = msg.jump_url

    utils.log("Updating {0} thread...".format(mp_type))
    err, response = _create_miniprix_message(mp_type, None, None, False)
    if not err and response:
        await msg.edit(response)
    utils.log("Update complete.")


@bot.slash_command(name="miniprix", description="List the track selection for the ongoing or next Mini-Prix")
async def miniprix(
        ctx: discord.ApplicationContext,
        event_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_mp_types)),
        track_filter: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_tracks),
                            description=TIP_MINIPRIX_TRACK_FILTER),
        utc_time: discord.Option(str, required=False, description=TIP_WHEN_FROM_TIME),
        verbose: discord.Option(bool, required=False, default=False, description=TIP_MINIPRIX_VERBOSE),
        ):
    """
    """
    utils.log(f"{ctx.author.name} used {ctx.command}.")
    private = "Private" in event_type
    event_type = mp_event_choices.get(event_type)
    err, response = _create_miniprix_message(event_type, track_filter, utc_time, verbose, private)
    await ctx.respond(err or response)


def _ninetynine():
    """
    """
    return '\n'.join(r99_mgr.get_formatted_events())


@bot.slash_command(name="ninetynine", description="List the track selection for the upcoming 99 races")
async def ninetynine(
        ctx: discord.ApplicationContext,
        ):
    """
    """
    utils.log(f"{ctx.author.name} used {ctx.command}.")
    response = _ninetynine()
    await ctx.respond(response)


def get_missing_event_types(evts):
    """ Print the next occurence of events of a type
        missing from the must-have list
    """
    must_have_evts = ["queen", "mqueen", "king", "mking", "miniprix", "classicprix"]
    present_evts = list(set([evt.name for evt in evts]))
    missing_evts = [evt for evt in must_have_evts if evt not in present_evts]
    results = []
    for name in missing_evts:
        extra = slot2mgr.when_event(names=[name], count=1)
        if extra:
            results.append(extra[0])
    # make sure results are ordered from next to last
    results = sorted(results, key=lambda item:item.start_time)
    return results


def format_schedule_edit(event_type, message):
    if event_type == "classicprix":
        return "{0} {1}".format(message, env.get("CLASSICPRIX_MSG_URL"))
    elif event_type == "miniprix":
        return "{0} {1}".format(message, env.get("MINIPRIX_MSG_URL"))
    return message


def kick_off_mp_update(mp_evt):
    kickoff_time = mp_evt.end_time

    @tasks.loop(time=kickoff_time.time(), count=1)
    async def start_mp_edit():
        await _edit_miniprix_message(mp_evt.name)

    utils.log("{0} will be edited at {1}.".format(mp_evt.name, kickoff_time.strftime("%H:%M")))
    start_mp_edit.start()


def _create_schedule_message():
    glitch_evts = event_choices.get("Glitch 99")
    evts = slot2mgr.list_events(next=119)
    glitches = slot1mgr.when_event(names=glitch_evts, count=5, limit=119)
    if not evts:
        utils.log("Could not fetch any event :(")
        return []
    response = ["F-Zero 99 Upcoming events in your local time:"]
    ongoing_evt = evts[0].name
    if ongoing_evt in ("miniprix", "classicprix"):
        kick_off_mp_update(evts[0])
    ongoing_evt_end = evts[0].end_time
    ongoing_str = formatters.format_current_event(ongoing_evt, ongoing_evt_end)
    response.append(format_schedule_edit(ongoing_evt, ongoing_str))
    for evt in evts[1:]:
        future_str = formatters.format_future_event(evt)
        response.append(format_schedule_edit(evt.name, future_str))
    if glitches:
        response.append("\nNext Glitch Races:")
        for glitch in glitches:
            response.append(formatters.format_future_event(glitch))

    # Also show events of desired types that aren't occuring soon
    missing_evts = get_missing_event_types(evts)
    if missing_evts:
        response.append("\nFuture events:")
        for evt in missing_evts:
            future_str = formatters.format_future_event(evt)
            response.append(format_schedule_edit(evt.name, future_str))
    return response


async def post_schedule_message():
    channel = bot.get_channel(int(env["SCHEDULE_EDIT_CHANNEL"]))

    response = _create_schedule_message()
    if not response:
        return

    msg = await channel.send('\n'.join(response))
    return msg.id


@tasks.loop(seconds=600)
async def edit_schedule_message():
    channel = bot.get_channel(int(env["SCHEDULE_EDIT_CHANNEL"]))
    msg_id = int(env["ANNOUNCE_MSG_ID"])
    msg = await channel.fetch_message(msg_id)

    response = _create_schedule_message()
    if not response:
        return

    # Edit message in place
    await msg.edit('\n'.join(response))


def _create_track_selection_message():
    response = r99_mgr.get_formatted_events()
    if not response:
        utils.log("Could not fetch track selection :(")
        return []
    response.append(" *(Refreshes every 10 minutes)*")
    return response


async def post_track_selection_message():
    channel = bot.get_channel(int(env["SCHEDULE_EDIT_CHANNEL"]))

    response = _create_track_selection_message()
    if not response:
        return

    msg = await channel.send('\n'.join(response))
    return msg.id


@tasks.loop(seconds=600)
async def edit_track_selection_message():
    channel = bot.get_channel(int(env["SCHEDULE_EDIT_CHANNEL"]))
    msg_id = int(env["TRACK_SELECTION_MSG_ID"])
    msg = await channel.fetch_message(msg_id)

    response = _create_track_selection_message()
    if not response:
        return

    # Edit message in place
    await msg.edit('\n'.join(response))


@tasks.loop(seconds=3600)
async def announce_schedule():
    await bot.wait_until_ready()
    channel = bot.get_channel(int(env["ANNOUNCE_CHANNEL"]))
    glitch_evts = event_choices.get("Glitch 99")
    evts = slot2mgr.list_events(next=120)
    glitches = slot1mgr.when_event(names=glitch_evts, count=5, limit=120)
    if not evts:
        print("Could not fetch any event :(")
        return None
    response = ["F-Zero 99 Upcoming events in your local time:"]
    has_king_gp = False
    ongoing_evt = evts[0].name
    ongoing_evt_end = evts[0].end_time
    response.append(formatters.format_current_event(ongoing_evt, ongoing_evt_end))
    for evt in evts[1:]:
        response.append(formatters.format_future_event(evt))
        if evt.name == "king":
            has_king_gp = True
    if glitches:
        response.append("\nNext Glitch Races:")
        for glitch in glitches:
            response.append(formatters.format_future_event(glitch))
    if not has_king_gp:
        king_evt = slot2mgr.when_event(names=["king"], count=1)
        if king_evt:
            response.append("\nNext King League:")
            response.append(formatters.format_future_event(king_evt[0]))
    await channel.send('\n'.join(response))


@bot.slash_command(name="misa", description="Provide a pearl of wisdom from The One Ahead Of Us.")
async def misa(ctx): # a slash command will be created with the name "ping"
    utils.log(f"{ctx.author.name} used {ctx.command}.")
    await ctx.respond(quotes.misa())


@bot.slash_command(name="ping", description="Sends the bot's latency.", guild_ids=[env['TEST_GUILD_ID']])
async def ping(ctx): # a slash command will be created with the name "ping"
    utils.log(f"{ctx.author.name} used {ctx.command}.")
    await ctx.respond(f"Pong! Latency is {bot.latency}")


if __name__ == "__main__":
    bot.run(env['DISCORD_BOT_TOKEN']) # run the bot with the token
