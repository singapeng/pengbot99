# 3rd party imports
import discord

# local imports
from pengbot99 import utils


async def get_msg_url(client, channel_id, message_id):
    """Returns the URL for a given message ID on a given channel."""
    channel = client.get_channel(int(channel_id))
    message = await channel.fetch_message(int(message_id))
    return message.jump_url


async def get_thread(channel, thread_id):
    """Get a Thread object for the requested thread.
    If the thread was archived, unarchive it.
    """
    thread = channel.get_thread(thread_id)
    if thread:
        return thread
    else:
        utils.log("Looking for thread in archive...")
        counter = 0
        async for thread in channel.archived_threads():
            counter += 1
            if thread.id == thread_id:
                await thread.unarchive()
                utils.log("Successfully unarchived thread {0}.".format(thread.id))
                return thread
        if counter >= 0:
            utils.log("Did not find thread amongst {0} in archive.".format(counter))
    # This will probably trigger an attribute error downstream (uncaught).
    # Possibly improve error handling in the future by raising a custom
    # exception instead.
    return None


async def update_activity(client, description, start_time=None):
    """Updates the bot's status activity message.
    Do not block if this task failed.

    start_time: a UTC timezone datetime object.
                This does nothing useful :(
    """
    try:
        await client.change_presence(
            activity=discord.CustomActivity(name=description, start=start_time)
        )
    except Exception as exc:
        utils.log("Failed to update status: '{0}'".format(exc))
