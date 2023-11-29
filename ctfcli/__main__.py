import configparser
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union

import click
import fire

from ctfcli.cli.challenges import ChallengeCommand
from ctfcli.cli.config import ConfigCommand
from ctfcli.cli.pages import PagesCommand
from ctfcli.cli.plugins import PluginsCommand
from ctfcli.cli.templates import TemplatesCommand
from ctfcli.core.exceptions import ProjectNotInitialized
from ctfcli.core.plugins import load_plugins
from ctfcli.utils.git import check_if_dir_is_inside_git_repo

# Init logging
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())

log = logging.getLogger("ctfcli.main")


class CTFCLI:
    @staticmethod
    def init(
        directory: Optional[Union[str, os.PathLike]] = None,
        no_git: bool = False,
        no_commit: bool = False,
    ):
        log.debug(f"init: (directory={directory}, no_git={no_git}, no_commit={no_commit})")
        project_path = Path.cwd()

        # Create our project directory if requested
        if directory:
            project_path = Path(directory)

            if not project_path.exists():
                project_path.mkdir(parents=True)
                click.secho(f"Created empty directory in {project_path.absolute()}", fg="green")

        # Avoid colliding with existing .ctf directory
        if (project_path / ".ctf").exists():
            click.secho(".ctf/ folder already exists. Aborting!", fg="red")
            return

        log.debug(f"project_path: {project_path}")

        # Create .ctf directory
        (project_path / ".ctf").mkdir()

        # Get variables from user
        ctf_url = click.prompt("Please enter CTFd instance URL", default="", show_default=False)

        ctf_token = click.prompt("Please enter CTFd Admin Access Token", default="", show_default=False)

        # Confirm information with user
        if not click.confirm(f"Do you want to continue with {ctf_url} and {ctf_token}", default=True):
            click.echo("Aborted!")
            return

        # Create initial .ctf/config file
        config = configparser.ConfigParser()
        config["config"] = {"url": ctf_url, "access_token": ctf_token}
        config["challenges"] = {}
        with (project_path / ".ctf" / "config").open(mode="a+") as config_file:
            config.write(config_file)

        # if git init is to be skipped we can return
        if no_git:
            click.secho("Skipping git init.", fg="yellow")
            return

        # also skip git init if git is already initialized
        if check_if_dir_is_inside_git_repo(cwd=project_path):
            click.secho("Already in a git repo. Skipping git init.", fg="yellow")

            # is git commit is to be skipped we can return
            if no_commit:
                click.secho("Skipping git commit.", fg="yellow")
                return

            subprocess.call(["git", "add", ".ctf/config"], cwd=project_path)
            subprocess.call(["git", "commit", "-m", "init ctfcli project"], cwd=project_path)
            return

        # Create a git repo in the project folder
        click.secho(f"Creating a git repo in {project_path}", fg="green")
        subprocess.call(["git", "init", str(project_path)])

        if no_commit:
            click.secho("Skipping git commit.", fg="yellow")
            return

        subprocess.call(["git", "add", ".ctf/config"], cwd=project_path)
        subprocess.call(["git", "commit", "-m", "init ctfcli project"], cwd=project_path)

    def config(self):
        return COMMANDS.get("config")

    def challenge(self):
        return COMMANDS.get("challenge")

    def pages(self):
        return COMMANDS.get("pages")

    def plugins(self):
        return COMMANDS.get("plugins")

    def templates(self):
        return COMMANDS.get("templates")


COMMANDS = {
    "challenge": ChallengeCommand(),
    "config": ConfigCommand(),
    "pages": PagesCommand(),
    "plugins": PluginsCommand(),
    "templates": TemplatesCommand(),
    "cli": CTFCLI(),
}


def main():
    # Load plugins
    load_plugins(COMMANDS)

    # Load CLI
    try:
        # if the command returns an int, then we serialize it as none to prevent fire from printing it
        # (this does not change the actual return value, so it's still good to use as an exit code)
        # everything else is returned as is, so fire can print help messages
        ret = fire.Fire(COMMANDS["cli"], serialize=lambda r: None if isinstance(r, int) else r)

        if isinstance(ret, int):
            sys.exit(ret)

    except ProjectNotInitialized:
        if click.confirm(
            "Outside of a ctfcli project, would you like to start a new project in this directory?",
            default=False,
        ):
            CTFCLI.init()
    except KeyboardInterrupt:
        click.secho("\n[Ctrl-C] Aborting.", fg="red")
        sys.exit(2)


if __name__ == "__main__":
    main()
