import utils


async def get_thread(channel, thread_id):
    """ Get a Thread object for the requested thread.
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
