from pathlib import Path
import subprocess

import click
import yaml

from .config import generate_session
from .tools import strings


class Yaml(dict):
    def __init__(self, data, file_path=None):
        super().__init__(data)
        self.file_path = Path(file_path)
        self.directory = self.file_path.parent


def load_challenge(path):
    try:
        with open(path) as f:
            return Yaml(data=yaml.safe_load(f.read()), file_path=path)
    except FileNotFoundError:
        click.secho(f"No challenge.yml was found in {path}", fg="red")
        return


def load_installed_challenge(challenge_id):
    s = generate_session()
    return s.get(f"/api/v1/challenges/{challenge_id}", json=True).json()["data"]


def load_installed_challenges():
    s = generate_session()
    return s.get("/api/v1/challenges?view=admin", json=True).json()["data"]


def sync_challenge(challenge, ignore=[]):
    data = {
        "name": challenge["name"],
        "category": challenge["category"],
        "description": challenge["description"],
        "type": challenge.get("type", "standard"),
        "value": int(challenge["value"]) if challenge["value"] else challenge["value"],
        **challenge.get("extra", {}),
    }

    # Some challenge types (e.g. dynamic) override value.
    # We can't send it to CTFd because we don't know the current value
    if challenge["value"] is None:
        del challenge["value"]

    if challenge.get("attempts") and "attempts" not in ignore:
        data["max_attempts"] = challenge.get("attempts")

    if challenge.get("connection_info") and "connection_info" not in ignore:
        data["connection_info"] = challenge.get("connection_info")

    data["state"] = "hidden"

    installed_challenges = load_installed_challenges()
    for c in installed_challenges:
        if c["name"] == challenge["name"]:
            challenge_id = c["id"]
            break
    else:
        return

    s = generate_session()

    original_challenge = s.get(f"/api/v1/challenges/{challenge_id}", json=data).json()[
        "data"
    ]

    r = s.patch(f"/api/v1/challenges/{challenge_id}", json=data)
    r.raise_for_status()

    # Create new flags
    if challenge.get("flags") and "flags" not in ignore:
        # Delete existing flags
        current_flags = s.get(f"/api/v1/flags", json=data).json()["data"]
        for flag in current_flags:
            if flag["challenge_id"] == challenge_id:
                flag_id = flag["id"]
                r = s.delete(f"/api/v1/flags/{flag_id}", json=True)
                r.raise_for_status()
        for flag in challenge["flags"]:
            if type(flag) == str:
                data = {"content": flag, "type": "static", "challenge_id": challenge_id}
                r = s.post(f"/api/v1/flags", json=data)
                r.raise_for_status()
            elif type(flag) == dict:
                flag["challenge_id"] = challenge_id
                r = s.post(f"/api/v1/flags", json=flag)
                r.raise_for_status()

    # Update topics
    if challenge.get("topics") and "topics" not in ignore:
        # Delete existing challenge topics
        current_topics = s.get(
            f"/api/v1/challenges/{challenge_id}/topics", json=""
        ).json()["data"]
        for topic in current_topics:
            topic_id = topic["id"]
            r = s.delete(
                f"/api/v1/topics?type=challenge&target_id={topic_id}", json=True
            )
            r.raise_for_status()
        # Add new challenge topics
        for topic in challenge["topics"]:
            r = s.post(
                f"/api/v1/topics",
                json={
                    "value": topic,
                    "type": "challenge",
                    "challenge_id": challenge_id,
                },
            )
            r.raise_for_status()

    # Update tags
    if challenge.get("tags") and "tags" not in ignore:
        # Delete existing tags
        current_tags = s.get(f"/api/v1/tags", json=data).json()["data"]
        for tag in current_tags:
            if tag["challenge_id"] == challenge_id:
                tag_id = tag["id"]
                r = s.delete(f"/api/v1/tags/{tag_id}", json=True)
                r.raise_for_status()
        for tag in challenge["tags"]:
            r = s.post(
                f"/api/v1/tags", json={"challenge_id": challenge_id, "value": tag}
            )
            r.raise_for_status()

    # Upload files
    if challenge.get("files") and "files" not in ignore:
        # Delete existing files
        all_current_files = s.get(f"/api/v1/files?type=challenge", json=data).json()[
            "data"
        ]
        for f in all_current_files:
            for used_file in original_challenge["files"]:
                if f["location"] in used_file:
                    file_id = f["id"]
                    r = s.delete(f"/api/v1/files/{file_id}", json=True)
                    r.raise_for_status()
        files = []
        for f in challenge["files"]:
            file_path = Path(challenge.directory, f)
            if file_path.exists():
                file_object = ("file", file_path.open(mode="rb"))
                files.append(file_object)
            else:
                click.secho(f"File {file_path} was not found", fg="red")
                raise Exception(f"File {file_path} was not found")

        data = {"challenge_id": challenge_id, "type": "challenge"}
        # Specifically use data= here instead of json= to send multipart/form-data
        r = s.post(f"/api/v1/files", files=files, data=data)
        r.raise_for_status()

    # Create hints
    if challenge.get("hints") and "hints" not in ignore:
        # Delete existing hints
        current_hints = s.get(f"/api/v1/hints", json=data).json()["data"]
        for hint in current_hints:
            if hint["challenge_id"] == challenge_id:
                hint_id = hint["id"]
                r = s.delete(f"/api/v1/hints/{hint_id}", json=True)
                r.raise_for_status()

        for hint in challenge["hints"]:
            if type(hint) == str:
                data = {"content": hint, "cost": 0, "challenge_id": challenge_id}
            else:
                data = {
                    "content": hint["content"],
                    "cost": hint["cost"],
                    "challenge_id": challenge_id,
                }

            r = s.post(f"/api/v1/hints", json=data)
            r.raise_for_status()

    # Update requirements
    if challenge.get("requirements") and "requirements" not in ignore:
        installed_challenges = load_installed_challenges()
        required_challenges = []
        for r in challenge["requirements"]:
            if type(r) == str:
                for c in installed_challenges:
                    if c["name"] == r:
                        required_challenges.append(c["id"])
            elif type(r) == int:
                required_challenges.append(r)

        required_challenges = list(set(required_challenges))
        data = {"requirements": {"prerequisites": required_challenges}}
        r = s.patch(f"/api/v1/challenges/{challenge_id}", json=data)
        r.raise_for_status()

    # Unhide challenge depending upon the value of "state" in spec
    if "state" not in ignore:
        data = {"state": "visible"}
        if challenge.get("state"):
            if challenge["state"] in ["hidden", "visible"]:
                data["state"] = challenge["state"]

        r = s.patch(f"/api/v1/challenges/{challenge_id}", json=data)
        r.raise_for_status()


def create_challenge(challenge, ignore=[]):
    data = {
        "name": challenge["name"],
        "category": challenge["category"],
        "description": challenge["description"],
        "type": challenge.get("type", "standard"),
        "value": int(challenge["value"]) if challenge["value"] else challenge["value"],
        **challenge.get("extra", {}),
    }

    # Some challenge types (e.g. dynamic) override value.
    # We can't send it to CTFd because we don't know the current value
    if challenge["value"] is None:
        del challenge["value"]

    if challenge.get("attempts") and "attempts" not in ignore:
        data["max_attempts"] = challenge.get("attempts")

    if challenge.get("connection_info") and "connection_info" not in ignore:
        data["connection_info"] = challenge.get("connection_info")

    s = generate_session()

    r = s.post("/api/v1/challenges", json=data)
    r.raise_for_status()

    challenge_data = r.json()
    challenge_id = challenge_data["data"]["id"]

    # Create flags
    if challenge.get("flags") and "flags" not in ignore:
        for flag in challenge["flags"]:
            if type(flag) == str:
                data = {"content": flag, "type": "static", "challenge_id": challenge_id}
                r = s.post(f"/api/v1/flags", json=data)
                r.raise_for_status()
            elif type(flag) == dict:
                flag["challenge"] = challenge_id
                r = s.post(f"/api/v1/flags", json=flag)
                r.raise_for_status()

    # Create topics
    if challenge.get("topics") and "topics" not in ignore:
        for topic in challenge["topics"]:
            r = s.post(
                f"/api/v1/topics",
                json={
                    "value": topic,
                    "type": "challenge",
                    "challenge_id": challenge_id,
                },
            )
            r.raise_for_status()

    # Create tags
    if challenge.get("tags") and "tags" not in ignore:
        for tag in challenge["tags"]:
            r = s.post(
                f"/api/v1/tags", json={"challenge_id": challenge_id, "value": tag}
            )
            r.raise_for_status()

    # Upload files
    if challenge.get("files") and "files" not in ignore:
        files = []
        for f in challenge["files"]:
            file_path = Path(challenge.directory, f)
            if file_path.exists():
                file_object = ("file", file_path.open(mode="rb"))
                files.append(file_object)
            else:
                click.secho(f"File {file_path} was not found", fg="red")
                raise Exception(f"File {file_path} was not found")

        data = {"challenge_id": challenge_id, "type": "challenge"}
        # Specifically use data= here instead of json= to send multipart/form-data
        r = s.post(f"/api/v1/files", files=files, data=data)
        r.raise_for_status()

    # Add hints
    if challenge.get("hints") and "hints" not in ignore:
        for hint in challenge["hints"]:
            if type(hint) == str:
                data = {"content": hint, "cost": 0, "challenge_id": challenge_id}
            else:
                data = {
                    "content": hint["content"],
                    "cost": hint["cost"],
                    "challenge_id": challenge_id,
                }

            r = s.post(f"/api/v1/hints", json=data)
            r.raise_for_status()

    # Add requirements
    if challenge.get("requirements") and "requirements" not in ignore:
        installed_challenges = load_installed_challenges()
        required_challenges = []
        for r in challenge["requirements"]:
            if type(r) == str:
                for c in installed_challenges:
                    if c["name"] == r:
                        required_challenges.append(c["id"])
            elif type(r) == int:
                required_challenges.append(r)

        required_challenges = list(set(required_challenges))
        data = {"requirements": {"prerequisites": required_challenges}}
        r = s.patch(f"/api/v1/challenges/{challenge_id}", json=data)
        r.raise_for_status()

    # Set challenge state
    if challenge.get("state") and "state" not in ignore:
        data = {"state": "hidden"}
        if challenge["state"] in ["hidden", "visible"]:
            data["state"] = challenge["state"]

        r = s.patch(f"/api/v1/challenges/{challenge_id}", json=data)
        r.raise_for_status()


def lint_challenge(path):
    try:
        challenge = load_challenge(path)
    except yaml.YAMLError as e:
        click.secho(f"Error parsing challenge.yml: {e}", fg="red")
        exit(1)

    required_fields = ["name", "author", "category", "description", "value"]
    errors = []
    for field in required_fields:
        if field == "value" and challenge.get("type") == "dynamic":
            pass
        else:
            if challenge.get(field) is None:
                errors.append(field)

    if len(errors) > 0:
        print("Missing fields: ", ", ".join(errors))
        exit(1)

    # Check that the image field and Dockerfile match
    if (Path(path).parent / "Dockerfile").is_file() and challenge.get("image") != ".":
        print("Dockerfile exists but image field does not point to it")
        exit(1)

    # Check that Dockerfile exists and is EXPOSE'ing a port
    if challenge.get("image") == ".":
        try:
            dockerfile = (Path(path).parent / "Dockerfile").open().read()
        except FileNotFoundError:
            print("Dockerfile specified in 'image' field but no Dockerfile found")
            exit(1)

        if "EXPOSE" not in dockerfile:
            print("Dockerfile missing EXPOSE")
            exit(1)

        # Check Dockerfile with hadolint
        proc = subprocess.run(
            ["docker", "run", "--rm", "-i", "hadolint/hadolint"],
            input=dockerfile.encode(),
        )
        if proc.returncode != 0:
            print("Hadolint found Dockerfile lint issues, please resolve")
            exit(1)

    # Check that all files exists
    files = challenge.get("files", [])
    errored = False
    for f in files:
        fpath = Path(path).parent / f
        if fpath.is_file() is False:
            print(f"File {f} specified but not found at {fpath.absolute()}")
            errored = True
    if errored:
        exit(1)

    # Check that files don't have a flag in them
    files = challenge.get("files", [])
    errored = False
    for f in files:
        fpath = Path(path).parent / f
        for s in strings(fpath):
            # TODO make flag format customizable
            if "flag" in s:
                print(
                    f"Potential flag {s} found in distributed file {fpath.absolute()}"
                )
                errored = True
    if errored:
        exit(1)

    exit(0)

def get_challenge_details(challenge_id):
    s = generate_session()
    r = s.get(f"/api/v1/challenges/{challenge_id}")
    r.raise_for_status()
    challenge = r.json()["data"]
    # Remove non-yaml fields

    challenge.pop("id")
    challenge.pop("type_data")
    challenge.pop("view")

    # Add flags
    r = s.get(f"/api/v1/challenges/{challenge_id}/flags")
    r.raise_for_status()
    flags = r.json()["data"]
    challenge["flags"] = [f["content"] if f["type"] == "static" and f["data"] == None else { "content": f["content"], "type": f["type"], "data": f["data"] } for f in flags]

    # Add tags
    r = s.get(f"/api/v1/challenges/{challenge_id}/tags")
    r.raise_for_status()
    tags = r.json()["data"]
    challenge["tags"] = [t["value"] for t in tags]

    # Add hints
    r = s.get(f"/api/v1/challenges/{challenge_id}/hints")
    r.raise_for_status()
    hints = r.json()["data"]
    challenge["hints"] = [{ "content": h["content"], "cost": h["cost"] } if h["cost"] > 0 else h["content"] for h in hints]

    # Add topics
    r = s.get(f"/api/v1/challenges/{challenge_id}/topics")
    r.raise_for_status()
    topics = r.json()["data"]
    challenge["topics"] = [t["value"] for t in topics]

    # Add requirements
    r = s.get(f"/api/v1/challenges/{challenge_id}/requirements")
    r.raise_for_status()
    requirements = r.json()["data"].get("prerequisites", [])
    if len(requirements) > 0:
        # Prefer challenge names over IDs
        r = s.get("/api/v1/challenges")
        r.raise_for_status()
        challenges = r.json()["data"]
        challenge["requirements"] = [c["name"] for c in challenges if c["id"] in requirements]

    return challenge

def verify_challenge(challenge, verify_contents=False):
    """
    Verify that the challenge.yml matches the remote challenge if one exists with the same name
    """
    s = generate_session()

    installed_challenges = load_installed_challenges()
    for c in installed_challenges:
        if c["name"] == challenge["name"]:
            challenge_id = c["id"]
            break
    else:
        return
    
    remote_challenge = get_challenge_details(challenge_id)
    for key in remote_challenge:
        # Special validation needed for files
        if key == "files":
            # Get base file name of challenge files
            local_files = {Path(f).name : f for f in challenge[key]}

            for f in remote_challenge["files"]:
                # Get base file name
                f_base = f.split("/")[-1]
                if f_base not in local_files:
                    raise Exception(f"Remote challenge has file {f_base} that is not present locally")
                else:
                    if verify_contents:
                        # Download remote file and compare contents
                        req = s.get(f"files/{f}")
                        req.raise_for_status()
                        remote_file = req.content
                        local_file = Path(challenge.directory, local_files[f_base]).read_bytes()
                        if remote_file != local_file:
                            raise Exception(f"Remote challenge file {f_base} does not match local file")

        if key not in challenge:
            raise Exception(f"Missing field {key} in challenge.yml")
            
        if challenge[key] != remote_challenge[key]:
            raise Exception(f"Field {key} in challenge.yml does not match remote challenge")

def pull_challenge(challenge, create_files=False):
    """
    Rewrite challenge.yml and local files to match the remote challenge
    """
    s = generate_session()
    installed_challenges = load_installed_challenges()
    for c in installed_challenges:
        if c["name"] == challenge["name"]:
            challenge_id = c["id"]
            break
    else:
        return
    
    details = get_challenge_details(challenge_id)
    local_files = {Path(f).name : f for f in challenge["files"]}
    # Update files
    remote_files = details["files"]
    for i, f in enumerate(remote_files):
        # Get base file name
        f_base = f.split("/")[-1]
        if f_base not in local_files and create_files:
            # Download remote file and save locally
            req = s.get(f"files/{f}")
            req.raise_for_status()
            Path(challenge.directory, f_base).write_bytes(req.content)
            details["files"].append(f_base)

        else:
            # Download remote file and replace local file
            req = s.get(f"files/{f}")
            req.raise_for_status()
            remote_file = req.content
            local_file = Path(challenge.directory, local_files[f_base])
            local_file.write_bytes(remote_file)
            details["files"][i] = local_files[f_base]

    # Update challenge.yml
    with open(Path(challenge.directory, "challenge.yml"), "w") as f:
        yaml.dump(details, f)