import re
import subprocess
from os import PathLike
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import click
import yaml
from slugify import slugify

from ctfcli.core.api import API
from ctfcli.core.exceptions import (
    InvalidChallengeDefinition,
    InvalidChallengeFile,
    LintException,
    RemoteChallengeNotFound,
)
from ctfcli.core.image import Image
from ctfcli.utils.tools import strings


def str_presenter(dumper, data):
    if len(data.splitlines()) > 1 or "\n" in data:
        text_list = [line.rstrip() for line in data.splitlines()]
        fixed_data = "\n".join(text_list)
        return dumper.represent_scalar("tag:yaml.org,2002:str", fixed_data, style="|")
    elif len(data) > 80:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data.rstrip(), style=">")

    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)
yaml.representer.SafeRepresenter.add_representer(str, str_presenter)


class Challenge(dict):
    key_order = [
        # fmt: off
        "name", "author", "category", "description", "value",
        "type", "extra", "image", "protocol", "host",
        "connection_info", "healthcheck", "attempts", "flags",
        "files", "topics", "tags", "files", "hints",
        "requirements", "state", "version",
        # fmt: on
    ]

    keys_with_newline = [
        # fmt: off
        "extra", "image", "attempts", "flags", "topics", "tags",
        "files", "hints", "requirements", "state", "version",
        # fmt: on
    ]

    @staticmethod
    def load_installed_challenge(challenge_id) -> Optional[Dict]:
        api = API()
        r = api.get(f"/api/v1/challenges/{challenge_id}")

        if not r.ok:
            return

        installed_challenge = r.json().get("data", None)
        if not installed_challenge:
            return

        return installed_challenge

    @staticmethod
    def load_installed_challenges() -> List:
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
        if key == "connection_info" and value is None:
            return True

        if key == "attempts" and value == 0:
            return True

        if key == "state" and value == "visible":
            return True

        if key == "type" and value == "standard":
            return True

        if key in ["tags", "hints", "topics", "requirements", "files"] and value == []:
            return True

        return False

    @property
    def api(self):
        if not self._api:
            self._api = API()

        return self._api

    # __init__ expects an absolute path to challenge_yml, or a relative one from the cwd
    # it does not join that path with the project_path
    def __init__(self, challenge_yml: Union[str, PathLike], overrides=None):
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
                raise InvalidChallengeFile(f"Challenge file at {self.challenge_file_path} could not be loaded:\n{e}")

            if type(challenge_definition) != dict:
                raise InvalidChallengeFile(
                    f"Challenge file at {self.challenge_file_path} is either empty or not a dictionary / object"
                )

        challenge_data = {**challenge_definition, **overrides}
        super(Challenge, self).__init__(challenge_data)

        # Challenge id is unknown before loading the remote challenge
        self.challenge_id = None

        # API is not initialized before running an API-related operation, but should be reused later
        self._api = None

        # Set Image to None if the challenge does not provide one
        self.image = None

        # Get name and a build path for the image if the challenge provides one
        if self.get("image"):
            self.image = Image(slugify(self["name"]), self.challenge_directory / self["image"])

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

    def _validate_files(self):
        # if the challenge defines files, make sure they exist before making any changes to the challenge
        for challenge_file in self["files"]:
            if not (self.challenge_directory / challenge_file).exists():
                raise InvalidChallengeFile(f"File {challenge_file} could not be loaded")

    def _get_initial_challenge_payload(self, ignore: Tuple[str] = ()) -> Dict:
        challenge = self
        challenge_payload = {
            "name": self["name"],
            "category": self.get("category", ""),
            "description": self.get("description", ""),
            "type": self.get("type", "standard"),
            # Hide the challenge for the duration of the sync / creation
            "state": "hidden",
        }

        # Some challenge types (e.g., dynamic) override value.
        # We can't send it to CTFd because we don't know the current value
        if challenge.get("value", None) is not None:
            # if value is an int as string, cast it
            if type(challenge["value"]) == str and challenge["value"].isdigit():
                challenge_payload["value"] = int(challenge["value"])

            if type(challenge["value"] == int):
                challenge_payload["value"] = challenge["value"]

        if "attempts" not in ignore:
            challenge_payload["max_attempts"] = challenge.get("attempts", 0)

        if "connection_info" not in ignore:
            challenge_payload["connection_info"] = challenge.get("connection_info", None)

        if "extra" not in ignore:
            challenge_payload = {**challenge_payload, **challenge.get("extra", {})}

        return challenge_payload

    # Flag delete/create
    def _delete_existing_flags(self):
        remote_flags = self.api.get("/api/v1/flags").json()["data"]
        for flag in remote_flags:
            if flag["challenge_id"] == self.challenge_id:
                r = self.api.delete(f"/api/v1/flags/{flag['id']}")
                r.raise_for_status()

    def _create_flags(self):
        for flag in self["flags"]:
            if type(flag) == str:
                flag_payload = {
                    "content": flag,
                    "type": "static",
                    "challenge_id": self.challenge_id,
                }
            else:
                flag_payload = {**flag, "challenge_id": self.challenge_id}

            r = self.api.post("/api/v1/flags", json=flag_payload)
            r.raise_for_status()

    # Topic delete/create
    def _delete_existing_topics(self):
        remote_topics = self.api.get(f"/api/v1/challenges/{self.challenge_id}/topics").json()["data"]
        for topic in remote_topics:
            r = self.api.delete(f"/api/v1/topics?type=challenge&target_id={topic['id']}")
            r.raise_for_status()

    def _create_topics(self):
        for topic in self["topics"]:
            r = self.api.post(
                "/api/v1/topics",
                json={
                    "value": topic,
                    "type": "challenge",
                    "challenge_id": self.challenge_id,
                },
            )
            r.raise_for_status()

    # Tag delete/create
    def _delete_existing_tags(self):
        remote_tags = self.api.get("/api/v1/tags").json()["data"]
        for tag in remote_tags:
            if tag["challenge_id"] == self.challenge_id:
                r = self.api.delete(f"/api/v1/tags/{tag['id']}")
                r.raise_for_status()

    def _create_tags(self):
        for tag in self["tags"]:
            r = self.api.post(
                "/api/v1/tags",
                json={"challenge_id": self.challenge_id, "value": tag},
            )
            r.raise_for_status()

    # File delete/create
    def _delete_existing_files(self):
        remote_challenge = self.load_installed_challenge(self.challenge_id)
        remote_files = self.api.get("/api/v1/files?type=challenge").json()["data"]

        for remote_file in remote_files:
            for utilized_file in remote_challenge["files"]:
                if remote_file["location"] in utilized_file:
                    r = self.api.delete(f"/api/v1/files/{remote_file['id']}")
                    r.raise_for_status()

    def _create_files(self):
        new_files = []
        for challenge_file in self["files"]:
            new_files.append(("file", open(self.challenge_directory / challenge_file, mode="rb")))

        files_payload = {"challenge_id": self.challenge_id, "type": "challenge"}
        # Specifically use data= here to send multipart/form-data
        r = self.api.post("/api/v1/files", files=new_files, data=files_payload)
        r.raise_for_status()

        for file_payload in new_files:
            file_payload[1].close()

    # Hint delete/create
    def _delete_existing_hints(self):
        remote_hints = self.api.get("/api/v1/hints").json()["data"]
        for hint in remote_hints:
            if hint["challenge_id"] == self.challenge_id:
                r = self.api.delete(f"/api/v1/hints/{hint['id']}")
                r.raise_for_status()

    def _create_hints(self):
        for hint in self["hints"]:
            if type(hint) == str:
                hint_payload = {
                    "content": hint,
                    "cost": 0,
                    "challenge_id": self.challenge_id,
                }
            else:
                hint_payload = {
                    "content": hint["content"],
                    "cost": hint["cost"],
                    "challenge_id": self.challenge_id,
                }

            r = self.api.post("/api/v1/hints", json=hint_payload)
            r.raise_for_status()

    # Required challenges
    def _set_required_challenges(self):
        remote_challenges = self.load_installed_challenges()
        required_challenges = []

        for required_challenge in self["requirements"]:
            if type(required_challenge) == str:
                # requirement by name
                # find the challenge id from installed challenges
                for remote_challenge in remote_challenges:
                    if remote_challenge["name"] == required_challenge:
                        required_challenges.append(remote_challenge["id"])

            elif type(required_challenge) == int:
                # requirement by challenge id
                # trust it and use it directly
                required_challenges.append(required_challenge)

        required_challenge_ids = list(set(required_challenges))

        if self.challenge_id in required_challenge_ids:
            click.secho(
                "Challenge cannot require itself. Skipping invalid requirement.",
                fg="yellow",
            )
            required_challenges.remove(self.challenge_id)

        requirements_payload = {"requirements": {"prerequisites": required_challenges}}
        r = self.api.patch(f"/api/v1/challenges/{self.challenge_id}", json=requirements_payload)
        r.raise_for_status()

    def sync(self, ignore: Tuple[str] = ()) -> None:
        challenge = self

        if "name" in ignore:
            click.secho(
                "Attribute 'name' cannot be ignored when syncing a challenge",
                fg="yellow",
            )

        if not self.get("name"):
            raise InvalidChallengeFile("Challenge does not provide a name")

        if challenge.get("files", False) and "files" not in ignore:
            # _validate_files will raise if file is not found
            self._validate_files()

        challenge_payload = self._get_initial_challenge_payload(ignore=ignore)

        self._load_challenge_id()
        remote_challenge = self.load_installed_challenge(self.challenge_id)

        # if value, category, type or description are ignored, revert them to the remote state in the initial payload
        reset_properties_if_ignored = ["value", "category", "type", "description"]
        for p in reset_properties_if_ignored:
            if p in ignore:
                challenge_payload[p] = remote_challenge[p]

        # Update simple properties
        r = self.api.patch(f"/api/v1/challenges/{self.challenge_id}", json=challenge_payload)
        r.raise_for_status()

        # Update flags
        if "flags" not in ignore:
            self._delete_existing_flags()
            if challenge.get("flags"):
                self._create_flags()

        # Update topics
        if "topics" not in ignore:
            self._delete_existing_topics()
            if challenge.get("topics"):
                self._create_topics()

        # Update tags
        if "tags" not in ignore:
            self._delete_existing_tags()
            if challenge.get("tags"):
                self._create_tags()

        # Create / Upload files
        if "files" not in ignore:
            self._delete_existing_files()
            if challenge.get("files"):
                self._create_files()

        # Update hints
        if "hints" not in ignore:
            self._delete_existing_hints()
            if challenge.get("hints"):
                self._create_hints()

        # Update requirements
        if challenge.get("requirements") and "requirements" not in ignore:
            self._set_required_challenges()

        make_challenge_visible = False

        # Bring back the challenge to be visible if:
        # 1. State is not ignored and set to visible, or defaults to visible
        if "state" not in ignore:
            if challenge.get("state", "visible") == "visible":
                make_challenge_visible = True

        # 2. State is ignored, but regardless of the local value, the remote state was visible
        else:
            if remote_challenge.get("state") == "visible":
                make_challenge_visible = True

        if make_challenge_visible:
            r = self.api.patch(f"/api/v1/challenges/{self.challenge_id}", json={"state": "visible"})
            r.raise_for_status()

    def create(self, ignore: Tuple[str] = ()) -> None:
        challenge = self

        for attr in ["name", "value"]:
            if attr in ignore:
                click.secho(
                    f"Attribute '{attr}' cannot be ignored when creating a challenge",
                    fg="yellow",
                )

        if not challenge.get("name", False):
            raise InvalidChallengeDefinition("Challenge does not provide a name")

        if not challenge.get("value", False) and challenge.get("type", "standard") != "dynamic":
            raise InvalidChallengeDefinition("Challenge does not provide a value")

        if challenge.get("files", False) and "files" not in ignore:
            # _validate_files will raise if file is not found
            self._validate_files()

        challenge_payload = self._get_initial_challenge_payload(ignore=ignore)

        # in the case of creation, value and type can't be ignored:
        # value is required (unless the challenge is a dynamic value challenge),
        # and the type will default to standard
        # if category or description are ignored, set them to an empty string
        reset_properties_if_ignored = ["category", "description"]
        for p in reset_properties_if_ignored:
            if p in ignore:
                challenge_payload[p] = ""

        r = self.api.post("/api/v1/challenges", json=challenge_payload)
        r.raise_for_status()

        self.challenge_id = r.json()["data"]["id"]

        # Create flags
        if challenge.get("flags") and "flags" not in ignore:
            self._create_flags()

        # Create topics
        if challenge.get("topics") and "topics" not in ignore:
            self._create_topics()

        # Create tags
        if challenge.get("tags") and "tags" not in ignore:
            self._create_tags()

        # Upload files
        if challenge.get("files") and "files" not in ignore:
            self._create_files()

        # Add hints
        if challenge.get("hints") and "hints" not in ignore:
            self._create_hints()

        # Add requirements
        if challenge.get("requirements") and "requirements" not in ignore:
            self._set_required_challenges()

        # Bring back the challenge if it's supposed to be visible
        # Either explicitly, or by assuming the default value (possibly because the state is ignored)
        if challenge.get("state", "visible") == "visible" or "state" in ignore:
            r = self.api.patch(f"/api/v1/challenges/{self.challenge_id}", json={"state": "visible"})
            r.raise_for_status()

    def lint(self, skip_hadolint=False, flag_format="flag{") -> bool:
        challenge = self

        issues = {"fields": [], "dockerfile": [], "hadolint": [], "files": []}

        # Check if required fields are present
        for field in ["name", "author", "category", "description", "value"]:
            # value is allowed to be none if the challenge type is dynamic
            if field == "value" and challenge.get("type") == "dynamic":
                continue

            if challenge.get(field) is None:
                issues["fields"].append(f"challenge.yml is missing required field: {field}")

        # Check that the image field and Dockerfile match
        if (self.challenge_directory / "Dockerfile").is_file() and challenge.get("image", "") != ".":
            issues["dockerfile"].append("Dockerfile exists but image field does not point to it")

        # Check that Dockerfile exists and is EXPOSE'ing a port
        if challenge.get("image") == ".":
            dockerfile_path = self.challenge_directory / "Dockerfile"
            has_dockerfile = dockerfile_path.is_file()

            if not has_dockerfile:
                issues["dockerfile"].append("Dockerfile specified in 'image' field but no Dockerfile found")

            if has_dockerfile:
                with open(dockerfile_path, "r") as dockerfile:
                    dockerfile_source = dockerfile.read()

                    if "EXPOSE" not in dockerfile_source:
                        issues["dockerfile"].append("Dockerfile is missing EXPOSE")

                    if not skip_hadolint:
                        # Check Dockerfile with hadolint
                        hadolint = subprocess.run(
                            ["docker", "run", "--rm", "-i", "hadolint/hadolint"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            input=dockerfile_source.encode(),
                        )

                        if hadolint.returncode != 0:
                            issues["hadolint"].append(hadolint.stdout.decode())

                    else:
                        click.secho("Skipping Hadolint", fg="yellow")

        # Check that all files exist
        challenge_files = challenge.get("files", [])
        for challenge_file in challenge_files:
            challenge_file_path = self.challenge_directory / challenge_file

            if challenge_file_path.is_file() is False:
                issues["files"].append(
                    f"Challenge file '{challenge_file}' specified, but not found at {challenge_file_path}"
                )

        # Check that files don't have a flag in them
        challenge_files = challenge.get("files", [])
        for challenge_file in challenge_files:
            challenge_file_path = self.challenge_directory / challenge_file

            if not challenge_file_path.exists():
                # The check for files present is above; this is only to look for flags in files that we do have
                continue

            for s in strings(challenge_file_path):
                if flag_format in s:
                    s = s.strip()
                    issues["files"].append(f"Potential flag found in distributed file '{challenge_file}':\n {s}")

        if any(messages for messages in issues.values() if len(messages) > 0):
            raise LintException(issues=issues)

        return True

    # Compare challenge requirements, will resolve all IDs to names
    def _compare_challenge_requirements(self, r1: List[Union[str, int]], r2: List[Union[str, int]]) -> bool:
        remote_challenges = self.load_installed_challenges()

        def normalize_requirements(requirements):
            normalized = []
            for r in requirements:
                if type(r) == int:
                    for remote_challenge in remote_challenges:
                        if remote_challenge["id"] == r:
                            normalized.append(remote_challenge["name"])
                            break
                else:
                    normalized.append(r)

            return normalized

        return normalize_requirements(r1) == normalize_requirements(r2)

    # Normalize challenge data from the API response to match challenge.yml
    # It will remove any extra fields from the remote, as well as expand external references
    # that have to be fetched separately (e.g., files, flags, hints, etc.)
    # Note: files won't be included for two reasons:
    # 1. To avoid downloading them unnecessarily, e.g., when they are ignored
    # 2. Because it's dependent on the implementation whether to save them (mirror) or just compare (verify)
    def _normalize_challenge(self, challenge_data: Dict[str, Any]):
        challenge = {}

        copy_keys = ["name", "category", "value", "type", "state", "connection_info"]
        for key in copy_keys:
            if key in challenge_data:
                challenge[key] = challenge_data[key]

        challenge["description"] = challenge_data["description"].strip().replace("\r\n", "\n").replace("\t", "")
        challenge["attempts"] = challenge_data["max_attempts"]

        for key in ["initial", "decay", "minimum"]:
            if key in challenge_data:
                if "extra" not in challenge:
                    challenge["extra"] = {}

                challenge["extra"][key] = challenge_data[key]

        # Add flags
        r = self.api.get(f"/api/v1/challenges/{self.challenge_id}/flags")
        r.raise_for_status()
        flags = r.json()["data"]
        challenge["flags"] = [
            f["content"]
            if f["type"] == "static" and (f["data"] is None or f["data"] == "")
            else {"content": f["content"].strip().replace("\r\n", "\n"), "type": f["type"], "data": f["data"]}
            for f in flags
        ]

        # Add tags
        r = self.api.get(f"/api/v1/challenges/{self.challenge_id}/tags")
        r.raise_for_status()
        tags = r.json()["data"]
        challenge["tags"] = [t["value"] for t in tags]

        # Add hints
        r = self.api.get(f"/api/v1/challenges/{self.challenge_id}/hints")
        r.raise_for_status()
        hints = r.json()["data"]
        # skipping pre-requisites for hints because they are not supported in ctfcli
        challenge["hints"] = [
            {"content": h["content"], "cost": h["cost"]} if h["cost"] > 0 else h["content"] for h in hints
        ]

        # Add topics
        r = self.api.get(f"/api/v1/challenges/{self.challenge_id}/topics")
        r.raise_for_status()
        topics = r.json()["data"]
        challenge["topics"] = [t["value"] for t in topics]

        # Add requirements
        r = self.api.get(f"/api/v1/challenges/{self.challenge_id}/requirements")
        r.raise_for_status()
        requirements = (r.json().get("data") or {}).get("prerequisites", [])
        if len(requirements) > 0:
            # Prefer challenge names over IDs
            r = self.api.get("/api/v1/challenges")
            r.raise_for_status()
            challenges = r.json()["data"]
            challenge["requirements"] = [c["name"] for c in challenges if c["id"] in requirements]

        return challenge

    def mirror(self, files_directory_name: str = "dist", ignore: Tuple[str] = ()) -> None:
        self._load_challenge_id()
        remote_challenge = self.load_installed_challenge(self.challenge_id)
        challenge = self._normalize_challenge(remote_challenge)

        # Add files which are not handled in _normalize_challenge
        if "files" not in ignore:
            local_files = {Path(f).name: f for f in challenge.get("files", [])}

            # Update files
            for remote_file in remote_challenge["files"]:
                # Get base file name
                remote_file_name = remote_file.split("/")[-1].split("?token=")[0]

                # The file is only present on the remote - we have to download it, and assume a path
                if remote_file_name not in local_files:
                    r = self.api.get(remote_file)
                    r.raise_for_status()

                    # Ensure the directory for the challenge files exists
                    challenge_files_directory = self.challenge_directory / files_directory_name
                    challenge_files_directory.mkdir(parents=True, exist_ok=True)

                    (challenge_files_directory / remote_file_name).write_bytes(r.content)
                    if "files" not in challenge:
                        challenge["files"] = []

                    challenge["files"].append(f"{files_directory_name}/{remote_file_name}")

                # The file is already present in the challenge.yml - we know the desired path
                else:
                    r = self.api.get(remote_file)
                    r.raise_for_status()
                    (self.challenge_directory / local_files[remote_file_name]).write_bytes(r.content)

            # Soft-Delete files that are not present on the remote
            # Remove them from challenge.yml but do not delete them from disk
            remote_file_names = [f.split("/")[-1].split("?token=")[0] for f in remote_challenge["files"]]
            challenge["files"] = [f for f in challenge.get("files", []) if Path(f).name in remote_file_names]

        for key in challenge.keys():
            if key not in ignore:
                self[key] = challenge[key]

        self.save()

    def verify(self, ignore: Tuple[str] = ()) -> bool:
        self._load_challenge_id()
        challenge = self
        remote_challenge = self.load_installed_challenge(self.challenge_id)
        normalized_challenge = self._normalize_challenge(remote_challenge)

        for key in normalized_challenge:
            if key in ignore:
                continue

            # If challenge.yml doesn't have some property from the remote
            # Check if it's a default value that can be omitted
            if key not in challenge:
                if self.is_default_challenge_property(key, normalized_challenge[key]):
                    continue

                return False

            if challenge[key] != normalized_challenge[key]:
                if key == "requirements":
                    if self._compare_challenge_requirements(challenge[key], normalized_challenge[key]):
                        continue

                return False

        # Handle a special case for files, unless they are ignored
        if "files" not in ignore:
            local_files = {Path(f).name: f for f in challenge.get("files", [])}
            remote_files = {f.split("/")[-1].split("?token=")[0]: f for f in remote_challenge["files"]}

            # Check if there are no extra local files
            for local_file in local_files:
                if local_file not in remote_files:
                    return False

            # Check if all remote files are present locally
            for remote_file in remote_files:
                if remote_file not in local_files:
                    return False

                # Check if the remote files are the same as local
                r = self.api.get(remote_files[remote_file])
                r.raise_for_status()
                remote_file_contents = r.content
                local_file_contents = (self.challenge_directory / local_files[remote_file]).read_bytes()

                if remote_file_contents != local_file_contents:
                    return False

        return True

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
            raise InvalidChallengeFile(f"Challenge file could not be saved:\n{e}")
