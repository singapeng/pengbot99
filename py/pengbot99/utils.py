from datetime import datetime

import os


def load_env(path=None):
    """ Reads the .env file and returns a dict
    """
    path = path or ".env"
    env = {}
    with open(path) as fd:
        lines = fd.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith('#'):
            # ignore comments
            continue
        var_name, var_value = line.split('=', 1)
        env[var_name] = var_value
    return env


def get_schedule_dir(env, profile=None):
    """ Returns the folder holding schedule config files for the given
        profile. Defaults to 'default'.
        Profile folders live as subfolders of the CONFIG_PATH root.
    """
    profile = profile or 'default'
    return os.path.join(env['CONFIG_PATH'], profile)


def log_profile_csv_warnings(env, profile):
    """ Logs a warning for CSV files in a profile folder that do not
        match any file in the default folder. Such files would only be
        loaded if a caller knew their name, so they are likely unused.
    """
    if not profile or profile == 'default':
        return
    profile_dir = get_schedule_dir(env, profile)
    default_dir = get_schedule_dir(env, 'default')
    if not os.path.isdir(profile_dir) or not os.path.isdir(default_dir):
        return
    default_names = {name for name in os.listdir(default_dir) if name.endswith('.csv')}
    for name in os.listdir(profile_dir):
        if name.endswith('.csv') and name not in default_names:
            log("WARNING profile '{0}': file '{1}' does not match any default "
                "schedule file.".format(profile, name))


def _sideload_data(env, data_name, base_path):
    if base_path and data_name in env:
        cfg_path = os.path.join(base_path, env[data_name])
        values = load_env(path=cfg_path)
    else:
        values = None
    return values


def load_config(path=None, profile='default'):
    """ Reads the .env file and returns a dict.
        If the .env defines a constants file path, load that too.
        Schedule constants are read from the 'default' profile folder,
        then overlaid with any constants defined in the active profile.
        Returns both as a tuple of dicts.
    """
    env = load_env(path)

    # schedule constants are versioned and live under the schedule
    # profile folders of the CONFIG_PATH root
    csts = _sideload_data(env, 'CONSTANTS_FILE', get_schedule_dir(env, 'default')) or {}
    if profile != 'default':
        overlay = _sideload_data(env, 'CONSTANTS_FILE', get_schedule_dir(env, profile))
        if overlay:
            csts.update(overlay)
    # explainer data is not part of the schedule profile structure
    # and loads directly from the CONFIG_PATH root
    xpln = _sideload_data(env, 'EXPLAIN_FILE', env.get('CONFIG_PATH'))
    return env, csts, xpln


def log(text):
    """ Log to stdout with timestamp.
    TODO: replace with logging
    """
    stamp = datetime.now()
    ymd = "%04d-%02d-%02d" % (stamp.year, stamp.month, stamp.day)
    hms = "%02d:%02d:%02d" % (stamp.hour, stamp.minute, stamp.second)
    print("{0} {1} {2}".format(ymd, hms, text))


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