import configparser
import subprocess

from pathlib import Path

import click
import fire

from ctfcli.cli.challenges import Challenge
from ctfcli.cli.config import Config
from ctfcli.cli.plugins import Plugins
from ctfcli.cli.templates import Templates
from ctfcli.cli.pages import Pages
from ctfcli.utils.plugins import load_plugins
from ctfcli.utils.git import check_if_dir_is_inside_git_repo


class CTFCLI(object):
    def init(self, directory=None, no_config=False, no_git=False):
        # Create our event directory if requested and use it as our base directory
        if directory:
            path = Path(directory)
            path.mkdir()
            click.secho(f"Created empty directory in {path.absolute()}", fg="green")
        else:
            path = Path(".")

        # Get variables from user
        ctf_url = click.prompt(
            "Please enter CTFd instance URL", default="", show_default=False
        )
        ctf_token = click.prompt(
            "Please enter CTFd Admin Access Token", default="", show_default=False
        )
        # Confirm information with user
        if (
            click.confirm(f"Do you want to continue with {ctf_url} and {ctf_token}")
            is False
        ):
            click.echo("Aborted!")
            return

        # Avoid colliding with existing .ctf directory
        if (path / ".ctf").exists():
            click.secho(".ctf/ folder already exists. Aborting!", fg="red")
            return

        # Create .ctf directory
        (path / ".ctf").mkdir()

        # Create initial .ctf/config file
        config = configparser.ConfigParser()
        config["config"] = {"url": ctf_url, "access_token": ctf_token}
        config["challenges"] = {}
        with (path / ".ctf" / "config").open(mode="a+") as f:
            config.write(f)

        # Create a git repo in the event folder
        if check_if_dir_is_inside_git_repo(dir=path.absolute()) is True:
            click.secho("Already in git repo. Skipping git init.", fg="yellow")
        elif no_git is True:
            click.secho("Skipping git init.", fg="yellow")
        else:
            click.secho(f"Creating git repo in {path.absolute()}", fg="green")
            subprocess.call(["git", "init", str(path)])

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
    "challenge": Challenge(),
    "config": Config(),
    "pages": Pages(),
    "plugins": Plugins(),
    "templates": Templates(),
    "cli": CTFCLI(),
}


def main():
    # load plugins
    load_plugins(COMMANDS)

    # Load CLI
    fire.Fire(CTFCLI)


if __name__ == "__main__":
    main()
