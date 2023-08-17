import logging
import os
import subprocess

import click
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import IniLexer, JsonLexer

from ctfcli.core.config import Config

log = logging.getLogger("ctfcli.cli.config")


class ConfigCommand:
    def edit(self):
        log.debug("edit")
        editor = os.getenv("EDITOR", "vi")

        log.debug(f"call(['{editor}', '{Config.get_config_path()}'])")
        subprocess.call([editor, Config.get_config_path()])

    def path(self):
        log.debug("path")
        click.echo(Config.get_config_path())

    def show(self, color=True, json=False):
        # alias for the view command
        log.debug(f"show (color={color}, json={json})")
        self.view(color=color, json=json)

    def view(self, color=True, json=False):
        log.debug(f"view (color={color}, json={json})")
        config = Config()

        if json:
            config_json = config.as_json(pretty=True)

            if color:
                return click.echo(highlight(config_json, JsonLexer(), TerminalFormatter()))

            return click.echo(config_json)

        with open(config.get_config_path(), "r") as config_file:
            config_ini = config_file.read()

            if color:
                return click.echo(highlight(config_ini, IniLexer(), TerminalFormatter()))

            return click.echo(config_ini)
