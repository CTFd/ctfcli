import logging
import shutil
import subprocess
from pathlib import Path

import click

from ctfcli.core.config import Config

log = logging.getLogger("ctfcli.cli.plugins")


class PluginsCommand:
    @staticmethod
    def install(plugin_url: str) -> int:
        log.debug(f"install: {plugin_url}")

        plugins_path = Config.get_plugins_path()
        if not plugin_url.endswith(".git"):
            click.secho(
                "Can only install plugins from git repositories - " f"{plugin_url} does not end with .git",
                fg="red",
            )
            return 1

        installed_plugin_path = plugins_path / Path(plugin_url).stem
        log.debug(f"call(['git', 'clone', '{plugin_url}', '{installed_plugin_path}'])")
        git_clone = subprocess.call(["git", "clone", plugin_url, installed_plugin_path])

        if git_clone != 0:
            click.secho(
                "Failed to clone the plugin repository. Please check git output above.",
                fg="red",
            )
            return 1

        requirements_path = installed_plugin_path / "requirements.txt"
        if requirements_path.exists():
            pip = shutil.which("pip")
            pip3 = shutil.which("pip3")

            if pip is None and pip3 is None:
                click.secho("Neither pip nor pip3 was found, is it in the PATH?", fg="red")
                return 1

            if pip is None:
                pip = pip3

            log.debug(f"call(['{pip}', 'install', '-r', '{requirements_path}'])")
            pip_install = subprocess.call([pip, "install", "-r", requirements_path])

            if pip_install != 0:
                click.secho(
                    "Failed to install plugin requirements. Please check pip output above.",
                    fg="red",
                )
                return 1

        return 0

    @staticmethod
    def uninstall(plugin_name: str) -> int:
        log.debug(f"uninstall: {plugin_name}")

        plugins_path = Config.get_plugins_path()
        plugin_path = plugins_path / plugin_name

        if not plugin_path.exists():
            click.secho(f"Could not find plugin {plugin_name} in {plugins_path}", fg="red")
            return 1

        shutil.rmtree(plugin_path)
        return 0

    @staticmethod
    def list() -> int:
        log.debug("list")

        installed_plugins = sorted(Config.get_plugins_path().iterdir())
        if len(installed_plugins) == 0:
            click.secho("Found no installed plugins", fg="blue")
            return 0

        click.secho("List of installed plugins:", fg="blue")
        for plugin in installed_plugins:
            click.echo(f" - {plugin}")

        return 0

    @staticmethod
    def dir() -> int:
        log.debug("dir")
        return PluginsCommand.path()

    @staticmethod
    def path() -> int:
        log.debug("path")
        click.echo(Config.get_plugins_path())
        return 0
