# pengbot99

A library and Discord bot for useful F-Zero 99 schedule info

## Setup

This project uses `uv` for dependency management.
From the repository root:

### Create & activate a virtual env

```bash
uv sync --dev # This creates a venv at ./.venv and installs dependencies there

# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

You may then import the module in your Python environment:

```bash
python -c "import pengbot99"
```

To run the application as a Discord bot, you will first need to set up a configuration file.

## Configuring the Discord bot

The bot requires some configuration so that it can start.
Base configuration is not provided in the repository and will need to be created alongside a fresh install.
By default, the bot will attempt to load a `.env` file from its working directory.
Here is a sample content for such a file with example (bogus) values.

```bash
# .env
# Discord Application Token (THIS IS A SECRET)
DISCORD_BOT_TOKEN=Al0ngAlph4numericT0k3nSuppliedByD1scord
# ID for the bot's announce channel (legacy method/commented out)
ANNOUNCE_CHANNEL=1234567890
# ID for the bot's schedule channel
SCHEDULE_EDIT_CHANNEL=9876543210
# Config files root folder (schedule profiles live as event_<name> subfolders, e.g. event_default/)
CONFIG_PATH=C:/Path/to/config
# Schedule constants file name (in the schedule profile folder)
CONSTANTS_FILE=constants.dat
# Main refresh interval (for primary schedule and ticker) in minutes
REFRESH_INTERVAL=5
```

Note that because this file contains secrets, it is not under version control, per the repository's `.gitignore` file.
Therefore, once you have created one, you are responsible for tracking changes to it and keeping it safe.

### Mandatory configuration

**DISCORD_BOT_TOKEN**: This is supplied by Discord through the developer portal and is used to uniquely identify your bot.

**SCHEDULE_EDIT_CHANNEL**: A Discord channel ID. The bot will post its schedule messages in this channel, and then will regularly update them (every 10 minutes or `REFRESH_INTERVAL` minutes).
It is suggested that only the bot has permission to post to this channel so that the schedule remains the last message on the channel.

**CONFIG_PATH**: The root path to the bot's configuration directory. Schedule configuration lives in profile subfolders, with the baseline schedule in `CONFIG_PATH/event_default`. A complete set of CSV schedule files and associated constants data is provided in the repository.

**CONSTANTS_FILE**: This file holds constants that are used for fine-tuning the schedule. It resides in the schedule profile folder (i.e. `CONFIG_PATH/event_default` by default). A constants file is provided in the repository for each event profile.

### Additional optional configuration

**TICKER_OVERRIDE**: This value can be omitted from the config. If missing or empty, the bot will update its status description every 10 minutes (or `REFRESH_INTERVAL` minutes) to show the current or next Grand Prix.
If a text string is provided in this configuration entry, the bot will instead display its content as status. No automatic update will occur.
Note that the status text has limited space for display on most clients. It is suggested to keep any override text short, i.e. 30 characters or less.

**ANNOUNCE_CHANNEL**: A Discord channel ID. This value can safely be omitted from the Config, as its associated method is currently considered deprecated. The bot's invocation of it is commented out but remains in code.
It is used to have the bot repeat a schedule message every hour in the given channel.

**REFRESH_INTERVAL**: How often the schedule and ticker message get refreshed, in minutes. If not specified, refresh every 10 minutes.

**EVENT_SCHEDULE_FILE**: This file holds rows of dates at which specific game schedules become active. It resides in the config folder (`CONFIG_PATH/server_events.csv`
by default). The content is read at startup time, if present, and no --profile flag is given. See how to run the bots below for details.

If any other configuration key is defined (using the `NAME=value` scheme), it will be read but ignored by the bot.
The configuration file may contain any number of comment lines starting with `#` character.

### Constants information

Constants are used to conveniently offset the schedule rotation without having to edit the schedule files.
All schedule-related constants are defined in the **CONSTANTS_FILE** that is referenced in the **.env** file.
Constants are defined using `NAME=VALUE` syntax. Name is conventionally all-caps. Value is an integer that may be negative.

The following constants are expected to be present:

- CLASSIC_LINE_UP_OFFSET
- MINIPRIX_LINE_UP_OFFSET
- MIRROR_LINE_UP_OFFSET
- PRIVATE_MP_MINUTE_OFFSET
- PRIVATE_MP_MIRROR_MINUTE_OFFSET
- PRIVATE_CMP_MINUTE_OFFSET
- NINETYNINE_MINUTE_OFFSET

All constants are first read from the `event_default` constants file. If the currently-active event profile is not default, AND the event's profile own constants file
also defines a constant, then this later value will override the default value. This means that event profiles outside default do not need to hold a constant's value,
if this value would be identical to the default profile's.
To change the offset the bot is using, simply edit the Constant file in the appropriate event profile and restart the bot.

Some of the schedule features are activated through feature flag constants defined in the constants file.
Flags are set to `1` to enable a feature, or `0` to disable it. Their associated tuning constants may remain defined regardless.

The bot activates the Machine Shuffle Weekend event when the `SHUFFLE_ENABLED` flag is set to `1`.
In that case, it will use the specified offsets for Miniprix events occuring at weekend time (UTC):

- SHUFFLE_MINIPRIX_LINE_UP_OFFSET
- SHUFFLE_MIRROR_LINE_UP_OFFSET
- PRIVATE_SHUFFLE_MP_MINUTE_OFFSET
- PRIVATE_SHUFFLE_MP_MIRROR_MINUTE_OFFSET

If there is no Machine Shuffle event, set the flag to `0`.
As of F-Zero 99 version 1.6.1, there is no mirroring in Private Machine Shuffle-Miniprix, unless the lobby is started at the time of a public Machine Shuffle event. In this later case, the track selection will follow the public event's setting. In any case, the mirroring constant currently does not affect the results in any way.

The Secret League feature can be activated by setting the `SECRET_LEAGUE_ENABLED` flag to `1`:

- `SECRET_LEAGUE_INTERVALS`

The value of SECRET_LEAGUE_INTERVALS is a comma-separated list of integers. Each integer represents an interval between Secret League Grand Prix. When enabled, the Grand Prix rotation proceeds as defined per the schedule, but some Grand Prix are replaced by Secret League as defined per the intervals. When this will happen, the Grand Prix will appear as `Secret League (replaces <replaced GP>)`, and the ticker will display Secret League instead of the replaced Grand Prix.
Once all intervals in the list have elapsed, the process repeats from the start of the list.

- SECRET_LEAGUE_OFFSET

This may optionally be defined, as an integer value, to change the start Grand Prix of the Secret League intervals sequence. If not defined, it is set to zero.

- WEEKEND_SECRET_LEAGUE_ENABLED
- WEEKEND_SECRET_LEAGUE_INTERVALS
- WEEKEND_SECRET_LEAGUE_OFFSET

In cases where the schedule defines a separate Grand Prix rotation for the weekend, the `WEEKEND_SECRET_LEAGUE_ENABLED` flag (along with the `SECRET_LEAGUE_ENABLED` flag) can be used to apply a separate intervals list and a separate offset applying to the weekend schedule. For v1.7, this is useful for Leagues weekend events. `WEEKEND_SECRET_LEAGUE_OFFSET` is set to zero if the constant is left undefined.

## Running the application

The application can be started through the `bot.py` module.
No assumption is made as to the target environment, therefore no shell script or similar is provided.

There are two different ways to run the bot:

**1. Automatic event profile switching mode**

In this mode, the `EVENT_SCHEDULE_FILE` CSV is loaded at startup. To use this feature, simply supply a CSV file in the expected location. The repository provides an
example event schedule file. 

Each row is in the CSV should be '<YYYY-MM-DD>,<profile>', meaning that the profile named by '<profile>' becomes active at 00:00 UTC on that date. Rows do not need to
be sorted; they are sorted by date on load. Comments (lines starting with '#') and malformed rows are ignored with a warning.

Upon starting, the bot will search for the present date and set the referenced schedule as active. It will then check the CSV daily and switch schedule profiles when
appropriate. It should be noted that the daily check involves reloading the CSV, therefore the event schedule may be modified without restarting the bot; however, any
change will only come in effect at the time of the daily check. For a change to become effective immediately, simply restart the bot.

When all event dates are in the past, the bot will remain on the last specified schedule indefinitely.

To start in this mode, make sure the environment file specifies `EVENT_SCHEDULE_FILE=file_name` and that `<filename>` is found in the `CONFIG_PATH` folder.
Then, start up the bot without specifying any flag.

```bash
python -m pengbot99.bot
```

**2. Single event profile mode**

This mode is active if no EVENT_SCHEDULE_FILE constant is found, or if a --profile flag is given to the bot at start up. It is also in effect if the EVENT_SCHEDULE_FILE
cannot be loaded.

The schedule profile to load can be selected with the `--profile` argument. The default profile is `default`; event profiles live in their own folder (prefixed `event_`) under `CONFIG_PATH` and overlay the default config. For example, to run with the Queen Leagues Weekend Event schedule (loaded from `CONFIG_PATH/event_queen`):

```bash
python -m pengbot99.bot --profile queen
```

In this mode, the bot only ever runs the given event profile schedule. Any EVENT_SCHEDULE_FILE is ignored and there is no daily check.

## Running tests

For simplicity's sake, tests are written using Python's built-in unittest module.
To run tests from the repository root:

```bash
python -m unittest discover -s tests
```

## Future improvements

- Refactor schedule manager to more elegantly manage rotations
- Bot Cogs
- Migrate tests to Pytest and automate with Github Actions, add coverage report
- Expand the /explain command to cover other topics than GP Rotation
- Support for protracks/team battle as an upgrade to current /ninetynine command

## References

- Rotation may be simplified by using Python's own deque implementation, since it has a .rotate function
  - deque docs <https://docs.python.org/3/library/collections.html#collections.deque>
- Event schedule could be written as a tree using anytree or bigtree
  - anytree <https://github.com/c0fec0de/anytree>
  - bigtree <https://bigtree.readthedocs.io/stable/>
