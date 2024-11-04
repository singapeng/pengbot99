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


def load_config(path=None):
    """ Reads the .env file and returns a dict.
        If the .env defines a constants file path, load that too.
        Returns both as a tuple of dicts.
    """
    env = load_env(path)

    # load schedule constants from a versioned config file
    if 'CONFIG_PATH' in env and 'CONSTANTS_FILE' in env:
        csts_path = os.path.join(env['CONFIG_PATH'], env['CONSTANTS_FILE'])
        csts = load_env(path=csts_path)
    else:
        csts = None
    return env, csts


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