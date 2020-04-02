import os
import shutil
import subprocess
from cookiecutter.main import cookiecutter
from pathlib import Path

import click

from ctfcli.utils.challenge import (
    create_challenge,
    lint_challenge,
    load_challenge,
    load_installed_challenges,
    sync_challenge,
)
from ctfcli.utils.config import (
    get_base_path,
    get_config_path,
    get_project_path,
    load_config,
)


class Challenge(object):
    def new(self, type):
        path = Path(get_base_path())
        if os.sep not in type:
            type += os.sep + "default"
        path = path / "templates" / type
        cookiecutter(str(path))

    def add(self, repo):
        config = load_config()

        if repo.endswith(".git"):
            # Get relative path from project root to current directory
            challenge_path = Path(os.path.relpath(os.getcwd(), get_project_path()))

            # Get new directory that will exist after clone
            base_repo_path = Path(os.path.basename(repo).rsplit(".", maxsplit=1)[0])

            # Join targets
            challenge_path = challenge_path / base_repo_path
            print(challenge_path)

            config["challenges"][str(challenge_path)] = repo

            with open(get_config_path(), "w+") as f:
                config.write(f)

            subprocess.call(["git", "clone", "--depth", "1", repo])
            shutil.rmtree(str(base_repo_path / ".git"))
        elif Path(repo).exists():
            config["challenges"][repo] = repo
            with open(get_config_path(), "w+") as f:
                config.write(f)
        else:
            click.secho(
                "Couldn't process that challenge path. Please check it for errors.",
                fg="red",
            )

    def restore(self):
        config = load_config()
        challenges = dict(config["challenges"])
        for folder, url in challenges.items():
            if url.endswith(".git"):
                click.echo(f"Cloning {url} to {folder}")
                subprocess.call(["git", "clone", "--depth", "1", url, folder])
                shutil.rmtree(str(Path(folder) / ".git"))
            else:
                click.echo(f"Skipping {url} - {folder}")

    def install(self, challenge=None, force=False):
        if challenge is None:
            challenge = os.getcwd()

        path = Path(challenge)

        if path.name.endswith(".yml") is False:
            path = path / "challenge.yml"

        click.secho(f"Found {path}")
        challenge = load_challenge(path)
        click.secho(f'Loaded {challenge["name"]}', fg="yellow")

        installed_challenges = load_installed_challenges()
        for c in installed_challenges:
            if c["name"] == challenge["name"]:
                click.secho(
                    "Already found existing challenge with same name. Perhaps you meant sync instead of install?",
                    fg="red",
                )
                if force is True:
                    click.secho(
                        "Ignoring existing challenge because of --force", fg="yellow"
                    )
                else:
                    return

        click.secho(f'Installing {challenge["name"]}', fg="yellow")
        create_challenge(challenge=challenge)
        click.secho(f"Success!", fg="green")

    def sync(self, challenge=None):
        if challenge is None:
            challenge = os.getcwd()

        path = Path(challenge)

        if path.name.endswith(".yml") is False:
            path = path / "challenge.yml"

        click.secho(f"Found {path}")
        challenge = load_challenge(path)
        click.secho(f'Loaded {challenge["name"]}', fg="yellow")

        installed_challenges = load_installed_challenges()
        for c in installed_challenges:
            if c["name"] == challenge["name"]:
                break
        else:
            click.secho(
                "Couldn't find existing challenge. Perhaps you meant install instead of sync?",
                fg="red",
            )

        click.secho(f'Syncing {challenge["name"]}', fg="yellow")
        sync_challenge(challenge=challenge)
        click.secho(f"Success!", fg="green")

    def lint(self, challenge=None):
        if challenge is None:
            challenge = os.getcwd()

        path = Path(challenge)

        if path.name.endswith(".yml") is False:
            path = path / "challenge.yml"

        lint_challenge(path)
