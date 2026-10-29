import logging
import os
import sys
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

logger = logging.getLogger("pengbot99")
# Silent by default: test runs stay quiet, and callers opt into console
# output by calling configure_logging() (see bot.py).
logger.addHandler(logging.NullHandler())

LOG_FORMAT = "%(asctime)s %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

# The game-content dumps ship inside the package, under this directory.
DATA_DIR = "data"
# The profile that holds a complete set of schedule files. Every other
# profile is a partial one, laid over it.
DEFAULT_PROFILE = "default"
# A profile's folder is its name with this prefix.
PROFILE_PREFIX = "event_"


def configure_logging(level=logging.INFO):
    """ Attaches a console handler to the pengbot99 logger.

        Keeps the historical log() output: one timestamped line per
        message on stdout. Idempotent; call once at bot startup.
    """
    logger.setLevel(level)
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT))
    logger.addHandler(handler)


@contextmanager
def silence_logging():
    """ Context manager that silences routine log output for its duration.

        Only warnings (and above) reach the console while active, so
        startup problems stay visible while construction logs are hidden.
        Used at startup so the bot reports its decision, then lets a
        schedule announce itself only when it is actually set active.
    """
    previous = logger.level
    logger.setLevel(logging.WARNING)
    try:
        yield
    finally:
        logger.setLevel(previous)


def log(text):
    """ Log a message through the pengbot99 logger.

        Messages starting with 'WARNING' are emitted at warning level,
        so they survive silence_logging() and the quiet test default.
    """
    if text.startswith("WARNING"):
        logger.warning(text)
    else:
        logger.info(text)


def _as_dir(path):
    """ Turns 'path' into something with '/', open(), is_file(), is_dir()
        and iterdir().

        None or empty is the packaged data directory, which is only a
        filesystem path when the package is installed unzipped -- hence
        not os.path.
    """
    if not path:
        return resources.files("pengbot99") / DATA_DIR
    if isinstance(path, (str, os.PathLike)):
        return Path(path)
    return path


def open_data_file(path, name, **kwargs):
    """ Opens a game content file, from 'path' or from the packaged copy.

        'path' is the CONFIG_PATH override: when it is set, the file is
        read from that directory, and when it is None or empty the copy
        that shipped inside the package is read instead. A directory
        returned by get_schedule_dir is accepted as well.
    """
    return (_as_dir(path) / name).open(**kwargs)


def has_data_file(path, name):
    """ Whether open_data_file would find 'name' in 'path'.
    """
    return (_as_dir(path) / name).is_file()


def parse_env(lines):
    """ Parses KEY=VALUE lines into a dict, ignoring comments.
    """
    env = {}
    for line in lines:
        line = line.strip()
        if line.startswith('#'):
            # ignore comments
            continue
        var_name, var_value = line.split('=', 1)
        env[var_name] = var_value
    return env


def load_env(path=None):
    """ Reads the .env file and returns a dict
    """
    path = path or ".env"
    with open(path) as fd:
        return parse_env(fd.readlines())


def get_schedule_dir(env, profile=None):
    """ Returns the folder holding schedule config files for the given
        profile. Defaults to 'default'.
        Profile folders live as 'event_<profile>' subfolders of the
        CONFIG_PATH root, or of the packaged data directory when the env
        names no CONFIG_PATH. The packaged one is not a str: hand it to
        open_data_file rather than to os.path.
    """
    profile = profile or DEFAULT_PROFILE
    folder = PROFILE_PREFIX + profile
    root = env.get('CONFIG_PATH')
    if root:
        return os.path.join(root, folder)
    return _as_dir(None) / folder


def is_valid_profile(env, profile='default'):
    """ Returns True if a schedule profile folder exists for the given
        profile name, False otherwise. 'default' is always resolvable
        to the baseline event_default folder.
    """
    profile = profile or DEFAULT_PROFILE
    return _as_dir(get_schedule_dir(env, profile)).is_dir()


def require_profile(env, profile):
    """ Raises FileNotFoundError when 'profile' has no folder.

        Every file of a profile is optional, so a misspelt profile name
        would otherwise load the default schedule and say nothing.
    """
    if not is_valid_profile(env, profile):
        raise FileNotFoundError(
            "No schedule profile '{0}' in {1}".format(
                profile, env.get('CONFIG_PATH') or "the packaged data"))


def list_profiles(env):
    """ The names of the profiles that have a folder, in no particular
        order: those of the CONFIG_PATH root, or the packaged ones.
    """
    root = _as_dir(env.get('CONFIG_PATH'))
    return [entry.name[len(PROFILE_PREFIX):] for entry in root.iterdir()
            if entry.is_dir() and entry.name.startswith(PROFILE_PREFIX)]


def log_profile_file_warnings(env, profile):
    """ Logs a warning for files in a profile folder that do not match any
        file in the default folder. Such files are never loaded, so they
        are likely misnamed.
    """
    if not profile or profile == DEFAULT_PROFILE:
        return
    profile_dir = _as_dir(get_schedule_dir(env, profile))
    default_dir = _as_dir(get_schedule_dir(env))
    if not profile_dir.is_dir() or not default_dir.is_dir():
        return
    default_names = {entry.name for entry in default_dir.iterdir()}
    for entry in profile_dir.iterdir():
        if entry.name not in default_names:
            log("WARNING profile '{0}': file '{1}' does not match any default "
                "schedule file.".format(profile, entry.name))


def _read_constants(folder, name):
    """ The KEY=VALUE pairs of 'name' in 'folder'; nothing when the folder
        has no such file.
    """
    if not has_data_file(folder, name):
        return {}
    with open_data_file(folder, name) as fd:
        return parse_env(fd.readlines())


def load_constants(cfg_path=None, profile=None, name="constants.dat"):
    """ Reads the schedule constants of a profile, as a dict of strings.

        The constants of the 'default' profile, overlaid per key with those
        of 'profile'. A profile folder without a constants file changes none
        of them. 'cfg_path' is the CONFIG_PATH root; None reads the packaged
        profiles. No .env is read, so this is how a caller that is not the
        bot gets what schedule_controller.ScheduleProfile takes.
    """
    env = {"CONFIG_PATH": cfg_path}
    csts = _read_constants(get_schedule_dir(env), name)
    if profile and profile != DEFAULT_PROFILE:
        require_profile(env, profile)
        csts.update(_read_constants(get_schedule_dir(env, profile), name))
    return csts


def load_csts(env, profile='default'):
    """ Loads the schedule constants overlay for the given profile.
        Constants are read from the 'default' profile folder, then
        overlaid with any constants defined in the active profile.
        Takes an already-parsed env dict (see load_env): CONFIG_PATH
        names the root, CONSTANTS_FILE the file; it is constants.dat
        otherwise.
    """
    return load_constants(env.get('CONFIG_PATH'), profile,
                          env.get('CONSTANTS_FILE', 'constants.dat'))


def load_config(path=None, profile='default'):
    """ Reads the .env file and returns a dict.
        Schedule constants are read from the 'default' profile folder,
        then overlaid with any constants defined in the active profile.
        Returns the environment and constants as a tuple of dicts.
    """
    env = load_env(path)
    csts = load_csts(env, profile)
    return env, csts


MSG_ENV_PATH = ".msg_struct"


def read_msg_struct():
    """ Reads the base message structure config
    """
    path = MSG_ENV_PATH
    try:
        msg_env = load_env(path)
    except Exception as exc:
        #TODO: more error handling
        log("Unable to load {0}. Error: '{1}'".format(path, str(exc)))
        return {}
    #TODO: validate keys in the env
    return msg_env


def write_msg_struct(msg_env):
    lines = []
    for key, value in msg_env.items():
        lines.append("{0}={1}\n".format(key, value))
    with open(MSG_ENV_PATH, "w") as fd:
        fd.writelines(lines)
