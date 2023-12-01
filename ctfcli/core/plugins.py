import importlib
import logging
import sys
from typing import Dict

from ctfcli.core.config import Config

log = logging.getLogger("ctfcli.core.plugins")


def load_plugins(commands: Dict):
    plugins_path = Config.get_plugins_path()
    sys.path.insert(0, str(plugins_path.absolute()))

    for plugin in sorted(plugins_path.iterdir()):
        if plugin.name.startswith("_") or plugin.name.startswith("."):
            continue

        plugin_path = plugins_path / plugin / "__init__.py"

        log.debug(f"Loading plugin '{plugin}' from '{plugin_path}'")

        loaded = importlib.import_module(plugin.stem)
        loaded.load(commands)

    sys.path.remove(str(plugins_path.absolute()))
