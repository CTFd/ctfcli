import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import click
import yaml
from cookiecutter.main import cookiecutter

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
from ctfcli.utils.deploy import DEPLOY_HANDLERS
from ctfcli.utils.spec import CHALLENGE_SPEC_DOCS, blank_challenge_spec
from ctfcli.utils.templates import get_template_dir


class Challenge(object):
    def new(self, type="blank"):
        if type == "blank":
            path = Path(get_base_path())
            path = path / "templates" / type / "default"
            cookiecutter(str(path))
        else:
            # Check if we're referencing an installed template
            template_dir = Path(get_template_dir())
            template_path = template_dir / type

            if template_path.is_dir():  # If we found a template directory, use it
                cookiecutter(str(template_path))
            else:  # If we didn't, use a built in template
                path = Path(get_base_path())
                if os.sep not in type:
                    type += os.sep + "default"
                path = path / "templates" / type
                cookiecutter(str(path))

    def templates(self):
        from ctfcli.cli.templates import Templates

        Templates().list()

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

    def restore(self, challenge=None):
        config = load_config()
        challenges = dict(config["challenges"])
        for folder, url in challenges.items():
            if url.endswith(".git"):
                if challenge is not None and folder != challenge:
                    continue
                click.echo(f"Cloning {url} to {folder}")
                subprocess.call(["git", "clone", "--depth", "1", url, folder])
                shutil.rmtree(str(Path(folder) / ".git"))
            else:
                click.echo(f"Skipping {url} - {folder}")

    def install(self, challenge=None, force=False, ignore=()):
        if challenge is None:
            # Get all challenges if not specifying a challenge
            config = load_config()
            challenges = dict(config["challenges"]).keys()
        else:
            challenges = [challenge]

        if isinstance(ignore, str):
            ignore = (ignore,)

        for challenge in challenges:
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
                        f'Already found existing challenge with same name ({challenge["name"]}). Perhaps you meant sync instead of install?',
                        fg="red",
                    )
                    if force is True:
                        click.secho(
                            "Ignoring existing challenge because of --force",
                            fg="yellow",
                        )
                    else:
                        break
            else:  # If we don't break because of duplicated challenge names
                click.secho(f'Installing {challenge["name"]}', fg="yellow")
                create_challenge(challenge=challenge, ignore=ignore)
                click.secho(f"Success!", fg="green")

    def sync(self, challenge=None, ignore=()):
        if challenge is None:
            # Get all challenges if not specifying a challenge
            config = load_config()
            challenges = dict(config["challenges"]).keys()
        else:
            challenges = [challenge]

        if isinstance(ignore, str):
            ignore = (ignore,)

        for challenge in challenges:
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
                    f'Couldn\'t find existing challenge {c["name"]}. Perhaps you meant install instead of sync?',
                    fg="red",
                )
                continue  # Go to the next challenge in the overall list

            click.secho(f'Syncing {challenge["name"]}', fg="yellow")
            sync_challenge(challenge=challenge, ignore=ignore)
            click.secho(f"Success!", fg="green")

    def update(self, challenge=None):
        config = load_config()
        challenges = dict(config["challenges"])
        for folder, url in challenges.items():
            if challenge and challenge != folder:
                continue
            if url.endswith(".git"):
                click.echo(f"Cloning {url} to {folder}")
                subprocess.call(["git", "init"], cwd=folder)
                subprocess.call(["git", "remote", "add", "origin", url], cwd=folder)
                subprocess.call(["git", "add", "-A"], cwd=folder)
                subprocess.call(
                    ["git", "commit", "-m", "Persist local changes (ctfcli)"],
                    cwd=folder,
                )
                subprocess.call(
                    ["git", "pull", "--allow-unrelated-histories", "origin", "master"],
                    cwd=folder,
                )
                subprocess.call(["git", "mergetool"], cwd=folder)
                subprocess.call(["git", "clean", "-f"], cwd=folder)
                subprocess.call(["git", "commit", "--no-edit"], cwd=folder)
                shutil.rmtree(str(Path(folder) / ".git"))
            else:
                click.echo(f"Skipping {url} - {folder}")

    def finalize(self, challenge=None):
        if challenge is None:
            challenge = os.getcwd()

        path = Path(challenge)
        spec = blank_challenge_spec()
        for k in spec:
            q = CHALLENGE_SPEC_DOCS.get(k)
            fields = q._asdict()

            ask = False
            required = fields.pop("required", False)
            if required is False:
                try:
                    ask = click.confirm(f"Would you like to add the {k} field?")
                    if ask is False:
                        continue
                except click.Abort:
                    click.echo("\n")
                    continue

            if ask is True:
                fields["text"] = "\t" + fields["text"]

            multiple = fields.pop("multiple", False)
            if multiple:
                fields["text"] += " (Ctrl-C to continue)"
                spec[k] = []
                try:
                    while True:
                        r = click.prompt(**fields)
                        spec[k].append(r)
                except click.Abort:
                    click.echo("\n")
            else:
                try:
                    r = click.prompt(**fields)
                    spec[k] = r
                except click.Abort:
                    click.echo("\n")

        with open(path / "challenge.yml", "w+") as f:
            yaml.dump(spec, stream=f, default_flow_style=False, sort_keys=False)

        print("challenge.yml written to", path / "challenge.yml")

    def lint(self, challenge=None):
        if challenge is None:
            challenge = os.getcwd()

        path = Path(challenge)

        if path.name.endswith(".yml") is False:
            path = path / "challenge.yml"

        lint_challenge(path)

    def deploy(self, challenge, host=None):
        if challenge is None:
            challenge = os.getcwd()

        path = Path(challenge)

        if path.name.endswith(".yml") is False:
            path = path / "challenge.yml"

        challenge = load_challenge(path)
        image = challenge.get("image")
        target_host = host or challenge.get("host") or input("Target host URI: ")
        if image is None:
            click.secho(
                "This challenge can't be deployed because it doesn't have an associated image",
                fg="red",
            )
            return
        if bool(target_host) is False:
            click.secho(
                "This challenge can't be deployed because there is no target host to deploy to",
                fg="red",
            )
            return
        url = urlparse(target_host)

        if bool(url.netloc) is False:
            click.secho(
                "Provided host has no URI scheme. Provide a URI scheme like ssh:// or registry://",
                fg="red",
            )
            return

        status, domain, port = DEPLOY_HANDLERS[url.scheme](
            challenge=challenge, host=target_host
        )

        if status:
            click.secho(
                f"Challenge deployed at {domain}:{port}", fg="green",
            )
        else:
            click.secho(
                f"An error occured during deployment", fg="red",
            )
