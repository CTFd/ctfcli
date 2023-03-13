import configobj
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
    parser = configobj.ConfigObj(path)

    return parser


def preview_config(as_string=False):
    config = load_config()

    preview = json.dumps(config, sort_keys=True, indent=4)

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
        if config["config"].get("ssl_verify"):
            ssl_verify = config["config"].as_bool("ssl_verify")
        else:
            ssl_verify = True
    except ValueError:
        # If we didn't a proper boolean value we should load it as a string
        # https://requests.kennethreitz.org/en/master/user/advanced/#ssl-cert-verification
        ssl_verify = config["config"].get("ssl_verify")

    s = APISession(prefix_url=url)
    s.verify = ssl_verify
    s.headers.update({"Authorization": f"Token {access_token}"})
    s.cookies.update(config["config"].get("cookies", {}))

    return s
