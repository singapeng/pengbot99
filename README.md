# pengbot99
A library and Discord bot for useful F-Zero 99 schedule info


## Setup

The files may be installed using pip. For example, from the source repository, simply run:
```
pip install .
```

You may then import the module in your Python environment.
```
>>> import pengbot99
```

You may want to use a virtual environment since pengbot99 has dependencies on third-party libraries (namely py-cord).
To create a virtual environment in a `venv` folder under the code location:

```
python -m venv venv
source venv/bin/activate
pip install .
```

Following this, you should be able to import modules as above.
To run the application as a Discord bot, you will first need to set up a configuration file.

## Configuring the Discord bot

The bot requires some configuration so that it can start. 
Base configuration is not provided in the repository and will need to be created alongside a fresh install.
By default, the bot will attempt to load a `.env` file from its working directory.
Here is a sample content for such a file with example (bogus) values.

```
# .env
# Discord Application Token (THIS IS A SECRET)
DISCORD_BOT_TOKEN=Al0ngAlph4numericT0k3nSuppliedByD1scord
# ID for the bot's announce channel (legacy method/commented out)
ANNOUNCE_CHANNEL=1234567890
# ID for the bot's schedule channel
SCHEDULE_EDIT_CHANNEL=9876543210
# Config files folder
CONFIG_PATH=C:/Path/to/schedule/files
# Schedule constants file name (in config folder)
CONSTANTS_FILE=constants.dat
```

Note that because this file contains secrets, it is not under version control, per the repository's `.gitignore` file.
Therefore, once you have created one, you are responsible for tracking changes to it and keeping it safe.

### Mandatory configuration

**DISCORD_BOT_TOKEN**: This is supplied by Discord through the developer portal and is used to uniquely identify your bot.

**SCHEDULE_EDIT_CHANNEL**: A Discord channel ID. The bot will post its schedule messages in this channel, and then will regularly update them (every 10 minutes).
It is suggested that only the bot has permission to post to this channel so that the schedule remains the last message on the channel.

**CONFIG_PATH**: The path to the bot's CSV schedule configuration directory. A complete set of CSV files is provided in the repository.

**CONSTANTS_FILE**: This file holds constants that are used for fine-tuning the schedule. It can reside alongside the CSV schedule files.
A default constants file is provided in the repository.

### Additional optional configuration

**TICKER_OVERRIDE**: This value can be omitted from the config. If missing or empty, the bot will update its status description every 10 minutes to show the current or next Grand Prix.
If a text string is provided in this configuration entry, the bot will instead display its content as status. No automatic update will occur.
Note that the status text has limited space for display on most clients. It is suggested to keep any override text short, i.e. 30 characters or less.

**ANNOUNCE_CHANNEL**: A Discord channel ID. This value can safely be omitted from the Config, as its associated method is currently considered deprecated. The bot's invocation of it is commented out but remains in code.
It is used to have the bot repeat a schedule message every hour in the given channel.

If any other configuration key is defined (using the `NAME=value` scheme), it will be read but ignored by the bot.
The configuration file may contain any number of comment lines starting with `#` character.


## Running the application

The application can be started through the `bot.py` module.
No assumption is made as to the target environment, therefore no shell script or similar is provided.

The main module implements a `__main__` function so it may be started using a Python 3.11+ executable.
```
python bot.py
```

## Running tests

For simplicity's sake, tests are written using Python's built-in unittest module.
To run tests, we would ideally execute a test runner command sourcing tests from the `tests` folder at the root of the repository.
At present, you may run tests using a simple python command, i.e.:
```
> python test_schedule.py
.............
----------------------------------------------------------------------
Ran 13 tests in 0.011s

OK
```

# Future improvements

- Refactor schedule manager to more elegantly manage rotations
- Bot Cogs
- Migrate tests to Pytest and automate with Github Actions, add coverage report
- Expand the /explain command to cover other topics than GP Rotation
- Support for protracks/team battle as an upgrade to current /ninetynine command


# References

* Rotation may be simplified by using Python's own deque implementation, since it has a .rotate function
    * deque docs https://docs.python.org/3/library/collections.html#collections.deque
* Event schedule could be written as a tree using anytree or bigtree
    * anytree https://github.com/c0fec0de/anytree
    * bigtree https://bigtree.readthedocs.io/stable/
