import os

import appdirs

from ctfcli import __name__ as pkg_name


def get_plugin_dir():
    plugins_path = os.path.join(get_data_dir(), "plugins")
    if not os.path.exists(plugins_path):
        os.makedirs(plugins_path)
    return os.path.join(plugins_path)


def get_data_dir():
    return appdirs.user_data_dir(appname=pkg_name)
