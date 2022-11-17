import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import click
import yaml
from cookiecutter.main import cookiecutter

from ctfcli.utils.challenge import (
    create_challenge,
    lint_challenge,
    load_challenge,
    load_installed_challenge,
    load_installed_challenges,
    sync_challenge,
    verify_challenge,
    pull_challenge
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
from ctfcli.utils.git import get_git_repo_head_branch


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

    def add(self, repo, yaml_path=None):
        config = load_config()

        if repo.endswith(".git"):
            # Get relative path from project root to current directory
            challenge_path = Path(os.path.relpath(os.getcwd(), get_project_path()))

            # Get new directory that will add the git subtree
            base_repo_path = Path(os.path.basename(repo).rsplit(".", maxsplit=1)[0])

            # Join targets
            challenge_path = challenge_path / base_repo_path
            print(challenge_path)

            # If a custom yaml_path is specified we add it to our challenge_key
            if yaml_path:
                challenge_key = str(challenge_path / yaml_path)
            else:
                challenge_key = str(challenge_path)

            config["challenges"][challenge_key] = repo

            head_branch = get_git_repo_head_branch(repo)
            subprocess.call(
                [
                    "git",
                    "subtree",
                    "add",
                    "--prefix",
                    challenge_path,
                    repo,
                    head_branch,
                    "--squash",
                ],
                cwd=get_project_path(),
            )
            with open(get_config_path(), "w+") as f:
                config.write(f)

            subprocess.call(
                ["git", "add", ".ctf/config"], cwd=get_project_path(),
            )
            subprocess.call(
                ["git", "commit", "-m", f"Added {str(challenge_path)}"],
                cwd=get_project_path(),
            )

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
                click.echo(f"Adding git repo {url} to {folder} as subtree")
                head_branch = get_git_repo_head_branch(url)
                subprocess.call(
                    [
                        "git",
                        "subtree",
                        "add",
                        "--prefix",
                        folder,
                        url,
                        head_branch,
                        "--squash",
                    ],
                    cwd=get_project_path(),
                )
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
                    f'Couldn\'t find existing challenge {challenge["name"]}. Perhaps you meant install instead of sync?',
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
                click.echo(f"Pulling latest {url} to {folder}")
                head_branch = get_git_repo_head_branch(url)
                subprocess.call(
                    [
                        "git",
                        "subtree",
                        "pull",
                        "--prefix",
                        folder,
                        url,
                        head_branch,
                        "--squash",
                    ],
                    cwd=get_project_path(),
                )
                subprocess.call(["git", "mergetool"], cwd=folder)
                subprocess.call(["git", "clean", "-f"], cwd=folder)
                subprocess.call(["git", "commit", "--no-edit"], cwd=folder)
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

    def push(self, challenge=None):
        config = load_config()
        challenges = dict(config["challenges"])
        if challenge is None:
            # Get relative path from project root to current directory
            challenge_path = Path(os.path.relpath(os.getcwd(), get_project_path()))
            challenge = str(challenge_path)

        try:
            url = challenges[challenge]
            head_branch = get_git_repo_head_branch(url)
            subprocess.call(
                ["git", "subtree", "push", "--prefix", challenge, url, head_branch],
                cwd=get_project_path(),
            )
        except KeyError:
            click.echo(
                "Couldn't process that challenge path. Please check that the challenge is added to .ctf/config and that your path matches."
            )

    def healthcheck(self, challenge):
        config = load_config()
        challenges = config["challenges"]

        # challenge_path = challenges[challenge]
        path = Path(challenge)
        if path.name.endswith(".yml") is False:
            path = path / "challenge.yml"

        challenge = load_challenge(path)
        click.secho(f'Loaded {challenge["name"]}', fg="yellow")
        try:
            healthcheck = challenge["healthcheck"]
        except KeyError:
            click.secho(f'{challenge["name"]} missing healthcheck parameter', fg="red")
            return

        # Get challenges installed from CTFd and try to find our challenge
        installed_challenges = load_installed_challenges()
        target = None
        for c in installed_challenges:
            if c["name"] == challenge["name"]:
                target = c
                break
        else:
            click.secho(
                f'Couldn\'t find challenge {c["name"]} on CTFd', fg="red",
            )
            return

        # Get the actual challenge data
        installed_challenge = load_installed_challenge(target["id"])
        connection_info = installed_challenge["connection_info"]

        # Run healthcheck
        if connection_info:
            rcode = subprocess.call(
                [healthcheck, "--connection-info", connection_info], cwd=path.parent
            )
        else:
            rcode = subprocess.call([healthcheck], cwd=path.parent)

        if rcode != 0:
            click.secho(
                f"Healcheck failed", fg="red",
            )
            sys.exit(1)
        else:
            click.secho(
                f"Success", fg="green",
            )
            sys.exit(0)

    def verify(self, challenge=None, ignore=(), verify_files=False, verify_defaults=False):
        if isinstance(ignore, str):
            ignore = (ignore,)
        
        if challenge is None:
            # Get all challenges if not specifying a challenge
            config = load_config()
            challenges = dict(config["challenges"]).keys()
        else:
            challenges = [challenge]

        for challenge in challenges:
            path = Path(challenge)

            if path.name.endswith(".yml") is False:
                path = path / "challenge.yml"

            click.secho(f"Found {path}")
            challenge = load_challenge(path)
            click.secho(f'Loaded {challenge["name"]}', fg="yellow")

            click.secho(f'Verifying {challenge["name"]}', fg="yellow")
            verify_challenge(challenge=challenge, ignore=ignore, verify_files=verify_files, verify_defaults=verify_defaults)
            click.secho("Success!", fg="green")
    
    def pull(self, challenge=None, ignore=(), update_files=False, create_files=False, create_defaults=False):
        if isinstance(ignore, str):
            ignore = (ignore,)
        
        if challenge is None:
            # Get all challenges if not specifying a challenge
            config = load_config()
            challenges = dict(config["challenges"]).keys()
        else:
            challenges = [challenge]

        for challenge in challenges:
            path = Path(challenge)

            if path.name.endswith(".yml") is False:
                path = path / "challenge.yml"

            click.secho(f"Found {path}")
            challenge = load_challenge(path)
            click.secho(f'Loaded {challenge["name"]}', fg="yellow")

            click.secho(f'Verifying {challenge["name"]}', fg="yellow")
            pull_challenge(challenge=challenge, ignore=ignore, update_files=update_files, create_files=create_files, create_defaults=create_defaults)
            click.secho("Success!", fg="green")