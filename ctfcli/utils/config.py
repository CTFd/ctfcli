import configparser
import json
import os

from ctfcli import __file__ as base_path

from .api import APISession


def get_base_path():
    return os.path.dirname(base_path)


def get_config_path():
    pwd = os.getcwd()
    while pwd:
        config = os.path.join(pwd, ".ctf/config")
        if os.path.isfile(config):
            return config
        new_pwd = os.path.dirname(pwd)
        pwd = None if new_pwd == pwd else new_pwd
    return None


def get_project_path():
    pwd = os.getcwd()
    while pwd:
        config = os.path.join(pwd, ".ctf/config")
        if os.path.isfile(config):
            return pwd
        new_pwd = os.path.dirname(pwd)
        pwd = None if new_pwd == pwd else new_pwd
    return None


def load_config():
    path = get_config_path()
    parser = configparser.ConfigParser()

    # Preserve case in configparser
    parser.optionxform = str

    parser.read(path)
    return parser


def preview_config(as_string=False):
    config = load_config()

    d = {}
    for section in config.sections():
        d[section] = {}
        for k, v in config.items(section):
            d[section][k] = v

    preview = json.dumps(d, sort_keys=True, indent=4)

    if as_string is True:
        return preview
    else:
        print(preview)


def generate_session():
    config = load_config()

    # Load required configuration values
    url = config["config"]["url"]
    access_token = config["config"]["access_token"]

    # Handle SSL verification disabling
    try:
        # Get an ssl_verify config. Default to True if it doesn't exist
        ssl_verify = config["config"].getboolean("ssl_verify", True)
    except ValueError:
        # If we didn't a proper boolean value we should load it as a string
        # https://requests.kennethreitz.org/en/master/user/advanced/#ssl-cert-verification
        ssl_verify = config["config"].get("ssl_verify")

    s = APISession(prefix_url=url)
    s.verify = ssl_verify
    s.headers.update({"Authorization": f"Token {access_token}"})

    # Handle cookies section in config
    if "cookies" in config:
        s.cookies.update(dict(config["cookies"]))

    return s
