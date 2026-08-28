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

> **Pending change — maintainer input needed.**
> Work to make `pengbot99` usable as an installed library moves the shipped CSV
> files out of `config/` and into the package itself, so that an installed copy
> carries its own data and `CONFIG_PATH` becomes optional rather than mandatory.
> Setting `CONFIG_PATH` will continue to override the packaged files and win, so
> a directory of hand-edited CSVs keeps working exactly as it does now.
>
> What needs confirming before that lands: if a running instance points
> `CONFIG_PATH` at *this repository's* `config/` directory, it will break — not
> because the override stopped working, but because the path no longer exists.
> If it points at a separate directory of CSVs, nothing changes for it.

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
