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

Following this, you should be able to run a bot and/or import modules as above.


## Running the application

The application can be started through the `bot.py` module.
No assumption is made as to the target environment, therefore no shell script or similar is provided.

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

The remaining configuration resides in the `CONFIG_PATH` folder defines above.
It consists of schedule data (csv files) and the `CONSTANTS_FILE` file that exists to facilitate fine-tuning the schedule.
Files matching the bot's setup are supplied in the repository.

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

- Rotation may be simplified by using Python's own deque implementation, since it has a .rotate function
 - deque docs https://docs.python.org/3/library/collections.html#collections.deque
- Event schedule could be written as a tree using anytree or bigtree
 - anytree https://github.com/c0fec0de/anytree
 - bigtree https://bigtree.readthedocs.io/stable/
