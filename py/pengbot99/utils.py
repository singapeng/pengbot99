import os
from datetime import datetime
from importlib import resources
from pathlib import Path

# The game-content dumps ship inside the package, under this directory.
DATA_DIR = "data"
# The profile that holds a complete schedule config. Every other profile is a
# partial one, laid over it.
DEFAULT_PROFILE = "default"


def _as_dir(path):
    """Turns 'path' into something with '/', open(), is_file() and iterdir().

    None or empty is the packaged data directory, which is only a filesystem
    path when the package is installed unzipped -- hence not os.path.
    """
    if not path:
        return resources.files("pengbot99") / DATA_DIR
    if isinstance(path, (str, os.PathLike)):
        return Path(path)
    return path


def open_data_file(path, name, **kwargs):
    """Opens a game content file, from 'path' or from the packaged copy.

    'path' is the CONFIG_PATH override: when it is set, the file is read from
    that directory, and when it is None or empty the copy that shipped inside
    the package is read instead. Resolved on every call, so a caller that
    passes a path for one file and none for the next gets what it asked for.
    A directory returned by get_schedule_dir is accepted as well.
    """
    return (_as_dir(path) / name).open(**kwargs)


def has_data_file(path, name):
    """Whether open_data_file would find 'name' in 'path'."""
    return (_as_dir(path) / name).is_file()


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


def get_schedule_dir(env, profile=None):
    """Returns the folder holding schedule config files for the given
    profile. Defaults to 'default'.
    Profile folders live as subfolders of the CONFIG_PATH root, or of the
    packaged data directory when the env names no CONFIG_PATH. The packaged
    one is not a str: hand it to open_data_file or schedule.load_schedule
    rather than to os.path.
    """
    profile = profile or DEFAULT_PROFILE
    root = env.get("CONFIG_PATH")
    if root:
        return os.path.join(root, profile)
    return _as_dir(None) / profile


def require_profile(env, profile):
    """Raises FileNotFoundError when 'profile' has no folder.

    Every file of a profile is optional, so a misspelt profile name would
    otherwise load the default schedule and say nothing.
    """
    if not _as_dir(get_schedule_dir(env, profile)).is_dir():
        raise FileNotFoundError(
            "No schedule profile '{0}' in {1}".format(
                profile, env.get("CONFIG_PATH") or "the packaged data"
            )
        )


def log_profile_csv_warnings(env, profile):
    """Logs a warning for CSV files in a profile folder that do not
    match any file in the default folder. Such files would only be
    loaded if a caller knew their name, so they are likely unused.
    """
    if not profile or profile == DEFAULT_PROFILE:
        return
    profile_dir = _as_dir(get_schedule_dir(env, profile))
    default_dir = _as_dir(get_schedule_dir(env))
    if not profile_dir.is_dir() or not default_dir.is_dir():
        return
    default_names = {
        entry.name for entry in default_dir.iterdir() if entry.name.endswith(".csv")
    }
    for entry in profile_dir.iterdir():
        if entry.name.endswith(".csv") and entry.name not in default_names:
            log(
                "WARNING profile '{0}': file '{1}' does not match any default "
                "schedule file.".format(profile, entry.name)
            )


def load_constants(cfg_path=None, profile=None, name="constants.dat"):
    """Reads the schedule constants of a profile, as a dict of strings.

    The constants of the 'default' profile, overlaid per key with those of
    'profile'. A profile folder without a constants file changes none of them.
    'cfg_path' is the CONFIG_PATH root; None reads the packaged profiles. No
    .env is read, so this is how a caller that is not the bot gets what
    managers.build_managers takes.
    """
    env = {"CONFIG_PATH": cfg_path}
    with open_data_file(get_schedule_dir(env), name) as fd:
        csts = parse_env(fd.readlines())
    if profile and profile != DEFAULT_PROFILE:
        require_profile(env, profile)
        profile_dir = get_schedule_dir(env, profile)
        if has_data_file(profile_dir, name):
            with open_data_file(profile_dir, name) as fd:
                csts.update(parse_env(fd.readlines()))
    return csts


def _sideload_data(env, data_name):
    """Loads a data file named by the env, from CONFIG_PATH or the package.

    An env that does not name the file gets None.
    """
    name = env.get(data_name)
    if not name:
        return None
    with open_data_file(env.get("CONFIG_PATH"), name) as fd:
        return parse_env(fd.readlines())


def load_config(path=None, profile=DEFAULT_PROFILE):
    """Reads the .env file and returns a dict.
    Schedule constants are read from the 'default' profile folder,
    then overlaid with any constants defined in the active profile.
    The .env may name the constants file; it is constants.dat otherwise.
    Returns the env, the constants and the explainer data as a tuple.
    """
    env = load_env(path)

    csts = load_constants(
        env.get("CONFIG_PATH"), profile, env.get("CONSTANTS_FILE", "constants.dat")
    )
    # explainer data is not part of the schedule profile structure
    # and loads directly from the CONFIG_PATH root
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
