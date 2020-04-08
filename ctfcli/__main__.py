import configparser
import importlib
import os
import subprocess
import sys
from pathlib import Path

import click

from ctfcli.cli.challenges import Challenge
from ctfcli.cli.config import Config
from ctfcli.cli.plugins import Plugins
from ctfcli.utils.plugins import get_plugin_dir

import fire


class CTFCLI(object):
    def init(self):
        ctf_url = click.prompt("Please enter CTFd instance URL")
        ctf_token = click.prompt("Please enter CTFd Admin Access Token")
        if (
            click.confirm(f"Do you want to continue with {ctf_url} and {ctf_token}")
            is False
        ):
            click.echo("Aborted!")
            return

        if Path(".ctf").exists():
            click.secho(".ctf/ folder already exists. Aborting!", fg="red")
            return

        os.mkdir(".ctf")

        config = configparser.ConfigParser()
        config["config"] = {"url": ctf_url, "access_token": ctf_token}
        config["challenges"] = {}

        with open(".ctf/config", "a+") as f:
            config.write(f)

        subprocess.call(["git", "init"])

    def config(self):
        return COMMANDS.get("config")

    def challenge(self):
        return COMMANDS.get("challenge")

    def plugins(self):
        return COMMANDS.get("plugins")


COMMANDS = {
    "challenge": Challenge(),
    "config": Config(),
    "plugins": Plugins(),
    "cli": CTFCLI(),
}


def main():
    # Load plugins
    plugin_dir = get_plugin_dir()
    sys.path.insert(0, plugin_dir)
    for plugin in sorted(os.listdir(plugin_dir)):
        plugin_path = os.path.join(plugin_dir, plugin, "__init__.py")
        print("Loading", plugin_path, "as", plugin)
        loaded = importlib.import_module(plugin)
        loaded.load(COMMANDS)
    sys.path.remove(plugin_dir)

    # Load CLI
    fire.Fire(CTFCLI)


if __name__ == "__main__":
    main()
