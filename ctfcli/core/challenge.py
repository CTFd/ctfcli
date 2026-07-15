import logging
import re
from os import PathLike
from pathlib import Path
from typing import Any

import click
import yaml
from cookiecutter.main import cookiecutter
from slugify import slugify

from ctfcli.core.api import API
from ctfcli.core.exceptions import (
    ChallengeException,
    InvalidChallengeDefinition,
    InvalidChallengeFile,
    RemoteChallengeNotFound,
)
from ctfcli.core.lint import lint_challenge
from ctfcli.core.properties import (
    NOT_PULLED,
    PROPERTIES,
    PropertyContext,
    get_property,
    has_property,
    operation_order,
)

log = logging.getLogger("ctfcli.core.challenge")


def str_presenter(dumper, data):
    if len(data.splitlines()) > 1 or "\n" in data:
        text_list = [line.rstrip() for line in data.splitlines()]
        fixed_data = "\n".join(text_list)
        return dumper.represent_scalar("tag:yaml.org,2002:str", fixed_data, style="|")

    if len(data) > 80:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data.rstrip(), style=">")

    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)
yaml.representer.SafeRepresenter.add_representer(str, str_presenter)


class Challenge(dict):
    # The order of the keys in challenge.yml, as well as the create/sync/mirror/verify
    # behavior of each of them, is defined by the property registry (ctfcli.core.properties)
    key_order = [p.key for p in PROPERTIES]
    keys_with_newline = [p.key for p in PROPERTIES if p.newline_before]

    @staticmethod
    def load_installed_challenge(challenge_id) -> dict:
        api = API()
        r = api.get(f"/api/v1/challenges/{challenge_id}?view=admin")

        if not r.ok:
            raise RemoteChallengeNotFound(f"Could not load challenge with id={challenge_id}")

        installed_challenge = r.json().get("data", None)
        if not installed_challenge:
            raise RemoteChallengeNotFound(f"Could not load challenge with id={challenge_id}")

        return installed_challenge

    @staticmethod
    def load_installed_challenges() -> list:
        api = API()
        r = api.get("/api/v1/challenges?view=admin")

        if not r.ok:
            return []

        installed_challenges = r.json().get("data", None)
        if not installed_challenges:
            return []

        return installed_challenges

    @staticmethod
    def is_default_challenge_property(key: str, value: Any) -> bool:
        return has_property(key) and get_property(key).is_default(value)

    @staticmethod
    def clone(config, remote_challenge):
        name = remote_challenge["name"]

        if name is None:
            raise ChallengeException(f"Could not get name of remote challenge with id {remote_challenge['id']}")

        # First, generate a name for the challenge directory
        category = remote_challenge.get("category", None)
        challenge_dir_name = slugify(name)
        if category is not None:
            challenge_dir_name = str(Path(slugify(category)) / challenge_dir_name)

        if Path(challenge_dir_name).exists():
            raise ChallengeException(
                f"Challenge directory '{challenge_dir_name}' for challenge '{name}' already exists"
            )

        # Create an blank/empty challenge, with only the challenge.yml containing the challenge name
        template_path = config.get_base_path() / "templates" / "blank" / "empty"
        log.debug(f"Challenge.clone: cookiecutter({template_path!s}, {name=}, {challenge_dir_name=}")
        cookiecutter(
            str(template_path),
            no_input=True,
            extra_context={"name": name, "dirname": challenge_dir_name},
        )

        if not Path(challenge_dir_name).exists():
            raise ChallengeException(f"Could not create challenge directory '{challenge_dir_name}' for '{name}'")

        # Add the newly created local challenge to the config file
        config["challenges"][challenge_dir_name] = challenge_dir_name
        with open(config.config_path, "w+") as f:
            config.write(f)

        return Challenge(f"{challenge_dir_name}/challenge.yml")

    @property
    def api(self):
        if not self._api:
            self._api = API()

        return self._api

    # __init__ expects an absolute path to challenge_yml, or a relative one from the cwd
    # it does not join that path with the project_path
    def __init__(self, challenge_yml: str | PathLike, overrides=None):
        log.debug(f"Challenge.__init__: ({challenge_yml=}, {overrides=}")
        if overrides is None:
            overrides = {}

        self.challenge_file_path = Path(challenge_yml)

        if not self.challenge_file_path.is_file():
            raise InvalidChallengeFile(f"Challenge file at {self.challenge_file_path} could not be found")

        self.challenge_directory = self.challenge_file_path.parent

        with open(self.challenge_file_path) as challenge_file:
            try:
                challenge_definition = yaml.safe_load(challenge_file.read())
            except yaml.YAMLError as e:
                raise InvalidChallengeFile(
                    f"Challenge file at {self.challenge_file_path} could not be loaded:\n{e}"
                ) from e

            if type(challenge_definition) != dict:
                raise InvalidChallengeFile(
                    f"Challenge file at {self.challenge_file_path} is either empty or not a dictionary / object"
                )

        challenge_data = {**challenge_definition, **overrides}
        super().__init__(challenge_data)

        # Challenge id is unknown before loading the remote challenge
        self.challenge_id = None

        # API is not initialized before running an API-related operation, but should be reused later
        self._api = None

        # Assign an image if the challenge provides one, otherwise this will be set to None
        self.image = get_property("image").resolve(PropertyContext(self))

    def __str__(self):
        return self["name"]

    def _load_challenge_id(self):
        remote_challenges = self.load_installed_challenges()
        if not remote_challenges:
            raise RemoteChallengeNotFound("Could not load any remote challenges")

        # get challenge id from the remote
        for inspected_challenge in remote_challenges:
            if inspected_challenge["name"] == self["name"]:
                self.challenge_id = inspected_challenge["id"]
                break

        # return if we failed to determine the challenge id (failed to find the challenge)
        if self.challenge_id is None:
            raise RemoteChallengeNotFound(f"Could not load remote challenge with name '{self['name']}'")

    # Normalize challenge data from the API response to match challenge.yml
    # It will remove any extra fields from the remote, as well as expand external references
    # that have to be fetched separately (e.g., flags, hints, requirements, etc.)
    # Note: files won't be included for two reasons:
    # 1. To avoid downloading them unnecessarily, e.g., when they are ignored
    # 2. Because it's dependent on the implementation whether to save them (mirror) or just compare (verify)
    def _normalize_challenge(self, challenge_data: dict[str, Any]) -> dict[str, Any]:
        ctx = PropertyContext(self)

        challenge = {}
        for prop in PROPERTIES:
            value = prop.pull(ctx, challenge_data)
            if value is not NOT_PULLED:
                challenge[prop.key] = value

        return challenge

    def sync(self, ignore: tuple[str] = ()) -> None:
        if "name" in ignore:
            click.secho(
                "Attribute 'name' cannot be ignored when syncing a challenge",
                fg="yellow",
            )

        if not self.get("name"):
            raise InvalidChallengeFile("Challenge does not provide a name")

        ctx = PropertyContext(self, ignore=ignore)

        if self.get("files", False) and "files" not in ignore:
            # validate will raise if a file is not found
            get_property("files").validate(ctx)

        self._load_challenge_id()
        ctx.remote_challenge = self.load_installed_challenge(self.challenge_id)

        # Update simple properties with a single PATCH,
        # ignored properties are reverted to their remote values
        challenge_payload = {}
        for prop in PROPERTIES:
            challenge_payload.update(prop.sync_payload(ctx))

        r = self.api.patch(f"/api/v1/challenges/{self.challenge_id}", json=challenge_payload)
        if r.ok is False:
            click.secho(f"Failed to sync challenge: ({r.status_code}) {r.text}", fg="red")
        r.raise_for_status()

        # Update properties stored in separate resources (flags, files, hints, etc.)
        for prop in operation_order():
            prop.sync(ctx)

        make_challenge_visible = False

        # Bring back the challenge to be visible if:
        # 1. State is not ignored and set to visible, or defaults to visible
        if "state" not in ignore:
            if self.get("state", "visible") == "visible":
                make_challenge_visible = True

        # 2. State is ignored, but regardless of the local value, the remote state was visible
        else:
            if ctx.remote_challenge.get("state") == "visible":
                make_challenge_visible = True

        if make_challenge_visible:
            r = self.api.patch(f"/api/v1/challenges/{self.challenge_id}", json={"state": "visible"})
            r.raise_for_status()

    def create(self, ignore: tuple[str] = ()) -> None:
        for attr in ["name", "value"]:
            if attr in ignore:
                click.secho(
                    f"Attribute '{attr}' cannot be ignored when creating a challenge",
                    fg="yellow",
                )

        if not self.get("name", False):
            raise InvalidChallengeDefinition("Challenge does not provide a name")

        if not self.get("value", False) and self.get("type", "standard") != "dynamic":
            raise InvalidChallengeDefinition("Challenge does not provide a value")

        ctx = PropertyContext(self, ignore=ignore)

        if self.get("files", False) and "files" not in ignore:
            # validate will raise if a file is not found
            get_property("files").validate(ctx)

        challenge_payload = {}
        for prop in PROPERTIES:
            challenge_payload.update(prop.create_payload(ctx))

        r = self.api.post("/api/v1/challenges", json=challenge_payload)
        if r.ok is False:
            click.secho(f"Failed to create challenge: ({r.status_code}) {r.text}", fg="red")
        r.raise_for_status()

        self.challenge_id = r.json()["data"]["id"]

        # Create properties stored in separate resources (flags, files, hints, etc.)
        for prop in operation_order():
            prop.create(ctx)

        # Bring back the challenge if it's supposed to be visible
        # Either explicitly, or by assuming the default value (possibly because the state is ignored)
        if self.get("state", "visible") == "visible" or "state" in ignore:
            r = self.api.patch(f"/api/v1/challenges/{self.challenge_id}", json={"state": "visible"})
            r.raise_for_status()

    def lint(self, skip_hadolint=False, flag_format="flag{") -> bool:
        return lint_challenge(self, skip_hadolint=skip_hadolint, flag_format=flag_format)

    def mirror(self, files_directory_name: str = "dist", ignore: tuple[str] = ()) -> None:
        self._load_challenge_id()
        ctx = PropertyContext(
            self,
            ignore=ignore,
            remote_challenge=self.load_installed_challenge(self.challenge_id),
            options={"files_directory_name": files_directory_name},
        )

        normalized_challenge = self._normalize_challenge(ctx.remote_challenge)

        # Some properties (e.g. files) are not part of the normalized challenge
        # and amend it during mirror instead (e.g. downloading the files to disk)
        for prop in PROPERTIES:
            prop.mirror(ctx, normalized_challenge)

        for key in normalized_challenge:
            if key not in ignore:
                self[key] = normalized_challenge[key]

        self.save()

    def verify(self, ignore: tuple[str] = ()) -> bool:
        self._load_challenge_id()
        ctx = PropertyContext(self, ignore=ignore, remote_challenge=self.load_installed_challenge(self.challenge_id))

        normalized_challenge = self._normalize_challenge(ctx.remote_challenge)
        for key in normalized_challenge:
            if key in ignore:
                continue

            # If challenge.yml doesn't have some property from the remote
            # Check if it's a default value that can be omitted
            if key not in self:
                if self.is_default_challenge_property(key, normalized_challenge[key]):
                    continue

                click.secho(f"{key} is not in challenge.", fg="yellow")

                return False

            if not get_property(key).matches(ctx, self[key], normalized_challenge[key]):
                click.secho(f"{key} comparison failed.", fg="yellow")

                return False

        # Some properties (e.g. files) are not part of the normalized challenge
        # and implement their own whole-run verification instead
        return all(prop.verify(ctx) for prop in PROPERTIES)

    def save(self):
        challenge_dict = dict(self)

        # sort the challenge dict by the key order defined from the spec
        # also strip any default values
        sorted_challenge_dict = {
            k: challenge_dict[k]
            for k in self.key_order
            if k in challenge_dict and not self.is_default_challenge_property(k, challenge_dict[k])
        }

        # if there are any additional keys append them at the end
        unknown_keys = set(challenge_dict) - set(self.key_order)
        for k in unknown_keys:
            sorted_challenge_dict[k] = challenge_dict[k]

        try:
            challenge_yml = yaml.safe_dump(sorted_challenge_dict, sort_keys=False, allow_unicode=True)

            # attempt to pretty print the yaml (add an extra newline between selected top-level keys)
            pattern = "|".join(r"^" + re.escape(key) + r":" for key in self.keys_with_newline)
            pretty_challenge_yml = re.sub(pattern, r"\n\g<0>", challenge_yml, flags=re.MULTILINE)

            with open(self.challenge_file_path, "w") as challenge_file:
                challenge_file.write(pretty_challenge_yml)

        except Exception as e:
            raise InvalidChallengeFile(f"Challenge file could not be saved:\n{e}") from e
