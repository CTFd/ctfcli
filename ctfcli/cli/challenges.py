import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Union
from urllib.parse import urlparse

import click
from cookiecutter.main import cookiecutter
from pygments import highlight
from pygments.formatters.terminal import TerminalFormatter
from pygments.lexers.data import YamlLexer

from ctfcli.core.challenge import Challenge
from ctfcli.core.config import Config
from ctfcli.core.deployment import get_deployment_handler
from ctfcli.core.exceptions import ChallengeException, LintException
from ctfcli.utils.git import get_git_repo_head_branch

log = logging.getLogger("ctfcli.cli.challenges")


class ChallengeCommand:
    def new(self, type: str = "blank") -> int:
        log.debug(f"new: (type={type})")

        # If the type is blank, use the built-in default template
        if type == "blank":
            template_path = Config.get_base_path() / "templates" / type / "default"
            log.debug(f"template_path: {template_path}")
            cookiecutter(str(template_path))
            return 0

        # If the type is not the default 'blank' - check if it's installed
        template_path = Config.get_templates_path() / type
        if template_path.is_dir():  # If we found a template directory, use it
            log.debug(f"template_path: {template_path}")
            cookiecutter(str(template_path))
            return 0

        # If it's not installed, check if it's built-in
        # Without a specified variant
        if os.sep not in type:
            template_path = Config.get_base_path() / "templates" / type / "default"
            log.debug(f"template_path: {template_path}")
            cookiecutter(str(template_path))
            return 0

        # With a specified variant
        template_path = Config.get_base_path() / "templates" / type
        if template_path.is_dir():
            log.debug(f"template_path: {template_path}")
            cookiecutter(str(template_path))
            return 0

        click.secho(
            f"Could not locate template '{type}' in either installed or built-in templates",
            fg="red",
        )
        return 1

    def edit(self, challenge: str, dockerfile: bool = False) -> int:
        log.debug(f"edit: {challenge} (dockerfile={dockerfile})")

        challenge_instance = self._resolve_single_challenge(challenge)
        if not challenge_instance:
            return 1

        edited_file_path = challenge_instance.challenge_file_path
        if dockerfile:
            dockerfile_path = challenge_instance.challenge_directory / challenge_instance.get("image", ".")

            if not str(dockerfile_path).endswith("Dockerfile"):
                dockerfile_path = dockerfile_path / "Dockerfile"

            if not dockerfile_path.exists():
                click.secho(
                    f"Could not open Dockerfile for editing, because it could not be found at: {dockerfile_path}",
                    fg="red",
                )
                return 1

            edited_file_path = dockerfile_path

        editor = os.getenv("EDITOR", "vi")
        log.debug(f"call(['{editor}', '{edited_file_path}'])")
        subprocess.call([editor, edited_file_path])
        return 0

    def show(self, challenge: str, color=True) -> int:
        log.debug(f"show: {challenge} (color={color})")
        return self.view(challenge, color=color)

    def view(self, challenge: str, color=True) -> int:
        log.debug(f"view: {challenge} (color={color})")

        challenge_instance = self._resolve_single_challenge(challenge)
        if not challenge_instance:
            return 1

        with open(challenge_instance.challenge_file_path, "r") as challenge_yml_file:
            challenge_yml = challenge_yml_file.read()

            if color:
                click.echo(highlight(challenge_yml, YamlLexer(), TerminalFormatter()))
                return 0

            click.echo(challenge_yml)
            return 0

    def templates(self) -> int:
        log.debug("templates")
        from ctfcli.cli.templates import TemplatesCommand

        return TemplatesCommand.list()

    def add(self, repo: str, directory: str = None, yaml_path: str = None) -> int:
        log.debug(f"add: {repo} (directory={directory}, yaml_path={yaml_path})")
        config = Config()

        # check if we're working with a remote challenge which has to be pulled first
        if repo.endswith(".git"):
            # Get a relative path from project root to current directory
            project_path = config.project_path
            project_relative_cwd = Path.cwd().relative_to(project_path)

            # Get a new directory that will add the git subtree
            repository_basename = Path(repo).stem

            # Use the custom subdirectory for the challenge if one was provided
            repository_path = repository_basename
            if directory:
                custom_directory_path = Path(directory)
                repository_path = custom_directory_path / repository_basename

            # Join targets
            challenge_path = project_relative_cwd / repository_path

            # If a custom yaml_path is specified, we add it to our challenge_key
            challenge_key = challenge_path
            if yaml_path:
                challenge_key = challenge_key / yaml_path

            # Add a new challenge to the config
            config["challenges"][str(challenge_key)] = repo
            head_branch = get_git_repo_head_branch(repo)

            log.debug(
                f"call(['git', 'subtree', 'add', '--prefix', '{challenge_path}', "
                f"'{repo}', '{head_branch}', '--squash'], cwd='{project_path}')"
            )
            git_subtree_add = subprocess.call(
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
                cwd=project_path,
            )

            if git_subtree_add != 0:
                click.secho(
                    "Could not add the challenge subtree. " "Please check git error messages above.",
                    fg="red",
                )
                return 1

            with open(config.config_path, "w+") as config_file:
                config.write(config_file)

            log.debug(f"call(['git', 'add', '.ctf/config'], cwd='{project_path}')")
            git_add = subprocess.call(["git", "add", ".ctf/config"], cwd=project_path)

            log.debug(f"call(['git', 'commit', '-m', 'Added {challenge_path}'], cwd='{project_path}')")
            git_commit = subprocess.call(["git", "commit", "-m", f"Added {challenge_path}"], cwd=project_path)

            if any(r != 0 for r in [git_add, git_commit]):
                click.secho(
                    "Could not commit the challenge subtree. " "Please check git error messages above.",
                    fg="red",
                )
                return 1

            return 0

        # otherwise - we're working with a folder path
        if Path(repo).exists():
            config["challenges"][repo] = repo
            with open(config.config_path, "w+") as f:
                config.write(f)

            return 0

        click.secho(f"Could not process the challenge path: '{repo}'", fg="red")
        return 1

    def push(self, challenge: str = None) -> int:
        log.debug(f"push: (challenge={challenge})")
        config = Config()

        challenge_path = Path.cwd()
        if challenge:
            challenge_path = config.project_path / Path(challenge)

        # Get a relative path from project root to the challenge
        # As this is what git subtree push requires
        challenge_path = challenge_path.relative_to(config.project_path)
        challenge_repo = config.challenges.get(str(challenge_path), None)

        # if we don't find the challenge by the directory,
        # check if it's saved with a direct path to challenge.yml
        if not challenge_repo:
            challenge_repo = config.challenges.get(str(challenge_path / "challenge.yml"), None)

        if not challenge_repo:
            click.secho(
                f"Could not find added challenge '{challenge_path}' "
                "Please check that the challenge is added to .ctf/config and that your path matches",
                fg="red",
            )
            return 1

        if not challenge_repo.endswith(".git"):
            click.secho(
                f"Cannot push challenge '{challenge_path}', as it's not a git-based challenge",
                fg="yellow",
            )
            return 1

        head_branch = get_git_repo_head_branch(challenge_repo)

        log.debug(f"call(['git', 'add', '.'], cwd='{config.project_path / challenge_path}')")
        git_add = subprocess.call(["git", "add", "."], cwd=config.project_path / challenge_path)

        log.debug(
            f"call(['git', 'commit', '-m', 'Pushing changes to {challenge_path}'], "
            f"cwd='{config.project_path / challenge_path}')"
        )
        git_commit = subprocess.call(
            ["git", "commit", "-m", f"Pushing changes to {challenge_path}"],
            cwd=config.project_path / challenge_path,
        )

        if any(r != 0 for r in [git_add, git_commit]):
            click.secho(
                "Could not commit the challenge changes. " "Please check git error messages above.",
                fg="red",
            )
            return 1

        log.debug(
            f"call(['git', 'subtree', 'push', '--prefix', '{challenge_path}', '{challenge_repo}', '{head_branch}'], "
            f"cwd='{config.project_path / challenge_path}')"
        )
        git_subtree_push = subprocess.call(
            [
                "git",
                "subtree",
                "push",
                "--prefix",
                challenge_path,
                challenge_repo,
                head_branch,
            ],
            cwd=config.project_path,
        )

        if git_subtree_push != 0:
            click.secho(
                "Could not push the challenge subtree. " "Please check git error messages above.",
                fg="red",
            )
            return 1

        return 0

    def pull(self, challenge: str = None) -> int:
        log.debug(f"pull: (challenge={challenge})")
        config = Config()

        challenge_path = Path.cwd()
        if challenge:
            challenge_path = config.project_path / Path(challenge)

        # Get a relative path from project root to the challenge
        # As this is what git subtree push requires
        challenge_path = challenge_path.relative_to(config.project_path)
        challenge_repo = config.challenges.get(str(challenge_path), None)

        # if we don't find the challenge by the directory,
        # check if it's saved with a direct path to challenge.yml
        if not challenge_repo:
            challenge_repo = config.challenges.get(str(challenge_path / "challenge.yml"), None)

        if not challenge_repo:
            click.secho(
                f"Could not find added challenge '{challenge_path}' "
                "Please check that the challenge is added to .ctf/config and that your path matches",
                fg="red",
            )
            return 1

        if not challenge_repo.endswith(".git"):
            click.secho(
                f"Cannot pull challenge '{challenge_path}', as it's not a git-based challenge",
                fg="yellow",
            )
            return 1

        click.secho(f"Pulling latest '{challenge_repo}' to '{challenge_path}'", fg="blue")
        head_branch = get_git_repo_head_branch(challenge_repo)

        log.debug(
            f"call(['git', 'subtree', 'pull', '--prefix', '{challenge_path}', "
            f"'{challenge_repo}', '{head_branch}', '--squash'], cwd='{config.project_path}')"
        )
        git_subtree_pull = subprocess.call(
            [
                "git",
                "subtree",
                "pull",
                "--prefix",
                challenge_path,
                challenge_repo,
                head_branch,
                "--squash",
            ],
            cwd=config.project_path,
        )

        if git_subtree_pull != 0:
            click.secho(
                f"Could not pull the subtree for challenge '{challenge_path}'. "
                "Please check git error messages above.",
                fg="red",
            )
            return 1

        log.debug(f"call(['git', 'mergetool'], cwd='{config.project_path / challenge_path}')")
        git_mergetool = subprocess.call(["git", "mergetool"], cwd=config.project_path / challenge_path)

        log.debug(f"call(['git', 'clean', '-f'], cwd='{config.project_path / challenge_path}')")
        git_clean = subprocess.call(["git", "clean", "-f"], cwd=config.project_path / challenge_path)

        log.debug(f"call(['git', 'commit', '--no-edit'], cwd='{config.project_path / challenge_path}')")
        subprocess.call(["git", "commit", "--no-edit"], cwd=config.project_path / challenge_path)

        # git commit is allowed to return a non-zero code because it would also mean that there's nothing to commit
        if any(r != 0 for r in [git_mergetool, git_clean]):
            click.secho(
                f"Could not commit the subtree for challenge '{challenge_path}'. "
                "Please check git error messages above.",
                fg="red",
            )
            return 1

        return 0

    def restore(self, challenge: str = None) -> int:
        log.debug(f"restore: (challenge={challenge})")
        config = Config()

        if len(config.challenges.items()) == 0:
            click.secho("Could not find any added challenges to restore", fg="yellow")
            return 1

        failed_restores = []
        for challenge_key, challenge_source in config.challenges.items():
            if challenge is not None and challenge_key != challenge:
                continue

            if not challenge_source.endswith(".git"):
                click.secho(
                    f"Skipping restore of '{challenge_key}', as it's not a git-based challenge",
                    fg="yellow",
                )
                continue

            # Check if we have a target directory, or the challenge is saved as a reference to challenge.yml.
            # We cannot restore this, as we don't know the root of the challenge to pull the subtree
            if challenge_key.endswith(".yml"):
                click.secho(
                    f"Skipping restore of '{challenge_key}', as it was added with a custom yaml_path. "
                    "Please restore this challenge again manually",
                    fg="yellow",
                )
                failed_restores.append(challenge_key)
                continue

            # Check if target directory exits
            if (config.project_path / challenge_key).exists():
                click.secho(
                    f"Skipping restore of '{challenge_key}', as the target directory exists. "
                    "Please remove this directory and retry restore.",
                    fg="yellow",
                )
                failed_restores.append(challenge_key)
                continue

            click.secho(
                f"Restoring git repo '{challenge_source}' to '{challenge_key}'",
                fg="blue",
            )
            head_branch = get_git_repo_head_branch(challenge_source)

            log.debug(
                f"call(['git', 'subtree', 'add', '--prefix', '{challenge_key}', '{challenge_source}', "
                f"'{head_branch}', '--squash'], cwd='{config.project_path}')"
            )
            git_subtree_add = subprocess.call(
                [
                    "git",
                    "subtree",
                    "add",
                    "--prefix",
                    challenge_key,
                    challenge_source,
                    head_branch,
                    "--squash",
                ],
                cwd=config.project_path,
            )

            if git_subtree_add != 0:
                click.secho(
                    f"Could not restore the subtree for challenge '{challenge_key}'. "
                    "Please check git error messages above.",
                    fg="red",
                )
                failed_restores.append(challenge_key)

        if len(failed_restores) == 0:
            click.secho("Success! All challenges restored!", fg="green")
            return 0

        click.secho("Restore failed for:", fg="red")
        for challenge in failed_restores:
            click.echo(f" - {challenge}")

        return 1

    def install(
        self, challenge: str = None, force: bool = False, hidden: bool = False, ignore: Union[str, Tuple[str]] = ()
    ) -> int:
        log.debug(f"install: (challenge={challenge}, force={force}, hidden={hidden}, ignore={ignore})")

        if challenge:
            challenge_instance = self._resolve_single_challenge(challenge)
            if not challenge_instance:
                return 1

            local_challenges = [challenge_instance]
        else:
            local_challenges = self._resolve_all_challenges()

        if isinstance(ignore, str):
            ignore = (ignore,)

        config = Config()
        remote_challenges = Challenge.load_installed_challenges()

        failed_installs = []
        with click.progressbar(local_challenges, label="Installing challenges") as challenges:
            for challenge_instance in challenges:
                click.echo()

                if hidden:
                    challenge_instance["state"] = "hidden"

                click.secho(
                    f"Installing '{challenge_instance}' ("
                    f"{challenge_instance.challenge_file_path.relative_to(config.project_path)}"
                    f") ...",
                    fg="blue",
                )

                found_duplicate = False
                for remote_challenge in remote_challenges:
                    if remote_challenge["name"] == challenge_instance["name"]:
                        click.secho(
                            f"Found already existing challenge with the same name ({remote_challenge['name']}). "
                            "Perhaps you meant sync instead of install?",
                            fg="red",
                        )
                        found_duplicate = True
                        break

                if found_duplicate:
                    if not force:
                        failed_installs.append(challenge_instance)
                        continue

                    click.secho("Syncing existing challenge instead (because of --force)", fg="yellow")
                    try:
                        challenge_instance.sync(ignore=ignore)
                    except ChallengeException as e:
                        click.secho("Failed to sync challenge", fg="red")
                        click.secho(str(e), fg="red")
                        failed_installs.append(challenge_instance)

                    continue

                # If we don't break because of duplicated challenge names - continue the installation
                try:
                    challenge_instance.create(ignore=ignore)
                except ChallengeException as e:
                    click.secho("Failed to install challenge", fg="red")
                    click.secho(str(e), fg="red")
                    failed_installs.append(challenge_instance)

        if len(failed_installs) == 0:
            click.secho("Success! All challenges installed!", fg="green")
            return 0

        click.secho("Install failed for:", fg="red")
        for challenge_instance in failed_installs:
            click.echo(f" - {challenge_instance}")

        return 1

    def sync(self, challenge: str = None, ignore: Union[str, Tuple[str]] = ()) -> int:
        log.debug(f"sync: (challenge={challenge}, ignore={ignore})")

        if challenge:
            challenge_instance = self._resolve_single_challenge(challenge)
            if not challenge_instance:
                return 1

            local_challenges = [challenge_instance]
        else:
            local_challenges = self._resolve_all_challenges()

        if isinstance(ignore, str):
            ignore = (ignore,)

        config = Config()
        remote_challenges = Challenge.load_installed_challenges()

        failed_syncs = []
        with click.progressbar(local_challenges, label="Syncing challenges") as challenges:
            for challenge_instance in challenges:
                click.echo()

                challenge_name = challenge_instance["name"]
                if not any(c["name"] == challenge_name for c in remote_challenges):
                    click.secho(
                        f"Could not find existing challenge {challenge_name}. "
                        f"Perhaps you meant install instead of sync?",
                        fg="red",
                    )
                    failed_syncs.append(challenge_instance)
                    continue

                click.secho(
                    f"Syncing '{challenge_name}' ("
                    f"{challenge_instance.challenge_file_path.relative_to(config.project_path)}"
                    f") ...",
                    fg="blue",
                )
                try:
                    challenge_instance.sync(ignore=ignore)
                except ChallengeException as e:
                    click.secho("Failed to sync challenge", fg="red")
                    click.secho(str(e), fg="red")
                    failed_syncs.append(challenge_instance)

        if len(failed_syncs) == 0:
            click.secho("Success! All challenges synced!", fg="green")
            return 0

        click.secho("Sync failed for:", fg="red")
        for challenge in failed_syncs:
            click.echo(f" - {challenge}")

        return 1

    def deploy(
        self,
        challenge: str = None,
        host: str = None,
        skip_login: bool = False,
    ) -> int:
        log.debug(f"deploy: (challenge={challenge}, host={host}, skip_login={skip_login})")

        if challenge:
            challenge_instance = self._resolve_single_challenge(challenge)
            if not challenge_instance:
                return 1

            challenges = [challenge_instance]
        else:
            challenges = self._resolve_all_challenges()

        deployable_challenges, failed_deployments, failed_syncs = [], [], []

        # get challenges which can be deployed (have an image)
        for challenge_instance in challenges:
            if challenge_instance.get("image"):
                deployable_challenges.append(challenge_instance)
            else:
                failed_deployments.append(challenge_instance)

        config = Config()
        with click.progressbar(deployable_challenges, label="Deploying challenges") as challenges:
            for challenge_instance in challenges:
                click.echo()

                challenge_name = challenge_instance.get("name")
                target_host = host or challenge_instance.get("host")

                # Default to cloud deployment if host is not specified
                scheme = "cloud"
                if bool(target_host):
                    url = urlparse(target_host)
                    if not bool(url.netloc):
                        click.secho(
                            f"Host for challenge service '{challenge_name}' has no URI scheme - {target_host}. "
                            "Provide a URI scheme like ssh:// or registry://",
                            fg="red",
                        )
                        continue

                    scheme = url.scheme

                deployment_handler = get_deployment_handler(scheme)(
                    challenge_instance, host=host, protocol=challenge_instance.get("protocol")
                )

                click.secho(
                    f"Deploying challenge service '{challenge_name}' "
                    f"({challenge_instance.challenge_file_path.relative_to(config.project_path)}) "
                    f"with {deployment_handler.__class__.__name__} ...",
                    fg="blue",
                )

                deployment_result = deployment_handler.deploy(skip_login=skip_login)

                # Don't modify the connection_info if it exists already
                if challenge_instance.get("connection_info"):
                    click.secho("Using connection_info from challenge.yml", fg="yellow")

                # Otherwise, use connection_info from the deployment result if provided
                elif deployment_result.connection_info:
                    challenge_instance["connection_info"] = deployment_result.connection_info

                # Finally, if no connection_info was provided in the challenge and the
                # deployment didn't result in one either, just ensure it's not present
                else:
                    challenge_instance["connection_info"] = None

                if not deployment_result.success:
                    click.secho("An error occurred during service deployment!", fg="red")
                    failed_deployments.append(challenge_instance)
                    continue

                installed_challenges = Challenge.load_installed_challenges()
                existing_challenge = next(
                    (c for c in installed_challenges if c["name"] == challenge_instance["name"]),
                    None,
                )

                if challenge_instance.get("connection_info"):
                    click.secho(
                        f"Challenge service deployed at: {challenge_instance['connection_info']}",
                        fg="green",
                    )

                    challenge_instance.save()  # Save the challenge with the new connection_info
                else:
                    click.secho(
                        "Could not resolve a connection_info for the deployed service.\n"
                        "If your DeploymentHandler does not return a connection_info, "
                        "make sure to provide one in the challenge.yml file.",
                        fg="yellow",
                    )

                try:
                    if existing_challenge:
                        click.secho(f"Updating challenge '{challenge_name}'", fg="blue")
                        challenge_instance.sync(
                            ignore=["flags", "topics", "tags", "files", "hints", "requirements", "state"]
                        )
                    else:
                        click.secho(f"Creating challenge '{challenge_name}'", fg="blue")
                        challenge_instance.create()

                except ChallengeException as e:
                    click.secho(
                        "Challenge service has been deployed, however the challenge could not be "
                        f"{'synced' if existing_challenge else 'created'}",
                        fg="red",
                    )
                    click.secho(str(e), fg="red")
                    failed_syncs.append(challenge_instance)

                click.secho("Success!\n", fg="green")

        if len(failed_deployments) == 0 and len(failed_syncs) == 0:
            click.secho(
                "Success! All challenges deployed and installed or synced.",
                fg="green",
            )
            return 0

        if len(failed_deployments) > 0:
            click.secho("Deployment failed for:", fg="red")
            for challenge_instance in failed_deployments:
                click.echo(f" - {challenge_instance}")

        if len(failed_syncs) > 0:
            click.secho("Install / Sync failed for:", fg="red")
            for challenge_instance in failed_deployments:
                click.echo(f" - {challenge_instance}")

        return 1

    def lint(
        self,
        challenge: str = None,
        skip_hadolint: bool = False,
        flag_format: str = "flag{",
    ) -> int:
        log.debug(f"lint: (challenge={challenge}, skip_hadolint={skip_hadolint}, flag_format='{flag_format}')")

        challenge_instance = self._resolve_single_challenge(challenge)
        if not challenge_instance:
            return 1

        click.secho(f"Loaded {challenge_instance}", fg="blue")
        try:
            challenge_instance.lint(skip_hadolint=skip_hadolint, flag_format=flag_format)
        except LintException as e:
            click.secho("Linting found issues!\n", fg="yellow")
            e.print_summary()
            return 1

        click.secho("Success! Lint didn't find any issues!", fg="green")
        return 0

    def healthcheck(self, challenge: Optional[str] = None) -> int:
        log.debug(f"healthcheck: (challenge={challenge})")

        challenge_instance = self._resolve_single_challenge(challenge)
        if not challenge_instance:
            return 1

        click.secho(f"Loaded {challenge_instance}", fg="blue")
        healthcheck = challenge_instance.get("healthcheck", None)
        if not healthcheck:
            click.secho(
                f"Challenge '{challenge_instance}' does not define a healthcheck.",
                fg="red",
            )
            return 1

        # Get challenges installed from CTFd and try to find our challenge
        remote_challenges = Challenge.load_installed_challenges()

        challenge_id = None
        for remote_challenge in remote_challenges:
            if challenge_instance["name"] == remote_challenge["name"]:
                challenge_id = remote_challenge["id"]

        if challenge_id is None:
            click.secho(
                f"Could not find existing challenge '{challenge_instance}'. "
                f"Challenge needs to be installed and deployed to run a healthcheck.",
                fg="red",
            )
            return 1

        challenge_data = Challenge.load_installed_challenge(challenge_id)
        if not challenge_data:
            click.secho(f"Could not load data for challenge '{challenge_instance}'.", fg="red")
            return 1

        connection_info = challenge_data.get("connection_info")
        if not connection_info:
            click.secho(
                f"Challenge '{challenge_instance}' does not provide connection info. "
                "Perhaps it needs to be deployed first?",
                fg="red",
            )
            return 1

        log.debug(
            f"call(['{healthcheck}', '--connection-info', '{connection_info}'], "
            f"cwd='{challenge_instance.challenge_directory}')"
        )
        healthcheck_status = subprocess.call(
            [healthcheck, "--connection-info", connection_info],
            cwd=challenge_instance.challenge_directory,
        )

        if healthcheck_status != 0:
            click.secho("Healthcheck failed!", fg="red")
            return 1

        click.secho("Success! Challenge passed the healthcheck.", fg="green")
        return 0

    def mirror(
        self,
        challenge: str = None,
        files_directory: str = "dist",
        skip_verify: bool = False,
        ignore: Union[str, Tuple[str]] = (),
    ) -> int:
        log.debug(
            f"mirror: (challenge={challenge}, files_directory={files_directory}, "
            f"skip_verify={skip_verify}, ignore={ignore})"
        )

        if challenge:
            challenge_instance = self._resolve_single_challenge(challenge)
            if not challenge_instance:
                return 1

            local_challenges = [challenge_instance]
        else:
            local_challenges = self._resolve_all_challenges()

        if isinstance(ignore, str):
            ignore = (ignore,)

        remote_challenges = Challenge.load_installed_challenges()
        if len(local_challenges) > 1:
            # Issue a warning if there are extra challenges on the remote that do not have a local version
            local_challenge_names = [c["name"] for c in local_challenges]

            for remote_challenge in remote_challenges:
                if remote_challenge["name"] not in local_challenge_names:
                    click.secho(
                        f"Found challenge '{remote_challenge['name']}' in CTFd, but not in .ctf/config\n"
                        "Mirroring does not create new local challenges\n"
                        "Please add the local challenge if you wish to manage it with ctfcli\n",
                        fg="yellow",
                    )

        failed_mirrors = []
        with click.progressbar(local_challenges, label="Mirroring challenges") as challenges:
            for challenge_instance in challenges:
                try:
                    if not skip_verify and challenge_instance.verify(ignore=ignore):
                        click.secho(
                            f"Challenge '{challenge_instance}' is already in sync. Skipping mirroring.",
                            fg="blue",
                        )
                    else:
                        # if skip_verify is True or challenge.verify(ignore=ignore) is False
                        challenge_instance.mirror(files_directory_name=files_directory, ignore=ignore)

                except ChallengeException as e:
                    click.secho(str(e), fg="red")
                    failed_mirrors.append(challenge_instance)

        if len(failed_mirrors) == 0:
            click.secho("Success! All challenges mirrored!", fg="green")
            return 0

        click.secho("Mirror failed for:", fg="red")
        for challenge_instance in failed_mirrors:
            click.echo(f" - {challenge_instance}")

        return 1

    def verify(self, challenge: str = None, ignore: Tuple[str] = ()) -> int:
        log.debug(f"verify: (challenge={challenge}, ignore={ignore})")

        if challenge:
            challenge_instance = self._resolve_single_challenge(challenge)
            if not challenge_instance:
                return 1

            local_challenges = [challenge_instance]
        else:
            local_challenges = self._resolve_all_challenges()

        if isinstance(ignore, str):
            ignore = (ignore,)

        remote_challenges = Challenge.load_installed_challenges()
        if len(local_challenges) > 1:
            # Issue a warning if there are extra challenges on the remote that do not have a local version
            local_challenge_names = [c["name"] for c in local_challenges]

            for remote_challenge in remote_challenges:
                if remote_challenge["name"] not in local_challenge_names:
                    click.secho(
                        f"Found challenge '{remote_challenge['name']}' in CTFd, but not in .ctf/config\n"
                        "Please add the local challenge if you wish to manage it with ctfcli\n",
                        fg="yellow",
                    )

        failed_verifications, challenges_in_sync, challenges_out_of_sync = [], [], []
        with click.progressbar(local_challenges, label="Verifying challenges") as challenges:
            for challenge_instance in challenges:
                try:
                    if not challenge_instance.verify(ignore=ignore):
                        challenges_out_of_sync.append(challenge_instance)
                    else:
                        challenges_in_sync.append(challenge_instance)

                except ChallengeException as e:
                    click.secho(str(e), fg="red")
                    failed_verifications.append(challenge_instance)

        if len(failed_verifications) == 0:
            click.secho("Success! All challenges verified!", fg="green")

            if len(challenges_in_sync) > 0:
                click.secho("Challenges in sync:", fg="green")
                for challenge_instance in challenges_in_sync:
                    click.echo(f" - {challenge_instance}")

            if len(challenges_out_of_sync) > 0:
                click.secho("Challenges out of sync:", fg="yellow")
                for challenge_instance in challenges_out_of_sync:
                    click.echo(f" - {challenge_instance}")

            if len(challenges_out_of_sync) > 1:
                return 2

            return 1

        click.secho("Verification failed for:", fg="red")
        for challenge_instance in failed_verifications:
            click.echo(f" - {challenge_instance}")

        return 1

    def format(self, challenge: Optional[str] = None) -> int:
        log.debug(f"format: (challenge={challenge})")

        if challenge:
            challenge_instance = self._resolve_single_challenge(challenge)
            if not challenge_instance:
                return 1

            challenges = [challenge_instance]
        else:
            challenges = self._resolve_all_challenges()

        failed_formats = []
        for challenge_instance in challenges:
            try:
                # save the challenge without changes to trigger the format
                challenge_instance.save()

            except ChallengeException as e:
                click.secho(str(e), fg="red")
                failed_formats.append(challenge_instance)
                continue

        if len(failed_formats) == 0:
            click.secho("Success! All challenges formatted!", fg="green")
            return 0

        click.secho("Format failed for:", fg="red")
        for challenge_instance in failed_formats:
            click.echo(f" - {challenge_instance}")

        return 1

    @staticmethod
    def _resolve_single_challenge(challenge: Optional[str] = None) -> Optional[Challenge]:
        # if a challenge is specified
        if challenge:
            # check if it's a path to challenge.yml, or the current directory
            if challenge.endswith(".yml") or challenge.endswith(".yaml") or challenge == ".":
                challenge_path = Path(challenge)

            # otherwise it's a name to be resolved from the config
            else:
                config = Config()
                challenge_path = config.project_path / Path(challenge)

        # otherwise, assume it's in the current directory
        else:
            challenge_path = Path.cwd()

        if not challenge_path.name.endswith(".yml") and not challenge_path.name.endswith(".yaml"):
            challenge_path = challenge_path / "challenge.yml"

        try:
            return Challenge(challenge_path)
        except ChallengeException as e:
            click.secho(str(e), fg="red")
            return

    @staticmethod
    def _resolve_all_challenges() -> List[Challenge]:
        config = Config()
        challenge_keys = config.challenges.keys()

        challenges = []
        for challenge_key in challenge_keys:
            challenge_path = config.project_path / Path(challenge_key)

            if not challenge_path.name.endswith(".yml"):
                challenge_path = challenge_path / "challenge.yml"

            try:
                challenges.append(Challenge(challenge_path))
            except ChallengeException as e:
                click.secho(str(e), fg="red")
                continue

        return challenges
