import appdirs
import importlib
import logging
import os
import sys
from pathlib import Path

from ctfcli import __name__ as pkg_name


def load_plugins(commands: dict):
    plugin_dir = get_plugin_dir()
    sys.path.insert(0, plugin_dir)

    for plugin in sorted(os.listdir(plugin_dir)):
        plugin_path = Path(plugin_dir) / plugin / "__init__.py"

        logging.debug(f"Loading {plugin_path} as {plugin}")

        loaded = importlib.import_module(plugin)
        loaded.load(commands)

    sys.path.remove(str(plugin_dir))


def get_plugin_dir():
    if os.getenv("CTFCLI_PLUGIN_DIR"):
        plugins_path = get_custom_plugin_dir()
    else:
        plugins_path = get_data_dir() / "plugins"

    if not plugins_path.exists():
        os.makedirs(plugins_path)

    return str(plugins_path.absolute())


def get_custom_plugin_dir() -> Path:
    custom_plugins_path = Path(os.getenv("CTFCLI_PLUGIN_DIR"))

    if custom_plugins_path.is_absolute():
        return custom_plugins_path

    base_dir = Path().parent.parent
    return base_dir / custom_plugins_path


def get_data_dir():
    return Path(appdirs.user_data_dir(appname=pkg_name))
