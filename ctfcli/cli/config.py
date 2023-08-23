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
    def edit(self) -> int:
        log.debug("edit")
        editor = os.getenv("EDITOR", "vi")

        log.debug(f"call(['{editor}', '{Config.get_config_path()}'])")
        subprocess.call([editor, Config.get_config_path()])
        return 0

    def path(self) -> int:
        log.debug("path")
        click.echo(Config.get_config_path())
        return 0

    def show(self, color=True, json=False) -> int:
        # alias for the view command
        log.debug(f"show (color={color}, json={json})")
        return self.view(color=color, json=json)

    def view(self, color=True, json=False) -> int:
        log.debug(f"view (color={color}, json={json})")
        config = Config()

        if json:
            config_json = config.as_json(pretty=True)

            if color:
                click.echo(highlight(config_json, JsonLexer(), TerminalFormatter()))
                return 0

            click.echo(config_json)
            return 0

        with open(config.get_config_path(), "r") as config_file:
            config_ini = config_file.read()

            if color:
                click.echo(highlight(config_ini, IniLexer(), TerminalFormatter()))
                return 0

            click.echo(config_ini)
            return 0
