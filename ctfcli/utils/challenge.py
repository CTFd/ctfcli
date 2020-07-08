import yaml

import click

from .config import generate_session


def load_challenge(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f.read())
    except FileNotFoundError:
        click.secho(f"No challenge.yml was found in {path}", fg="red")
        return


def load_installed_challenges():
    s = generate_session()
    return s.get("/api/v1/challenges?view=admin", json=True).json()["data"]


def sync_challenge(challenge):
    data = {
        "name": challenge["name"],
        "category": challenge["category"],
        "description": challenge["description"],
        "type": challenge.get("type", "standard"),
        "value": int(challenge["value"]),
    }
    if challenge.get("attempts"):
        data["max_attempts"] = challenge.get("attempts")

    if data["type"] == "dynamic":
        data["minimum"] = challenge.get("minimum")
        data["decay"] = challenge.get("decay")
        data["initial"] = data["value"]
        del data["value"]

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

    # Delete existing flags
    current_flags = s.get(f"/api/v1/flags", json=data).json()["data"]
    for flag in current_flags:
        if flag["challenge_id"] == challenge_id:
            flag_id = flag["id"]
            r = s.delete(f"/api/v1/flags/{flag_id}", json=True)
            r.raise_for_status()

    # Create new flags
    if challenge.get("flags"):
        for flag in challenge["flags"]:
            if type(flag) == str:
                data = {"content": flag, "type": "static", "challenge": challenge_id}
                r = s.post(f"/api/v1/flags", json=data)
                r.raise_for_status()

    # Delete existing tags
    current_tags = s.get(f"/api/v1/tags", json=data).json()["data"]
    for tag in current_tags:
        if tag["challenge_id"] == challenge_id:
            tag_id = tag["id"]
            r = s.delete(f"/api/v1/tags/{tag_id}", json=True)
            r.raise_for_status()

    # Update tags
    if challenge.get("tags"):
        for tag in challenge["tags"]:
            r = s.post(f"/api/v1/tags", json={"challenge": challenge_id, "value": tag})
            r.raise_for_status()

    # Delete existing files
    all_current_files = s.get(f"/api/v1/files?type=challenge", json=data).json()["data"]
    for f in all_current_files:
        for used_file in original_challenge["files"]:
            if f["location"] in used_file:
                file_id = f["id"]
                r = s.delete(f"/api/v1/files/{file_id}", json=True)
                r.raise_for_status()

    # Upload files
    if challenge.get("files"):
        files = []
        for f in challenge["files"]:
            files.append(("file", open(f, "rb")))

        data = {"challenge": challenge_id, "type": "challenge"}
        # Specifically use data= here instead of json= to send multipart/form-data
        r = s.post(f"/api/v1/files", files=files, data=data)
        r.raise_for_status()

    # Delete existing hints
    current_hints = s.get(f"/api/v1/hints", json=data).json()["data"]
    for hint in current_hints:
        if hint["challenge_id"] == challenge_id:
            hint_id = hint["id"]
            r = s.delete(f"/api/v1/hints/{hint_id}", json=True)
            r.raise_for_status()

    # Create hints
    if challenge.get("hints"):
        for hint in challenge["hints"]:
            if type(hint) == str:
                data = {"content": hint, "cost": 0, "challenge": challenge_id}
            else:
                data = {
                    "content": hint["content"],
                    "cost": hint["cost"],
                    "challenge": challenge_id,
                }

            r = s.post(f"/api/v1/hints", json=data)
            r.raise_for_status()

    # Update requirements
    if challenge.get("requirements"):
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
    data = {"state": "hidden"}
    if challenge.get("state"):
        if challenge["state"] in ["hidden", "visible"]:
            data["state"] = challenge["state"]

    r = s.patch(f"/api/v1/challenges/{challenge_id}", json=data)
    r.raise_for_status()


def create_challenge(challenge):
    data = {
        "name": challenge["name"],
        "category": challenge["category"],
        "description": challenge["description"],
        "type": challenge.get("type", "standard"),
        "value": int(challenge["value"]),
    }
    if challenge.get("attempts"):
        data["max_attempts"] = challenge.get("attempts")

    # If challenge type is dynamic, get minimum score for challenge, and the decay (amount)
    # of solves before it reaches the minimum score
    if data["type"] == "dynamic":
        data["minimum"] = challenge.get("minimum")
        data["decay"] = challenge.get("decay")

    s = generate_session()

    r = s.post("/api/v1/challenges", json=data)
    r.raise_for_status()

    challenge_data = r.json()
    challenge_id = challenge_data["data"]["id"]

    # Create flags
    if challenge.get("flags"):
        for flag in challenge["flags"]:
            if type(flag) == str:
                data = {"content": flag, "type": "static", "challenge": challenge_id}
                r = s.post(f"/api/v1/flags", json=data)
                r.raise_for_status()

    # Create tags
    if challenge.get("tags"):
        for tag in challenge["tags"]:
            r = s.post(f"/api/v1/tags", json={"challenge": challenge_id, "value": tag})
            r.raise_for_status()

    # Upload files
    if challenge.get("files"):
        files = []
        for f in challenge["files"]:
            files.append(("file", open(f, "rb")))

        data = {"challenge": challenge_id, "type": "challenge"}
        # Specifically use data= here instead of json= to send multipart/form-data
        r = s.post(f"/api/v1/files", files=files, data=data)
        r.raise_for_status()

    # Add hints
    if challenge.get("hints"):
        for hint in challenge["hints"]:
            if type(hint) == str:
                data = {"content": hint, "cost": 0, "challenge": challenge_id}
            else:
                data = {
                    "content": hint["content"],
                    "cost": hint["cost"],
                    "challenge": challenge_id,
                }

            r = s.post(f"/api/v1/hints", json=data)
            r.raise_for_status()

    # Add requirements
    if challenge.get("requirements"):
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
    if challenge.get("state"):
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
        if challenge.get(field) is None:
            errors.append(field)

    if len(errors) > 0:
        print("Missing fields: ", ", ".join(errors))
        exit(1)

    exit(0)
