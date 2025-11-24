# Python imports
from datetime import datetime, timedelta, timezone


# 3rd party imports
import discord
from discord.ext import tasks


# local imports
from pengbot99 import apiadapter
from pengbot99 import choicerace
from pengbot99 import explain_cmd
from pengbot99 import formatters
from pengbot99 import miniprix
from pengbot99 import schedule
from pengbot99 import ui
from pengbot99 import utils


# Load tokens, ids, etc from an unversioned env file
# Load schedule constants from a env-defined versioned config file
env, csts, xpln = utils.load_config()

class Pengbot(object):
    def __init__(self, env, csts):
        self.env = env
        self.csts = csts

        # all env values are str, convert schedule offsets to int now
        mp_offset = int(csts["MINIPRIX_LINE_UP_OFFSET"])
        cmp_offset = int(csts["CLASSIC_LINE_UP_OFFSET"])
        mirror_offset = int(csts["MIRROR_LINE_UP_OFFSET"])

        # load the schedule for slot 1 (99 races)
        r99sched = schedule.load_schedule(env['CONFIG_PATH'], 'slot1_schedule')
        # load the weekday schedule for slot 2 (Prix and special events)
        wdsched = schedule.load_schedule(env['CONFIG_PATH'], 'slot2_schedule')
        # load the weekend schedule for slot 2 (Prix and special events)
        wesched = schedule.load_schedule(env['CONFIG_PATH'], 'slot2_schedule_weekend')
        # load the Classic Mini Prix track schedule
        cmpsched = schedule.load_schedule(env['CONFIG_PATH'], 'classic_mp_schedule')
        # load the Mini Prix track schedule
        mpsched = schedule.load_schedule(env['CONFIG_PATH'], 'miniprix_schedule')
        mirrorsc = schedule.load_schedule(env['CONFIG_PATH'], 'miniprix_mirroring_schedule')
        # load the schedule for Private Lobbies Mini-Prix
        plmpsched = schedule.load_schedule(env["CONFIG_PATH"], "private_miniprix_schedule")
        plcmpsched = schedule.load_schedule(env["CONFIG_PATH"], "private_classic_mp_schedule")

        # Create the Public schedule managers
        r99_offset = int(csts["NINETYNINE_MINUTE_OFFSET"])

        self.slot1mgr = schedule.Slot1ScheduleManager(schedule.glitch_origin, r99sched)
        self.slot2mgr = schedule.Slot2ScheduleManager(schedule.origin, wdsched, wesched)
        self.cmp_mgr = miniprix.MiniPrixManager("classicprix", self.slot2mgr, cmpsched, offset=cmp_offset)
        self.mp_mgr = miniprix.MiniPrixManager("miniprix", self.slot2mgr, mpsched, mirrorsc,
                mp_offset, mirror_offset)
        utils.log("Setting cycles to {0} for {1}.".format(self.mp_mgr.mp_cycles, self.mp_mgr.name))
        self.r99_mgr = choicerace.init_99_manager(name=None, glitch_mgr=self.slot1mgr, env=env,
                minutes_offset=r99_offset)

        # Create Private Lobby schedule managers
        pmp_origin = schedule.origin + timedelta(minutes=int(csts["PRIVATE_MP_MINUTE_OFFSET"]))
        pmp_mirror_origin = schedule.origin + timedelta(minutes=int(csts["PRIVATE_MP_MIRROR_MINUTE_OFFSET"]))
        pcmp_origin = schedule.origin + timedelta(minutes=int(csts["PRIVATE_CMP_MINUTE_OFFSET"]))

        pl_slot1 = schedule.Slot1ScheduleManager(pmp_origin, plmpsched)
        mirror_slot1 = schedule.Slot1ScheduleManager(pmp_mirror_origin, mirrorsc)
        self.pmp_mgr = miniprix.PrivateMPManager("miniprix", pl_slot1, self.mp_mgr, mirror_slot1)
        plcmp_slot1 = schedule.Slot1ScheduleManager(pcmp_origin, plcmpsched)
        self.pcmp_mgr = miniprix.PrivateMPManager("classicprix", plcmp_slot1, self.cmp_mgr)

        # Shuffle Mini-Prix schedule managers
        self.smp_mgr = None
        self.psmp_mgr = None

        smp_offset = csts.get("SHUFFLE_MINIPRIX_LINE_UP_OFFSET")
        if smp_offset:
            smp_offset = int(smp_offset)
            smp_mirror_offset = int(csts.get("SHUFFLE_MIRROR_LINE_UP_OFFSET", mirror_offset))
            self.smp_mgr = miniprix.MiniPrixManager("miniprix", self.slot2mgr, mpsched, mirrorsc,
                    smp_offset, smp_mirror_offset)
            psmp_origin = schedule.origin + timedelta(minutes=int(csts["PRIVATE_SHUFFLE_MP_MINUTE_OFFSET"]))
            psl_slot1 = schedule.Slot1ScheduleManager(psmp_origin, plmpsched)
            self.psmp_mgr = miniprix.PrivateMPManager("miniprix", psl_slot1, self.smp_mgr, None)
            utils.log("!! Configured Shuffle Weekend !!")

        utils.log("Initializing Mini World Tour managers.")
        self.mwt_on = False
        mp_offset = int(csts["MWT_MINIPRIX_LINE_UP_OFFSET"])
        cmp_offset = int(csts["MWT_CLASSIC_LINE_UP_OFFSET"])
        mirror_offset = int(csts["MWT_MIRROR_LINE_UP_OFFSET"])

        # load the schedule for slot 2 (Prix and special events)
        mwtsched = schedule.load_schedule(env['CONFIG_PATH'], 'mwt_schedule')

        # Those managers are offline as long as mwt_on is False
        # then we will store the currently active managers in here.
        # Mini World Tour slot2 manager intentionally uses the same
        # schedule for weekdays and weekend days.
        self._off_slot2mgr = schedule.Slot2ScheduleManager(schedule.origin, mwtsched, mwtsched)
        self._off_cmp_mgr = miniprix.MiniPrixManager("classicprix", self._off_slot2mgr, cmpsched, offset=cmp_offset)
        self._off_mp_mgr = miniprix.MiniPrixManager("miniprix", self._off_slot2mgr, mpsched, mirrorsc,
                mp_offset, mirror_offset)
        self._off_pmp_mgr = miniprix.PrivateMPManager("miniprix", pl_slot1, self._off_mp_mgr, mirror_slot1)
        self._off_pcmp_mgr = miniprix.PrivateMPManager("classicprix", plcmp_slot1, self._off_cmp_mgr)

    def is_shuffle_on(self):
        if self.smp_mgr:
            return True
        return False

    def flip_mwt(self):
        self.mwt_on = not self.mwt_on
        # hold these temporarily
        slot2mgr = self.slot2mgr
        mp_mgr = self.mp_mgr
        cmp_mgr = self.cmp_mgr
        pmp_mgr = self.pmp_mgr
        pcmp_mgr = self.pcmp_mgr
        # bring offline managers online
        self.slot2mgr = self._off_slot2mgr
        self.mp_mgr = self._off_mp_mgr
        self.cmp_mgr = self._off_cmp_mgr
        self.pmp_mgr = self._off_pmp_mgr
        self.pcmp_mgr = self._off_pcmp_mgr
        # store offlined managers safely
        self._off_slot2mgr = slot2mgr
        self._off_mp_mgr = mp_mgr
        self._off_cmp_mgr = cmp_mgr
        self._off_pmp_mgr = pmp_mgr
        self._off_pcmp_mgr = pcmp_mgr


# Using the Pengbot class as a holder for all schedule managers for now.
pb = Pengbot(env, csts)
bot = discord.Bot()

explainer = explain_cmd.Explainer(xpln, pb.slot2mgr)


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
    return list(ui.event_choices.keys())


async def get_mp_types(ctx: discord.AutocompleteContext):
    """ 
    """
    return list(ui.mp_event_choices.keys())


async def get_tracks(ctx: discord.AutocompleteContext):
    """ 
    """
    if ctx.options.get("event_type") == "Classic Mini-Prix":
        return list(ui.cmp_track_choices.keys())
    else:
        return list(ui.mp_track_choices.keys())


async def get_topics(ctx: discord.AutocompleteContext):
    """ explain command options
    """
    return explainer.topics


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
    # if ticker override is set, set description now.
    ticker = env.get("TICKER_OVERRIDE")
    if ticker:
        utils.log("Ticker override is active, schedule ticker disabled.")
        await apiadapter.update_activity(bot, ticker)
    # Kick-off the automatic announce
    #announce_schedule.start()
    # configure event mode flip
    if csts.get("MWT_MINIPRIX_LINE_UP_OFFSET"):
        await configure_mwt_flip()


async def configure_mwt_flip():
    """ Mini world tour vacation flip!
    """
    mwt_on_time = datetime(2025, 11, 30, 23, 55, tzinfo=timezone.utc)

    @tasks.loop(time=mwt_on_time.time())
    async def flip_mwt():
        # flip-on/off dates:
        mwt_on_time = datetime(2025, 11, 30, 23, 54, tzinfo=timezone.utc)
        mwt_off_time = datetime(2025, 12, 7, 23, 54, tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        flipped = False

        if mwt_on_time < now < mwt_off_time and not pb.mwt_on:
            utils.log("Doing a flip!")
            pb.flip_mwt()
            flipped = True
        elif now > mwt_off_time and pb.mwt_on:
            utils.log("Doing a backflip!")
            pb.flip_mwt()
            flipped = True

        if flipped:
            for mp_type in ("miniprix", "classicprix"):
                await _edit_miniprix_message(mp_type)

    utils.log("Mini World-Tour check will activate at {0}.".format(mwt_on_time.strftime("%H:%M")))
    flip_mwt.start()


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
    evts = pb.slot2mgr.list_events(timestamp=from_time, next=80)
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
    names = ui.event_choices.get(event_type)
    if event_type == "Glitch 99":
        mgr = pb.slot1mgr
        evts = mgr.when_event(names=names, count=count, timestamp=from_time)
    else:
        mgr = pb.slot2mgr
        evts = mgr.when_event(names=names, count=count, timestamp=from_time)
    if not evts:
        utils.log("Could not fetch any '{0}' event :(".format(event_type))
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


def _fetch_miniprix_events(event_type, from_time, private):
    """
    """
    if event_type == "classicprix":
        if private:
            mgr = pb.pcmp_mgr
        else:
            mgr = pb.cmp_mgr
    else:
        if private:
            mgr = pb.pmp_mgr
        else:
            mgr = pb.mp_mgr
    evts = mgr.get_miniprix(timestamp=from_time)
    if evts and event_type != "classicprix" and pb.is_shuffle_on():
        if not pb.slot2mgr.is_weekday(evts[0].start_time):
            if private:
                mgr = pb.psmp_mgr
            else:
                mgr = pb.smp_mgr
            evts = mgr.get_miniprix(timestamp=from_time)
    return evts


def _build_mp_event_name(event_type, private, start_time):
    evt_name = formatters.event_display_names.get(event_type)
    if event_type != "classicprix":
       if pb.is_shuffle_on() and not pb.slot2mgr.is_weekday(start_time):
           evt_name = "Machine Shuffle {0}".format(evt_name)
    if private:
        evt_name = "Private {0}".format(evt_name)
    return evt_name


def _create_miniprix_message(event_type, track_filter, utc_time, verbose, private=False):
    """
    """
    response = None
    err, from_time = _validate_utc_time(utc_time)

    if not err:
        if event_type == "classicprix":
            track = ui.cmp_track_choices.get(track_filter)
        else:
            track = ui.mp_track_choices.get(track_filter)

        evts = _fetch_miniprix_events(event_type, from_time, private)
        if evts:
            evt_name = _build_mp_event_name(event_type, private, evts[0].start_time)
            start = int(evts[0].start_time.timestamp())
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
    event_type = ui.mp_event_choices.get(event_type)
    err, response = _create_miniprix_message(event_type, track_filter, utc_time, verbose, private)
    await ctx.respond(err or response)


def _ninetynine():
    """
    """
    return '\n'.join(pb.r99_mgr.get_formatted_events())


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
    present_evts = list(set([evt.name for evt in evts]))
    missing_evts = []
    # we should show one of each standard/mirror prix pair
    for mprix in [["knight", "mknight"], ["queen", "mqueen"], ["king", "mking"], ["ace", "mace"]]:
        if mprix[0] not in present_evts and mprix[1] not in present_evts:
            missing_evts.append(mprix)
    # now add events that don't have a mirror version
    for name in ["miniprix", "classicprix"]:
        if name not in present_evts:
            missing_evts.append([name])
    results = []
    for item in missing_evts:
        # for mirrored prix, we query both names but will only get the closest
        extra = pb.slot2mgr.when_event(names=item, count=1)
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


async def _update_bot_status(bot):
    gps = ui.event_choices["Grand Prix"]
    evt = pb.slot2mgr.get_current_event()
    if evt.name not in gps:
        evts = pb.slot2mgr.get_events(names=gps, count=1)
        evt = evts[0]
        evt_name = formatters.event_display_names.get(evt.name, evt.name)
        delta = (evt.start_time - datetime.now(timezone.utc)).seconds // 60
        if delta > 10:
            content = "{0} in {1} minutes.".format(evt_name, delta)
        else:
            content = "{0} soon.".format(evt_name)
    else:
        content = "Now: " + formatters.event_display_names.get(evt.name, evt.name)
    await apiadapter.update_activity(bot, content, evt.start_time)
    return content


def _create_schedule_message():
    glitch_evts = ui.event_choices.get("Glitch 99")
    evts = pb.slot2mgr.list_events(next=119)
    glitches = pb.slot1mgr.when_event(names=glitch_evts, count=5, limit=119)
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

    # Update status
    if not env.get("TICKER_OVERRIDE"):
        await _update_bot_status(bot)


### Festival League auto-update 99 race schedule ###

# these functions are currently unused

def _create_track_selection_message():
    response = pb.r99_mgr.get_formatted_events()
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

### End Festival League auto-update 99 race schedule ###


@tasks.loop(seconds=3600)
async def announce_schedule():
    """ Deprecated, currently unused and may not work.

        This creates a new message every hour in the given channel.
        It will cause the channel to go unread each time, which may
        or may not be desirable. On some clients, it may be necessary
        to scroll down from the last unread message when catching up.
        That is most likely not desirable.
    """
    await bot.wait_until_ready()
    channel = bot.get_channel(int(env["ANNOUNCE_CHANNEL"]))
    glitch_evts = ui.event_choices.get("Glitch 99")
    evts = pb.slot2mgr.list_events(next=110)
    glitches = pb.slot1mgr.when_event(names=glitch_evts, count=5, limit=110)
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
        king_evt = pb.slot2mgr.when_event(names=["king"], count=1)
        if king_evt:
            response.append("\nNext King League:")
            response.append(formatters.format_future_event(king_evt[0]))
    await channel.send('\n'.join(response))


@bot.slash_command(name="explain", description="Explain a thing.")
async def explain(
        ctx: discord.ApplicationContext,
        topic: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_topics)),
        ):
    utils.log(f"{ctx.author.name} used {ctx.command}.")
    await ctx.respond(explainer.explain(topic))


@bot.slash_command(name="ping", description="Sends the bot's latency.", guild_ids=[env['TEST_GUILD_ID']])
async def ping(ctx): # a slash command will be created with the name "ping"
    utils.log(f"{ctx.author.name} used {ctx.command}.")
    await ctx.respond(f"Pong! Latency is {bot.latency}")


if __name__ == "__main__":
    bot.run(env['DISCORD_BOT_TOKEN']) # run the bot with the token
