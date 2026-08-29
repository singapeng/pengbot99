import os
from datetime import datetime
from importlib import resources

# The game-content dumps ship inside the package, under this directory.
DATA_DIR = "data"


def open_data_file(path, name, **kwargs):
    """Opens a game content file, from 'path' or from the packaged copy.

    'path' is the CONFIG_PATH override: when it is set, the file is read from
    that directory, and when it is None or empty the copy that shipped inside
    the package is read instead. Resolved on every call, so a caller that
    passes a path for one file and none for the next gets what it asked for.
    """
    if path:
        return open(os.path.join(path, name), **kwargs)
    return (resources.files("pengbot99") / DATA_DIR / name).open(**kwargs)


def parse_env(lines):
    """Parses KEY=VALUE lines into a dict, ignoring comments."""
    env = {}
    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            # ignore comments
            continue
        var_name, var_value = line.split("=", 1)
        env[var_name] = var_value
    return env


def load_env(path=None):
    """Reads the .env file and returns a dict"""
    path = path or ".env"
    with open(path) as fd:
        return parse_env(fd.readlines())


def _sideload_data(env, data_name, default_name=None):
    """Loads a data file named by the env, from CONFIG_PATH or the package.

    'default_name' is the packaged file to fall back on when the env does not
    name one. Without it, an env that does not name the file gets nothing,
    which is the behaviour these files had before any of them were packaged.
    """
    name = env.get(data_name, default_name)
    if not name:
        return None
    with open_data_file(env.get("CONFIG_PATH"), name) as fd:
        return parse_env(fd.readlines())


def load_config(path=None):
    """Reads the .env file and returns a dict.
    If the .env defines a constants file path, load that too.
    Returns both as a tuple of dicts.
    """
    env = load_env(path)

    # load schedule constants from a versioned config file
    csts = _sideload_data(env, "CONSTANTS_FILE", "constants.dat")
    # load explainer data from its config file
    xpln = _sideload_data(env, "EXPLAIN_FILE")
    return env, csts, xpln


def log(text):
    """Log to stdout with timestamp.
    TODO: replace with logging
    """
    stamp = datetime.now()
    ymd = "%04d-%02d-%02d" % (stamp.year, stamp.month, stamp.day)
    hms = "%02d:%02d:%02d" % (stamp.hour, stamp.minute, stamp.second)
    print("{0} {1} {2}".format(ymd, hms, text))


MSG_ENV_PATH = ".msg_struct"


def read_msg_struct():
    """Reads the base message structure config"""
    path = MSG_ENV_PATH
    try:
        msg_env = load_env(path)
    except Exception as exc:
        # TODO: more error handling
        log("Unable to load {0}. Error: '{1}'".format(path, str(exc)))
        return {}
    # TODO: validate keys in the env
    return msg_env


def write_msg_struct(msg_env):
    lines = []
    for key, value in msg_env.items():
        lines.append("{0}={1}\n".format(key, value))
    with open(MSG_ENV_PATH, "w") as fd:
        fd.writelines(lines)
