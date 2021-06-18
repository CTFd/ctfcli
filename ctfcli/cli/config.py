import os
import subprocess

import click
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import IniLexer, JsonLexer

from ctfcli.utils.config import get_config_path, preview_config


class Config(object):
    def edit(self):
        editor = os.getenv("EDITOR", "vi")
        command = editor, get_config_path()
        subprocess.call(command)

    def path(self):
        click.echo(get_config_path())

    def view(self, color=True, json=False):
        config = get_config_path()
        with open(config) as f:
            if json is True:
                config = preview_config(as_string=True)
                if color:
                    config = highlight(config, JsonLexer(), TerminalFormatter())
            else:
                config = f.read()
                if color:
                    config = highlight(config, IniLexer(), TerminalFormatter())

            print(config)
