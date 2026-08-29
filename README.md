# pengbot99

A library and Discord bot for useful F-Zero 99 schedule info

## Setup

This project uses `uv` for dependency management.
From the repository root:

`.python-version` pins Python 3.11, the oldest version `requires-python`
supports and the one `ruff` targets. Developing against the floor is what keeps
that floor honest for anything installing this package; the test suite also
passes on 3.12, 3.13 and 3.14.

### Create & activate a virtual env

```bash
uv sync --dev # This creates a venv at ./.venv and installs dependencies there

# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

The Discord client library is an optional dependency, so the command above
installs the schedule logic and the test suite but not `py-cord`. To work on or
run the bot, ask for the `bot` extra as well:

```bash
uv sync --dev --extra bot
```

You may then import the module in your Python environment:

```bash
python -c "import pengbot99"
```

The game content the schedule is computed from ships inside the package, so a
consumer that only wants the schedule logic needs neither a checkout nor a
configuration file:

```bash
python -c "from pengbot99 import schedule; print(schedule.load_schedule(None, 'slot2_schedule'))"
```

Passing a directory in place of `None` reads that file from there instead. The
bot does exactly this with `CONFIG_PATH`, described below.

### Using it as a library

Individual schedules are rarely what a caller wants. `pengbot99.managers` turns
the constants and the content dumps into the managers that answer questions,
which is the same call the bot makes at startup:

```python
from datetime import datetime, timezone

from pengbot99 import managers, utils

with utils.open_data_file(None, "constants.dat") as fd:
    csts = utils.parse_env(fd.readlines())

mgrs = managers.build_managers(csts)
print(mgrs.slot2mgr.get_events(timestamp=datetime.now(timezone.utc), limit=120))
```

`build_managers` takes an optional second argument, the `CONFIG_PATH` directory
to read the content from; without it, the packaged copy is read. It needs no
`.env`, no Discord and no particular working directory. The managers it returns
are described in the module.

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
# Config files folder (optional; overrides the packaged schedules)
CONFIG_PATH=C:/Path/to/schedule/files
# Schedule constants file name (in config folder)
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

**CONSTANTS_FILE**: This file holds constants that are used for fine-tuning the schedule. It can reside alongside the CSV schedule files.
If omitted, the packaged `constants.dat` is used — see below.

### Additional optional configuration

**CONFIG_PATH**: The path to a directory of CSV schedule files and, optionally, a `constants.dat` alongside them.

A complete set of these files ships inside the package, in `py/pengbot99/data`, and the bot loads those when `CONFIG_PATH` is unset. Setting it overrides them: every file is then read from that directory instead, which is what you want if you keep a directory of hand-edited schedules. The override is all-or-nothing per file name — there is no merging of a partial directory with the packaged one.

Note that the files moved out of a top-level `config/` directory when the package was made installable. An instance whose `.env` pointed `CONFIG_PATH` at that directory should either drop the setting, to use the packaged copies, or point it at a directory of its own.

**TICKER_OVERRIDE**: This value can be omitted from the config. If missing or empty, the bot will update its status description every 10 minutes (or `REFRESH_INTERVAL` minutes) to show the current or next Grand Prix.
If a text string is provided in this configuration entry, the bot will instead display its content as status. No automatic update will occur.
Note that the status text has limited space for display on most clients. It is suggested to keep any override text short, i.e. 30 characters or less.

**ANNOUNCE_CHANNEL**: A Discord channel ID. This value can safely be omitted from the Config, as its associated method is currently considered deprecated. The bot's invocation of it is commented out but remains in code.
It is used to have the bot repeat a schedule message every hour in the given channel.

**REFRESH_INTERVAL**: How often the schedule and ticker message get refreshed, in minutes. If not specified, refresh every 10 minutes.

If any other configuration key is defined (using the `NAME=value` scheme), it will be read but ignored by the bot.
The configuration file may contain any number of comment lines starting with `#` character.

### Constants information

Constants are used to conveniently offset the schedule rotation without having to edit the schedule files.
Constants are defined using `NAME=VALUE` syntax. Name is conventionally all-caps. Value is an integer that may be negative.
The following constants are expected to be present:

- CLASSIC_LINE_UP_OFFSET
- MINIPRIX_LINE_UP_OFFSET
- MIRROR_LINE_UP_OFFSET
- PRIVATE_MP_MINUTE_OFFSET
- PRIVATE_MP_MIRROR_MINUTE_OFFSET
- PRIVATE_CMP_MINUTE_OFFSET
- NINETYNINE_MINUTE_OFFSET

To change the offset the bot is using, simply edit the Constant file and restart the bot.

The bot uses the presence of the following constants as an indication that Machine Shuffle Weekend event is on:

- SHUFFLE_MINIPRIX_LINE_UP_OFFSET
- SHUFFLE_MIRROR_LINE_UP_OFFSET
- PRIVATE_SHUFFLE_MP_MINUTE_OFFSET
- PRIVATE_SHUFFLE_MP_MIRROR_MINUTE_OFFSET

When they are present, the bot will use the specified offset for Miniprix events occuring at weekend time (UTC).
If there is no Machine Shuffle event, those constants should be omitted from the config, or commented out.
As of F-Zero 99 version 1.6.1, there is no mirroring in Private Machine Shuffle-Miniprix, unless the lobby is started at the time of a public Machine Shuffle event. In this later case, the track selection will follow the public event's setting. In any case, the mirroring constant currently does not affect the results in any way.

The bot uses the presence of the following constant as an indication that Secret League is active:

- SECRET_LEAGUE_INTERVALS

The value of SECRET_LEAGUE_INTERVALS is a comma-separated list of integers. Each integer represents an interval between Secret League Grand Prix. When enabled, the Grand Prix rotation proceeds as defined per the schedule, but some Grand Prix are replaced by Secret League as defined per the intervals. When this will happen, the Grand Prix will appear as `Secret League (replaces <replaced GP>)`, and the ticker will display Secret League instead of the replaced Grand Prix.
Once all intervals in the list have elapsed, the process repeats from the start of the list.

- SECRET_LEAGUE_OFFSET

This may optionally be defined, as an integer value, to change the start Grand Prix of the Secret League intervals sequence. If not defined, it is set to zero.

- WEEKEND_SECRET_LEAGUE_INTERVALS
- WEEKEND_SECRET_LEAGUE_OFFSET

In cases where the schedule defines a separate Grand Prix rotation for the weekend, these values can be defined to apply a separate intervals list and a separate offset applying to the weekend schedule. For v1.7, this is useful for Leagues weekend events. Similarly with the `SECRET_LEAGUE_INTERVALS` constant, the presence or absence of `WEEKEND_SECRET_LEAGUE_INTERVALS` is used to determine whether this feature should be activated when the bot starts. `WEEKEND_SECRET_LEAGUE_OFFSET` is set to zero if the constant is left undefined.

## Running the application

The application can be started through the `bot.py` module.
No assumption is made as to the target environment, therefore no shell script or similar is provided.

```bash
python -m pengbot99.bot
```

The bot requires the `bot` extra, which brings in `py-cord`. Installing the
package without it gives the schedule logic alone, and starting the bot then
fails at import with `ModuleNotFoundError: No module named 'discord'`:

```bash
uv pip install '.[bot]'   # bot deployment
uv pip install .          # schedule logic only, for use as a library
```

The split exists because the schedule computation is useful on its own -- it
reads CSV files and does arithmetic, and a caller that only wants that has no
reason to install a Discord gateway client. `apiadapter.py` and `bot.py` are the
only modules that require it, and a test in `tests/test_import_boundary.py`
fails if a Discord import ever reaches the schedule modules.

## Running tests

Tests are written using Python's built-in unittest module and are run with
`pytest`, which executes `unittest.TestCase` classes as they are. From the
repository root:

```bash
uv run pytest
```

The built-in runner still works and needs no extra dependency:

```bash
python -m unittest discover -s tests
```

Both resolve the fixture directory from `tests/conftest.py`, so neither depends
on the working directory and neither needs a configuration file to be created
first.

## Releasing

`pengbot99` is consumed as a library by other projects, which pin it to an
immutable git reference rather than to a branch. Tags are that reference: when a
change is ready to be depended on, tag it.

```bash
# bump `version` in pyproject.toml first
git tag -a v0.2.0 -m "Short summary of what changed"
git push origin v0.2.0
```

Use annotated tags (`-a`) rather than lightweight ones, and keep the tag in step
with `version` in `pyproject.toml`. Either the maintainer or a contributor can
cut one — what matters is that a tag exists, because without it a consumer has
to pin a bare commit sha. That works, but it goes stale silently: nothing tells
the consumer a newer release has happened.

`shuffle_on` is an older feature marker, not a release tag.

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
