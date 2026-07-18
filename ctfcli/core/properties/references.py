import click

from ctfcli.core.properties.base import Property, PropertyContext


class RequirementsProperty(Property):
    key = "requirements"
    newline_before = True
    op_order = 60

    def is_default(self, value) -> bool:
        return value == [] or value == {"prerequisites": [], "anonymize": False}

    def create(self, ctx: PropertyContext) -> None:
        if ctx.challenge.get("requirements") and not self.ignored(ctx):
            self._set(ctx)

    def sync(self, ctx: PropertyContext) -> None:
        self.create(ctx)

    def _set(self, ctx: PropertyContext) -> None:
        requirements = ctx.challenge["requirements"]
        required_challenges = []
        anonymize = False
        if type(requirements) == dict:
            rc = requirements.get("prerequisites", [])
            anonymize = requirements.get("anonymize", False)
        else:
            rc = requirements

        for required_challenge in rc:
            if type(required_challenge) == str:
                # requirement by name
                # find the challenge id from installed challenges
                found = False
                for remote_challenge in ctx.installed_challenges():
                    if remote_challenge["name"] == required_challenge:
                        required_challenges.append(remote_challenge["id"])
                        found = True
                        break
                if found is False:
                    click.secho(
                        f'Challenge id cannot be found. Skipping invalid requirement name "{required_challenge}".',
                        fg="yellow",
                    )

            elif type(required_challenge) == int:
                # requirement by challenge id
                # trust it and use it directly
                required_challenges.append(required_challenge)

        required_challenge_ids = list(set(required_challenges))

        if ctx.challenge_id in required_challenge_ids:
            click.secho(
                "Challenge cannot require itself. Skipping invalid requirement.",
                fg="yellow",
            )
            required_challenges.remove(ctx.challenge_id)
        required_challenges.sort()

        requirements_payload = {
            "requirements": {
                "prerequisites": required_challenges,
                "anonymize": anonymize,
            }
        }
        r = ctx.api.patch(f"/api/v1/challenges/{ctx.challenge_id}", json=requirements_payload)
        r.raise_for_status()

    def pull(self, ctx: PropertyContext, remote_data: dict):
        r = ctx.api.get(f"/api/v1/challenges/{ctx.challenge_id}/requirements")
        r.raise_for_status()
        prerequisites = (r.json().get("data") or {}).get("prerequisites", [])

        requirements = {"prerequisites": [], "anonymize": False}
        if len(prerequisites) > 0:
            # Prefer challenge names over IDs
            requirements["prerequisites"] = [c["name"] for c in ctx.installed_challenges() if c["id"] in prerequisites]

        requirements["anonymize"] = (r.json().get("data") or {}).get("anonymize", False)
        return requirements

    # Compare challenge requirements, will resolve all IDs to names
    def matches(self, ctx: PropertyContext, local, remote) -> bool:
        if local == remote:
            return True

        if type(local) == dict:
            local_prerequisites = local["prerequisites"]
            local_anonymize = local.get("anonymize", False)
        else:
            local_prerequisites = local
            local_anonymize = False

        def normalize_requirements(requirements):
            normalized = []
            for requirement in requirements:
                if type(requirement) == int:
                    for remote_challenge in ctx.installed_challenges():
                        if remote_challenge["id"] == requirement:
                            normalized.append(remote_challenge["name"])
                            break
                else:
                    normalized.append(requirement)

            return normalized

        nr1 = normalize_requirements(local_prerequisites)
        nr1.sort()
        nr2 = normalize_requirements(remote["prerequisites"])
        nr2.sort()
        return nr1 == nr2 and local_anonymize == remote["anonymize"]


class NextProperty(Property):
    key = "next"
    op_order = 70

    def is_default(self, value) -> bool:
        return value is None

    def create(self, ctx: PropertyContext) -> None:
        if not self.ignored(ctx):
            self._set(ctx)

    def sync(self, ctx: PropertyContext) -> None:
        self.create(ctx)

    def _set(self, ctx: PropertyContext) -> None:
        _next = ctx.challenge.get("next", None)

        if type(_next) == str:
            # next by name
            # find the challenge id from installed challenges
            resolved_next = None
            for remote_challenge in ctx.installed_challenges():
                if remote_challenge["name"] == _next:
                    resolved_next = remote_challenge["id"]
                    break
            if resolved_next is None:
                click.secho(
                    "Challenge cannot find next challenge. Maybe it is invalid name or id. It will be cleared.",
                    fg="yellow",
                )
            _next = resolved_next
        elif type(_next) == int and _next > 0:
            # next by challenge id
            # trust it and use it directly
            pass
        else:
            _next = None

        if ctx.challenge_id == _next:
            click.secho(
                "Challenge cannot set next challenge itself. Skipping invalid next challenge.",
                fg="yellow",
            )
            _next = None

        next_payload = {"next_id": _next}
        r = ctx.api.patch(f"/api/v1/challenges/{ctx.challenge_id}", json=next_payload)
        r.raise_for_status()

    def pull(self, ctx: PropertyContext, remote_data: dict):
        nid = remote_data.get("next_id")
        if not nid:
            return None

        # Prefer the challenge name over the ID
        r = ctx.api.get(f"/api/v1/challenges/{nid}")
        r.raise_for_status()
        return (r.json().get("data") or {}).get("name", None)

    # Compare next challenges, will resolve all IDs to names
    def matches(self, ctx: PropertyContext, local, remote) -> bool:
        def normalize_next(value):
            if type(value) == int:
                if value > 0:
                    remote_challenge = ctx.challenge.load_installed_challenge(value)
                    if remote_challenge["id"] == value:
                        return remote_challenge["name"]
                return None

            return value

        return normalize_next(local) == normalize_next(remote)


class ModuleProperty(Property):
    key = "module"
    op_order = 80

    def is_default(self, value) -> bool:
        return value is None

    def create(self, ctx: PropertyContext) -> None:
        if ctx.challenge.get("module") and not self.ignored(ctx):
            self._set(ctx)

    def sync(self, ctx: PropertyContext) -> None:
        # Only touch the module assignment if the key is present in challenge.yml -
        # an explicit "module: null" removes the challenge from its module,
        # while an absent key leaves the remote assignment untouched
        if "module" in ctx.challenge and not self.ignored(ctx):
            self._set(ctx)

    def _set(self, ctx: PropertyContext) -> None:
        module = ctx.challenge.get("module", None)

        if module is None or module == "":
            # explicit null (or empty) module - remove the challenge from its module
            module_id = None
        else:
            # module is always treated as a name - coerce so a numeric name
            # (e.g. "2024", which YAML loads as an int) is handled as a string
            module = str(module)

            # find the module id from the modules installed on the remote
            module_id = None
            r = ctx.api.get("/api/v1/modules")
            r.raise_for_status()
            remote_modules = r.json()["data"]
            for remote_module in remote_modules:
                if remote_module["name"] == module:
                    module_id = remote_module["id"]
                    break

            # the module does not exist yet - create it
            if module_id is None:
                r = ctx.api.post("/api/v1/modules", json={"name": module})
                r.raise_for_status()
                module_id = r.json()["data"]["id"]
                click.secho(
                    f'Created module "{module}". '
                    "Remember to assign audiences to it in the admin panel if you want to restrict access.",
                    fg="yellow",
                )

        module_payload = {"module_id": module_id}
        r = ctx.api.patch(f"/api/v1/challenges/{ctx.challenge_id}", json=module_payload)
        r.raise_for_status()

    def pull(self, ctx: PropertyContext, remote_data: dict):
        module_id = remote_data.get("module_id")
        if not module_id:
            return None

        # Prefer the module name over the ID
        r = ctx.api.get(f"/api/v1/modules/{module_id}")
        r.raise_for_status()
        return (r.json().get("data") or {}).get("name", None)

    # Compare module assignments - modules are always referenced by name, so a
    # numeric name (loaded from YAML as an int) is coerced to a string to compare
    def matches(self, ctx: PropertyContext, local, remote) -> bool:
        def normalize_module(value):
            return None if value is None else str(value)

        return normalize_module(local) == normalize_module(remote)
